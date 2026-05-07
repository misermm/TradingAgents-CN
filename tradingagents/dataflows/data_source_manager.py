#!/usr/bin/env python3
"""
数据源管理器
统一管理中国股票数据源的选择和切换，支持Tushare、AKShare、BaoStock等
"""

import os
import time
import json
import threading
from typing import Dict, List, Optional, Any
from enum import Enum
import warnings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')
warnings.filterwarnings('ignore')

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()

# 导入统一数据源编码
from tradingagents.constants import DataSourceCode


class ChinaDataSource(Enum):
    """
    中国股票数据源枚举

    注意：这个枚举与 tradingagents.constants.DataSourceCode 保持同步
    值使用统一的数据源编码
    """
    MONGODB = DataSourceCode.MONGODB  # MongoDB数据库缓存（最高优先级）
    TUSHARE = DataSourceCode.TUSHARE
    AKSHARE = DataSourceCode.AKSHARE
    BAOSTOCK = DataSourceCode.BAOSTOCK
    SINA = DataSourceCode.SINA          # 新浪财经
    EASTMONEY = DataSourceCode.EASTMONEY  # 东方财富直接API


# ==================== 数据源能力矩阵 ====================
# 声明每个数据源支持的数据类型，用于智能降级选择
PROVIDER_CAPABILITIES = {
    ChinaDataSource.TUSHARE: {
        "realtime_quotes",    # 实时行情
        "historical_data",    # 历史数据
        "financial_data",     # 财务数据
        "fundamentals",       # 基本面数据
        "stock_info",         # 股票基本信息
    },
    ChinaDataSource.AKSHARE: {
        "realtime_quotes",
        "historical_data",
        "financial_data",
        "fundamentals",
        "stock_info",
        "news",               # 新闻资讯
    },
    ChinaDataSource.BAOSTOCK: {
        "historical_data",
        "financial_data",
        "fundamentals",
        "stock_info",
    },
    ChinaDataSource.SINA: {
        "realtime_quotes",    # A股实时行情
        "historical_data",    # A股历史K线
        "hk_quotes",          # 港股实时行情
    },
    ChinaDataSource.EASTMONEY: {
        "realtime_quotes",    # A股实时行情
        "batch_quotes",       # 批量行情
        "financial_data",     # 财务数据
        "industry_data",      # 行业数据
    },
}


class USDataSource(Enum):
    """
    美股数据源枚举

    注意：这个枚举与 tradingagents.constants.DataSourceCode 保持同步
    值使用统一的数据源编码
    """
    MONGODB = DataSourceCode.MONGODB  # MongoDB数据库缓存（最高优先级）
    YFINANCE = DataSourceCode.YFINANCE  # Yahoo Finance（免费，股票价格和技术指标）
    ALPHA_VANTAGE = DataSourceCode.ALPHA_VANTAGE  # Alpha Vantage（基本面和新闻）
    FINNHUB = DataSourceCode.FINNHUB  # Finnhub（备用数据源）





class SourceHealth:
    """数据源健康状态记录"""
    __slots__ = ('consecutive_failures', 'last_failure_time', 'circuit_state', 'cooldown_until', 'total_calls', 'total_failures')

    def __init__(self):
        self.consecutive_failures: int = 0
        self.last_failure_time: Optional[float] = None
        self.circuit_state: str = "closed"
        self.cooldown_until: float = 0.0
        self.total_calls: int = 0
        self.total_failures: int = 0


class SourceHealthTracker:
    """
    数据源级别健康跟踪器
    跨请求跟踪数据源健康状态，连续3次失败后熔断，冷却30s后半开探测
    与HTTP级别CircuitBreaker互补
    """

    FAILURE_THRESHOLD = 3
    COOLDOWN_SECONDS = 30.0

    def __init__(self):
        self._health: Dict[str, SourceHealth] = {}

    def _get_health(self, source_name: str) -> SourceHealth:
        if source_name not in self._health:
            self._health[source_name] = SourceHealth()
        return self._health[source_name]

    def is_available(self, source_name: str) -> bool:
        health = self._get_health(source_name)
        now = time.monotonic()
        if health.circuit_state == "closed":
            return True
        if health.circuit_state == "open":
            if now >= health.cooldown_until:
                health.circuit_state = "half_open"
                return True
            return False
        if health.circuit_state == "half_open":
            return True
        return True

    def record_success(self, source_name: str):
        health = self._get_health(source_name)
        health.consecutive_failures = 0
        health.circuit_state = "closed"
        health.total_calls += 1

    def record_failure(self, source_name: str):
        health = self._get_health(source_name)
        health.consecutive_failures += 1
        health.total_calls += 1
        health.total_failures += 1
        health.last_failure_time = time.monotonic()

        if health.circuit_state == "half_open":
            health.circuit_state = "open"
            health.cooldown_until = time.monotonic() + self.COOLDOWN_SECONDS
            logger.warning(f"🔴 [健康跟踪] {source_name} 半开探测失败，重新熔断 {self.COOLDOWN_SECONDS}s")
        elif health.consecutive_failures >= self.FAILURE_THRESHOLD:
            health.circuit_state = "open"
            health.cooldown_until = time.monotonic() + self.COOLDOWN_SECONDS
            logger.warning(f"🔴 [健康跟踪] {source_name} 连续失败 {health.consecutive_failures} 次，熔断 {self.COOLDOWN_SECONDS}s")

    def get_available_sources(self, source_list: list) -> list:
        return [s for s in source_list if self.is_available(self._source_key(s))]

    def get_status(self) -> Dict[str, Dict]:
        result = {}
        for name, health in self._health.items():
            result[name] = {
                "state": health.circuit_state,
                "consecutive_failures": health.consecutive_failures,
                "total_calls": health.total_calls,
                "total_failures": health.total_failures,
            }
        return result

    @staticmethod
    def _source_key(source) -> str:
        if hasattr(source, 'value'):
            return source.value
        return str(source)


