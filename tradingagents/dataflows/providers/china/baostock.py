#!/usr/bin/env python3
"""
BaoStock统一数据提供器
实现BaseStockDataProvider接口，提供标准化的BaoStock数据访问
"""
import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union
import pandas as pd

from ..base_provider import BaseStockDataProvider

logger = logging.getLogger(__name__)


class BaoStockConnectionPool:
    """
    BaoStock连接池
    
    维持BaoStock长连接，替代每次login/logout的模式。
    特性：
    - 心跳检测：每5分钟ping一次，保持连接活跃
    - 自动重连：连接断开时自动重连（最多3次，间隔2s/4s/8s）
    - 线程安全：使用锁防止并发操作冲突
    """
    
    # 心跳间隔（秒）
    HEARTBEAT_INTERVAL = 300  # 5分钟
    # 重连参数
    MAX_RECONNECT_ATTEMPTS = 3
    RECONNECT_DELAYS = [2, 4, 8]  # 指数退避重连间隔
    
    def __init__(self):
        """初始化连接池"""
        self._bs = None  # BaoStock模块引用
        self._connected = False  # 连接状态
        self._lock = threading.RLock()  # 可重入锁，防止并发冲突
        self._last_heartbeat_time = 0.0  # 上次心跳时间
        self._heartbeat_thread = None  # 心跳线程
        self._stop_heartbeat = threading.Event()  # 停止心跳信号
        self._initialized = False
        
    def initialize(self) -> bool:
        """
        初始化连接池，加载BaoStock模块并建立首次连接
        
        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            return self._connected
            
        try:
            import baostock as bs
            self._bs = bs
            
            # 建立首次连接
            if self._connect():
                self._initialized = True
                # 启动心跳线程
                self._start_heartbeat()
                logger.info("✅ BaoStock连接池初始化成功，心跳检测已启动")
                return True
            else:
                logger.error("❌ BaoStock连接池初始化失败：首次连接失败")
                return False
                
        except ImportError as e:
            logger.error(f"❌ BaoStock模块未安装: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ BaoStock连接池初始化异常: {e}")
            return False
    
    def _connect(self) -> bool:
        """
        建立BaoStock连接（内部方法，需在锁内调用）
        
        Returns:
            bool: 连接是否成功
        """
        try:
            lg = self._bs.login()
            if lg.error_code == '0':
                self._connected = True
                self._last_heartbeat_time = time.monotonic()
                logger.debug("✅ BaoStock连接建立成功")
                return True
            else:
                self._connected = False
                logger.error(f"❌ BaoStock登录失败: {lg.error_msg}")
                return False
        except Exception as e:
            self._connected = False
            logger.error(f"❌ BaoStock连接异常: {e}")
            return False
    
    def _disconnect(self):
        """
        断开BaoStock连接（内部方法，需在锁内调用）
        """
        if self._connected and self._bs:
            try:
                self._bs.logout()
            except Exception as e:
                logger.debug(f"BaoStock登出异常（可忽略）: {e}")
            finally:
                self._connected = False
    
    def _reconnect(self) -> bool:
        """
        自动重连BaoStock（最多3次，间隔2s/4s/8s）
        
        Returns:
            bool: 重连是否成功
        """
        for attempt in range(self.MAX_RECONNECT_ATTEMPTS):
            delay = self.RECONNECT_DELAYS[attempt] if attempt < len(self.RECONNECT_DELAYS) else 8
            logger.warning(f"🔄 BaoStock重连尝试 {attempt + 1}/{self.MAX_RECONNECT_ATTEMPTS}，{delay}秒后重连...")
            time.sleep(delay)
            
            # 先断开旧连接
            self._disconnect()
            
            # 尝试重新连接
            if self._connect():
                logger.info(f"✅ BaoStock重连成功（第{attempt + 1}次尝试）")
                return True
        
        logger.error(f"❌ BaoStock重连失败，已尝试{self.MAX_RECONNECT_ATTEMPTS}次")
        return False
    
    def _start_heartbeat(self):
        """启动心跳检测线程"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        
        self._stop_heartbeat.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="BaoStock-Heartbeat",
            daemon=True  # 守护线程，主线程退出时自动结束
        )
        self._heartbeat_thread.start()
        logger.debug("💓 BaoStock心跳线程已启动")
    
    def _heartbeat_loop(self):
        """心跳检测循环（在独立线程中运行）"""
        while not self._stop_heartbeat.is_set():
            # 等待心跳间隔
            if self._stop_heartbeat.wait(timeout=self.HEARTBEAT_INTERVAL):
                break  # 收到停止信号
            
            try:
                self._ping()
            except Exception as e:
                logger.warning(f"⚠️ BaoStock心跳检测异常: {e}")
    
    def _ping(self) -> bool:
        """
        心跳检测：执行一次简单的查询来验证连接是否活跃
        
        Returns:
            bool: 连接是否正常
        """
        with self._lock:
            if not self._connected:
                logger.warning("⚠️ BaoStock心跳检测：连接已断开，尝试重连")
                return self._reconnect()
            
            try:
                # 使用查询股票基本信息作为心跳检测
                rs = self._bs.query_stock_basic()
                if rs.error_code == '0':
                    self._last_heartbeat_time = time.monotonic()
                    logger.debug("💓 BaoStock心跳检测正常")
                    return True
                else:
                    logger.warning(f"⚠️ BaoStock心跳检测失败: {rs.error_msg}")
                    return self._reconnect()
            except Exception as e:
                logger.warning(f"⚠️ BaoStock心跳检测异常: {e}")
                return self._reconnect()
    
    def execute(self, func, *args, **kwargs):
        """
        在连接池中执行BaoStock操作
        
        自动管理连接状态，如果连接断开会自动重连。
        使用锁确保线程安全。
        
        Args:
            func: 要执行的BaoStock操作函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            Exception: 连接不可用或执行失败时抛出异常
        """
        with self._lock:
            # 检查连接状态
            if not self._connected:
                logger.warning("⚠️ BaoStock连接已断开，尝试重连...")
                if not self._reconnect():
                    raise ConnectionError("BaoStock连接不可用，重连失败")
            
            try:
                result = func(*args, **kwargs)
                self._last_heartbeat_time = time.monotonic()
                return result
            except Exception as e:
                # 执行失败，可能是连接断开
                logger.warning(f"⚠️ BaoStock操作执行失败: {e}")
                # 尝试重连一次
                if self._reconnect():
                    # 重连成功，重试操作
                    try:
                        result = func(*args, **kwargs)
                        self._last_heartbeat_time = time.monotonic()
                        return result
                    except Exception as retry_e:
                        logger.error(f"❌ BaoStock重连后操作仍失败: {retry_e}")
                        raise
                else:
                    raise ConnectionError(f"BaoStock操作失败且重连失败: {e}")
    
    def shutdown(self):
        """关闭连接池，释放资源"""
        logger.info("🔒 BaoStock连接池正在关闭...")
        # 停止心跳线程
        self._stop_heartbeat.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        
        # 断开连接
        with self._lock:
            self._disconnect()
        
        self._initialized = False
        logger.info("✅ BaoStock连接池已关闭")
    
    @property
    def is_connected(self) -> bool:
        """连接是否活跃"""
        return self._connected
    
    @property
    def bs(self):
        """获取BaoStock模块引用"""
        return self._bs


