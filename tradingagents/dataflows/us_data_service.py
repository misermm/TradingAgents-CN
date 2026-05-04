#!/usr/bin/env python3
"""
美股数据服务模块

从 interface.py 拆分出的美股市场数据获取逻辑
"""

from tradingagents.utils.logging_init import setup_dataflow_logging

logger = setup_dataflow_logging()


def _get_enabled_us_data_sources() -> list:
    try:
        from tradingagents.config.config_manager import get_config_manager
        config_manager = get_config_manager()
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
            return provider.get_stock_data(symbol, start_date, end_date)
        except ImportError:
            from tradingagents.dataflows.providers.us.optimized import get_us_stock_data_cached
            return get_us_stock_data_cached(symbol, start_date, end_date)
    except Exception as e:
        logger.error(f"❌ 获取美股数据失败: {e}")
        return f"❌ 获取美股{symbol}数据失败: {e}"
