#!/usr/bin/env python3
"""
美股数据服务模块

从 interface.py 拆分出的美股市场数据获取逻辑
"""

from tradingagents.utils.logging_init import setup_dataflow_logging

logger = setup_dataflow_logging()


def _get_enabled_us_data_sources() -> list:
    try:
        from tradingagents.config.config_manager import config_manager
        configs = config_manager.get_datasource_configs()
        us_sources = []
        for cfg in configs:
            if cfg.get("market") == "us" and cfg.get("enabled", False):
                us_sources.append(cfg.get("source", "").lower())
        if us_sources:
            return us_sources
    except Exception as e:
        logger.debug(f"从数据库读取美股数据源配置失败: {e}")

    return ["yfinance", "finnhub"]


def get_us_stock_data(symbol: str, start_date: str = None, end_date: str = None) -> str:
    try:
        try:
            from .providers.us import OptimizedUSDataProvider
            provider = OptimizedUSDataProvider()
            result = provider.get_stock_data(symbol, start_date, end_date)
        except ImportError:
            from tradingagents.dataflows.providers.us.optimized import get_us_stock_data_cached
            result = get_us_stock_data_cached(symbol, start_date, end_date)

        if result is None:
            logger.error(f"❌ 获取美股数据返回空结果: {symbol}")
            return f"❌ 获取美股{symbol}数据失败: 数据提供器返回空结果，请检查股票代码或稍后重试"
        return result
    except Exception as e:
        logger.error(f"❌ 获取美股数据异常: {type(e).__name__}: {e}", exc_info=True)
        return f"❌ 获取美股{symbol}数据失败: {type(e).__name__}: {e}"