class DataSnapshotManager:
    """
    本地数据快照管理器
    
    功能：
    - 存储路径：data_cache/snapshots/{market}/{symbol}/
    - 快照格式：JSON，包含 data/fetched_at/completeness_score/source
    - 读取优先级：实时数据 > 未过期快照 > 过期快照(标注时效)
    - 快照有效期：行情1天，基本面30天，财务报表90天
    """
    
    # 数据类型对应的有效期（天）
    TTL_DAYS = {
        "quotes": 1,          # 行情数据：1天
        "stock_data": 1,      # 股票行情：1天
        "fundamentals": 30,   # 基本面：30天
        "financial": 90,      # 财务报表：90天
        "news": 1,            # 新闻：1天
        "stock_info": 30,     # 股票基本信息：30天
    }
    
    def __init__(self, base_dir: str = None):
        """
        初始化快照管理器
        
        Args:
            base_dir: 快照存储根目录，默认为项目根目录下的 data_cache/snapshots
        """
        if base_dir is None:
            # 默认路径：项目根目录/data_cache/snapshots
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dir = os.path.join(project_root, "data_cache", "snapshots")
        self.base_dir = base_dir
        logger.info(f"📦 数据快照管理器初始化，存储路径: {base_dir}")
    
    def _get_snapshot_dir(self, market: str, symbol: str) -> str:
        """获取快照存储目录"""
        snapshot_dir = os.path.join(self.base_dir, market, symbol)
        os.makedirs(snapshot_dir, exist_ok=True)
        return snapshot_dir
    
    def _get_snapshot_path(self, market: str, symbol: str, data_type: str) -> str:
        """获取快照文件路径"""
        snapshot_dir = self._get_snapshot_dir(market, symbol)
        return os.path.join(snapshot_dir, f"{data_type}.json")
    
    def _detect_market(self, symbol: str) -> str:
        """根据股票代码检测市场"""
        if not symbol:
            return "unknown"
        symbol = str(symbol).strip()
        if symbol.startswith(('60', '68', '90')):
            return "sh"
        elif symbol.startswith(('00', '30', '20')):
            return "sz"
        elif symbol.startswith(('8', '4')):
            return "bj"
        else:
            return "cn"
    
    def _calculate_completeness(self, data: str) -> float:
        """
        计算数据完整度分数
        
        Args:
            data: 数据文本
            
        Returns:
            完整度分数 (0.0 - 1.0)
        """
        if not data:
            return 0.0
        
        score = 0.5  # 基础分：有数据
        
        # 检查关键字段是否存在
        key_indicators = ['PE', 'PB', 'ROE', '市值', '换手率', 'MA5', 'MACD', 'RSI']
        found = sum(1 for indicator in key_indicators if indicator in data)
        score += (found / len(key_indicators)) * 0.5
        
        return min(1.0, score)
    
    def save_snapshot(self, symbol: str, data_type: str, data: str, source: str = "unknown") -> bool:
        """
        保存数据快照
        
        Args:
            symbol: 股票代码
            data_type: 数据类型 (quotes/stock_data/fundamentals/financial/news/stock_info)
            data: 数据文本
            source: 数据来源
            
        Returns:
            是否保存成功
        """
        try:
            market = self._detect_market(symbol)
            snapshot_path = self._get_snapshot_path(market, symbol, data_type)
            
            snapshot = {
                "data": data,
                "fetched_at": datetime.now().isoformat(),
                "completeness_score": self._calculate_completeness(data),
                "source": source,
                "data_type": data_type,
                "symbol": symbol,
                "market": market,
            }
            
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"📦 [快照保存] {symbol} {data_type} 快照已保存 (完整度: {snapshot['completeness_score']:.2f})")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ [快照保存] 保存 {symbol} {data_type} 快照失败: {e}")
            return False
    
    def load_snapshot(self, symbol: str, data_type: str, allow_expired: bool = True) -> Optional[Dict[str, Any]]:
        """
        加载数据快照
        
        读取优先级：实时数据 > 未过期快照 > 过期快照(标注时效)
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            allow_expired: 是否允许返回过期快照
            
        Returns:
            快照字典，包含 data/fetched_at/completeness_score/source/is_expired 等字段
            如果快照不存在则返回None
        """
        try:
            market = self._detect_market(symbol)
            snapshot_path = self._get_snapshot_path(market, symbol, data_type)
            
            if not os.path.exists(snapshot_path):
                return None
            
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
            
            # 检查是否过期
            fetched_at = datetime.fromisoformat(snapshot.get("fetched_at", "2000-01-01"))
            ttl_days = self.TTL_DAYS.get(data_type, 1)
            is_expired = (datetime.now() - fetched_at) > timedelta(days=ttl_days)
            
            snapshot["is_expired"] = is_expired
            
            # 如果不允许过期且已过期，返回None
            if is_expired and not allow_expired:
                logger.debug(f"📦 [快照加载] {symbol} {data_type} 快照已过期，跳过")
                return None
            
            if is_expired:
                logger.debug(f"📦 [快照加载] {symbol} {data_type} 快照已过期但允许使用（标注时效）")
            else:
                logger.debug(f"📦 [快照加载] {symbol} {data_type} 快照命中（未过期）")
            
            return snapshot
            
        except Exception as e:
            logger.warning(f"⚠️ [快照加载] 加载 {symbol} {data_type} 快照失败: {e}")
            return None
    
    def get_fresh_snapshot(self, symbol: str, data_type: str) -> Optional[str]:
        """
        获取未过期的快照数据（便捷方法）
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            
        Returns:
            快照数据文本，如果不存在或已过期则返回None
        """
        snapshot = self.load_snapshot(symbol, data_type, allow_expired=False)
        if snapshot and not snapshot.get("is_expired", True):
            return snapshot.get("data")
        return None
    
    def get_any_snapshot(self, symbol: str, data_type: str) -> Optional[str]:
        """
        获取任意可用的快照数据（包括过期的，便捷方法）
        
        过期快照会在数据前添加时效警告
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            
        Returns:
            快照数据文本，如果不存在则返回None
        """
        snapshot = self.load_snapshot(symbol, data_type, allow_expired=True)
        if snapshot:
            data = snapshot.get("data", "")
            if snapshot.get("is_expired", False):
                fetched_at = snapshot.get("fetched_at", "未知")
                data = f"⚠️ 以下数据来自过期快照（获取时间: {fetched_at}），可能已不具时效性\n\n{data}"
            return data
        return None
    
    def cleanup_expired(self, data_type: str = None) -> int:
        """
        清理过期快照
        
        Args:
            data_type: 指定数据类型，为None则清理所有类型
            
        Returns:
            清理的快照数量
        """
        cleaned = 0
        try:
            if not os.path.exists(self.base_dir):
                return 0
            
            for market_dir in os.listdir(self.base_dir):
                market_path = os.path.join(self.base_dir, market_dir)
                if not os.path.isdir(market_path):
                    continue
                
                for symbol_dir in os.listdir(market_path):
                    symbol_path = os.path.join(market_path, symbol_dir)
                    if not os.path.isdir(symbol_path):
                        continue
                    
                    for filename in os.listdir(symbol_path):
                        if not filename.endswith('.json'):
                            continue
                        
                        file_type = filename.replace('.json', '')
                        if data_type and file_type != data_type:
                            continue
                        
                        filepath = os.path.join(symbol_path, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                snapshot = json.load(f)
                            
                            fetched_at = datetime.fromisoformat(snapshot.get("fetched_at", "2000-01-01"))
                            ttl_days = self.TTL_DAYS.get(file_type, 1)
                            
                            if (datetime.now() - fetched_at) > timedelta(days=ttl_days * 3):
                                # 过期3倍时间以上的快照才删除
                                os.remove(filepath)
                                cleaned += 1
                        except Exception:
                            continue
            
            if cleaned > 0:
                logger.info(f"📦 [快照清理] 已清理 {cleaned} 个过期快照")
            
        except Exception as e:
            logger.warning(f"⚠️ [快照清理] 清理过期快照失败: {e}")
        
        return cleaned


class DataSourceManager:
    """数据源管理器"""

    def __init__(self):
        """初始化数据源管理器"""
        # 检查是否启用MongoDB缓存
        self.use_mongodb_cache = self._check_mongodb_enabled()

        # 数据源健康跟踪器
        self._health_tracker = SourceHealthTracker()

        # 本地数据快照管理器
        self._snapshot_manager = DataSnapshotManager()

        self.default_source = self._get_default_source()
        self.available_sources = self._check_available_sources()
        self.current_source = self.default_source

        # 初始化统一缓存管理器
        self.cache_manager = None
        self.cache_enabled = False
        try:
            from .cache import get_cache
            self.cache_manager = get_cache()
            self.cache_enabled = True
            logger.info(f"✅ 统一缓存管理器已启用")
        except Exception as e:
            logger.warning(f"⚠️ 统一缓存管理器初始化失败: {e}")

        logger.info(f"📊 数据源管理器初始化完成")
        logger.info(f"   MongoDB缓存: {'✅ 已启用' if self.use_mongodb_cache else '❌ 未启用'}")
        logger.info(f"   统一缓存: {'✅ 已启用' if self.cache_enabled else '❌ 未启用'}")
        logger.info(f"   数据快照: ✅ 已启用")
        logger.info(f"   默认数据源: {self.default_source.value}")
        logger.info(f"   可用数据源: {[s.value for s in self.available_sources]}")

    def _check_mongodb_enabled(self) -> bool:
        """检查是否启用MongoDB缓存"""
        from tradingagents.config.runtime_settings import use_app_cache_enabled
        return use_app_cache_enabled()

    def _get_data_source_priority_order(self, symbol: Optional[str] = None) -> List[ChinaDataSource]:
        """
        从数据库获取数据源优先级顺序（用于降级）

        Args:
            symbol: 股票代码，用于识别市场类型（A股/美股/港股）

        Returns:
            按优先级排序的数据源列表（不包含MongoDB，因为MongoDB是最高优先级）
        """
        # 🔥 识别市场类型
        market_category = self._identify_market_category(symbol)

        try:
            # 🔥 从数据库读取数据源配置（使用同步客户端）
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            config_collection = db.system_configs

            # 获取最新的激活配置
            config_data = config_collection.find_one(
                {"is_active": True},
                sort=[("version", -1)]
            )

            if config_data and config_data.get('data_source_configs'):
                data_source_configs = config_data.get('data_source_configs', [])

                # 🔥 过滤出启用的数据源，并按市场分类过滤
                enabled_sources = []
                for ds in data_source_configs:
                    if not ds.get('enabled', True):
                        continue

                    # 检查数据源是否属于当前市场分类
                    market_categories = ds.get('market_categories', [])
                    if market_categories and market_category:
                        # 如果数据源配置了市场分类，只选择匹配的数据源
                        if market_category not in market_categories:
                            continue

                    enabled_sources.append(ds)

                # 按优先级排序（数字越大优先级越高）
                enabled_sources.sort(key=lambda x: x.get('priority', 0), reverse=True)

                # 转换为 ChinaDataSource 枚举（使用统一编码）
                source_mapping = {
                    DataSourceCode.TUSHARE: ChinaDataSource.TUSHARE,
                    DataSourceCode.AKSHARE: ChinaDataSource.AKSHARE,
                    DataSourceCode.BAOSTOCK: ChinaDataSource.BAOSTOCK,
                    DataSourceCode.SINA: ChinaDataSource.SINA,
                    DataSourceCode.EASTMONEY: ChinaDataSource.EASTMONEY,
                }

                result = []
                for ds in enabled_sources:
                    ds_type = ds.get('type', '').lower()
                    if ds_type in source_mapping:
                        source = source_mapping[ds_type]
                        # 排除 MongoDB（MongoDB 是最高优先级，不参与降级）
                        if source != ChinaDataSource.MONGODB and source in self.available_sources:
                            result.append(source)

                if result:
                    logger.info(f"✅ [数据源优先级] 市场={market_category or '全部'}, 从数据库读取: {[s.value for s in result]}")
                    return result
                else:
                    logger.warning(f"⚠️ [数据源优先级] 市场={market_category or '全部'}, 数据库配置中没有可用的数据源，使用默认顺序")
            else:
                logger.warning("⚠️ [数据源优先级] 数据库中没有数据源配置，使用默认顺序")
        except Exception as e:
            logger.warning(f"⚠️ [数据源优先级] 从数据库读取失败: {e}，使用默认顺序")

        # 🔥 回退到默认顺序（兼容性）
        # 默认顺序：AKShare > Tushare > 新浪财经 > 东方财富直连 > BaoStock
        default_order = [
            ChinaDataSource.AKSHARE,
            ChinaDataSource.TUSHARE,
            ChinaDataSource.SINA,
            ChinaDataSource.EASTMONEY,
            ChinaDataSource.BAOSTOCK,
        ]
        # 只返回可用的数据源
        return [s for s in default_order if s in self.available_sources]

    def _identify_market_category(self, symbol: Optional[str]) -> Optional[str]:
        """
        识别股票代码所属的市场分类

        Args:
            symbol: 股票代码

        Returns:
            市场分类ID（a_shares/us_stocks/hk_stocks），如果无法识别则返回None
        """
        if not symbol:
            return None

        try:
            from tradingagents.utils.stock_utils import StockUtils, StockMarket

            market = StockUtils.identify_stock_market(symbol)

            # 映射到市场分类ID
            market_mapping = {
                StockMarket.CHINA_A: 'a_shares',
                StockMarket.US: 'us_stocks',
                StockMarket.HONG_KONG: 'hk_stocks',
            }

            category = market_mapping.get(market)
            if category:
                logger.debug(f"🔍 [市场识别] {symbol} → {category}")
            return category
        except Exception as e:
            logger.warning(f"⚠️ [市场识别] 识别失败: {e}")
            return None

    def _get_default_source(self) -> ChinaDataSource:
        """获取默认数据源"""
        # 如果启用MongoDB缓存，MongoDB作为最高优先级数据源
        if self.use_mongodb_cache:
            return ChinaDataSource.MONGODB

        # 从环境变量获取，默认使用AKShare作为第一优先级数据源
        env_source = os.getenv('DEFAULT_CHINA_DATA_SOURCE', DataSourceCode.AKSHARE).lower()

        # 映射到枚举（使用统一编码）
        source_mapping = {
            DataSourceCode.TUSHARE: ChinaDataSource.TUSHARE,
            DataSourceCode.AKSHARE: ChinaDataSource.AKSHARE,
            DataSourceCode.BAOSTOCK: ChinaDataSource.BAOSTOCK,
            DataSourceCode.SINA: ChinaDataSource.SINA,
            DataSourceCode.EASTMONEY: ChinaDataSource.EASTMONEY,
        }

        return source_mapping.get(env_source, ChinaDataSource.AKSHARE)

    # ==================== Tushare数据接口 ====================

    def get_china_stock_data_tushare(self, symbol: str, start_date: str, end_date: str) -> str:
        """
        使用Tushare获取中国A股历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            str: 格式化的股票数据报告
        """
        # 临时切换到Tushare数据源
        original_source = self.current_source
        self.current_source = ChinaDataSource.TUSHARE

        try:
            result = self._get_tushare_data(symbol, start_date, end_date)
            return result
        finally:
            # 恢复原始数据源
            self.current_source = original_source

    def get_fundamentals_data(self, symbol: str) -> str:
        """
        获取基本面数据，支持多数据源和自动降级
        优先级：缓存 → MongoDB → Tushare → AKShare → 生成分析

        缓存优先读取流程：
        查本地缓存 → 命中且未过期 → 直接使用
                        ↓ 未命中或过期
                实时获取 → 成功 → 更新缓存 → 使用
                            ↓ 失败
                        使用本地快照(标注时效)

        Args:
            symbol: 股票代码

        Returns:
            str: 基本面分析报告
        """
        # ===== Phase 2.2: 缓存优先读取 =====
        cached_result = self._try_cache_first_fundamentals(symbol)
        if cached_result is not None:
            return cached_result

        logger.info(f"📊 [数据来源: {self.current_source.value}] 开始获取基本面数据: {symbol}",
                   extra={
                       'symbol': symbol,
                       'data_source': self.current_source.value,
                       'event_type': 'fundamentals_fetch_start'
                   })

        start_time = time.time()

        try:
            # 根据数据源调用相应的获取方法
            if self.current_source == ChinaDataSource.MONGODB:
                result = self._get_mongodb_fundamentals(symbol)
            elif self.current_source == ChinaDataSource.TUSHARE:
                result = self._get_tushare_fundamentals(symbol)
            elif self.current_source == ChinaDataSource.AKSHARE:
                result = self._get_akshare_fundamentals(symbol)
            else:
                # 其他数据源暂不支持基本面数据，生成基本分析
                result = self._generate_fundamentals_analysis(symbol)

            # 检查结果
            duration = time.time() - start_time
            result_length = len(result) if result else 0

            if result and "❌" not in result:
                # 基本面数据补全：检测缺失字段并从备选接口补全
                missing_fields = self._detect_missing_fields(result)
                if missing_fields:
                    logger.info(f"📊 [数据补全] 基本面检测到 {symbol} 缺失字段: {missing_fields}")
                    result = self._complete_missing_fields(result, symbol, missing_fields)

                # 数据溯源摘要：附加到结果末尾
                try:
                    from tradingagents.dataflows.data_quality_engine import get_data_quality_engine
                    engine = get_data_quality_engine()
                    provenance_note = (
                        f"\n\n--- 数据溯源 ---\n"
                        f"主数据源: {self.current_source.value}\n"
                        f"补全字段: {', '.join(missing_fields) if missing_fields else '无'}\n"
                        f"获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    result += provenance_note
                except Exception as e:
                    logger.debug(f"数据溯源摘要生成失败: {e}")

                logger.info(f"✅ [数据来源: {self.current_source.value}] 成功获取基本面数据: {symbol} ({result_length}字符, 耗时{duration:.2f}秒)",
                           extra={
                               'symbol': symbol,
                               'data_source': self.current_source.value,
                               'duration': duration,
                               'result_length': result_length,
                               'event_type': 'fundamentals_fetch_success'
                           })
                # 保存基本面数据快照
                self._snapshot_manager.save_snapshot(symbol, "fundamentals", result, source=self.current_source.value)
                return result
            else:
                logger.warning(f"⚠️ [数据来源: {self.current_source.value}失败] 基本面数据质量异常，尝试降级: {symbol}",
                              extra={
                                  'symbol': symbol,
                                  'data_source': self.current_source.value,
                                  'event_type': 'fundamentals_fetch_fallback'
                              })
                return self._try_fallback_fundamentals(symbol)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ [数据来源: {self.current_source.value}异常] 获取基本面数据失败: {symbol} - {e}",
                        extra={
                            'symbol': symbol,
                            'data_source': self.current_source.value,
                            'duration': duration,
                            'error': str(e),
                            'event_type': 'fundamentals_fetch_exception'
                        }, exc_info=True)
            return self._try_fallback_fundamentals(symbol)

    def get_china_stock_fundamentals_tushare(self, symbol: str) -> str:
        """
        使用Tushare获取中国股票基本面数据（兼容旧接口）

        Args:
            symbol: 股票代码

        Returns:
            str: 基本面分析报告
        """
        # 重定向到统一接口
        return self._get_tushare_fundamentals(symbol)

    def get_news_data(self, symbol: str = None, hours_back: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取新闻数据的统一接口，支持多数据源和自动降级
        优先级：MongoDB → Tushare → AKShare

        Args:
            symbol: 股票代码，为空则获取市场新闻
            hours_back: 回溯小时数
            limit: 返回数量限制

        Returns:
            List[Dict]: 新闻数据列表
        """
        logger.info(f"📰 [数据来源: {self.current_source.value}] 开始获取新闻数据: {symbol or '市场新闻'}, 回溯{hours_back}小时",
                   extra={
                       'symbol': symbol,
                       'hours_back': hours_back,
                       'limit': limit,
                       'data_source': self.current_source.value,
                       'event_type': 'news_fetch_start'
                   })

        start_time = time.time()

        try:
            # 根据数据源调用相应的获取方法
            if self.current_source == ChinaDataSource.MONGODB:
                result = self._get_mongodb_news(symbol, hours_back, limit)
            elif self.current_source == ChinaDataSource.TUSHARE:
                result = self._get_tushare_news(symbol, hours_back, limit)
            elif self.current_source == ChinaDataSource.AKSHARE:
                result = self._get_akshare_news(symbol, hours_back, limit)
            else:
                # 其他数据源暂不支持新闻数据
                logger.warning(f"⚠️ 数据源 {self.current_source.value} 不支持新闻数据")
                result = []

            # 检查结果
            duration = time.time() - start_time
            result_count = len(result) if result else 0

            if result and result_count > 0:
                logger.info(f"✅ [数据来源: {self.current_source.value}] 成功获取新闻数据: {symbol or '市场新闻'} ({result_count}条, 耗时{duration:.2f}秒)",
                           extra={
                               'symbol': symbol,
                               'data_source': self.current_source.value,
                               'news_count': result_count,
                               'duration': duration,
                               'event_type': 'news_fetch_success'
                           })
                return result
            else:
                logger.warning(f"⚠️ [数据来源: {self.current_source.value}] 未获取到新闻数据: {symbol or '市场新闻'}，尝试降级",
                              extra={
                                  'symbol': symbol,
                                  'data_source': self.current_source.value,
                                  'duration': duration,
                                  'event_type': 'news_fetch_fallback'
                              })
                return self._try_fallback_news(symbol, hours_back, limit)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ [数据来源: {self.current_source.value}异常] 获取新闻数据失败: {symbol or '市场新闻'} - {e}",
                        extra={
                            'symbol': symbol,
                            'data_source': self.current_source.value,
                            'duration': duration,
                            'error': str(e),
                            'event_type': 'news_fetch_exception'
                        }, exc_info=True)
            return self._try_fallback_news(symbol, hours_back, limit)

    def _check_available_sources(self) -> List[ChinaDataSource]:
        """
        检查可用的数据源

        检查逻辑：
        1. 检查依赖包是否安装（技术可用性）
        2. 检查数据库配置中是否启用（业务可用性）

        Returns:
            可用且已启用的数据源列表
        """
        available = []

        # 🔥 从数据库读取数据源配置，获取启用状态
        enabled_sources_in_db = set()
        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            config_collection = db.system_configs

            # 获取最新的激活配置
            config_data = config_collection.find_one(
                {"is_active": True},
                sort=[("version", -1)]
            )

            if config_data and config_data.get('data_source_configs'):
                data_source_configs = config_data.get('data_source_configs', [])

                # 提取已启用的数据源类型
                for ds in data_source_configs:
                    if ds.get('enabled', True):
                        ds_type = ds.get('type', '').lower()
                        enabled_sources_in_db.add(ds_type)

                logger.info(f"✅ [数据源配置] 从数据库读取到已启用的数据源: {enabled_sources_in_db}")

                # 免费数据源自动启用：新浪财经和东方财富直连作为免费备选，自动加入
                free_auto_enable = {'sina', 'eastmoney'}
                for free_src in free_auto_enable:
                    if free_src not in enabled_sources_in_db:
                        enabled_sources_in_db.add(free_src)
                        logger.info(f"✅ [数据源配置] 免费数据源 {free_src} 自动启用")
            else:
                logger.warning("⚠️ [数据源配置] 数据库中没有数据源配置，将检查所有已安装的数据源")
                # 如果数据库中没有配置，默认所有数据源都启用
                enabled_sources_in_db = {'mongodb', 'tushare', 'akshare', 'baostock', 'sina', 'eastmoney'}
        except Exception as e:
            logger.warning(f"⚠️ [数据源配置] 从数据库读取失败: {e}，将检查所有已安装的数据源")
            # 如果读取失败，默认所有数据源都启用
            enabled_sources_in_db = {'mongodb', 'tushare', 'akshare', 'baostock', 'sina', 'eastmoney'}

        # 检查MongoDB（最高优先级）
        if self.use_mongodb_cache and 'mongodb' in enabled_sources_in_db:
            try:
                from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
                adapter = get_mongodb_cache_adapter()
                if adapter.use_app_cache and adapter.db is not None:
                    available.append(ChinaDataSource.MONGODB)
                    logger.info("✅ MongoDB数据源可用且已启用（最高优先级）")
                else:
                    logger.warning("⚠️ MongoDB数据源不可用: 数据库未连接")
            except Exception as e:
                logger.warning(f"⚠️ MongoDB数据源不可用: {e}")
        elif self.use_mongodb_cache and 'mongodb' not in enabled_sources_in_db:
            logger.info("ℹ️ MongoDB数据源已在数据库中禁用")

        # 从数据库读取数据源配置
        datasource_configs = self._get_datasource_configs_from_db()

        # 检查Tushare
        if 'tushare' in enabled_sources_in_db:
            try:
                import tushare as ts
                # 优先从数据库配置读取 API Key，其次从环境变量读取
                token = datasource_configs.get('tushare', {}).get('api_key') or os.getenv('TUSHARE_TOKEN')
                if token:
                    available.append(ChinaDataSource.TUSHARE)
                    source = "数据库配置" if datasource_configs.get('tushare', {}).get('api_key') else "环境变量"
                    logger.info(f"✅ Tushare数据源可用且已启用 (API Key来源: {source})")
                else:
                    logger.warning("⚠️ Tushare数据源不可用: API Key未配置（数据库和环境变量均未找到）")
            except ImportError:
                logger.warning("⚠️ Tushare数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ Tushare数据源已在数据库中禁用")

        # 检查AKShare
        if 'akshare' in enabled_sources_in_db:
            try:
                import akshare as ak
                available.append(ChinaDataSource.AKSHARE)
                logger.info("✅ AKShare数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ AKShare数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ AKShare数据源已在数据库中禁用")

        # 检查BaoStock
        if 'baostock' in enabled_sources_in_db:
            try:
                import baostock as bs
                available.append(ChinaDataSource.BAOSTOCK)
                logger.info(f"✅ BaoStock数据源可用且已启用")
            except ImportError:
                logger.warning(f"⚠️ BaoStock数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ BaoStock数据源已在数据库中禁用")

        # 检查新浪财经
        if 'sina' in enabled_sources_in_db:
            try:
                from tradingagents.dataflows.providers.china.sina_finance import SinaFinanceProvider
                import requests  # 新浪财经依赖requests库
                available.append(ChinaDataSource.SINA)
                logger.info("✅ 新浪财经数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ 新浪财经数据源不可用: 依赖库未安装")
        else:
            logger.info("ℹ️ 新浪财经数据源已在数据库中禁用")

        # 检查东方财富直接API
        if 'eastmoney' in enabled_sources_in_db:
            try:
                from tradingagents.dataflows.providers.china.eastmoney_direct import EastMoneyDirectProvider
                # 东方财富直接API依赖requests或curl_cffi，至少有一个即可
                try:
                    import requests
                except ImportError:
                    from curl_cffi import requests  # noqa: F401
                available.append(ChinaDataSource.EASTMONEY)
                logger.info("✅ 东方财富直接API数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ 东方财富直接API数据源不可用: 依赖库未安装")
        else:
            logger.info("ℹ️ 东方财富直接API数据源已在数据库中禁用")

        # TDX (通达信) 已移除
        # 不再检查和支持 TDX 数据源

        return available

    def _get_datasource_configs_from_db(self) -> dict:
        try:
            from tradingagents.config.config_manager import get_config_manager
            config_manager = get_config_manager()
            configs = config_manager.get_datasource_configs()
            if configs:
                result = {}
                for ds_config in configs:
                    name = ds_config.get('name', '').lower()
                    result[name] = {
                        'api_key': ds_config.get('api_key', ''),
                        'api_secret': ds_config.get('api_secret', ''),
                        'config_params': ds_config.get('config_params', {})
                    }
                return result
        except Exception as e:
            logger.debug(f"ConfigManager不可用: {e}")

        try:
            from app.services.config_service import ConfigService
            service = ConfigService()
            configs = service.get_datasource_configs()
            if configs:
                result = {}
                for ds_config in configs:
                    name = ds_config.get('name', '').lower()
                    result[name] = {
                        'api_key': ds_config.get('api_key', ''),
                        'api_secret': ds_config.get('api_secret', ''),
                        'config_params': ds_config.get('config_params', {})
                    }
                return result
        except (ImportError, Exception) as e:
            logger.debug(f"ConfigService不可用: {e}")

        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            config = db.system_configs.find_one({"is_active": True})
            if not config:
                return {}
            datasource_configs = config.get('data_source_configs', [])
            result = {}
            for ds_config in datasource_configs:
                name = ds_config.get('name', '').lower()
                result[name] = {
                    'api_key': ds_config.get('api_key', ''),
                    'api_secret': ds_config.get('api_secret', ''),
                    'config_params': ds_config.get('config_params', {})
                }
            return result
        except Exception as e:
            logger.warning(f"⚠️ 从数据库读取数据源配置失败: {e}")
            return {}

    def get_current_source(self) -> ChinaDataSource:
        """获取当前数据源"""
        return self.current_source

    def set_current_source(self, source: ChinaDataSource) -> bool:
        """设置当前数据源"""
        if source in self.available_sources:
            self.current_source = source
            logger.info(f"✅ 数据源已切换到: {source.value}")
            return True
        else:
            logger.error(f"❌ 数据源不可用: {source.value}")
            return False

    def get_data_adapter(self):
        """获取当前数据源的适配器"""
        if self.current_source == ChinaDataSource.MONGODB:
            return self._get_mongodb_adapter()
        elif self.current_source == ChinaDataSource.TUSHARE:
            return self._get_tushare_adapter()
        elif self.current_source == ChinaDataSource.AKSHARE:
            return self._get_akshare_adapter()
        elif self.current_source == ChinaDataSource.BAOSTOCK:
            return self._get_baostock_adapter()
        # TDX 已移除
        else:
            raise ValueError(f"不支持的数据源: {self.current_source}")

    def _get_mongodb_adapter(self):
        """获取MongoDB适配器"""
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
            return get_mongodb_cache_adapter()
        except ImportError as e:
            logger.error(f"❌ MongoDB适配器导入失败: {e}")
            return None

    def _get_tushare_adapter(self):
        """获取Tushare提供器（原adapter已废弃，现在直接使用provider）"""
        try:
            from .providers.china.tushare import get_tushare_provider
            return get_tushare_provider()
        except ImportError as e:
            logger.error(f"❌ Tushare提供器导入失败: {e}")
            return None

    def _get_akshare_adapter(self):
        """获取AKShare适配器"""
        try:
            from .providers.china.akshare import get_akshare_provider
            return get_akshare_provider()
        except ImportError as e:
            logger.error(f"❌ AKShare适配器导入失败: {e}")
            return None

    def _get_baostock_adapter(self):
        """获取BaoStock适配器"""
        try:
            from .providers.china.baostock import get_baostock_provider
            return get_baostock_provider()
        except ImportError as e:
            logger.error(f"❌ BaoStock适配器导入失败: {e}")
            return None

    # TDX 适配器已移除
    # def _get_tdx_adapter(self):
    #     """获取TDX适配器 (已移除)"""
    #     logger.error(f"❌ TDX数据源已不再支持")
    #     return None

    def _get_cached_text(self, symbol: str, data_type: str, start_date: str = None, end_date: str = None, data_source: str = "default") -> Optional[str]:
        """
        从缓存获取文本格式数据（用于AKShare/BaoStock等返回字符串的数据源）

        Args:
            symbol: 股票代码
            data_type: 数据类型 (stock_data/fundamentals/news)
            start_date: 开始日期
            end_date: 结束日期
            data_source: 数据源名称

        Returns:
            str: 缓存的文本数据，如果没有则返回None
        """
        if not self.cache_enabled or not self.cache_manager:
            return None

        try:
            from .cache.cache_config import generate_cache_key, detect_market, get_ttl_seconds

            market = detect_market(symbol)
            cache_key = generate_cache_key(
                market=market, data_type=data_type, symbol=symbol,
                start_date=start_date or "", end_date=end_date or "",
                data_source=data_source,
            )

            cached = self.cache_manager.load_stock_data(cache_key)
            if cached is not None:
                if isinstance(cached, str) and "❌" not in cached:
                    logger.debug(f"📦 [缓存命中] {symbol} {data_type} 数据")
                    return cached
                if hasattr(cached, 'empty') and not cached.empty:
                    logger.debug(f"📦 [缓存命中] {symbol} {data_type} DataFrame数据")
                    return None
        except Exception as e:
            logger.debug(f"缓存读取跳过: {e}")

        return None

    def _save_cached_text(self, symbol: str, data_type: str, data: str, start_date: str = None, end_date: str = None, data_source: str = "default"):
        """
        保存文本格式数据到缓存

        Args:
            symbol: 股票代码
            data_type: 数据类型
            data: 文本数据
            start_date: 开始日期
            end_date: 结束日期
            data_source: 数据源名称
        """
        if not self.cache_enabled or not self.cache_manager:
            return

        try:
            if data and "❌" not in data:
                from .cache.cache_config import generate_cache_key, detect_market

                market = detect_market(symbol)
                cache_key = generate_cache_key(
                    market=market, data_type=data_type, symbol=symbol,
                    start_date=start_date or "", end_date=end_date or "",
                    data_source=data_source,
                )
                self.cache_manager.save_stock_data(symbol, data, start_date, end_date)
                logger.debug(f"📦 [缓存写入] {symbol} {data_type} 数据")
        except Exception as e:
            logger.debug(f"缓存写入跳过: {e}")

    # ==================== Phase 2.2: 缓存优先读取 ====================

    def _try_cache_first_stock_data(self, symbol: str, start_date: str = None,
                                     end_date: str = None, period: str = "daily") -> Optional[str]:
        """
        缓存优先读取股票数据

        流程：查本地缓存 → 命中且未过期 → 直接使用
                           ↓ 未命中或过期
                   实时获取 → 成功 → 更新缓存 → 使用
                               ↓ 失败
                           使用本地快照(标注时效)

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期

        Returns:
            str: 缓存命中的数据，未命中返回None（由调用方继续原有流程）
        """
        try:
            from .cache.cache_config import generate_cache_key, detect_market, get_ttl_seconds

            market = detect_market(symbol)
            cache_key = generate_cache_key(
                market=market, data_type="stock_data", symbol=symbol,
                start_date=start_date or "", end_date=end_date or "",
                period=period,
            )

            # 1. 尝试从统一缓存读取
            cached = self._get_cached_text(symbol, "stock_data", start_date, end_date)
            if cached and "❌" not in cached:
                logger.info(f"✅ [缓存命中] {symbol} stock_data")
                return cached

            # 2. 尝试从本地快照读取（兜底）
            snapshot_data = self._snapshot_manager.get_any_snapshot(symbol, "stock_data")
            if snapshot_data:
                logger.info(f"📦 [快照兜底] {symbol} stock_data（使用本地快照，标注时效）")
                return snapshot_data

        except Exception as e:
            logger.debug(f"缓存优先读取跳过: {e}")

        # 缓存未命中，返回None，由调用方继续原有实时获取流程
        return None

    # ==================== Phase 2.3: 增量更新 ====================

    def _try_incremental_stock_data(self, symbol: str, start_date: str = None,
                                     end_date: str = None, period: str = "daily") -> Optional[str]:
        """
        增量更新股票历史K线数据

        当缓存中有历史数据但未覆盖到请求的结束日期时，只请求缺失部分。
        注意：增量更新只适用于历史K线数据，不适用于实时行情。

        流程：
        1. 从缓存获取已有的DataFrame数据
        2. 如果缓存数据的最后日期已覆盖请求的结束日期 → 直接格式化返回
        3. 如果缓存数据的最后日期未覆盖结束日期 → 只请求缺失部分并合并
        4. 缓存中无DataFrame数据 → 返回None，由调用方走全量获取流程

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期

        Returns:
            str: 增量更新后的格式化数据，无法增量更新时返回None
        """
        # 增量更新仅适用于日线级别的历史K线数据
        if period != "daily":
            return None

        # 必须有结束日期才能判断是否需要增量更新
        if not end_date:
            return None

        try:
            # 从缓存获取已有的DataFrame数据
            cached_df = self._get_cached_data(symbol, start_date, end_date, max_age_hours=168)  # 7天内均可
            if cached_df is None or cached_df.empty:
                return None

            # 确保缓存数据有日期列
            if 'date' not in cached_df.columns:
                return None

            # 获取缓存数据的最后日期
            cached_df['date'] = pd.to_datetime(cached_df['date'])
            last_cached_date = cached_df['date'].max()
            end_date_ts = pd.Timestamp(end_date)

            # 如果缓存数据已覆盖到请求的结束日期，直接格式化返回
            if last_cached_date >= end_date_ts:
                logger.info(f"✅ [增量更新] {symbol} 缓存数据已覆盖到 {end_date}，无需增量获取")
                # 过滤出请求日期范围内的数据
                start_date_ts = pd.Timestamp(start_date) if start_date else None
                if start_date_ts:
                    filtered_df = cached_df[cached_df['date'] >= start_date_ts]
                else:
                    filtered_df = cached_df

                if not filtered_df.empty:
                    stock_name = f'股票{symbol}'
                    if 'name' in filtered_df.columns and not filtered_df['name'].empty:
                        stock_name = filtered_df['name'].iloc[0]
                    result = self._format_stock_data_response(
                        filtered_df, symbol, stock_name,
                        start_date or str(filtered_df['date'].min().date()),
                        end_date
                    )
                    return result
                return None

            # 缓存数据未覆盖到结束日期，需要增量获取
            incremental_start = (last_cached_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            logger.info(f"🔄 [增量更新] {symbol} 缓存数据截止到 {last_cached_date.date()}，增量获取 {incremental_start} 至 {end_date}")

            # 获取增量数据
            new_data = self._fetch_incremental_data(symbol, incremental_start, end_date, period)
            if new_data is not None and not new_data.empty:
                # 合并数据
                new_data['date'] = pd.to_datetime(new_data['date'])
                merged = pd.concat([cached_df, new_data]).drop_duplicates(subset=['date'])
                merged = merged.sort_values('date').reset_index(drop=True)

                # 保存合并后的数据到缓存
                self._save_to_cache(symbol, merged, start_date, end_date)

                # 格式化返回
                start_date_ts = pd.Timestamp(start_date) if start_date else None
                if start_date_ts:
                    filtered_df = merged[merged['date'] >= start_date_ts]
                else:
                    filtered_df = merged

                if not filtered_df.empty:
                    stock_name = f'股票{symbol}'
                    if 'name' in filtered_df.columns and not filtered_df['name'].empty:
                        stock_name = filtered_df['name'].iloc[0]
                    result = self._format_stock_data_response(
                        filtered_df, symbol, stock_name,
                        start_date or str(filtered_df['date'].min().date()),
                        end_date
                    )
                    logger.info(f"✅ [增量更新] {symbol} 增量合并成功: 原有{len(cached_df)}条 + 新增{len(new_data)}条 = 合并{len(merged)}条")
                    return result
            else:
                # 增量获取失败，返回缓存中的部分数据（标注时效）
                logger.warning(f"⚠️ [增量更新] {symbol} 增量获取失败，使用缓存中的部分数据（截止到 {last_cached_date.date()}）")
                start_date_ts = pd.Timestamp(start_date) if start_date else None
                if start_date_ts:
                    filtered_df = cached_df[cached_df['date'] >= start_date_ts]
                else:
                    filtered_df = cached_df

                if not filtered_df.empty:
                    stock_name = f'股票{symbol}'
                    if 'name' in filtered_df.columns and not filtered_df['name'].empty:
                        stock_name = filtered_df['name'].iloc[0]
                    result = self._format_stock_data_response(
                        filtered_df, symbol, stock_name,
                        start_date or str(filtered_df['date'].min().date()),
                        str(last_cached_date.date())
                    )
                    # 标注数据时效
                    result = f"⚠️ 以下数据截止到 {last_cached_date.date()}，未覆盖到请求的结束日期 {end_date}\n\n{result}"
                    return result

        except Exception as e:
            logger.debug(f"增量更新跳过: {e}")

        return None

    def _fetch_incremental_data(self, symbol: str, start_date: str, end_date: str,
                                 period: str = "daily") -> Optional[pd.DataFrame]:
        """
        获取增量数据（仅获取缺失日期范围的数据）

        按数据源优先级尝试获取，不触发完整的降级流程

        Args:
            symbol: 股票代码
            start_date: 增量开始日期
            end_date: 增量结束日期
            period: 数据周期

        Returns:
            pd.DataFrame: 增量数据，获取失败返回None
        """
        try:
            # 尝试从MongoDB获取
            if self.use_mongodb_cache:
                from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
                adapter = get_mongodb_cache_adapter()
                df = adapter.get_historical_data(symbol, start_date, end_date, period=period)
                if df is not None and not df.empty:
                    logger.info(f"📊 [增量更新-MongoDB] {symbol} 获取到 {len(df)}条增量数据")
                    return df

            # 尝试从各数据源获取
            from tradingagents.dataflows.cache.cache_config import detect_market
            market = detect_market(symbol)

            # A股数据源
            if market == "cn":
                for fetch_func in [self._fetch_from_akshare, self._fetch_from_tushare, self._fetch_from_baostock]:
                    try:
                        df = fetch_func(symbol, start_date, end_date, period)
                        if df is not None and not df.empty:
                            return df
                    except Exception:
                        continue
            # 美股数据源
            elif market == "us":
                try:
                    df = self._fetch_from_yfinance(symbol, start_date, end_date, period)
                    if df is not None and not df.empty:
                        return df
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"增量数据获取失败: {e}")

        return None

    def _fetch_from_akshare(self, symbol: str, start_date: str, end_date: str,
                             period: str = "daily") -> Optional[pd.DataFrame]:
        """从AKShare获取增量数据"""
        try:
            from .providers.china.akshare import get_akshare_provider
            import asyncio
            provider = get_akshare_provider()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            df = loop.run_until_complete(provider.get_historical_data(symbol, start_date, end_date, period))
            if df is not None and not df.empty:
                logger.debug(f"📊 [增量更新-AKShare] {symbol} 获取到 {len(df)}条")
            return df
        except Exception as e:
            logger.debug(f"AKShare增量获取失败: {e}")
            return None

    def _fetch_from_tushare(self, symbol: str, start_date: str, end_date: str,
                             period: str = "daily") -> Optional[pd.DataFrame]:
        """从Tushare获取增量数据"""
        try:
            from .providers.china.tushare import get_tushare_provider
            import asyncio
            provider = get_tushare_provider()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            df = loop.run_until_complete(provider.get_historical_data(symbol, start_date, end_date))
            if df is not None and not df.empty:
                logger.debug(f"📊 [增量更新-Tushare] {symbol} 获取到 {len(df)}条")
            return df
        except Exception as e:
            logger.debug(f"Tushare增量获取失败: {e}")
            return None

    def _fetch_from_baostock(self, symbol: str, start_date: str, end_date: str,
                              period: str = "daily") -> Optional[pd.DataFrame]:
        """从BaoStock获取增量数据"""
        try:
            from .providers.china.baostock import get_baostock_provider
            import asyncio
            provider = get_baostock_provider()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            df = loop.run_until_complete(provider.get_historical_data(symbol, start_date, end_date, period))
            if df is not None and not df.empty:
                logger.debug(f"📊 [增量更新-BaoStock] {symbol} 获取到 {len(df)}条")
            return df
        except Exception as e:
            logger.debug(f"BaoStock增量获取失败: {e}")
            return None

    def _fetch_from_yfinance(self, symbol: str, start_date: str, end_date: str,
                              period: str = "daily") -> Optional[pd.DataFrame]:
        """从yfinance获取增量数据（美股）"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol.upper())
            # yfinance 使用 yyyy-mm-dd 格式
            start_fmt = start_date.replace("", "") if len(start_date) == 8 else start_date
            end_fmt = end_date.replace("", "") if len(end_date) == 8 else end_date
            # 如果是 YYYYMMDD 格式，转换为 YYYY-MM-DD
            if len(start_fmt) == 8 and start_fmt.isdigit():
                start_fmt = f"{start_fmt[:4]}-{start_fmt[4:6]}-{start_fmt[6:8]}"
            if len(end_fmt) == 8 and end_fmt.isdigit():
                end_fmt = f"{end_fmt[:4]}-{end_fmt[4:6]}-{end_fmt[6:8]}"
            data = ticker.history(start=start_fmt, end=end_fmt)
            if data is not None and not data.empty:
                # 标准化列名
                data = data.reset_index()
                rename_map = {}
                for col in data.columns:
                    col_lower = str(col).lower()
                    if col_lower == 'date' or 'date' in col_lower:
                        rename_map[col] = 'date'
                    elif col_lower in ('open', 'high', 'low', 'close', 'volume'):
                        rename_map[col] = col_lower
                    elif col_lower == 'adj close':
                        rename_map[col] = 'adj_close'
                if rename_map:
                    data = data.rename(columns=rename_map)
                if 'date' not in data.columns and data.index.name == 'Date':
                    data = data.reset_index()
                    data = data.rename(columns={'Date': 'date'})
                logger.debug(f"📊 [增量更新-yfinance] {symbol} 获取到 {len(data)}条")
                return data
        except Exception as e:
            logger.debug(f"yfinance增量获取失败: {e}")
            return None

    def _try_cache_first_fundamentals(self, symbol: str) -> Optional[str]:
        """
        缓存优先读取基本面数据

        流程：查本地缓存 → 命中且未过期 → 直接使用
                           ↓ 未命中或过期
                   实时获取 → 成功 → 更新缓存 → 使用
                               ↓ 失败
                           使用本地快照(标注时效)

        Args:
            symbol: 股票代码

        Returns:
            str: 缓存命中的数据，未命中返回None（由调用方继续原有流程）
        """
        try:
            from .cache.cache_config import generate_cache_key, detect_market, get_ttl_seconds

            market = detect_market(symbol)

            # 1. 尝试从统一缓存读取
            cached = self._get_cached_text(symbol, "fundamentals")
            if cached and "❌" not in cached:
                logger.info(f"✅ [缓存命中] {symbol} fundamentals")
                return cached

            # 2. 尝试从本地快照读取（兜底）
            snapshot_data = self._snapshot_manager.get_any_snapshot(symbol, "fundamentals")
            if snapshot_data:
                logger.info(f"📦 [快照兜底] {symbol} fundamentals（使用本地快照，标注时效）")
                return snapshot_data

        except Exception as e:
            logger.debug(f"缓存优先读取跳过: {e}")

        # 缓存未命中，返回None，由调用方继续原有实时获取流程
        return None

    def _get_cached_data(self, symbol: str, start_date: str = None, end_date: str = None, max_age_hours: int = 24) -> Optional[pd.DataFrame]:
        """
        从缓存获取数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            max_age_hours: 最大缓存时间（小时）

        Returns:
            DataFrame: 缓存的数据，如果没有则返回None
        """
        if not self.cache_enabled or not self.cache_manager:
            return None

        try:
            cache_key = self.cache_manager.find_cached_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                max_age_hours=max_age_hours
            )

            if cache_key:
                cached_data = self.cache_manager.load_stock_data(cache_key)
                if cached_data is not None and hasattr(cached_data, 'empty') and not cached_data.empty:
                    logger.debug(f"📦 从缓存获取{symbol}数据: {len(cached_data)}条")
                    return cached_data
        except Exception as e:
            logger.warning(f"⚠️ 从缓存读取数据失败: {e}")

        return None

    def _save_to_cache(self, symbol: str, data: pd.DataFrame, start_date: str = None, end_date: str = None):
        """
        保存数据到缓存

        Args:
            symbol: 股票代码
            data: 数据
            start_date: 开始日期
            end_date: 结束日期
        """
        if not self.cache_enabled or not self.cache_manager:
            return

        try:
            if data is not None and hasattr(data, 'empty') and not data.empty:
                self.cache_manager.save_stock_data(symbol, data, start_date, end_date)
                logger.debug(f"💾 保存{symbol}数据到缓存: {len(data)}条")
        except Exception as e:
            logger.warning(f"⚠️ 保存数据到缓存失败: {e}")

    def _get_volume_safely(self, data: pd.DataFrame) -> float:
        """
        安全获取成交量数据

        Args:
            data: 股票数据DataFrame

        Returns:
            float: 成交量，如果获取失败返回0
        """
        try:
            if 'volume' in data.columns:
                return data['volume'].iloc[-1]
            elif 'vol' in data.columns:
                return data['vol'].iloc[-1]
            else:
                return 0
        except Exception:
            return 0

    def _format_stock_data_response(self, data: pd.DataFrame, symbol: str, stock_name: str,
                                    start_date: str, end_date: str) -> str:
        """
        格式化股票数据响应（包含技术指标）

        Args:
            data: 股票数据DataFrame
            symbol: 股票代码
            stock_name: 股票名称
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            str: 格式化的数据报告（包含技术指标）
        """
        def _sf(val, fmt=".2f"):
            if val is None or (isinstance(val, float) and val != val):
                return "N/A"
            try:
                return f"{val:{fmt}}"
            except (TypeError, ValueError):
                return str(val)

        try:
            original_data_count = len(data)
            logger.info(f"📊 [技术指标] 开始计算技术指标，原始数据: {original_data_count}条")

            # 🔧 计算技术指标（使用完整数据）
            # 确保数据按日期排序
            if 'date' in data.columns:
                data = data.sort_values('date')

            # 计算移动平均线
            data['ma5'] = data['close'].rolling(window=5, min_periods=1).mean()
            data['ma10'] = data['close'].rolling(window=10, min_periods=1).mean()
            data['ma20'] = data['close'].rolling(window=20, min_periods=1).mean()
            data['ma60'] = data['close'].rolling(window=60, min_periods=1).mean()

            # 计算RSI（相对强弱指标）- 同花顺风格：使用中国式SMA（EMA with adjust=True）
            # 参考：https://blog.csdn.net/u011218867/article/details/117427927
            # 同花顺/通达信的RSI使用SMA函数，等价于pandas的ewm(com=N-1, adjust=True)
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # RSI6 - 使用中国式SMA
            avg_gain6 = gain.ewm(com=5, adjust=True).mean()  # com = N - 1
            avg_loss6 = loss.ewm(com=5, adjust=True).mean()
            rs6 = avg_gain6 / avg_loss6.replace(0, np.nan)
            data['rsi6'] = 100 - (100 / (1 + rs6))

            # RSI12 - 使用中国式SMA
            avg_gain12 = gain.ewm(com=11, adjust=True).mean()
            avg_loss12 = loss.ewm(com=11, adjust=True).mean()
            rs12 = avg_gain12 / avg_loss12.replace(0, np.nan)
            data['rsi12'] = 100 - (100 / (1 + rs12))

            # RSI24 - 使用中国式SMA
            avg_gain24 = gain.ewm(com=23, adjust=True).mean()
            avg_loss24 = loss.ewm(com=23, adjust=True).mean()
            rs24 = avg_gain24 / avg_loss24.replace(0, np.nan)
            data['rsi24'] = 100 - (100 / (1 + rs24))

            # 保留RSI14作为国际标准参考（使用简单移动平均）
            gain14 = gain.rolling(window=14, min_periods=1).mean()
            loss14 = loss.rolling(window=14, min_periods=1).mean()
            rs14 = gain14 / loss14.replace(0, np.nan)
            data['rsi14'] = 100 - (100 / (1 + rs14))

            # 计算MACD
            ema12 = data['close'].ewm(span=12, adjust=False).mean()
            ema26 = data['close'].ewm(span=26, adjust=False).mean()
            data['macd_dif'] = ema12 - ema26
            data['macd_dea'] = data['macd_dif'].ewm(span=9, adjust=False).mean()
            data['macd'] = (data['macd_dif'] - data['macd_dea']) * 2

            # 计算布林带
            data['boll_mid'] = data['close'].rolling(window=20, min_periods=1).mean()
            std = data['close'].rolling(window=20, min_periods=1).std()
            data['boll_upper'] = data['boll_mid'] + 2 * std
            data['boll_lower'] = data['boll_mid'] - 2 * std

            logger.info(f"✅ [技术指标] 技术指标计算完成")

            # 🔧 只保留最后3-5天的数据用于展示（减少token消耗）
            display_rows = min(5, len(data))
            display_data = data.tail(display_rows)
            latest_data = data.iloc[-1]

            # 🔍 [调试日志] 打印最近5天的原始数据和技术指标
            logger.info(f"🔍 [技术指标详情] ===== 最近{display_rows}个交易日数据 =====")
            for i, (idx, row) in enumerate(display_data.iterrows(), 1):
                logger.info(f"🔍 [技术指标详情] 第{i}天 ({row.get('date', 'N/A')}):")
                logger.info(f"   价格: 开={row.get('open', 0):.2f}, 高={row.get('high', 0):.2f}, 低={row.get('low', 0):.2f}, 收={row.get('close', 0):.2f}")
                logger.info(f"   MA: MA5={row.get('ma5', 0):.2f}, MA10={row.get('ma10', 0):.2f}, MA20={row.get('ma20', 0):.2f}, MA60={row.get('ma60', 0):.2f}")
                logger.info(f"   MACD: DIF={row.get('macd_dif', 0):.4f}, DEA={row.get('macd_dea', 0):.4f}, MACD={row.get('macd', 0):.4f}")
                logger.info(f"   RSI: RSI6={row.get('rsi6', 0):.2f}, RSI12={row.get('rsi12', 0):.2f}, RSI24={row.get('rsi24', 0):.2f} (同花顺风格)")
                logger.info(f"   RSI14: {row.get('rsi14', 0):.2f} (国际标准)")
                logger.info(f"   BOLL: 上={row.get('boll_upper', 0):.2f}, 中={row.get('boll_mid', 0):.2f}, 下={row.get('boll_lower', 0):.2f}")

            logger.info(f"🔍 [技术指标详情] ===== 数据详情结束 =====")

            # 计算最新价格和涨跌幅
            latest_price = latest_data.get('close', 0)
            prev_close = data.iloc[-2].get('close', latest_price) if len(data) > 1 else latest_price
            change = latest_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close != 0 else 0

            # 格式化数据报告
            result = f"📊 {stock_name}({symbol}) - 技术分析数据\n"
            result += f"数据期间: {start_date} 至 {end_date}\n"
            result += f"数据条数: {original_data_count}条 (展示最近{display_rows}个交易日)\n\n"

            result += f"💰 最新价格: ¥{_sf(latest_price)}\n"
            result += f"📈 涨跌额: {_sf(change, '+.2f')} ({_sf(change_pct, '+.2f')}%)\n\n"

            # 添加技术指标
            result += f"📊 移动平均线 (MA):\n"
            result += f"   MA5:  ¥{_sf(latest_data.get('ma5', 0))}"
            if latest_price > latest_data.get('ma5', 0):
                result += " (价格在MA5上方 ↑)\n"
            else:
                result += " (价格在MA5下方 ↓)\n"

            result += f"   MA10: ¥{_sf(latest_data.get('ma10', 0))}"
            if latest_price > latest_data.get('ma10', 0):
                result += " (价格在MA10上方 ↑)\n"
            else:
                result += " (价格在MA10下方 ↓)\n"

            result += f"   MA20: ¥{_sf(latest_data.get('ma20', 0))}"
            if latest_price > latest_data.get('ma20', 0):
                result += " (价格在MA20上方 ↑)\n"
            else:
                result += " (价格在MA20下方 ↓)\n"

            result += f"   MA60: ¥{_sf(latest_data.get('ma60', 0))}"
            if latest_price > latest_data.get('ma60', 0):
                result += " (价格在MA60上方 ↑)\n\n"
            else:
                result += " (价格在MA60下方 ↓)\n\n"

            # MACD指标
            result += f"📈 MACD指标:\n"
            result += f"   DIF:  {latest_data['macd_dif']:.3f}\n"
            result += f"   DEA:  {latest_data['macd_dea']:.3f}\n"
            result += f"   MACD: {latest_data['macd']:.3f}"
            if latest_data['macd'] > 0:
                result += " (多头 ↑)\n"
            else:
                result += " (空头 ↓)\n"

            # 判断金叉/死叉
            if len(data) > 1:
                prev_dif = data.iloc[-2]['macd_dif']
                prev_dea = data.iloc[-2]['macd_dea']
                curr_dif = latest_data['macd_dif']
                curr_dea = latest_data['macd_dea']

                if prev_dif <= prev_dea and curr_dif > curr_dea:
                    result += "   ⚠️ MACD金叉信号（DIF上穿DEA）\n\n"
                elif prev_dif >= prev_dea and curr_dif < curr_dea:
                    result += "   ⚠️ MACD死叉信号（DIF下穿DEA）\n\n"
                else:
                    result += "\n"
            else:
                result += "\n"

            # RSI指标 - 同花顺风格 (6, 12, 24)
            rsi6 = latest_data.get('rsi6', 0)
            rsi12 = latest_data.get('rsi12', 0)
            rsi24 = latest_data.get('rsi24', 0)
            result += f"📉 RSI指标 (同花顺风格):\n"
            result += f"   RSI6:  {_sf(rsi6)}"
            if rsi6 and rsi6 >= 80:
                result += " (超买 ⚠️)\n"
            elif rsi6 and rsi6 <= 20:
                result += " (超卖 ⚠️)\n"
            else:
                result += "\n"

            result += f"   RSI12: {_sf(rsi12)}"
            if rsi12 and rsi12 >= 80:
                result += " (超买 ⚠️)\n"
            elif rsi12 and rsi12 <= 20:
                result += " (超卖 ⚠️)\n"
            else:
                result += "\n"

            result += f"   RSI24: {_sf(rsi24)}"
            if rsi24 and rsi24 >= 80:
                result += " (超买 ⚠️)\n"
            elif rsi24 and rsi24 <= 20:
                result += " (超卖 ⚠️)\n"
            else:
                result += "\n"

            # 判断RSI趋势
            if rsi6 > rsi12 > rsi24:
                result += "   趋势: 多头排列 ↑\n\n"
            elif rsi6 < rsi12 < rsi24:
                result += "   趋势: 空头排列 ↓\n\n"
            else:
                result += "   趋势: 震荡整理 ↔\n\n"

            # 布林带
            result += f"📊 布林带 (BOLL):\n"
            result += f"   上轨: ¥{_sf(latest_data.get('boll_upper', 0))}\n"
            result += f"   中轨: ¥{_sf(latest_data.get('boll_mid', 0))}\n"
            result += f"   下轨: ¥{_sf(latest_data.get('boll_lower', 0))}\n"

            # 判断价格在布林带的位置
            boll_position = (latest_price - latest_data['boll_lower']) / (latest_data['boll_upper'] - latest_data['boll_lower']) * 100
            result += f"   价格位置: {boll_position:.1f}%"
            if boll_position >= 80:
                result += " (接近上轨，可能超买 ⚠️)\n\n"
            elif boll_position <= 20:
                result += " (接近下轨，可能超卖 ⚠️)\n\n"
            else:
                result += " (中性区域)\n\n"

            # 价格统计
            result += f"📊 价格统计 (最近{display_rows}个交易日):\n"
            result += f"   最高价: ¥{display_data['high'].max():.2f}\n"
            result += f"   最低价: ¥{display_data['low'].min():.2f}\n"
            result += f"   平均价: ¥{display_data['close'].mean():.2f}\n"

            # 防御性获取成交量数据
            volume_value = self._get_volume_safely(display_data)
            result += f"   平均成交量: {volume_value:,.0f}股\n"

            return result

        except Exception as e:
            logger.error(f"❌ 格式化数据响应失败: {e}", exc_info=True)
            return f"❌ 格式化{symbol}数据失败: {e}"

    def get_stock_dataframe(self, symbol: str, start_date: str = None, end_date: str = None, period: str = "daily") -> pd.DataFrame:
        """
        获取股票数据的 DataFrame 接口，支持多数据源和自动降级

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期（daily/weekly/monthly），默认为daily

        Returns:
            pd.DataFrame: 股票数据 DataFrame，列标准：open, high, low, close, vol, amount, date
        """
        logger.info(f"📊 [DataFrame接口] 获取股票数据: {symbol} ({start_date} 到 {end_date})")

        try:
            # 尝试当前数据源
            df = None
            if self.current_source == ChinaDataSource.MONGODB:
                from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
                adapter = get_mongodb_cache_adapter()
                df = adapter.get_historical_data(symbol, start_date, end_date, period=period)
            elif self.current_source == ChinaDataSource.TUSHARE:
                from .providers.china.tushare import get_tushare_provider
                provider = get_tushare_provider()
                df = provider.get_daily_data(symbol, start_date, end_date)
            elif self.current_source == ChinaDataSource.AKSHARE:
                from .providers.china.akshare import get_akshare_provider
                provider = get_akshare_provider()
                df = provider.get_stock_data(symbol, start_date, end_date)
            elif self.current_source == ChinaDataSource.BAOSTOCK:
                from .providers.china.baostock import get_baostock_provider
                provider = get_baostock_provider()
                df = provider.get_stock_data(symbol, start_date, end_date)

            if df is not None and not df.empty:
                logger.info(f"✅ [DataFrame接口] 从 {self.current_source.value} 获取成功: {len(df)}条")
                return self._standardize_dataframe(df)

            # 降级到其他数据源
            logger.warning(f"⚠️ [DataFrame接口] {self.current_source.value} 失败，尝试降级")
            for source in self.available_sources:
                if source == self.current_source:
                    continue
                try:
                    if source == ChinaDataSource.MONGODB:
                        from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
                        adapter = get_mongodb_cache_adapter()
                        df = adapter.get_historical_data(symbol, start_date, end_date, period=period)
                    elif source == ChinaDataSource.TUSHARE:
                        from .providers.china.tushare import get_tushare_provider
                        provider = get_tushare_provider()
                        df = provider.get_daily_data(symbol, start_date, end_date)
                    elif source == ChinaDataSource.AKSHARE:
                        from .providers.china.akshare import get_akshare_provider
                        provider = get_akshare_provider()
                        df = provider.get_stock_data(symbol, start_date, end_date)
                    elif source == ChinaDataSource.BAOSTOCK:
                        from .providers.china.baostock import get_baostock_provider
                        provider = get_baostock_provider()
                        df = provider.get_stock_data(symbol, start_date, end_date)

                    if df is not None and not df.empty:
                        logger.info(f"✅ [DataFrame接口] 降级到 {source.value} 成功: {len(df)}条")
                        return self._standardize_dataframe(df)
                except Exception as e:
                    logger.warning(f"⚠️ [DataFrame接口] {source.value} 失败: {e}")
                    continue

            logger.error(f"❌ [DataFrame接口] 所有数据源都失败: {symbol}")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ [DataFrame接口] 获取失败: {e}", exc_info=True)
            return pd.DataFrame()

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化 DataFrame 列名和格式

        委托给 unified_dataframe.standardize_dataframe() 统一处理
        """
        from .unified_dataframe import standardize_dataframe
        from .cache.cache_config import detect_market
        market = detect_market(getattr(self, '_last_symbol', ''))
        return standardize_dataframe(df, market=market)

    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None, period: str = "daily") -> str:
        """
        获取股票数据的统一接口，支持多周期数据

        缓存优先读取流程：
        查本地缓存 → 命中且未过期 → 直接使用
                        ↓ 未命中或过期
                实时获取 → 成功 → 更新缓存 → 使用
                            ↓ 失败
                        使用本地快照(标注时效)

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期（daily/weekly/monthly），默认为daily

        Returns:
            str: 格式化的股票数据
        """
        # ===== Phase 2.2: 缓存优先读取 =====
        cached_result = self._try_cache_first_stock_data(symbol, start_date, end_date, period)
        if cached_result is not None:
            return cached_result

        # ===== Phase 2.3: 增量更新（仅适用于历史K线数据） =====
        incremental_result = self._try_incremental_stock_data(symbol, start_date, end_date, period)
        if incremental_result is not None:
            return incremental_result

        # 记录详细的输入参数
        logger.info(f"📊 [数据来源: {self.current_source.value}] 开始获取{period}数据: {symbol}",
                   extra={
                       'symbol': symbol,
                       'start_date': start_date,
                       'end_date': end_date,
                       'period': period,
                       'data_source': self.current_source.value,
                       'event_type': 'data_fetch_start'
                   })

        # 添加详细的股票代码追踪日志
        logger.info(f"🔍 [股票代码追踪] DataSourceManager.get_stock_data 接收到的股票代码: '{symbol}' (类型: {type(symbol)})")
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(symbol))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(symbol))}")
        logger.info(f"🔍 [股票代码追踪] 当前数据源: {self.current_source.value}")

        start_time = time.time()

        try:
            # 根据数据源调用相应的获取方法
            actual_source = None  # 实际使用的数据源

            if self.current_source == ChinaDataSource.MONGODB:
                result, actual_source = self._get_mongodb_data(symbol, start_date, end_date, period)
            elif self.current_source == ChinaDataSource.TUSHARE:
                logger.info(f"🔍 [股票代码追踪] 调用 Tushare 数据源，传入参数: symbol='{symbol}', period='{period}'")
                result = self._get_tushare_data(symbol, start_date, end_date, period)
                actual_source = "tushare"
            elif self.current_source == ChinaDataSource.AKSHARE:
                result = self._get_akshare_data(symbol, start_date, end_date, period)
                actual_source = "akshare"
            elif self.current_source == ChinaDataSource.BAOSTOCK:
                result = self._get_baostock_data(symbol, start_date, end_date, period)
                actual_source = "baostock"
            # TDX 已移除
            else:
                result = f"❌ 不支持的数据源: {self.current_source.value}"
                actual_source = None

            # 记录详细的输出结果
            duration = time.time() - start_time
            result_length = len(result) if result else 0
            is_success = result and "❌" not in result and "错误" not in result

            # 使用实际数据源名称，如果没有则使用 current_source
            display_source = actual_source or self.current_source.value

            if is_success:
                logger.info(f"✅ [数据来源: {display_source}] 成功获取股票数据: {symbol} ({result_length}字符, 耗时{duration:.2f}秒)",
                           extra={
                               'symbol': symbol,
                               'start_date': start_date,
                               'end_date': end_date,
                               'data_source': display_source,
                               'actual_source': actual_source,
                               'requested_source': self.current_source.value,
                               'duration': duration,
                               'result_length': result_length,
                               'result_preview': result[:200] + '...' if result_length > 200 else result,
                               'event_type': 'data_fetch_success'
                           })
                # 保存数据快照
                self._snapshot_manager.save_snapshot(symbol, "stock_data", result, source=display_source or "unknown")
                return result
            else:
                logger.warning(f"⚠️ [数据来源: {self.current_source.value}失败] 数据质量异常，尝试降级到其他数据源: {symbol}",
                              extra={
                                  'symbol': symbol,
                                  'start_date': start_date,
                                  'end_date': end_date,
                                  'data_source': self.current_source.value,
                                  'duration': duration,
                                  'result_length': result_length,
                                  'result_preview': result[:200] + '...' if result_length > 200 else result,
                                  'event_type': 'data_fetch_warning'
                              })

                # 数据质量异常时也尝试降级到其他数据源
                fallback_result = self._try_fallback_sources(symbol, start_date, end_date)
                if fallback_result and "❌" not in fallback_result and "错误" not in fallback_result:
                    logger.info(f"✅ [数据来源: 备用数据源] 降级成功获取数据: {symbol}")
                    return fallback_result
                else:
                    logger.error(f"❌ [数据来源: 所有数据源失败] 所有数据源都无法获取有效数据: {symbol}")
                    return result  # 返回原始结果（包含错误信息）

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ [数据获取] 异常失败: {e}",
                        extra={
                            'symbol': symbol,
                            'start_date': start_date,
                            'end_date': end_date,
                            'data_source': self.current_source.value,
                            'duration': duration,
                            'error': str(e),
                            'event_type': 'data_fetch_exception'
                        }, exc_info=True)
            return self._try_fallback_sources(symbol, start_date, end_date)

    def _get_mongodb_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> tuple[str, str | None]:
        """
        从MongoDB获取多周期数据 - 包含技术指标计算

        Returns:
            tuple[str, str | None]: (结果字符串, 实际使用的数据源名称)
        """
        logger.debug(f"📊 [MongoDB] 调用参数: symbol={symbol}, start_date={start_date}, end_date={end_date}, period={period}")

        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
            adapter = get_mongodb_cache_adapter()

            # 从MongoDB获取指定周期的历史数据
            df = adapter.get_historical_data(symbol, start_date, end_date, period=period)

            if df is not None and not df.empty:
                logger.info(f"✅ [数据来源: MongoDB缓存] 成功获取{period}数据: {symbol} ({len(df)}条记录)")

                # 🔧 修复：使用统一的格式化方法，包含技术指标计算
                # 获取股票名称（从DataFrame中提取或使用默认值）
                stock_name = f'股票{symbol}'
                if 'name' in df.columns and not df['name'].empty:
                    stock_name = df['name'].iloc[0]

                # 调用统一的格式化方法（包含技术指标计算）
                result = self._format_stock_data_response(df, symbol, stock_name, start_date, end_date)

                logger.info(f"✅ [MongoDB] 已计算技术指标: MA5/10/20/60, MACD, RSI, BOLL")
                return result, "mongodb"
            else:
                # MongoDB没有数据（adapter内部已记录详细的数据源信息），降级到其他数据源
                logger.info(f"🔄 [MongoDB] 未找到{period}数据: {symbol}，开始尝试备用数据源")
                return self._try_fallback_sources(symbol, start_date, end_date, period)

        except Exception as e:
            logger.error(f"❌ [数据来源: MongoDB异常] 获取{period}数据失败: {symbol}, 错误: {e}")
            # MongoDB异常，降级到其他数据源
            return self._try_fallback_sources(symbol, start_date, end_date, period)

    def _get_tushare_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> str:
        """使用Tushare获取多周期数据 - 使用provider + 统一缓存"""
        logger.debug(f"📊 [Tushare] 调用参数: symbol={symbol}, start_date={start_date}, end_date={end_date}, period={period}")

        # 添加详细的股票代码追踪日志
        logger.info(f"🔍 [股票代码追踪] _get_tushare_data 接收到的股票代码: '{symbol}' (类型: {type(symbol)})")
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(symbol))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(symbol))}")
        logger.info(f"🔍 [DataSourceManager详细日志] _get_tushare_data 开始执行")
        logger.info(f"🔍 [DataSourceManager详细日志] 当前数据源: {self.current_source.value}")

        start_time = time.time()
        try:
            # 1. 先尝试从缓存获取
            cached_data = self._get_cached_data(symbol, start_date, end_date, max_age_hours=24)
            if cached_data is not None and not cached_data.empty:
                logger.info(f"✅ [缓存命中] 从缓存获取{symbol}数据")
                # 获取股票基本信息
                provider = self._get_tushare_adapter()
                if provider:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        # 在线程池中没有事件循环，创建新的
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    stock_info = loop.run_until_complete(provider.get_stock_basic_info(symbol))
                    stock_name = stock_info.get('name', f'股票{symbol}') if stock_info else f'股票{symbol}'
                else:
                    stock_name = f'股票{symbol}'

                # 格式化返回
                return self._format_stock_data_response(cached_data, symbol, stock_name, start_date, end_date)

            # 2. 缓存未命中，从provider获取
            logger.info(f"🔍 [股票代码追踪] 调用 tushare_provider，传入参数: symbol='{symbol}'")
            logger.info(f"🔍 [DataSourceManager详细日志] 开始调用tushare_provider...")

            provider = self._get_tushare_adapter()
            if not provider:
                return f"❌ Tushare提供器不可用"

            # 使用异步方法获取历史数据
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                # 在线程池中没有事件循环，创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            data = loop.run_until_complete(provider.get_historical_data(symbol, start_date, end_date))

            if data is not None and not data.empty:
                # 保存到缓存
                self._save_to_cache(symbol, data, start_date, end_date)

                # 获取股票基本信息（异步）
                stock_info = loop.run_until_complete(provider.get_stock_basic_info(symbol))
                stock_name = stock_info.get('name', f'股票{symbol}') if stock_info else f'股票{symbol}'

                # 格式化返回
                result = self._format_stock_data_response(data, symbol, stock_name, start_date, end_date)

                duration = time.time() - start_time
                logger.info(f"🔍 [DataSourceManager详细日志] 调用完成，耗时: {duration:.3f}秒")
                logger.info(f"🔍 [股票代码追踪] 返回结果前200字符: {result[:200] if result else 'None'}")
                logger.debug(f"📊 [Tushare] 调用完成: 耗时={duration:.2f}s, 结果长度={len(result) if result else 0}")

                return result
            else:
                result = f"❌ 未获取到{symbol}的有效数据"
                duration = time.time() - start_time
                logger.warning(f"⚠️ [Tushare] 未获取到数据，耗时={duration:.2f}s")
                return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ [Tushare] 调用失败: {e}, 耗时={duration:.2f}s", exc_info=True)
            logger.error(f"❌ [DataSourceManager详细日志] 异常类型: {type(e).__name__}")
            logger.error(f"❌ [DataSourceManager详细日志] 异常信息: {str(e)}")
            import traceback
            logger.error(f"❌ [DataSourceManager详细日志] 异常堆栈: {traceback.format_exc()}")
            raise

    def _get_akshare_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> str:
        """使用AKShare获取多周期数据 - 包含技术指标计算"""
        logger.debug(f"📊 [AKShare] 调用参数: symbol={symbol}, start_date={start_date}, end_date={end_date}, period={period}")

        cached = self._get_cached_text(symbol, "stock_data", start_date, end_date, "akshare")
        if cached:
            self._health_tracker.record_success(ChinaDataSource.AKSHARE.value)
            return cached

        start_time = time.time()
        try:
            from .providers.china.akshare import get_akshare_provider
            provider = get_akshare_provider()

            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            data = loop.run_until_complete(provider.get_historical_data(symbol, start_date, end_date, period))

            duration = time.time() - start_time

            if data is not None and not data.empty:
                stock_info = loop.run_until_complete(provider.get_stock_basic_info(symbol))
                stock_name = stock_info.get('name', f'股票{symbol}') if stock_info else f'股票{symbol}'

                result = self._format_stock_data_response(data, symbol, stock_name, start_date, end_date)

                missing_fields = self._detect_missing_fields(result)
                if missing_fields:
                    logger.info(f"📊 [数据补全] 检测到 {symbol} 缺失字段: {missing_fields}")
                    result = self._complete_missing_fields(result, symbol, missing_fields)

                self._health_tracker.record_success(ChinaDataSource.AKSHARE.value)
                self._save_cached_text(symbol, "stock_data", result, start_date, end_date, "akshare")
                logger.debug(f"📊 [AKShare] 调用成功: 耗时={duration:.2f}s, 数据条数={len(data)}, 结果长度={len(result)}")
                logger.info(f"✅ [AKShare] 已计算技术指标: MA5/10/20/60, MACD, RSI, BOLL")
                return result
            else:
                self._health_tracker.record_failure(ChinaDataSource.AKSHARE.value)
                result = f"❌ 未能获取{symbol}的股票数据"
                logger.warning(f"⚠️ [AKShare] 数据为空: 耗时={duration:.2f}s")
                return result

        except Exception as e:
            duration = time.time() - start_time
            self._health_tracker.record_failure(ChinaDataSource.AKSHARE.value)
            logger.error(f"❌ [AKShare] 调用失败: {e}, 耗时={duration:.2f}s", exc_info=True)
            return f"❌ AKShare获取{symbol}数据失败: {e}"

    def _get_baostock_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> str:
        """使用BaoStock获取多周期数据 - 包含技术指标计算"""
        cached = self._get_cached_text(symbol, "stock_data", start_date, end_date, "baostock")
        if cached:
            self._health_tracker.record_success(ChinaDataSource.BAOSTOCK.value)
            return cached

        from .providers.china.baostock import get_baostock_provider
        provider = get_baostock_provider()

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            data = loop.run_until_complete(provider.get_historical_data(symbol, start_date, end_date, period))

            if data is not None and not data.empty:
                stock_info = loop.run_until_complete(provider.get_stock_basic_info(symbol))
                stock_name = stock_info.get('name', f'股票{symbol}') if stock_info else f'股票{symbol}'

                result = self._format_stock_data_response(data, symbol, stock_name, start_date, end_date)

                missing_fields = self._detect_missing_fields(result)
                if missing_fields:
                    logger.info(f"📊 [数据补全] BaoStock检测到 {symbol} 缺失字段: {missing_fields}")
                    result = self._complete_missing_fields(result, symbol, missing_fields)

                self._health_tracker.record_success(ChinaDataSource.BAOSTOCK.value)
                self._save_cached_text(symbol, "stock_data", result, start_date, end_date, "baostock")
                logger.info(f"✅ [BaoStock] 已计算技术指标: MA5/10/20/60, MACD, RSI, BOLL")
                return result
            else:
                self._health_tracker.record_failure(ChinaDataSource.BAOSTOCK.value)
                return f"❌ 未能获取{symbol}的股票数据"
        except Exception as e:
            self._health_tracker.record_failure(ChinaDataSource.BAOSTOCK.value)
            logger.error(f"❌ [BaoStock] 调用失败: {e}", exc_info=True)
            return f"❌ BaoStock获取{symbol}数据失败: {e}"

    # ==================== 新浪财经数据接口 ====================

    def _get_sina_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> str:
        """
        使用新浪财经获取A股数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期

        Returns:
            str: 格式化的股票数据报告
        """
        try:
            import asyncio
            from tradingagents.dataflows.providers.china.sina_finance import SinaFinanceProvider

            provider = SinaFinanceProvider()

            # 获取实时行情
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在已有事件循环中，使用线程执行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.connect())
                        future.result(timeout=15)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.get_stock_quotes(symbol))
                        quotes = future.result(timeout=15)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.get_historical_data(symbol, start_date, end_date))
                        hist_data = future.result(timeout=30)
                else:
                    asyncio.run(provider.connect())
                    quotes = asyncio.run(provider.get_stock_quotes(symbol))
                    hist_data = asyncio.run(provider.get_historical_data(symbol, start_date, end_date))
            except RuntimeError:
                # 没有事件循环，直接创建
                asyncio.run(provider.connect())
                quotes = asyncio.run(provider.get_stock_quotes(symbol))
                hist_data = asyncio.run(provider.get_historical_data(symbol, start_date, end_date))

            # 格式化输出
            result_parts = []
            result_parts.append(f"📊 {symbol} 股票数据（新浪财经）\n")

            # 实时行情
            if quotes:
                result_parts.append("📈 实时行情:")
                result_parts.append(f"  名称: {quotes.get('name', '未知')}")
                result_parts.append(f"  当前价: {quotes.get('current_price', 'N/A')}")
                result_parts.append(f"  涨跌幅: {quotes.get('pct_chg', 'N/A')}%")
                result_parts.append(f"  成交量: {quotes.get('volume', 'N/A')}")
                result_parts.append(f"  成交额: {quotes.get('amount', 'N/A')}")
                result_parts.append("")

            # 历史数据
            if hist_data is not None and not hist_data.empty:
                result_parts.append(f"📉 历史数据: 共{len(hist_data)}条记录")
                # 计算基本统计
                if 'close' in hist_data.columns:
                    latest = hist_data['close'].iloc[-1]
                    result_parts.append(f"  最新收盘价: {latest}")
                    if 'pct_chg' in hist_data.columns:
                        avg_chg = hist_data['pct_chg'].mean()
                        result_parts.append(f"  平均涨跌幅: {avg_chg:.2f}%")
                result_parts.append("")

            output = "\n".join(result_parts)
            if len(output) > 50:
                self._health_tracker.record_success(ChinaDataSource.SINA.value)
                logger.info(f"✅ [新浪财经] 成功获取{symbol}数据")
                return output
            else:
                self._health_tracker.record_failure(ChinaDataSource.SINA.value)
                return f"❌ 新浪财经获取{symbol}数据不完整"

        except ImportError:
            self._health_tracker.record_failure(ChinaDataSource.SINA.value)
            return f"❌ 新浪财经依赖库未安装"
        except Exception as e:
            self._health_tracker.record_failure(ChinaDataSource.SINA.value)
            logger.error(f"❌ [新浪财经] 调用失败: {e}", exc_info=True)
            return f"❌ 新浪财经获取{symbol}数据失败: {e}"

    # ==================== 东方财富直接API数据接口 ====================

    def _get_eastmoney_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> str:
        """
        使用东方财富直接API获取A股数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期

        Returns:
            str: 格式化的股票数据报告
        """
        try:
            import asyncio
            from tradingagents.dataflows.providers.china.eastmoney_direct import EastMoneyDirectProvider

            provider = EastMoneyDirectProvider()

            # 获取实时行情和财务数据
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.connect())
                        future.result(timeout=15)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.get_stock_quotes(symbol))
                        quotes = future.result(timeout=15)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.get_financial_data(symbol))
                        financial = future.result(timeout=15)
                else:
                    asyncio.run(provider.connect())
                    quotes = asyncio.run(provider.get_stock_quotes(symbol))
                    financial = asyncio.run(provider.get_financial_data(symbol))
            except RuntimeError:
                asyncio.run(provider.connect())
                quotes = asyncio.run(provider.get_stock_quotes(symbol))
                financial = asyncio.run(provider.get_financial_data(symbol))

            # 格式化输出
            result_parts = []
            result_parts.append(f"📊 {symbol} 股票数据（东方财富直连）\n")

            # 实时行情
            if quotes:
                result_parts.append("📈 实时行情:")
                result_parts.append(f"  名称: {quotes.get('name', '未知')}")
                result_parts.append(f"  当前价: {quotes.get('current_price', 'N/A')}")
                result_parts.append(f"  涨跌幅: {quotes.get('pct_chg', 'N/A')}%")
                result_parts.append(f"  PE(TTM): {quotes.get('pe_ttm', 'N/A')}")
                result_parts.append(f"  PB: {quotes.get('pb', 'N/A')}")
                result_parts.append(f"  换手率: {quotes.get('turnover_rate', 'N/A')}%")
                result_parts.append(f"  总市值: {quotes.get('total_mv', 'N/A')}")
                result_parts.append("")

            # 财务数据
            if financial and financial.get("periods"):
                result_parts.append("💰 财务数据:")
                for i, period_data in enumerate(financial["periods"][:4]):
                    report_date = period_data.get("report_date", "未知")
                    if isinstance(report_date, str) and len(report_date) >= 10:
                        report_date = report_date[:10]
                    result_parts.append(f"  报告期: {report_date}")
                    result_parts.append(f"    EPS: {period_data.get('basic_eps', 'N/A')}")
                    result_parts.append(f"    ROE: {period_data.get('roe', 'N/A')}%")
                    result_parts.append(f"    营收同比: {period_data.get('revenue_yoy', 'N/A')}%")
                    result_parts.append(f"    净利润同比: {period_data.get('net_profit_yoy', 'N/A')}%")
                result_parts.append("")

            output = "\n".join(result_parts)
            if len(output) > 50:
                self._health_tracker.record_success(ChinaDataSource.EASTMONEY.value)
                logger.info(f"✅ [东方财富直连] 成功获取{symbol}数据")
                return output
            else:
                self._health_tracker.record_failure(ChinaDataSource.EASTMONEY.value)
                return f"❌ 东方财富直连获取{symbol}数据不完整"

        except ImportError:
            self._health_tracker.record_failure(ChinaDataSource.EASTMONEY.value)
            return f"❌ 东方财富直连依赖库未安装"
        except Exception as e:
            self._health_tracker.record_failure(ChinaDataSource.EASTMONEY.value)
            logger.error(f"❌ [东方财富直连] 调用失败: {e}", exc_info=True)
            return f"❌ 东方财富直连获取{symbol}数据失败: {e}"

    def _get_volume_safely(self, data) -> float:
        """安全地获取成交量数据，支持多种列名"""
        try:
            # 支持多种可能的成交量列名
            volume_columns = ['volume', 'vol', 'turnover', 'trade_volume']

            for col in volume_columns:
                if col in data.columns:
                    logger.info(f"✅ 找到成交量列: {col}")
                    return data[col].sum()

            # 如果都没找到，记录警告并返回0
            logger.warning(f"⚠️ 未找到成交量列，可用列: {list(data.columns)}")
            return 0

        except Exception as e:
            logger.error(f"❌ 获取成交量失败: {e}")
            return 0

    def _try_fallback_sources(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> tuple[str, str | None]:
        """
        尝试备用数据源 - 避免递归调用

        Returns:
            tuple[str, str | None]: (结果字符串, 实际使用的数据源名称)
        """
        logger.info(f"🔄 [{self.current_source.value}] 失败，尝试备用数据源获取{period}数据: {symbol}")

        fallback_order = self._get_data_source_priority_order(symbol)

        # 过滤掉熔断状态的数据源
        available_fallbacks = self._health_tracker.get_available_sources(fallback_order)
        skipped = [s for s in fallback_order if s not in available_fallbacks]
        if skipped:
            logger.info(f"🔴 [健康跟踪] 跳过熔断数据源: {[s.value for s in skipped]}")

        for source in available_fallbacks:
            if source != self.current_source and source in self.available_sources:
                try:
                    logger.info(f"🔄 [备用数据源] 尝试 {source.value} 获取{period}数据: {symbol}")

                    if source == ChinaDataSource.TUSHARE:
                        result = self._get_tushare_data(symbol, start_date, end_date, period)
                    elif source == ChinaDataSource.AKSHARE:
                        result = self._get_akshare_data(symbol, start_date, end_date, period)
                    elif source == ChinaDataSource.BAOSTOCK:
                        result = self._get_baostock_data(symbol, start_date, end_date, period)
                    elif source == ChinaDataSource.SINA:
                        result = self._get_sina_data(symbol, start_date, end_date, period)
                    elif source == ChinaDataSource.EASTMONEY:
                        result = self._get_eastmoney_data(symbol, start_date, end_date, period)
                    else:
                        logger.warning(f"⚠️ 未知数据源: {source.value}")
                        continue

                    if "❌" not in result:
                        self._health_tracker.record_success(source.value)
                        logger.info(f"✅ [备用数据源-{source.value}] 成功获取{period}数据: {symbol}")
                        return result, source.value
                    else:
                        self._health_tracker.record_failure(source.value)
                        logger.warning(f"⚠️ [备用数据源-{source.value}] 返回错误结果: {symbol}")

                except Exception as e:
                    self._health_tracker.record_failure(source.value)
                    logger.error(f"❌ [备用数据源-{source.value}] 获取失败: {symbol}, 错误: {e}")
                    continue

        logger.error(f"❌ [所有数据源失败] 无法获取{period}数据: {symbol}")
        
        # 最后尝试从本地快照获取数据
        snapshot_data = self._snapshot_manager.get_any_snapshot(symbol, "stock_data")
        if snapshot_data:
            logger.info(f"📦 [快照兜底] 从本地快照获取{symbol}数据成功")
            return snapshot_data, "snapshot"
        
        return f"❌ 所有数据源都无法获取{symbol}的{period}数据", None

    def _detect_missing_fields(self, data: str) -> List[str]:
        """
        检测格式化数据文本中缺失的关键字段

        检查PE/PB/市值/换手率/量比/ROE等关键字段是否为None/N/A/空值
        """
        missing = []
        field_patterns = {
            'pe': [r"'pe':\s*None", r"市盈率.*N/A", r"PE.*N/A"],
            'pb': [r"'pb':\s*None", r"市净率.*N/A", r"PB.*N/A"],
            'total_mv': [r"'total_mv':\s*None", r"总市值.*N/A"],
            'circ_mv': [r"'circ_mv':\s*None", r"流通市值.*N/A"],
            'turnover_rate': [r"'turnover_rate':\s*None", r"换手率.*N/A", r"'turnover_rate':\s*0\.0"],
            'volume_ratio': [r"'volume_ratio':\s*None", r"量比.*N/A", r"'volume_ratio':\s*0\.0"],
            'roe': [r"ROE.*N/A", r"净资产收益率.*N/A", r"roe.*None"],
        }
        import re
        for field, patterns in field_patterns.items():
            for pattern in patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    missing.append(field)
                    break
        return missing

    def _complete_missing_fields(self, data: str, symbol: str, missing_fields: List[str]) -> str:
        """
        从备选接口补全缺失字段

        当主数据源返回的数据中某些关键字段缺失时，
        从备选AKShare接口补全这些字段。

        补全规则：
        - ROE缺失 → 从 stock_financial_analysis_indicator 补
        - PE/PB缺失 → 从 stock_zh_a_spot_em 补
        - 市值缺失 → 从 stock_zh_a_spot_em 补
        - 换手率/量比缺失 → 从 stock_zh_a_spot_em 补

        Args:
            data: 原始数据文本
            symbol: 股票代码
            missing_fields: 缺失字段列表

        Returns:
            补全后的数据文本
        """
        if not missing_fields:
            return data

        try:
            import akshare as ak
            supplement_data = {}

            # 判断需要从哪个备选接口获取数据
            need_spot_em = any(f in missing_fields for f in ['pe', 'pb', 'total_mv', 'circ_mv', 'turnover_rate', 'volume_ratio'])
            need_financial = any(f in missing_fields for f in ['roe'])

            # 从 stock_zh_a_spot_em 补全 PE/PB/市值/换手率/量比
            if need_spot_em:
                try:
                    spot_df = ak.stock_zh_a_spot_em()
                    if spot_df is not None and not spot_df.empty:
                        stock_row = spot_df[spot_df['代码'] == symbol]
                        if not stock_row.empty:
                            row = stock_row.iloc[0]
                            if 'pe' in missing_fields:
                                pe_val = row.get('市盈率-动态', None)
                                if pe_val is not None and not (isinstance(pe_val, float) and np.isnan(pe_val)):
                                    supplement_data['pe'] = float(pe_val)
                            if 'pb' in missing_fields:
                                pb_val = row.get('市净率', None)
                                if pb_val is not None and not (isinstance(pb_val, float) and np.isnan(pb_val)):
                                    supplement_data['pb'] = float(pb_val)
                            if 'total_mv' in missing_fields:
                                mv_val = row.get('总市值', None)
                                if mv_val is not None and not (isinstance(mv_val, float) and np.isnan(mv_val)):
                                    supplement_data['total_mv'] = float(mv_val) / 1e8  # 转换为亿元
                            if 'circ_mv' in missing_fields:
                                circ_val = row.get('流通市值', None)
                                if circ_val is not None and not (isinstance(circ_val, float) and np.isnan(circ_val)):
                                    supplement_data['circ_mv'] = float(circ_val) / 1e8
                            if 'turnover_rate' in missing_fields:
                                tr_val = row.get('换手率', None)
                                if tr_val is not None and not (isinstance(tr_val, float) and np.isnan(tr_val)):
                                    supplement_data['turnover_rate'] = float(tr_val)
                            if 'volume_ratio' in missing_fields:
                                vr_val = row.get('量比', None)
                                if vr_val is not None and not (isinstance(vr_val, float) and np.isnan(vr_val)):
                                    supplement_data['volume_ratio'] = float(vr_val)
                            logger.info(f"✅ [数据补全] 从 stock_zh_a_spot_em 补全 {symbol} 字段: {list(supplement_data.keys())}")
                except Exception as e:
                    logger.warning(f"⚠️ [数据补全] 从 stock_zh_a_spot_em 补全失败: {e}")

            # 从 stock_financial_analysis_indicator 补全 ROE
            if need_financial:
                try:
                    fin_df = ak.stock_financial_analysis_indicator(symbol=symbol)
                    if fin_df is not None and not fin_df.empty:
                        latest = fin_df.iloc[0]
                        if 'roe' in missing_fields:
                            roe_val = latest.get('净资产收益率(%)', None)
                            if roe_val is not None:
                                try:
                                    supplement_data['roe'] = float(roe_val)
                                    logger.info(f"✅ [数据补全] 从 stock_financial_analysis_indicator 补全 {symbol} ROE: {roe_val}")
                                except (ValueError, TypeError):
                                    pass
                except Exception as e:
                    logger.warning(f"⚠️ [数据补全] 从 stock_financial_analysis_indicator 补全 ROE 失败: {e}")

            # 将补全数据追加到原始数据文本
            if supplement_data:
                supplement_text = "\n📊 补全数据（来自备选接口）:\n"
                field_name_map = {
                    'pe': '市盈率(PE)',
                    'pb': '市净率(PB)',
                    'total_mv': '总市值(亿元)',
                    'circ_mv': '流通市值(亿元)',
                    'turnover_rate': '换手率(%)',
                    'volume_ratio': '量比',
                    'roe': '净资产收益率(ROE)(%)',
                }
                for field_key, field_val in supplement_data.items():
                    display_name = field_name_map.get(field_key, field_key)
                    if isinstance(field_val, float):
                        supplement_text += f"   {display_name}: {field_val:.2f}\n"
                    else:
                        supplement_text += f"   {display_name}: {field_val}\n"
                data += supplement_text

            return data

        except ImportError:
            logger.warning("⚠️ [数据补全] AKShare未安装，无法补全缺失字段")
            return data
        except Exception as e:
            logger.error(f"❌ [数据补全] 补全缺失字段失败: {e}")
            return data

    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取股票基本信息，支持多数据源和自动降级
        优先级：MongoDB → Tushare → AKShare → BaoStock
        """
        logger.info(f"📊 [数据来源: {self.current_source.value}] 开始获取股票信息: {symbol}")

        # 优先使用 App Mongo 缓存（当 ta_use_app_cache=True）
        try:
            from tradingagents.config.runtime_settings import use_app_cache_enabled  # type: ignore
            use_cache = use_app_cache_enabled(False)
            logger.info(f"🔧 [配置检查] use_app_cache_enabled() 返回值: {use_cache}")
        except Exception as e:
            logger.error(f"❌ [配置检查] use_app_cache_enabled() 调用失败: {e}", exc_info=True)
            use_cache = False

        logger.info(f"🔧 [配置] ta_use_app_cache={use_cache}, current_source={self.current_source.value}")

        if use_cache:

            try:
                from .cache.app_adapter import get_basics_from_cache, get_market_quote_dataframe
                doc = get_basics_from_cache(symbol)
                if doc:
                    name = doc.get('name') or doc.get('stock_name') or ''
                    # 规范化行业与板块（避免把“中小板/创业板”等板块值误作行业）
                    board_labels = {'主板', '中小板', '创业板', '科创板'}
                    raw_industry = (doc.get('industry') or doc.get('industry_name') or '').strip()
                    sec_or_cat = (doc.get('sec') or doc.get('category') or '').strip()
                    market_val = (doc.get('market') or '').strip()
                    industry_val = raw_industry or sec_or_cat or '未知'
                    changed = False
                    if raw_industry in board_labels:
                        # 若industry是板块名，则将其用于market；industry改用更细分类（sec/category）
                        if not market_val:
                            market_val = raw_industry
                            changed = True
                        if sec_or_cat:
                            industry_val = sec_or_cat
                            changed = True
                    if changed:
                        try:
                            logger.debug(f"🔧 [字段归一化] industry原值='{raw_industry}' → 行业='{industry_val}', 市场/板块='{market_val or doc.get('market', '未知')}'")
                        except Exception:
                            pass

                    result = {
                        'symbol': symbol,
                        'name': name or f'股票{symbol}',
                        'area': doc.get('area', '未知'),
                        'industry': industry_val or '未知',
                        'market': market_val or doc.get('market', '未知'),
                        'list_date': doc.get('list_date', '未知'),
                        'source': 'app_cache'
                    }
                    # 追加快照行情（若存在）
                    try:
                        df = get_market_quote_dataframe(symbol)
                        if df is not None and not df.empty:
                            row = df.iloc[-1]
                            result['current_price'] = row.get('close')
                            result['change_pct'] = row.get('pct_chg')
                            result['volume'] = row.get('volume')
                            result['quote_date'] = row.get('date')
                            result['quote_source'] = 'market_quotes'
                            logger.info(f"✅ [股票信息] 附加行情 | price={result['current_price']} pct={result['change_pct']} vol={result['volume']} code={symbol}")
                    except Exception as _e:
                        logger.debug(f"附加行情失败（忽略）：{_e}")

                    if name:
                        logger.info(f"✅ [数据来源: MongoDB-stock_basic_info] 成功获取: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ [数据来源: MongoDB] 未找到有效名称: {symbol}，降级到其他数据源")
            except Exception as e:
                logger.error(f"❌ [数据来源: MongoDB异常] 获取股票信息失败: {e}", exc_info=True)


        # 首先尝试当前数据源
        try:
            if self.current_source == ChinaDataSource.TUSHARE:
                from .interface import get_china_stock_info_tushare
                info_str = get_china_stock_info_tushare(symbol)
                result = self._parse_stock_info_string(info_str, symbol)

                # 检查是否获取到有效信息
                if result.get('name') and result['name'] != f'股票{symbol}':
                    logger.info(f"✅ [数据来源: Tushare-股票信息] 成功获取: {symbol}")
                    return result
                else:
                    logger.warning(f"⚠️ [数据来源: Tushare失败] 返回无效信息，尝试降级: {symbol}")
                    return self._try_fallback_stock_info(symbol)
            else:
                adapter = self.get_data_adapter()
                if adapter and hasattr(adapter, 'get_stock_info'):
                    result = adapter.get_stock_info(symbol)
                    if result.get('name') and result['name'] != f'股票{symbol}':
                        logger.info(f"✅ [数据来源: {self.current_source.value}-股票信息] 成功获取: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ [数据来源: {self.current_source.value}失败] 返回无效信息，尝试降级: {symbol}")
                        return self._try_fallback_stock_info(symbol)
                else:
                    logger.warning(f"⚠️ [数据来源: {self.current_source.value}] 不支持股票信息获取，尝试降级: {symbol}")
                    return self._try_fallback_stock_info(symbol)

        except Exception as e:
            logger.error(f"❌ [数据来源: {self.current_source.value}异常] 获取股票信息失败: {e}", exc_info=True)
            return self._try_fallback_stock_info(symbol)

    def get_stock_basic_info(self, stock_code: str = None) -> Optional[Dict[str, Any]]:
        """
        获取股票基础信息（兼容 stock_data_service 接口）

        Args:
            stock_code: 股票代码，如果为 None 则返回所有股票列表

        Returns:
            Dict: 股票信息字典，或包含 error 字段的错误字典
        """
        if stock_code is None:
            # 返回所有股票列表
            logger.info("📊 获取所有股票列表")
            try:
                # 尝试从 MongoDB 获取
                from tradingagents.config.database_manager import get_database_manager
                db_manager = get_database_manager()
                if db_manager and db_manager.is_mongodb_available():
                    collection = db_manager.mongodb_db['stock_basic_info']
                    stocks = list(collection.find({}, {'_id': 0}))
                    if stocks:
                        logger.info(f"✅ 从MongoDB获取所有股票: {len(stocks)}条")
                        return stocks
            except Exception as e:
                logger.warning(f"⚠️ 从MongoDB获取所有股票失败: {e}")

            # 降级：返回空列表
            return []

        # 获取单个股票信息
        try:
            result = self.get_stock_info(stock_code)
            if result and result.get('name'):
                return result
            else:
                return {'error': f'未找到股票 {stock_code} 的信息'}
        except Exception as e:
            logger.error(f"❌ 获取股票信息失败: {e}")
            return {'error': str(e)}

    def get_stock_data_with_fallback(self, stock_code: str, start_date: str, end_date: str) -> str:
        """
        获取股票数据（兼容 stock_data_service 接口）

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            str: 格式化的股票数据报告
        """
        logger.info(f"📊 获取股票数据: {stock_code} ({start_date} 到 {end_date})")

        try:
            # 使用统一的数据获取接口
            return self.get_stock_data(stock_code, start_date, end_date)
        except Exception as e:
            logger.error(f"❌ 获取股票数据失败: {e}")
            return f"❌ 获取股票数据失败: {str(e)}\n\n💡 建议：\n1. 检查网络连接\n2. 确认股票代码格式正确\n3. 检查数据源配置"

    def _try_fallback_stock_info(self, symbol: str) -> Dict:
        """尝试使用备用数据源获取股票基本信息"""
        logger.error(f"🔄 {self.current_source.value}失败，尝试备用数据源获取股票信息...")

        # 获取所有可用数据源
        available_sources = self.available_sources.copy()

        # 移除当前数据源
        if self.current_source.value in available_sources:
            available_sources.remove(self.current_source.value)

        # 尝试所有备用数据源
        for source_name in available_sources:
            try:
                source = ChinaDataSource(source_name)
                logger.info(f"🔄 尝试备用数据源获取股票信息: {source_name}")

                # 根据数据源类型获取股票信息
                if source == ChinaDataSource.TUSHARE:
                    # 🔥 直接调用 Tushare 适配器，避免循环调用
                    result = self._get_tushare_stock_info(symbol)
                elif source == ChinaDataSource.AKSHARE:
                    result = self._get_akshare_stock_info(symbol)
                elif source == ChinaDataSource.BAOSTOCK:
                    result = self._get_baostock_stock_info(symbol)
                else:
                    # 尝试通用适配器
                    original_source = self.current_source
                    self.current_source = source
                    adapter = self.get_data_adapter()
                    self.current_source = original_source

                    if adapter and hasattr(adapter, 'get_stock_info'):
                        result = adapter.get_stock_info(symbol)
                    else:
                        logger.warning(f"⚠️ [股票信息] {source_name}不支持股票信息获取")
                        continue

                # 检查是否获取到有效信息
                if result.get('name') and result['name'] != f'股票{symbol}':
                    logger.info(f"✅ [数据来源: 备用数据源] 降级成功获取股票信息: {source_name}")
                    return result
                else:
                    logger.warning(f"⚠️ [数据来源: {source_name}] 返回无效信息")

            except Exception as e:
                logger.error(f"❌ 备用数据源{source_name}失败: {e}")
                continue

        # 所有数据源都失败，返回默认值
        logger.error(f"❌ 所有数据源都无法获取{symbol}的股票信息")
        return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'unknown'}

    def _get_akshare_stock_info(self, symbol: str) -> Dict:
        """使用AKShare获取股票基本信息

        🔥 重要：AKShare 需要区分股票和指数
        - 对于 000001，如果不加后缀，会被识别为"深圳成指"（指数）
        - 对于股票，需要使用完整代码（如 sz000001 或 sh600000）
        """
        try:
            import akshare as ak

            # 🔥 转换为 AKShare 格式的股票代码
            # AKShare 的 stock_individual_info_em 需要使用 "sz000001" 或 "sh600000" 格式
            if symbol.startswith('6'):
                # 上海股票：600000 -> sh600000
                akshare_symbol = f"sh{symbol}"
            elif symbol.startswith(('0', '3', '2')):
                # 深圳股票：000001 -> sz000001
                akshare_symbol = f"sz{symbol}"
            elif symbol.startswith(('8', '4')):
                # 北京股票：830000 -> bj830000
                akshare_symbol = f"bj{symbol}"
            else:
                # 其他情况，直接使用原始代码
                akshare_symbol = symbol

            logger.debug(f"📊 [AKShare股票信息] 原始代码: {symbol}, AKShare格式: {akshare_symbol}")

            # 尝试获取个股信息
            stock_info = ak.stock_individual_info_em(symbol=akshare_symbol)

            if stock_info is not None and not stock_info.empty:
                # 转换为字典格式
                info = {'symbol': symbol, 'source': 'akshare'}

                # 提取股票名称
                name_row = stock_info[stock_info['item'] == '股票简称']
                if not name_row.empty:
                    stock_name = name_row['value'].iloc[0]
                    info['name'] = stock_name
                    logger.info(f"✅ [AKShare股票信息] {symbol} -> {stock_name}")
                else:
                    info['name'] = f'股票{symbol}'
                    logger.warning(f"⚠️ [AKShare股票信息] 未找到股票简称: {symbol}")

                # 提取其他信息
                info['area'] = '未知'  # AKShare没有地区信息
                info['industry'] = '未知'  # 可以通过其他API获取
                info['market'] = '未知'  # 可以根据股票代码推断
                info['list_date'] = '未知'  # 可以通过其他API获取

                return info
            else:
                logger.warning(f"⚠️ [AKShare股票信息] 返回空数据: {symbol}")
                return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'akshare'}

        except Exception as e:
            logger.error(f"❌ [股票信息] AKShare获取失败: {symbol}, 错误: {e}")
            return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'akshare', 'error': str(e)}

    def _get_baostock_stock_info(self, symbol: str) -> Dict:
        """使用BaoStock获取股票基本信息"""
        try:
            import baostock as bs

            # 转换股票代码格式
            if symbol.startswith('6'):
                bs_code = f"sh.{symbol}"
            else:
                bs_code = f"sz.{symbol}"

            # 登录BaoStock
            lg = bs.login()
            if lg.error_code != '0':
                logger.error(f"❌ [股票信息] BaoStock登录失败: {lg.error_msg}")
                return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'baostock'}

            # 查询股票基本信息
            rs = bs.query_stock_basic(code=bs_code)
            if rs.error_code != '0':
                bs.logout()
                logger.error(f"❌ [股票信息] BaoStock查询失败: {rs.error_msg}")
                return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'baostock'}

            # 解析结果
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            # 登出
            bs.logout()

            if data_list:
                info = {'symbol': symbol, 'source': 'baostock'}
                row = data_list[0] if len(data_list) > 0 else []
                info['name'] = row[1] if len(row) > 1 else f'股票{symbol}'
                info['area'] = '未知'
                info['industry'] = '未知'
                info['market'] = '未知'
                info['list_date'] = row[2] if len(row) > 2 else '未知'

                return info
            else:
                return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'baostock'}

        except Exception as e:
            logger.error(f"❌ [股票信息] BaoStock获取失败: {e}")
            return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'baostock', 'error': str(e)}

    def _parse_stock_info_string(self, info_str: str, symbol: str) -> Dict:
        """解析股票信息字符串为字典"""
        try:
            info = {'symbol': symbol, 'source': self.current_source.value}
            lines = info_str.split('\n')

            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    if '股票名称' in key:
                        info['name'] = value
                    elif '所属行业' in key:
                        info['industry'] = value
                    elif '所属地区' in key:
                        info['area'] = value
                    elif '上市市场' in key:
                        info['market'] = value
                    elif '上市日期' in key:
                        info['list_date'] = value

            return info

        except Exception as e:
            logger.error(f"⚠️ 解析股票信息失败: {e}")
            return {'symbol': symbol, 'name': f'股票{symbol}', 'source': self.current_source.value}

    # ==================== 基本面数据获取方法 ====================

    def _get_mongodb_fundamentals(self, symbol: str) -> str:
        """从 MongoDB 获取财务数据"""
        logger.debug(f"📊 [MongoDB] 调用参数: symbol={symbol}")

        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
            import pandas as pd
            adapter = get_mongodb_cache_adapter()

            # 从 MongoDB 获取财务数据
            financial_data = adapter.get_financial_data(symbol)

            # 检查数据类型和内容
            if financial_data is not None:
                # 如果是 DataFrame，转换为字典列表
                if isinstance(financial_data, pd.DataFrame):
                    if not financial_data.empty:
                        logger.info(f"✅ [数据来源: MongoDB-财务数据] 成功获取: {symbol} ({len(financial_data)}条记录)")
                        # 转换为字典列表
                        financial_dict_list = financial_data.to_dict('records')
                        # 格式化财务数据为报告
                        return self._format_financial_data(symbol, financial_dict_list)
                    else:
                        logger.warning(f"⚠️ [数据来源: MongoDB] 财务数据为空: {symbol}，降级到其他数据源")
                        return self._try_fallback_fundamentals(symbol)
                # 如果是列表
                elif isinstance(financial_data, list) and len(financial_data) > 0:
                    logger.info(f"✅ [数据来源: MongoDB-财务数据] 成功获取: {symbol} ({len(financial_data)}条记录)")
                    return self._format_financial_data(symbol, financial_data)
                # 如果是单个字典（这是MongoDB实际返回的格式）
                elif isinstance(financial_data, dict):
                    logger.info(f"✅ [数据来源: MongoDB-财务数据] 成功获取: {symbol} (单条记录)")
                    # 将单个字典包装成列表
                    financial_dict_list = [financial_data]
                    return self._format_financial_data(symbol, financial_dict_list)
                else:
                    logger.warning(f"⚠️ [数据来源: MongoDB] 未找到财务数据: {symbol}，降级到其他数据源")
                    return self._try_fallback_fundamentals(symbol)
            else:
                logger.warning(f"⚠️ [数据来源: MongoDB] 未找到财务数据: {symbol}，降级到其他数据源")
                # MongoDB 没有数据，降级到其他数据源
                return self._try_fallback_fundamentals(symbol)

        except Exception as e:
            logger.error(f"❌ [数据来源: MongoDB异常] 获取财务数据失败: {e}", exc_info=True)
            # MongoDB 异常，降级到其他数据源
            return self._try_fallback_fundamentals(symbol)

    def _get_tushare_fundamentals(self, symbol: str) -> str:
        """从 Tushare 获取基本面数据 - 暂时不可用，需要实现"""
        logger.warning(f"⚠️ Tushare基本面数据功能暂时不可用")
        return f"⚠️ Tushare基本面数据功能暂时不可用，请使用其他数据源"

    def _get_akshare_fundamentals(self, symbol: str) -> str:
        """从 AKShare 获取真实基本面数据（财务指标+三大报表+估值指标）"""
        logger.debug(f"📊 [AKShare] 获取基本面数据: symbol={symbol}")

        try:
            import akshare as ak
            import numpy as np
            result_parts = []
            result_parts.append(f"📊 {symbol} 基本面分析（AKShare）\n")

            # 1. 获取估值指标（PE/PB/市值/换手率）从 stock_zh_a_spot_em
            try:
                spot_df = ak.stock_zh_a_spot_em()
                if spot_df is not None and not spot_df.empty:
                    stock_row = spot_df[spot_df['代码'] == symbol]
                    if not stock_row.empty:
                        row = stock_row.iloc[0]
                        result_parts.append("📈 估值指标:")
                        pe_val = row.get('市盈率-动态', None)
                        pb_val = row.get('市净率', None)
                        mv_val = row.get('总市值', None)
                        circ_val = row.get('流通市值', None)
                        tr_val = row.get('换手率', None)
                        vr_val = row.get('量比', None)

                        def safe_fmt(val, unit='', divide=1):
                            if val is None or (isinstance(val, float) and np.isnan(val)):
                                return 'N/A'
                            try:
                                v = float(val) / divide
                                return f"{v:.2f}{unit}"
                            except (ValueError, TypeError):
                                return 'N/A'

                        result_parts.append(f"  PE(动态): {safe_fmt(pe_val)}")
                        result_parts.append(f"  PB: {safe_fmt(pb_val)}")
                        result_parts.append(f"  总市值: {safe_fmt(mv_val, '亿元', 1e8)}")
                        result_parts.append(f"  流通市值: {safe_fmt(circ_val, '亿元', 1e8)}")
                        result_parts.append(f"  换手率: {safe_fmt(tr_val, '%')}")
                        result_parts.append(f"  量比: {safe_fmt(vr_val)}")
                        result_parts.append("")
                        logger.info(f"✅ [AKShare-基本面] 获取{symbol}估值指标成功")
            except Exception as e:
                logger.warning(f"⚠️ [AKShare-基本面] 获取估值指标失败: {e}")
                # AKShare估值指标失败时，尝试从东方财富直连获取
                try:
                    import asyncio
                    from tradingagents.dataflows.providers.china.eastmoney_direct import EastMoneyDirectProvider
                    em = EastMoneyDirectProvider()
                    loop = asyncio.new_event_loop()
                    try:
                        em_result = loop.run_until_complete(em.get_stock_quotes(symbol))
                    finally:
                        loop.close()
                    if em_result is not None and isinstance(em_result, pd.DataFrame) and not em_result.empty:
                        row = em_result.iloc[0]
                        result_parts.append("📈 估值指标（东方财富直连）:")
                        def safe_fmt_em(val, unit='', divide=1):
                            if val is None or (isinstance(val, float) and np.isnan(val)):
                                return 'N/A'
                            try:
                                v = float(val) / divide
                                return f"{v:.2f}{unit}"
                            except (ValueError, TypeError):
                                return 'N/A'
                        result_parts.append(f"  PE(TTM): {safe_fmt_em(row.get('pe_ttm', row.get('PE(TTM)', None)))}")
                        result_parts.append(f"  PB: {safe_fmt_em(row.get('pb', row.get('PB', None)))}")
                        result_parts.append(f"  总市值: {safe_fmt_em(row.get('total_mv', row.get('总市值', None)), '亿元', 1e8)}")
                        result_parts.append(f"  换手率: {safe_fmt_em(row.get('turnover_rate', row.get('换手率', None)), '%')}")
                        result_parts.append(f"  量比: {safe_fmt_em(row.get('volume_ratio', row.get('量比', None)))}")
                        result_parts.append("")
                        logger.info(f"✅ [东方财富-基本面] 获取{symbol}估值指标成功")
                except Exception as em_e:
                    logger.warning(f"⚠️ [东方财富-基本面] 获取估值指标也失败: {em_e}")
                    # 东方财富也失败时，尝试新浪财经
                    try:
                        import asyncio
                        from tradingagents.dataflows.providers.china.sina_finance import SinaFinanceProvider
                        sina = SinaFinanceProvider()
                        sina_result = asyncio.get_event_loop().run_until_complete(sina.get_stock_quotes(symbol))
                        if sina_result is not None and isinstance(sina_result, pd.DataFrame) and not sina_result.empty:
                            row = sina_result.iloc[0]
                            result_parts.append("📈 估值指标（新浪财经）:")
                            def safe_fmt_sina(val, unit='', divide=1):
                                if val is None or (isinstance(val, float) and np.isnan(val)):
                                    return 'N/A'
                                try:
                                    v = float(val) / divide
                                    return f"{v:.2f}{unit}"
                                except (ValueError, TypeError):
                                    return 'N/A'
                            result_parts.append(f"  当前价: {safe_fmt_sina(row.get('price', row.get('当前价', None)))}元")
                            result_parts.append(f"  涨跌幅: {safe_fmt_sina(row.get('change_pct', row.get('涨跌幅', None)))}%")
                            result_parts.append(f"  成交量: {safe_fmt_sina(row.get('volume', row.get('成交量', None)))}手")
                            result_parts.append("")
                            logger.info(f"✅ [新浪财经-基本面] 获取{symbol}行情成功")
                    except Exception as sina_e:
                        logger.warning(f"⚠️ [新浪财经-基本面] 获取行情也失败: {sina_e}")

            # 2. 获取财务分析指标（ROE/ROA/毛利率/净利率等）
            try:
                fin_df = ak.stock_financial_analysis_indicator(symbol=symbol)
                if fin_df is None or fin_df.empty:
                    # AKShare接口返回空数据时，使用BaoStock获取盈利能力数据
                    try:
                        import baostock as bs
                        lg = bs.login()
                        if lg.error_code == '0':
                            bs_code = f"sz.{symbol}" if symbol.startswith('0') or symbol.startswith('3') else f"sh.{symbol}"
                            current_year = datetime.now().year
                            profit_rows = []
                            for q in range(4, 0, -1):
                                rs = bs.query_profit_data(code=bs_code, year=current_year, quarter=q)
                                while (rs.error_code == '0') and rs.next():
                                    profit_rows.append(rs.get_row_data())
                                if profit_rows:
                                    break
                            if not profit_rows:
                                for q in range(4, 0, -1):
                                    rs = bs.query_profit_data(code=bs_code, year=current_year - 1, quarter=q)
                                    while (rs.error_code == '0') and rs.next():
                                        profit_rows.append(rs.get_row_data())
                                    if profit_rows:
                                        break
                            bs.logout()
                            if profit_rows:
                                result_parts.append("💰 财务指标（BaoStock盈利能力）:")
                                for row_data in profit_rows[:4]:
                                    result_parts.append(f"  报告期: {row_data[1] if len(row_data) > 1 else '未知'}")
                                    def safe_bs(idx, default='N/A'):
                                        try:
                                            val = row_data[idx] if len(row_data) > idx else default
                                            if val is None or val == '':
                                                return 'N/A'
                                            return f"{float(val):.2f}"
                                        except (ValueError, TypeError, IndexError):
                                            return 'N/A'
                                    result_parts.append(f"    ROE: {safe_bs(2)}%")
                                    result_parts.append(f"    净利率: {safe_bs(3)}%")
                                    result_parts.append(f"    毛利率: {safe_bs(4)}%")
                                    result_parts.append(f"    净利润(元): {safe_bs(5)}")
                                result_parts.append("")
                                logger.info(f"✅ [BaoStock-基本面] 获取{symbol}盈利能力成功({len(profit_rows)}期)")
                                fin_df = None  # 标记已处理
                    except Exception as bs_e:
                        logger.warning(f"⚠️ [BaoStock-基本面] 获取盈利能力失败: {bs_e}")
                if fin_df is not None and not fin_df.empty:
                    result_parts.append("💰 财务指标:")
                    for i in range(min(4, len(fin_df))):
                        row = fin_df.iloc[i]
                        date_val = row.get('日期', row.iloc[0] if len(row) > 0 else '未知')
                        result_parts.append(f"  报告期: {date_val}")

                        def safe_get(key, default='N/A'):
                            val = row.get(key, default)
                            if val is None or (isinstance(val, float) and np.isnan(val)):
                                return 'N/A'
                            try:
                                return f"{float(val):.2f}"
                            except (ValueError, TypeError):
                                return str(val) if val else 'N/A'

                        result_parts.append(f"    ROE: {safe_get('净资产收益率(%)')}%")
                        result_parts.append(f"    ROA: {safe_get('总资产净利率(%)')}%")
                        result_parts.append(f"    毛利率: {safe_get('销售毛利率(%)')}%")
                        result_parts.append(f"    净利率: {safe_get('销售净利率(%)')}%")
                        result_parts.append(f"    资产负债率: {safe_get('资产负债率(%)')}%")
                        result_parts.append(f"    流动比率: {safe_get('流动比率')}")
                        result_parts.append(f"    速动比率: {safe_get('速动比率')}")
                    result_parts.append("")
                    logger.info(f"✅ [AKShare-基本面] 获取{symbol}财务指标成功({min(4, len(fin_df))}期)")
            except Exception as e:
                logger.warning(f"⚠️ [AKShare-基本面] 获取财务指标失败: {e}")

            # 3. 获取利润表
            try:
                income_df = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
                if income_df is None:
                    income_df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
                if income_df is not None and not income_df.empty:
                    result_parts.append("📋 利润表:")
                    date_col = None
                    for col_name in ['报告日', 'REPORT_DATE', '日期', 'REPORT_DATE_NAME', '报告期']:
                        if col_name in income_df.columns:
                            date_col = col_name
                            break
                    if date_col is None and len(income_df.columns) > 0:
                        date_col = income_df.columns[0]
                    for i in range(min(2, len(income_df))):
                        row = income_df.iloc[i]
                        date_val = '未知'
                        if date_col and date_col in income_df.columns:
                            date_val = row.get(date_col, '未知')
                            if isinstance(date_val, str) and len(date_val) >= 10:
                                date_val = date_val[:10]

                        def safe_big(key, unit='亿元', divide=1e8):
                            val = row.get(key, None)
                            if val is None or (isinstance(val, float) and np.isnan(val)):
                                return 'N/A'
                            try:
                                return f"{float(val)/divide:.2f}{unit}"
                            except (ValueError, TypeError):
                                return 'N/A'

                        result_parts.append(f"  报告期: {date_val}")
                        result_parts.append(f"    营业收入: {safe_big('营业收入')}")
                        result_parts.append(f"    营业总成本: {safe_big('营业总成本')}")
                        result_parts.append(f"    净利润: {safe_big('净利润')}")
                        result_parts.append(f"    归母净利润: {safe_big('归属于母公司所有者的净利润')}")
                        result_parts.append(f"    营业利润: {safe_big('营业利润')}")
                    result_parts.append("")
                    logger.info(f"✅ [AKShare-基本面] 获取{symbol}利润表成功")
                else:
                    logger.warning(f"⚠️ [AKShare-基本面] 利润表数据为空")
            except Exception as e:
                logger.warning(f"⚠️ [AKShare-基本面] 获取利润表失败: {e}")

            # 4. 获取现金流量表
            try:
                cashflow_df = ak.stock_financial_report_sina(stock=symbol, symbol="现金流量表")
                if cashflow_df is None:
                    cashflow_df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
                if cashflow_df is not None and not cashflow_df.empty:
                    result_parts.append("💵 现金流量表:")
                    date_col = None
                    for col_name in ['报告日', 'REPORT_DATE', '日期', 'REPORT_DATE_NAME', '报告期']:
                        if col_name in cashflow_df.columns:
                            date_col = col_name
                            break
                    if date_col is None and len(cashflow_df.columns) > 0:
                        date_col = cashflow_df.columns[0]
                    for i in range(min(2, len(cashflow_df))):
                        row = cashflow_df.iloc[i]
                        date_val = '未知'
                        if date_col and date_col in cashflow_df.columns:
                            date_val = row.get(date_col, '未知')
                            if isinstance(date_val, str) and len(date_val) >= 10:
                                date_val = date_val[:10]

                        def safe_big2(key, unit='亿元', divide=1e8):
                            val = row.get(key, None)
                            if val is None or (isinstance(val, float) and np.isnan(val)):
                                return 'N/A'
                            try:
                                return f"{float(val)/divide:.2f}{unit}"
                            except (ValueError, TypeError):
                                return 'N/A'

                        result_parts.append(f"  报告期: {date_val}")
                        result_parts.append(f"    经营现金流: {safe_big2('经营活动产生的现金流量')}")
                        result_parts.append(f"    销售收到现金: {safe_big2('销售商品、提供劳务收到的现金')}")
                        result_parts.append(f"    购买支付现金: {safe_big2('购买商品、接受劳务支付的现金')}")
                    result_parts.append("")
                    logger.info(f"✅ [AKShare-基本面] 获取{symbol}现金流量表成功")
            except Exception as e:
                logger.warning(f"⚠️ [AKShare-基本面] 获取现金流量表失败: {e}")

            output = "\n".join(result_parts)
            if len(output) > 50:
                logger.info(f"✅ [AKShare-基本面] 成功获取{symbol}基本面数据({len(output)}字符)")
                return output
            else:
                logger.warning(f"⚠️ [AKShare-基本面] 数据不足({len(output)}字符)，降级到生成分析")
                return self._generate_fundamentals_analysis(symbol)

        except Exception as e:
            logger.error(f"❌ [AKShare-基本面] 获取基本面数据失败: {e}")
            return f"❌ 获取{symbol}基本面数据失败: {e}"

    def _get_eastmoney_fundamentals(self, symbol: str) -> str:
        """从东方财富直接API获取基本面数据"""
        try:
            import asyncio
            from tradingagents.dataflows.providers.china.eastmoney_direct import EastMoneyDirectProvider

            provider = EastMoneyDirectProvider()

            # 获取实时行情（含PE/PB等估值指标）和财务数据
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.connect())
                        future.result(timeout=15)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.get_stock_quotes(symbol))
                        quotes = future.result(timeout=15)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, provider.get_financial_data(symbol))
                        financial = future.result(timeout=15)
                else:
                    asyncio.run(provider.connect())
                    quotes = asyncio.run(provider.get_stock_quotes(symbol))
                    financial = asyncio.run(provider.get_financial_data(symbol))
            except RuntimeError:
                asyncio.run(provider.connect())
                quotes = asyncio.run(provider.get_stock_quotes(symbol))
                financial = asyncio.run(provider.get_financial_data(symbol))

            # 格式化基本面报告
            result_parts = []
            result_parts.append(f"📊 {symbol} 基本面分析（东方财富直连）\n")

            if quotes:
                result_parts.append("📈 估值指标:")
                result_parts.append(f"  PE(TTM): {quotes.get('pe_ttm', 'N/A')}")
                result_parts.append(f"  PE(动态): {quotes.get('pe_dynamic', 'N/A')}")
                result_parts.append(f"  PB: {quotes.get('pb', 'N/A')}")
                result_parts.append(f"  总市值: {quotes.get('total_mv', 'N/A')}")
                result_parts.append(f"  流通市值: {quotes.get('circ_mv', 'N/A')}")
                result_parts.append(f"  换手率: {quotes.get('turnover_rate', 'N/A')}%")
                result_parts.append("")

            if financial and financial.get("periods"):
                result_parts.append("💰 财务数据:")
                for period_data in financial["periods"][:4]:
                    report_date = period_data.get("report_date", "未知")
                    if isinstance(report_date, str) and len(report_date) >= 10:
                        report_date = report_date[:10]
                    result_parts.append(f"  报告期: {report_date}")
                    result_parts.append(f"    EPS: {period_data.get('basic_eps', 'N/A')}")
                    result_parts.append(f"    ROE: {period_data.get('roe', 'N/A')}%")
                    result_parts.append(f"    毛利率: {period_data.get('gross_margin', 'N/A')}%")
                    result_parts.append(f"    营收: {period_data.get('revenue', 'N/A')}")
                    result_parts.append(f"    营收同比: {period_data.get('revenue_yoy', 'N/A')}%")
                    result_parts.append(f"    净利润: {period_data.get('net_profit', 'N/A')}")
                    result_parts.append(f"    净利润同比: {period_data.get('net_profit_yoy', 'N/A')}%")
                result_parts.append("")

            output = "\n".join(result_parts)
            if len(output) > 50:
                logger.info(f"✅ [东方财富直连] 成功获取{symbol}基本面数据")
                return output
            else:
                return f"⚠️ 东方财富直连获取{symbol}基本面数据不完整"

        except ImportError:
            return f"❌ 东方财富直连依赖库未安装"
        except Exception as e:
            logger.error(f"❌ [东方财富直连] 获取基本面失败: {e}", exc_info=True)
            return f"❌ 东方财富直连获取{symbol}基本面失败: {e}"

    def _get_valuation_indicators(self, symbol: str) -> Dict:
        """从stock_basic_info集合获取估值指标"""
        try:
            db_manager = get_database_manager()
            if not db_manager.is_mongodb_available():
                return {}
                
            client = db_manager.get_mongodb_client()
            db = client[db_manager.config.mongodb_config.database_name]
            
            # 从stock_basic_info集合获取估值指标
            collection = db['stock_basic_info']
            result = collection.find_one({'ts_code': symbol})
            
            if result:
                return {
                    'pe': result.get('pe'),
                    'pb': result.get('pb'),
                    'pe_ttm': result.get('pe_ttm'),
                    'total_mv': result.get('total_mv'),
                    'circ_mv': result.get('circ_mv')
                }
            return {}
            
        except Exception as e:
            logger.error(f"获取{symbol}估值指标失败: {e}")
            return {}

    def _format_financial_data(self, symbol: str, financial_data: List[Dict]) -> str:
        """格式化财务数据为报告"""
        try:
            if not financial_data or len(financial_data) == 0:
                return f"❌ 未找到{symbol}的财务数据"

            # 获取最新的财务数据
            latest = financial_data[0]

            # 构建报告
            report = f"📊 {symbol} 基本面数据（来自MongoDB）\n\n"

            # 基本信息
            report += f"📅 报告期: {latest.get('report_period', latest.get('end_date', '未知'))}\n"
            report += f"📈 数据来源: MongoDB财务数据库\n\n"

            # 财务指标
            report += "💰 财务指标:\n"
            revenue = latest.get('revenue') or latest.get('total_revenue')
            if revenue is not None:
                report += f"   营业总收入: {revenue:,.2f}\n"
            
            net_profit = latest.get('net_profit') or latest.get('net_income')
            if net_profit is not None:
                report += f"   净利润: {net_profit:,.2f}\n"
                
            total_assets = latest.get('total_assets')
            if total_assets is not None:
                report += f"   总资产: {total_assets:,.2f}\n"
                
            total_liab = latest.get('total_liab')
            if total_liab is not None:
                report += f"   总负债: {total_liab:,.2f}\n"
                
            total_equity = latest.get('total_equity')
            if total_equity is not None:
                report += f"   股东权益: {total_equity:,.2f}\n"

            # 估值指标 - 从stock_basic_info集合获取
            report += "\n📊 估值指标:\n"
            valuation_data = self._get_valuation_indicators(symbol)
            if valuation_data:
                pe = valuation_data.get('pe')
                if pe is not None:
                    report += f"   市盈率(PE): {pe:.2f}\n"
                    
                pb = valuation_data.get('pb')
                if pb is not None:
                    report += f"   市净率(PB): {pb:.2f}\n"
                    
                pe_ttm = valuation_data.get('pe_ttm')
                if pe_ttm is not None:
                    report += f"   市盈率TTM(PE_TTM): {pe_ttm:.2f}\n"
                    
                total_mv = valuation_data.get('total_mv')
                if total_mv is not None:
                    report += f"   总市值: {total_mv:.2f}亿元\n"
                    
                circ_mv = valuation_data.get('circ_mv')
                if circ_mv is not None:
                    report += f"   流通市值: {circ_mv:.2f}亿元\n"
            else:
                # 如果无法从stock_basic_info获取，尝试从财务数据计算
                pe = latest.get('pe')
                if pe is not None:
                    report += f"   市盈率(PE): {pe:.2f}\n"
                    
                pb = latest.get('pb')
                if pb is not None:
                    report += f"   市净率(PB): {pb:.2f}\n"
                    
                ps = latest.get('ps')
                if ps is not None:
                    report += f"   市销率(PS): {ps:.2f}\n"

            # 盈利能力
            report += "\n💹 盈利能力:\n"
            roe = latest.get('roe')
            if roe is not None:
                report += f"   净资产收益率(ROE): {roe:.2f}%\n"
                
            roa = latest.get('roa')
            if roa is not None:
                report += f"   总资产收益率(ROA): {roa:.2f}%\n"
                
            gross_margin = latest.get('gross_margin')
            if gross_margin is not None:
                report += f"   毛利率: {gross_margin:.2f}%\n"
                
            netprofit_margin = latest.get('netprofit_margin') or latest.get('net_margin')
            if netprofit_margin is not None:
                report += f"   净利率: {netprofit_margin:.2f}%\n"

            # 现金流
            n_cashflow_act = latest.get('n_cashflow_act')
            if n_cashflow_act is not None:
                report += "\n💰 现金流:\n"
                report += f"   经营活动现金流: {n_cashflow_act:,.2f}\n"
                
                n_cashflow_inv_act = latest.get('n_cashflow_inv_act')
                if n_cashflow_inv_act is not None:
                    report += f"   投资活动现金流: {n_cashflow_inv_act:,.2f}\n"
                    
                c_cash_equ_end_period = latest.get('c_cash_equ_end_period')
                if c_cash_equ_end_period is not None:
                    report += f"   期末现金及等价物: {c_cash_equ_end_period:,.2f}\n"

            report += f"\n📝 共有 {len(financial_data)} 期财务数据\n"

            return report

        except Exception as e:
            logger.error(f"❌ 格式化财务数据失败: {e}")
            return f"❌ 格式化{symbol}财务数据失败: {e}"

    def _generate_fundamentals_analysis(self, symbol: str) -> str:
        """生成基本的基本面分析"""
        try:
            # 获取股票基本信息
            stock_info = self.get_stock_info(symbol)

            report = f"📊 {symbol} 基本面分析（生成）\n\n"
            report += f"📈 股票名称: {stock_info.get('name', '未知')}\n"
            report += f"🏢 所属行业: {stock_info.get('industry', '未知')}\n"
            report += f"📍 所属地区: {stock_info.get('area', '未知')}\n"
            report += f"📅 上市日期: {stock_info.get('list_date', '未知')}\n"
            report += f"🏛️ 交易所: {stock_info.get('exchange', '未知')}\n\n"

            report += "⚠️ 注意: 详细财务数据需要从数据源获取\n"
            report += "💡 建议: 启用MongoDB缓存以获取完整的财务数据\n"

            return report

        except Exception as e:
            logger.error(f"❌ 生成基本面分析失败: {e}")
            return f"❌ 生成{symbol}基本面分析失败: {e}"

    def _try_fallback_fundamentals(self, symbol: str) -> str:
        """基本面数据降级处理"""
        logger.error(f"🔄 {self.current_source.value}失败，尝试备用数据源获取基本面...")

        # 🔥 从数据库获取数据源优先级顺序（根据股票代码识别市场）
        fallback_order = self._get_data_source_priority_order(symbol)

        for source in fallback_order:
            if source != self.current_source and source in self.available_sources:
                try:
                    logger.info(f"🔄 尝试备用数据源获取基本面: {source.value}")

                    # 直接调用具体的数据源方法，避免递归
                    if source == ChinaDataSource.TUSHARE:
                        result = self._get_tushare_fundamentals(symbol)
                    elif source == ChinaDataSource.AKSHARE:
                        result = self._get_akshare_fundamentals(symbol)
                    elif source == ChinaDataSource.EASTMONEY:
                        # 东方财富直连可以提供财务数据
                        result = self._get_eastmoney_fundamentals(symbol)
                    else:
                        continue

                    if result and "❌" not in result:
                        logger.info(f"✅ [数据来源: 备用数据源] 降级成功获取基本面: {source.value}")
                        return result
                    else:
                        logger.warning(f"⚠️ 备用数据源{source.value}返回错误结果")

                except Exception as e:
                    logger.error(f"❌ 备用数据源{source.value}异常: {e}")
                    continue

        # 所有数据源都失败，生成基本分析
        logger.warning(f"⚠️ [数据来源: 生成分析] 所有数据源失败，生成基本分析: {symbol}")
        return self._generate_fundamentals_analysis(symbol)

    def _get_mongodb_news(self, symbol: str, hours_back: int, limit: int) -> List[Dict[str, Any]]:
        """从MongoDB获取新闻数据"""
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
            adapter = get_mongodb_cache_adapter()

            # 从MongoDB获取新闻数据
            news_data = adapter.get_news_data(symbol, hours_back=hours_back, limit=limit)

            if news_data and len(news_data) > 0:
                logger.info(f"✅ [数据来源: MongoDB-新闻] 成功获取: {symbol or '市场新闻'} ({len(news_data)}条)")
                return news_data
            else:
                logger.warning(f"⚠️ [数据来源: MongoDB] 未找到新闻: {symbol or '市场新闻'}，降级到其他数据源")
                return self._try_fallback_news(symbol, hours_back, limit)

        except Exception as e:
            logger.error(f"❌ [数据来源: MongoDB] 获取新闻失败: {e}")
            return self._try_fallback_news(symbol, hours_back, limit)

    def _get_tushare_news(self, symbol: str, hours_back: int, limit: int) -> List[Dict[str, Any]]:
        """从Tushare获取新闻数据"""
        try:
            # Tushare新闻功能暂时不可用，返回空列表
            logger.warning(f"⚠️ [数据来源: Tushare] Tushare新闻功能暂时不可用")
            return []

        except Exception as e:
            logger.error(f"❌ [数据来源: Tushare] 获取新闻失败: {e}")
            return []

    def _get_akshare_news(self, symbol: str, hours_back: int, limit: int) -> List[Dict[str, Any]]:
        """从AKShare获取新闻数据"""
        try:
            # AKShare新闻功能暂时不可用，返回空列表
            logger.warning(f"⚠️ [数据来源: AKShare] AKShare新闻功能暂时不可用")
            return []

        except Exception as e:
            logger.error(f"❌ [数据来源: AKShare] 获取新闻失败: {e}")
            return []

    def _try_fallback_news(self, symbol: str, hours_back: int, limit: int) -> List[Dict[str, Any]]:
        """新闻数据降级处理"""
        logger.error(f"🔄 {self.current_source.value}失败，尝试备用数据源获取新闻...")

        # 🔥 从数据库获取数据源优先级顺序（根据股票代码识别市场）
        fallback_order = self._get_data_source_priority_order(symbol)

        for source in fallback_order:
            if source != self.current_source and source in self.available_sources:
                try:
                    logger.info(f"🔄 尝试备用数据源获取新闻: {source.value}")

                    # 直接调用具体的数据源方法，避免递归
                    if source == ChinaDataSource.TUSHARE:
                        result = self._get_tushare_news(symbol, hours_back, limit)
                    elif source == ChinaDataSource.AKSHARE:
                        result = self._get_akshare_news(symbol, hours_back, limit)
                    else:
                        continue

                    if result and len(result) > 0:
                        logger.info(f"✅ [数据来源: 备用数据源] 降级成功获取新闻: {source.value}")
                        return result
                    else:
                        logger.warning(f"⚠️ 备用数据源{source.value}未返回新闻")

                except Exception as e:
                    logger.error(f"❌ 备用数据源{source.value}异常: {e}")
                    continue

        # 所有数据源都失败
        logger.warning(f"⚠️ [数据来源: 所有数据源失败] 无法获取新闻: {symbol or '市场新闻'}")
        return []


