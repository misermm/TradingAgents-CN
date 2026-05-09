#!/usr/bin/env python3
"""
数据编排器 - 统一降级框架

整合数据获取、降级、补全、交叉验证的统一入口
"""

import logging
from typing import Dict, Any, List, Optional

from tradingagents.utils.logging_init import setup_dataflow_logging

logger = setup_dataflow_logging()


class DataOrchestrator:
    """
    统一数据获取+降级+补全+验证框架

    职责：
    1. 按能力矩阵筛选可用数据源
    2. 按优先级+健康状态排序
    3. 逐个尝试，收集结果
    4. 数据补全（缺失字段从备选源补）
    5. 交叉验证（关键指标多源对比）
    6. 质量评分+溯源标记
    7. 写缓存+快照
    """

    def __init__(self):
        self._health_tracker = None
        self._cache_manager = None
        self._snapshot_manager = None

    def _get_health_tracker(self):
        if self._health_tracker is None:
            try:
                from .data_source_manager import get_data_source_manager
                manager = get_data_source_manager()
                self._health_tracker = manager._health_tracker
            except Exception as e:
                logger.debug(f"获取健康跟踪器失败: {e}")
        return self._health_tracker

    def _get_cache_manager(self):
        if self._cache_manager is None:
            try:
                from .cache import get_cache
                self._cache_manager = get_cache()
            except Exception as e:
                logger.debug(f"获取缓存管理器失败: {e}")
        return self._cache_manager

    def _get_snapshot_manager(self):
        if self._snapshot_manager is None:
            try:
                from .data_source_manager import get_data_source_manager
                manager = get_data_source_manager()
                self._snapshot_manager = manager._snapshot_manager
            except Exception as e:
                logger.debug(f"获取快照管理器失败: {e}")
        return self._snapshot_manager

    def get_available_sources(self, market: str, data_type: str) -> List[str]:
        """按能力矩阵筛选可用数据源"""
        capability_map = {
            ("cn", "stock_data"): ["akshare", "baostock", "sina", "eastmoney", "tushare"],
            ("cn", "fundamentals"): ["akshare", "baostock", "eastmoney", "tushare"],
            ("cn", "news"): ["eastmoney", "sina", "akshare"],
            ("us", "stock_data"): ["yfinance", "finnhub", "alpha_vantage"],
            ("us", "fundamentals"): ["yfinance", "finnhub", "alpha_vantage"],
            ("hk", "stock_data"): ["akshare", "yfinance", "finnhub"],
            ("hk", "fundamentals"): ["akshare", "yfinance"],
        }
        return capability_map.get((market, data_type), [])

    def sort_by_priority_and_health(self, sources: List[str]) -> List[str]:
        """按优先级+健康状态排序"""
        health_tracker = self._get_health_tracker()
        if not health_tracker:
            return sources

        available = []
        unavailable = []
        for source in sources:
            if health_tracker.is_available(source):
                available.append(source)
            else:
                unavailable.append(source)

        return available + unavailable

    def try_sources_in_order(
        self,
        sources: List[str],
        fetch_func,
        symbol: str,
        **kwargs
    ) -> Optional[str]:
        """
        按顺序尝试数据源，返回第一个成功的结果

        Args:
            sources: 数据源列表（已排序）
            fetch_func: 获取函数，接受 (source, symbol, **kwargs) 参数
            symbol: 股票代码
            **kwargs: 其他参数

        Returns:
            成功的结果字符串，或 None
        """
        health_tracker = self._get_health_tracker()
        failed_details = []

        for source in sources:
            try:
                logger.info(f"🔄 尝试从 {source} 获取 {symbol} 数据")
                result = fetch_func(source, symbol, **kwargs)

                if result and not any(m in result[:100] for m in ("❌", "错误：", "Error:", "失败：", "FAILED")):
                    logger.info(f"✅ {source} 数据获取成功: {symbol}")
                    if health_tracker:
                        health_tracker.record_success(source)
                    return result
                else:
                    error_preview = result[:200] if result else "空结果"
                    failed_details.append(f"{source}: 返回错误 - {error_preview}")
                    logger.warning(f"⚠️ {source} 返回错误结果，尝试下一个数据源")
                    if health_tracker:
                        health_tracker.record_failure(source)

            except Exception as e:
                failed_details.append(f"{source}: 异常 - {e}")
                logger.error(f"⚠️ {source} 数据获取失败: {e}")
                if health_tracker:
                    health_tracker.record_failure(source)

        error_summary = f"所有数据源均失败 ({symbol}): " + "; ".join(failed_details)
        logger.error(f"❌ {error_summary}")
        return f"❌ {error_summary}"


_orchestrator = None


def get_data_orchestrator() -> DataOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DataOrchestrator()
    return _orchestrator