# 全局连接池实例
_connection_pool = None
_pool_lock = threading.Lock()


def get_connection_pool() -> BaoStockConnectionPool:
    """获取全局BaoStock连接池实例"""
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                _connection_pool = BaoStockConnectionPool()
                _connection_pool.initialize()
    return _connection_pool


def shutdown_connection_pool():
    global _connection_pool
    with _pool_lock:
        if _connection_pool is None:
            return
        try:
            _connection_pool.shutdown()
        finally:
            _connection_pool = None


class BaoStockProvider(BaseStockDataProvider):
    """
    BaoStock统一数据提供器
    
    使用BaoStockConnectionPool管理长连接，替代每次login/logout的模式
    """
    
    def __init__(self):
        """初始化BaoStock提供器"""
        super().__init__("baostock")
        self._pool = None  # 延迟初始化连接池
        self.connected = False
        self._init_baostock()

        from ..resilient_http_client import ResilientHttpClient
        self._http_client = ResilientHttpClient(
            max_retries=3,
            timeout_seconds=60.0,
            connect_timeout=15.0,
            name="baostock",
            retryable_exceptions=[ConnectionError, TimeoutError, OSError],
        )
    
    def _init_baostock(self):
        """初始化BaoStock连接（延迟初始化连接池）"""
        try:
            import baostock as bs
            # 不再直接login，而是使用连接池
            # 连接池会在首次使用时自动初始化
            self.connected = True
            logger.info("🔧 BaoStock模块加载成功（将使用连接池）")
        except ImportError as e:
            logger.error(f"❌ BaoStock模块未安装: {e}")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ BaoStock初始化失败: {e}")
            self.connected = False
    
    def _get_pool(self) -> BaoStockConnectionPool:
        """获取连接池实例（延迟初始化）"""
        if self._pool is None:
            self._pool = get_connection_pool()
        return self._pool
    
    @property
    def bs(self):
        """获取BaoStock模块引用（兼容旧代码）"""
        pool = self._get_pool()
        return pool.bs
    
    async def connect(self) -> bool:
        """连接到BaoStock数据源"""
        return await self.test_connection()

    async def disconnect(self):
        if self._pool is not None:
            try:
                shutdown_connection_pool()
            finally:
                self._pool = None
        self.connected = False
        logger.info("BaoStock provider disconnected")

    async def test_connection(self) -> bool:
        """测试BaoStock连接（使用连接池）"""
        if not self.connected:
            return False
        
        try:
            pool = self._get_pool()
            # 使用连接池执行心跳检测
            def test_pool_connection():
                return pool._ping()
            
            result = await asyncio.to_thread(test_pool_connection)
            if result:
                logger.info("✅ BaoStock连接测试成功（连接池模式）")
            return result
        except Exception as e:
            logger.error(f"❌ BaoStock连接测试失败: {e}")
            return False
    
    def get_stock_list_sync(self) -> Optional[pd.DataFrame]:
        """获取股票列表（同步版本，使用连接池）"""
        if not self.connected:
            return None

        try:
            logger.info("📋 获取BaoStock股票列表（同步）...")
            pool = self._get_pool()

            def query_stock_list():
                rs = pool.bs.query_stock_basic()
                if rs.error_code != '0':
                    raise Exception(f"查询失败: {rs.error_msg}")

                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                return data_list, rs.fields

            data_list, fields = pool.execute(query_stock_list)

            if not data_list:
                logger.warning("⚠️ BaoStock股票列表为空")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(data_list, columns=fields)

            # 只保留股票类型（type=1）
            df = df[df['type'] == '1']

            logger.info(f"✅ BaoStock股票列表获取成功: {len(df)}只股票")
            return df

        except Exception as e:
            logger.error(f"❌ BaoStock获取股票列表失败: {e}")
            return None

    async def get_stock_list(self) -> List[Dict[str, Any]]:
        """
        获取股票列表（使用连接池）
        
        Returns:
            股票列表，包含代码和名称
        """
        if not self.connected:
            return []
        
        try:
            logger.info("📋 获取BaoStock股票列表...")
            pool = self._get_pool()
            
            def fetch_stock_list():
                rs = pool.bs.query_stock_basic()
                if rs.error_code != '0':
                    raise Exception(f"查询失败: {rs.error_msg}")
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                return data_list, rs.fields
            
            data_list, fields = await asyncio.to_thread(lambda: pool.execute(fetch_stock_list))
            
            if not data_list:
                logger.warning("⚠️ BaoStock股票列表为空")
                return []
            
            # 转换为标准格式
            stock_list = []
            for row in data_list:
                if len(row) >= 6:
                    code = row[0]  # code
                    name = row[1]  # code_name
                    stock_type = row[4] if len(row) > 4 else '0'  # type
                    status = row[5] if len(row) > 5 else '0'  # status
                    
                    # 只保留A股股票 (type=1, status=1)
                    if stock_type == '1' and status == '1':
                        # 转换代码格式 sh.600000 -> 600000
                        clean_code = code.replace('sh.', '').replace('sz.', '')
                        stock_list.append({
                            "code": clean_code,
                            "name": str(name),
                            "source": "baostock"
                        })
            
            logger.info(f"✅ BaoStock股票列表获取成功: {len(stock_list)}只股票")
            return stock_list
            
        except Exception as e:
            logger.error(f"❌ BaoStock获取股票列表失败: {e}")
            return []
    
    async def get_stock_basic_info(self, code: str) -> Dict[str, Any]:
        """
        获取股票基础信息

        Args:
            code: 股票代码

        Returns:
            标准化的股票基础信息
        """
        if not self.connected:
            return {}

        try:
            # 获取详细信息
            basic_info = await self._get_stock_info_detail(code)

            # 标准化数据
            return {
                "code": code,
                "name": basic_info.get("name", f"股票{code}"),
                "industry": basic_info.get("industry", "未知"),
                "area": basic_info.get("area", "未知"),
                "list_date": basic_info.get("list_date", ""),
                "full_symbol": self._get_full_symbol(code),
                "market_info": self._get_market_info(code),
                "data_source": "baostock",
                "last_sync": datetime.now(timezone.utc),
                "sync_status": "success"
            }

        except Exception as e:
            logger.error(f"❌ BaoStock获取{code}基础信息失败: {e}")
            return {}

    async def get_valuation_data(self, code: str, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取股票估值数据（PE、PB、PS、PCF等），使用连接池

        Args:
            code: 股票代码
            trade_date: 交易日期 (YYYY-MM-DD)，默认为最近交易日

        Returns:
            估值数据字典
        """
        if not self.connected:
            return {}

        try:
            if not trade_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
            else:
                start_date = trade_date
                end_date = trade_date

            logger.debug(f"📊 获取{code}估值数据: {start_date} 到 {end_date}")
            pool = self._get_pool()

            def fetch_valuation_data():
                bs_code = self._to_baostock_code(code)
                rs = pool.bs.query_history_k_data_plus(
                    code=bs_code,
                    fields="date,code,close,peTTM,pbMRQ,psTTM,pcfNcfTTM",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"
                )

                if rs.error_code != '0':
                    raise Exception(f"查询失败: {rs.error_msg}")

                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())

                return data_list, rs.fields

            data_list, fields = await asyncio.to_thread(lambda: pool.execute(fetch_valuation_data))

            if not data_list:
                logger.warning(f"⚠️ {code}估值数据为空")
                return {}

            # 取最新一条数据
            latest_row = data_list[-1]

            # 解析数据（fields: date, code, close, peTTM, pbMRQ, psTTM, pcfNcfTTM）
            valuation_data = {
                "date": latest_row[0] if len(latest_row) > 0 else None,
                "code": code,
                "close": self._safe_float(latest_row[2]) if len(latest_row) > 2 else None,
                "pe_ttm": self._safe_float(latest_row[3]) if len(latest_row) > 3 else None,
                "pb_mrq": self._safe_float(latest_row[4]) if len(latest_row) > 4 else None,
                "ps_ttm": self._safe_float(latest_row[5]) if len(latest_row) > 5 else None,
                "pcf_ttm": self._safe_float(latest_row[6]) if len(latest_row) > 6 else None,
            }

            logger.debug(f"✅ {code}估值数据获取成功: PE={valuation_data['pe_ttm']}, PB={valuation_data['pb_mrq']}")
            return valuation_data

        except Exception as e:
            logger.error(f"❌ BaoStock获取{code}估值数据失败: {e}")
            return {}
    
    async def _get_stock_info_detail(self, code: str) -> Dict[str, Any]:
        """获取股票详细信息（使用连接池）"""
        try:
            pool = self._get_pool()
            
            def fetch_stock_info():
                bs_code = self._to_baostock_code(code)
                rs = pool.bs.query_stock_basic(code=bs_code)
                if rs.error_code != '0':
                    return {"code": code, "name": f"股票{code}"}
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                if not data_list:
                    return {"code": code, "name": f"股票{code}"}
                
                row = data_list[0]
                return {
                    "code": code,
                    "name": str(row[1]) if len(row) > 1 else f"股票{code}",
                    "list_date": str(row[2]) if len(row) > 2 else "",
                    "industry": "未知",
                    "area": "未知"
                }
            
            return await asyncio.to_thread(lambda: pool.execute(fetch_stock_info))
            
        except Exception as e:
            logger.debug(f"获取{code}详细信息失败: {e}")
            return {"code": code, "name": f"股票{code}", "industry": "未知", "area": "未知"}
    
    async def get_stock_quotes(self, code: str) -> Dict[str, Any]:
        """
        获取股票实时行情
        
        Args:
            code: 股票代码
            
        Returns:
            标准化的行情数据
        """
        if not self.connected:
            return {}
        
        try:
            # BaoStock没有实时行情接口，使用最新日K线数据
            quotes_data = await self._get_latest_kline_data(code)
            
            if not quotes_data:
                return {}
            
            # 标准化数据
            return {
                "code": code,
                "name": quotes_data.get("name", f"股票{code}"),
                "price": quotes_data.get("close", 0),
                "change": quotes_data.get("change", 0),
                "change_percent": quotes_data.get("change_percent", 0),
                "volume": quotes_data.get("volume", 0),
                "amount": quotes_data.get("amount", 0),
                "open": quotes_data.get("open", 0),
                "high": quotes_data.get("high", 0),
                "low": quotes_data.get("low", 0),
                "pre_close": quotes_data.get("preclose", 0),
                "full_symbol": self._get_full_symbol(code),
                "market_info": self._get_market_info(code),
                "data_source": "baostock",
                "last_sync": datetime.now(timezone.utc),
                "sync_status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ BaoStock获取{code}行情失败: {e}")
            return {}
    
    async def _get_latest_kline_data(self, code: str) -> Dict[str, Any]:
        """获取最新K线数据作为行情（使用连接池）"""
        try:
            pool = self._get_pool()
            
            def fetch_latest_kline():
                bs_code = self._to_baostock_code(code)
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
                
                rs = pool.bs.query_history_k_data_plus(
                    code=bs_code,
                    fields="date,code,open,high,low,close,preclose,volume,amount,pctChg",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"
                )
                
                if rs.error_code != '0':
                    return {}
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                if not data_list:
                    return {}
                
                latest_row = data_list[-1]
                return {
                    "name": f"股票{code}",
                    "open": self._safe_float(latest_row[2]),
                    "high": self._safe_float(latest_row[3]),
                    "low": self._safe_float(latest_row[4]),
                    "close": self._safe_float(latest_row[5]),
                    "preclose": self._safe_float(latest_row[6]),
                    "volume": self._safe_int(latest_row[7]),
                    "amount": self._safe_float(latest_row[8]),
                    "change_percent": self._safe_float(latest_row[9]),
                    "change": self._safe_float(latest_row[5]) - self._safe_float(latest_row[6])
                }
            
            return await asyncio.to_thread(lambda: pool.execute(fetch_latest_kline))
            
        except Exception as e:
            logger.debug(f"获取{code}最新K线数据失败: {e}")
            return {}
    
    def _to_baostock_code(self, symbol: str) -> str:
        """转换为BaoStock代码格式"""
        s = str(symbol).strip().upper()
        # 处理 600519.SH / 000001.SZ / 600519 / 000001
        if s.endswith('.SH') or s.endswith('.SZ'):
            code, exch = s.split('.')
            prefix = 'sh' if exch == 'SH' else 'sz'
            return f"{prefix}.{code}"
        # 6 开头上交所，否则深交所（简化规则）
        if len(s) >= 6 and s[0] == '6':
            return f"sh.{s[:6]}"
        return f"sz.{s[:6]}"
    
    def _determine_market(self, code: str) -> str:
        """确定股票所属市场"""
        if code.startswith('6'):
            return "上海证券交易所"
        elif code.startswith('0') or code.startswith('3'):
            return "深圳证券交易所"
        elif code.startswith('8'):
            return "北京证券交易所"
        else:
            return "未知市场"
    
    def _get_full_symbol(self, code: str) -> str:
        """
        获取完整股票代码

        Args:
            code: 6位股票代码

        Returns:
            完整标准化代码，如果无法识别则返回原始代码（确保不为空）
        """
        # 确保 code 不为空
        if not code:
            return ""

        # 标准化为字符串
        code = str(code).strip()

        # 根据代码前缀判断交易所
        if code.startswith(('6', '9')):  # 上海证券交易所（增加9开头的B股）
            return f"{code}.SS"
        elif code.startswith(('0', '3', '2')):  # 深圳证券交易所（增加2开头的B股）
            return f"{code}.SZ"
        elif code.startswith(('8', '4')):  # 北京证券交易所（增加4开头的新三板）
            return f"{code}.BJ"
        else:
            # 无法识别的代码，返回原始代码（确保不为空）
            return code if code else ""
    
    def _get_market_info(self, code: str) -> Dict[str, Any]:
        """获取市场信息"""
        if code.startswith('6'):
            return {
                "market_type": "CN",
                "exchange": "SSE",
                "exchange_name": "上海证券交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai"
            }
        elif code.startswith('0') or code.startswith('3'):
            return {
                "market_type": "CN",
                "exchange": "SZSE", 
                "exchange_name": "深圳证券交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai"
            }
        elif code.startswith('8'):
            return {
                "market_type": "CN",
                "exchange": "BSE",
                "exchange_name": "北京证券交易所", 
                "currency": "CNY",
                "timezone": "Asia/Shanghai"
            }
        else:
            return {
                "market_type": "CN",
                "exchange": "UNKNOWN",
                "exchange_name": "未知交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai"
            }
    
    def _safe_float(self, value: Any) -> float:
        """安全转换为浮点数"""
        try:
            if value is None or value == '' or value == 'None':
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_int(self, value: Any) -> int:
        """安全转换为整数"""
        try:
            if value is None or value == '' or value == 'None':
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    
    def _safe_str(self, value: Any) -> str:
        """安全转换为字符串"""
        try:
            if value is None:
                return ""
            return str(value)
        except:
            return ""

    async def get_historical_data(self, code: str, start_date: str, end_date: str,
                                period: str = "daily") -> Optional[pd.DataFrame]:
        """
        获取历史数据（使用连接池）

        Args:
            code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            period: 数据周期 (daily, weekly, monthly)

        Returns:
            历史数据DataFrame
        """
        if not self.connected:
            return None

        try:
            logger.info(f"📊 获取BaoStock历史数据: {code} ({start_date} 到 {end_date})")

            # 转换周期参数
            frequency_map = {
                "daily": "d",
                "weekly": "w",
                "monthly": "m"
            }
            bs_frequency = frequency_map.get(period, "d")
            pool = self._get_pool()

            def fetch_historical_data():
                bs_code = self._to_baostock_code(code)
                if bs_frequency == "d":
                    fields_str = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
                else:
                    fields_str = "date,code,open,high,low,close,volume,amount,pctChg"

                rs = pool.bs.query_history_k_data_plus(
                    code=bs_code,
                    fields=fields_str,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=bs_frequency,
                    adjustflag="2"  # 前复权
                )

                if rs.error_code != '0':
                    raise Exception(f"查询失败: {rs.error_msg}")

                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())

                return data_list, rs.fields

            result = await asyncio.to_thread(
                lambda: self._http_client.call_sync_with_timeout(
                    lambda: pool.execute(fetch_historical_data), timeout=60.0
                )
            )

            if not result.success:
                logger.error(f"❌ BaoStock历史数据获取失败: {result.error}")
                return None

            data_list, fields = result.data

            if not data_list:
                logger.warning(f"⚠️ BaoStock历史数据为空: {code}")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(data_list, columns=fields)

            # 数据类型转换
            numeric_cols = ['open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'pctChg', 'turn']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 如果没有preclose字段，使用前一日收盘价估算
            if 'preclose' not in df.columns and len(df) > 0:
                df['preclose'] = df['close'].shift(1)
                df.loc[0, 'preclose'] = df.loc[0, 'close']  # 第一行使用当日收盘价

            # 标准化列名
            df = df.rename(columns={
                'pctChg': 'change_percent'
            })

            # 添加标准化字段
            df['股票代码'] = code
            df['full_symbol'] = self._get_full_symbol(code)

            logger.info(f"✅ BaoStock历史数据获取成功: {code}, {len(df)}条记录")
            return df

        except Exception as e:
            logger.error(f"❌ BaoStock获取{code}历史数据失败: {e}")
            return None

    async def get_financial_data(self, code: str, year: Optional[int] = None,
                               quarter: Optional[int] = None) -> Dict[str, Any]:
        """
        获取财务数据

        Args:
            code: 股票代码
            year: 年份
            quarter: 季度

        Returns:
            财务数据字典
        """
        if not self.connected:
            return {}

        try:
            logger.info(f"💰 获取BaoStock财务数据: {code}")

            # 如果没有指定年份和季度，使用当前年份的最新季度
            if year is None:
                year = datetime.now().year
            if quarter is None:
                current_month = datetime.now().month
                quarter = (current_month - 1) // 3 + 1

            financial_data = {}

            # 1. 获取盈利能力数据
            try:
                profit_data = await self._get_profit_data(code, year, quarter)
                if profit_data:
                    financial_data['profit_data'] = profit_data
                    logger.debug(f"✅ {code}盈利能力数据获取成功")
            except Exception as e:
                logger.debug(f"获取{code}盈利能力数据失败: {e}")

            # 2. 获取营运能力数据
            try:
                operation_data = await self._get_operation_data(code, year, quarter)
                if operation_data:
                    financial_data['operation_data'] = operation_data
                    logger.debug(f"✅ {code}营运能力数据获取成功")
            except Exception as e:
                logger.debug(f"获取{code}营运能力数据失败: {e}")

            # 3. 获取成长能力数据
            try:
                growth_data = await self._get_growth_data(code, year, quarter)
                if growth_data:
                    financial_data['growth_data'] = growth_data
                    logger.debug(f"✅ {code}成长能力数据获取成功")
            except Exception as e:
                logger.debug(f"获取{code}成长能力数据失败: {e}")

            # 4. 获取偿债能力数据
            try:
                balance_data = await self._get_balance_data(code, year, quarter)
                if balance_data:
                    financial_data['balance_data'] = balance_data
                    logger.debug(f"✅ {code}偿债能力数据获取成功")
            except Exception as e:
                logger.debug(f"获取{code}偿债能力数据失败: {e}")

            # 5. 获取现金流量数据
            try:
                cash_flow_data = await self._get_cash_flow_data(code, year, quarter)
                if cash_flow_data:
                    financial_data['cash_flow_data'] = cash_flow_data
                    logger.debug(f"✅ {code}现金流量数据获取成功")
            except Exception as e:
                logger.debug(f"获取{code}现金流量数据失败: {e}")

            if financial_data:
                logger.info(f"✅ BaoStock财务数据获取成功: {code}, {len(financial_data)}个数据集")
            else:
                logger.warning(f"⚠️ BaoStock财务数据为空: {code}")

            return financial_data

        except Exception as e:
            logger.error(f"❌ BaoStock获取{code}财务数据失败: {e}")
            return {}

    async def _get_profit_data(self, code: str, year: int, quarter: int) -> Optional[Dict[str, Any]]:
        """获取盈利能力数据（使用连接池）"""
        try:
            pool = self._get_pool()

            def fetch_profit_data():
                bs_code = self._to_baostock_code(code)
                rs = pool.bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
                if rs.error_code != '0':
                    return None

                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())

                return data_list, rs.fields

            result = await asyncio.to_thread(lambda: pool.execute(fetch_profit_data))
            if not result or not result[0]:
                return None

            data_list, fields = result
            df = pd.DataFrame(data_list, columns=fields)
            return df.to_dict('records')[0] if not df.empty else None

        except Exception as e:
            logger.debug(f"获取{code}盈利能力数据失败: {e}")
            return None

    async def _get_operation_data(self, code: str, year: int, quarter: int) -> Optional[Dict[str, Any]]:
        """获取营运能力数据（使用连接池）"""
        try:
            pool = self._get_pool()

            def fetch_operation_data():
                bs_code = self._to_baostock_code(code)
                rs = pool.bs.query_operation_data(code=bs_code, year=year, quarter=quarter)
                if rs.error_code != '0':
                    return None

                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())

                return data_list, rs.fields

            result = await asyncio.to_thread(lambda: pool.execute(fetch_operation_data))
            if not result or not result[0]:
                return None

            data_list, fields = result
            df = pd.DataFrame(data_list, columns=fields)
            return df.to_dict('records')[0] if not df.empty else None

        except Exception as e:
            logger.debug(f"获取{code}营运能力数据失败: {e}")
            return None

    async def _get_growth_data(self, code: str, year: int, quarter: int) -> Optional[Dict[str, Any]]:
        """获取成长能力数据（使用连接池）"""
        try:
            pool = self._get_pool()

            def fetch_growth_data():
                bs_code = self._to_baostock_code(code)
                rs = pool.bs.query_growth_data(code=bs_code, year=year, quarter=quarter)
                if rs.error_code != '0':
                    return None

                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())

                return data_list, rs.fields

            result = await asyncio.to_thread(lambda: pool.execute(fetch_growth_data))
            if not result or not result[0]:
                return None

            data_list, fields = result
            df = pd.DataFrame(data_list, columns=fields)
            return df.to_dict('records')[0] if not df.empty else None

        except Exception as e:
            logger.debug(f"获取{code}成长能力数据失败: {e}")
            return None

    async def _get_balance_data(self, code: str, year: int, quarter: int) -> Optional[Dict[str, Any]]:
        """获取偿债能力数据（使用连接池）"""
        try:
            pool = self._get_pool()

            def fetch_balance_data():
                bs_code = self._to_baostock_code(code)
                rs = pool.bs.query_balance_data(code=bs_code, year=year, quarter=quarter)
                if rs.error_code != '0':
                    return None

                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())

                return data_list, rs.fields

            result = await asyncio.to_thread(lambda: pool.execute(fetch_balance_data))
            if not result or not result[0]:
                return None

            data_list, fields = result
            df = pd.DataFrame(data_list, columns=fields)
            return df.to_dict('records')[0] if not df.empty else None

        except Exception as e:
            logger.debug(f"获取{code}偿债能力数据失败: {e}")
            return None

    async def _get_cash_flow_data(self, code: str, year: int, quarter: int) -> Optional[Dict[str, Any]]:
        """获取现金流量数据（使用连接池）"""
        try:
            pool = self._get_pool()

            def fetch_cash_flow_data():
                bs_code = self._to_baostock_code(code)
                rs = pool.bs.query_cash_flow_data(code=bs_code, year=year, quarter=quarter)
                if rs.error_code != '0':
                    return None

                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())

                return data_list, rs.fields

            result = await asyncio.to_thread(lambda: pool.execute(fetch_cash_flow_data))
            if not result or not result[0]:
                return None

            data_list, fields = result
            df = pd.DataFrame(data_list, columns=fields)
            return df.to_dict('records')[0] if not df.empty else None

        except Exception as e:
            logger.debug(f"获取{code}现金流量数据失败: {e}")
            return None


# 全局提供器实例
_baostock_provider = None


def get_baostock_provider() -> BaoStockProvider:
    """获取全局BaoStock提供器实例"""
    global _baostock_provider
    if _baostock_provider is None:
        _baostock_provider = BaoStockProvider()
    return _baostock_provider