# 全局数据源管理器实例
_data_source_manager = None
_manager_lock = threading.Lock()

def get_data_source_manager() -> DataSourceManager:
    global _data_source_manager
    if _data_source_manager is None:
        with _manager_lock:
            if _data_source_manager is None:
                _data_source_manager = DataSourceManager()
    return _data_source_manager


def get_china_stock_data_unified(symbol: str, start_date: str, end_date: str) -> str:
    """
    统一的中国股票数据获取接口
    自动使用配置的数据源，支持备用数据源

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        str: 格式化的股票数据
    """
    from tradingagents.utils.logging_init import get_logger


    # 添加详细的股票代码追踪日志
    logger.info(f"🔍 [股票代码追踪] data_source_manager.get_china_stock_data_unified 接收到的股票代码: '{symbol}' (类型: {type(symbol)})")
    logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(symbol))}")
    logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(symbol))}")

    manager = get_data_source_manager()
    logger.info(f"🔍 [股票代码追踪] 调用 manager.get_stock_data，传入参数: symbol='{symbol}', start_date='{start_date}', end_date='{end_date}'")
    result = manager.get_stock_data(symbol, start_date, end_date)
    # 分析返回结果的详细信息
    if result:
        lines = result.split('\n')
        data_lines = [line for line in lines if '2025-' in line and symbol in line]
        logger.info(f"🔍 [股票代码追踪] 返回结果统计: 总行数={len(lines)}, 数据行数={len(data_lines)}, 结果长度={len(result)}字符")
        logger.info(f"🔍 [股票代码追踪] 返回结果前500字符: {result[:500]}")
        if len(data_lines) > 0:
            logger.info(f"🔍 [股票代码追踪] 数据行示例: 第1行='{data_lines[0][:100]}', 最后1行='{data_lines[-1][:100]}'")
    else:
        logger.info(f"🔍 [股票代码追踪] 返回结果: None")
    return result


def get_china_stock_info_unified(symbol: str) -> Dict:
    """
    统一的中国股票信息获取接口

    Args:
        symbol: 股票代码

    Returns:
        Dict: 股票基本信息
    """
    manager = get_data_source_manager()
    return manager.get_stock_info(symbol)


# ==================== 兼容性接口 ====================
# 为了兼容 stock_data_service，提供相同的接口

def get_stock_data_service() -> DataSourceManager:
    """
    获取股票数据服务实例（兼容 stock_data_service 接口）

    ⚠️ 此函数为兼容性接口，实际返回 DataSourceManager 实例
    推荐直接使用 get_data_source_manager()
    """
    return get_data_source_manager()


# ==================== 美股数据源管理器 ====================

class USDataSourceManager:
    """
    美股数据源管理器

    支持的数据源：
    - yfinance: 股票价格和技术指标（免费）
    - alpha_vantage: 基本面和新闻数据（需要API Key）
    - finnhub: 备用数据源（需要API Key）
    - mongodb: 缓存数据源（最高优先级）
    """

    def __init__(self):
        """初始化美股数据源管理器"""
        # 检查是否启用 MongoDB 缓存
        self.use_mongodb_cache = self._check_mongodb_enabled()

        # 检查可用的数据源
        self.available_sources = self._check_available_sources()

        # 设置默认数据源
        self.default_source = self._get_default_source()
        self.current_source = self.default_source

        logger.info(f"📊 美股数据源管理器初始化完成")
        logger.info(f"   MongoDB缓存: {'✅ 已启用' if self.use_mongodb_cache else '❌ 未启用'}")
        logger.info(f"   默认数据源: {self.default_source.value}")
        logger.info(f"   可用数据源: {[s.value for s in self.available_sources]}")

    def _check_mongodb_enabled(self) -> bool:
        """检查是否启用MongoDB缓存"""
        from tradingagents.config.runtime_settings import use_app_cache_enabled
        return use_app_cache_enabled()

    def _get_data_source_priority_order(self, symbol: Optional[str] = None) -> List[USDataSource]:
        """
        从数据库获取美股数据源优先级顺序（用于降级）

        Args:
            symbol: 股票代码

        Returns:
            按优先级排序的数据源列表（不包含MongoDB）
        """
        try:
            # 从数据库读取数据源配置
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()

            # 方法1: 从 datasource_groupings 集合读取（推荐）
            groupings_collection = db.datasource_groupings
            groupings = list(groupings_collection.find({
                "market_category_id": "us_stocks",
                "enabled": True
            }).sort("priority", -1))  # 降序排序，优先级高的在前

            if groupings:
                # 转换为 USDataSource 枚举
                # 🔥 数据源名称映射（数据库名称 → USDataSource 枚举）
                source_mapping = {
                    'yfinance': USDataSource.YFINANCE,
                    'yahoo_finance': USDataSource.YFINANCE,  # 别名
                    'alpha_vantage': USDataSource.ALPHA_VANTAGE,
                    'finnhub': USDataSource.FINNHUB,
                }

                result = []
                for grouping in groupings:
                    ds_name = grouping.get('data_source_name', '').lower()
                    if ds_name in source_mapping:
                        source = source_mapping[ds_name]
                        # 排除 MongoDB（MongoDB 是最高优先级，不参与降级）
                        if source != USDataSource.MONGODB and source in self.available_sources:
                            result.append(source)

                if result:
                    logger.info(f"✅ [美股数据源优先级] 从数据库读取: {[s.value for s in result]}")
                    return result

            logger.warning("⚠️ [美股数据源优先级] 数据库中没有配置，使用默认顺序")
        except Exception as e:
            logger.warning(f"⚠️ [美股数据源优先级] 从数据库读取失败: {e}，使用默认顺序")

        # 回退到默认顺序
        # 默认顺序：yfinance > Alpha Vantage > Finnhub
        default_order = [
            USDataSource.YFINANCE,
            USDataSource.ALPHA_VANTAGE,
            USDataSource.FINNHUB,
        ]
        # 只返回可用的数据源
        return [s for s in default_order if s in self.available_sources]

    def _get_default_source(self) -> USDataSource:
        """获取默认数据源"""
        # 如果启用MongoDB缓存，MongoDB作为最高优先级数据源
        if self.use_mongodb_cache:
            return USDataSource.MONGODB

        # 从环境变量获取，默认使用 yfinance
        env_source = os.getenv('DEFAULT_US_DATA_SOURCE', DataSourceCode.YFINANCE).lower()

        # 映射到枚举
        source_mapping = {
            DataSourceCode.YFINANCE: USDataSource.YFINANCE,
            DataSourceCode.ALPHA_VANTAGE: USDataSource.ALPHA_VANTAGE,
            DataSourceCode.FINNHUB: USDataSource.FINNHUB,
        }

        return source_mapping.get(env_source, USDataSource.YFINANCE)

    def _check_available_sources(self) -> List[USDataSource]:
        """
        检查可用的数据源

        从数据库读取启用状态，并检查依赖是否满足
        """
        available = []

        # MongoDB 缓存
        if self.use_mongodb_cache:
            available.append(USDataSource.MONGODB)
            logger.info("✅ MongoDB缓存数据源可用")

        # 从数据库读取启用的数据源列表和配置
        enabled_sources_in_db = self._get_enabled_sources_from_db()
        datasource_configs = self._get_datasource_configs_from_db()

        # 检查 yfinance
        if 'yfinance' in enabled_sources_in_db:
            try:
                import yfinance
                available.append(USDataSource.YFINANCE)
                logger.info("✅ yfinance数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ yfinance数据源不可用: 未安装 yfinance 库")
        else:
            logger.info("ℹ️ yfinance数据源已在数据库中禁用")

        # 检查 Alpha Vantage
        if 'alpha_vantage' in enabled_sources_in_db:
            try:
                # 优先从数据库配置读取 API Key，其次从环境变量读取
                api_key = datasource_configs.get('alpha_vantage', {}).get('api_key') or os.getenv("ALPHA_VANTAGE_API_KEY")
                if api_key:
                    available.append(USDataSource.ALPHA_VANTAGE)
                    source = "数据库配置" if datasource_configs.get('alpha_vantage', {}).get('api_key') else "环境变量"
                    logger.info(f"✅ Alpha Vantage数据源可用且已启用 (API Key来源: {source})")
                else:
                    logger.warning("⚠️ Alpha Vantage数据源不可用: API Key未配置（数据库和环境变量均未找到）")
            except Exception as e:
                logger.warning(f"⚠️ Alpha Vantage数据源检查失败: {e}")
        else:
            logger.info("ℹ️ Alpha Vantage数据源已在数据库中禁用")

        # 检查 Finnhub
        if 'finnhub' in enabled_sources_in_db:
            try:
                # 优先从数据库配置读取 API Key，其次从环境变量读取
                api_key = datasource_configs.get('finnhub', {}).get('api_key') or os.getenv("FINNHUB_API_KEY")
                if api_key:
                    available.append(USDataSource.FINNHUB)
                    source = "数据库配置" if datasource_configs.get('finnhub', {}).get('api_key') else "环境变量"
                    logger.info(f"✅ Finnhub数据源可用且已启用 (API Key来源: {source})")
                else:
                    logger.warning("⚠️ Finnhub数据源不可用: API Key未配置（数据库和环境变量均未找到）")
            except Exception as e:
                logger.warning(f"⚠️ Finnhub数据源检查失败: {e}")
        else:
            logger.info("ℹ️ Finnhub数据源已在数据库中禁用")

        return available

    def _get_enabled_sources_from_db(self) -> List[str]:
        """从数据库读取启用的数据源列表"""
        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()

            # 从 datasource_groupings 集合读取
            groupings = list(db.datasource_groupings.find({
                "market_category_id": "us_stocks",
                "enabled": True
            }))

            # 🔥 数据源名称映射（数据库名称 → 代码中使用的名称）
            name_mapping = {
                'alpha vantage': 'alpha_vantage',
                'yahoo finance': 'yfinance',
                'finnhub': 'finnhub',
            }

            result = []
            for g in groupings:
                db_name = g.get('data_source_name', '').lower()
                # 使用映射表转换名称
                code_name = name_mapping.get(db_name, db_name)
                result.append(code_name)
                logger.debug(f"🔄 数据源名称映射: '{db_name}' → '{code_name}'")

            return result
        except Exception as e:
            logger.warning(f"⚠️ 从数据库读取启用的数据源失败: {e}")
            # 默认全部启用
            return ['yfinance', 'alpha_vantage', 'finnhub']

    def _get_datasource_configs_from_db(self) -> dict:
        try:
            from tradingagents.config.config_manager import get_config_manager
            config_manager = get_config_manager()
            configs = config_manager.get_datasource_configs()
            if configs:
                result = {}
                for ds_config in configs:
                    name = ds_config.get('name', '').lower()
                    result[name] = {
                        'api_key': ds_config.get('api_key', ''),
                        'api_secret': ds_config.get('api_secret', ''),
                        'config_params': ds_config.get('config_params', {})
                    }
                return result
        except Exception as e:
            logger.debug(f"ConfigManager不可用: {e}")

        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            config = db.system_configs.find_one({"is_active": True})
            if not config:
                return {}
            datasource_configs = config.get('data_source_configs', [])
            result = {}
            for ds_config in datasource_configs:
                name = ds_config.get('name', '').lower()
                result[name] = {
                    'api_key': ds_config.get('api_key', ''),
                    'api_secret': ds_config.get('api_secret', ''),
                    'config_params': ds_config.get('config_params', {})
                }
            return result
        except Exception as e:
            logger.warning(f"⚠️ 从数据库读取数据源配置失败: {e}")
            return {}

    def get_current_source(self) -> USDataSource:
        """获取当前数据源"""
        return self.current_source

    def set_current_source(self, source: USDataSource) -> bool:
        """设置当前数据源"""
        if source in self.available_sources:
            self.current_source = source
            logger.info(f"✅ 美股数据源已切换到: {source.value}")
            return True
        else:
            logger.error(f"❌ 美股数据源不可用: {source.value}")
            return False


# 全局美股数据源管理器实例
_us_data_source_manager = None
_us_manager_lock = threading.Lock()

def get_us_data_source_manager() -> USDataSourceManager:
    global _us_data_source_manager
    if _us_data_source_manager is None:
        with _us_manager_lock:
            if _us_data_source_manager is None:
                _us_data_source_manager = USDataSourceManager()
    return _us_data_source_manager
