#!/usr/bin/env python3
"""
港股数据服务模块

从 interface.py 拆分出的港股市场数据获取逻辑
"""

from typing import Dict

from tradingagents.utils.logging_init import setup_dataflow_logging

logger = setup_dataflow_logging()

try:
    from .providers.hk.hk_stock import get_hk_stock_data, get_hk_stock_info
    HK_STOCK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ 港股工具不可用: {e}")
    HK_STOCK_AVAILABLE = False

try:
    from .providers.hk.improved_hk import get_hk_stock_data_akshare, get_hk_stock_info_akshare
    AKSHARE_HK_AVAILABLE = True
except (ImportError, AttributeError) as e:
    logger.warning(f"⚠️ AKShare港股工具不可用: {e}")
    AKSHARE_HK_AVAILABLE = False

    def get_hk_stock_data_akshare(*args, **kwargs):
        return None

    def get_hk_stock_info_akshare(*args, **kwargs):
        return None


def _get_enabled_hk_data_sources() -> list:
    try:
        from tradingagents.config.config_manager import config_manager
        configs = config_manager.get_datasource_configs()
        hk_sources = []
        for cfg in configs:
            if cfg.get("market") == "hk" and cfg.get("enabled", False):
                hk_sources.append(cfg.get("source", "").lower())
        if hk_sources:
            return hk_sources
    except Exception as e:
        logger.debug(f"从数据库读取港股数据源配置失败: {e}")

    return ["akshare", "yfinance", "finnhub"]


def get_hk_stock_data_unified(symbol: str, start_date: str = None, end_date: str = None) -> str:
    try:
        logger.info(f"🇭🇰 获取港股数据: {symbol}")

        from tradingagents.utils.dataflow_utils import get_trading_date_range

        original_start_date = start_date
        original_end_date = end_date

        try:
            from app.core.config import get_settings
            settings = get_settings()
            lookback_days = settings.MARKET_ANALYST_LOOKBACK_DAYS
        except Exception as e:
            lookback_days = 60
            logger.warning(f"⚠️ [港股配置验证] 无法获取配置，使用默认值: {lookback_days}天")

        start_date, end_date = get_trading_date_range(end_date, lookback_days=lookback_days)

        logger.info(f"📅 [港股智能日期] 原始输入: {original_start_date} 至 {original_end_date}")
        logger.info(f"📅 [港股智能日期] 计算结果: {start_date} 至 {end_date}")

        enabled_sources = _get_enabled_hk_data_sources()

        for source in enabled_sources:
            if source == 'akshare' and AKSHARE_HK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用AKShare获取港股数据: {symbol}")
                    result = get_hk_stock_data_akshare(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ AKShare港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ AKShare返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ AKShare港股数据获取失败: {e}，尝试下一个数据源")

            elif source == 'yfinance' and HK_STOCK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用Yahoo Finance获取港股数据: {symbol}")
                    result = get_hk_stock_data(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ Yahoo Finance港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ Yahoo Finance返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ Yahoo Finance港股数据获取失败: {e}，尝试下一个数据源")

            elif source == 'finnhub':
                try:
                    try:
                        from .providers.us import OptimizedUSDataProvider
                        provider = OptimizedUSDataProvider()
                        get_us_stock_data_cached = provider.get_stock_data
                    except ImportError:
                        from tradingagents.dataflows.providers.us.optimized import get_us_stock_data_cached

                    logger.info(f"🔄 使用FINNHUB获取港股数据: {symbol}")
                    result = get_us_stock_data_cached(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ FINNHUB港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ FINNHUB返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ FINNHUB港股数据获取失败: {e}，尝试下一个数据源")

        error_msg = f"❌ 无法获取港股{symbol}数据 - 所有启用的数据源都不可用"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        logger.error(f"❌ 获取港股数据失败: {e}")
        return f"❌ 获取港股{symbol}数据失败: {e}"


def get_hk_stock_info_unified(symbol: str) -> Dict:
    try:
        enabled_sources = _get_enabled_hk_data_sources()

        for source in enabled_sources:
            if source == 'akshare' and AKSHARE_HK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用AKShare获取港股信息: {symbol}")
                    result = get_hk_stock_info_akshare(symbol)
                    if result and 'error' not in result and not result.get('name', '').startswith('港股'):
                        logger.info(f"✅ AKShare成功获取港股信息: {symbol} -> {result.get('name', 'N/A')}")
                        return result
                    else:
                        logger.warning(f"⚠️ AKShare返回默认信息，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ AKShare港股信息获取失败: {e}，尝试下一个数据源")

            elif source == 'yfinance' and HK_STOCK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用Yahoo Finance获取港股信息: {symbol}")
                    result = get_hk_stock_info(symbol)
                    if result and 'error' not in result and not result.get('name', '').startswith('港股'):
                        logger.info(f"✅ Yahoo Finance成功获取港股信息: {symbol} -> {result.get('name', 'N/A')}")
                        return result
                    else:
                        logger.warning(f"⚠️ Yahoo Finance返回默认信息，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ Yahoo Finance港股信息获取失败: {e}，尝试下一个数据源")

        logger.warning(f"⚠️ 所有启用的数据源都失败，使用默认信息: {symbol}")
        return {
            'symbol': symbol,
            'name': f'港股{symbol}',
            'currency': 'HKD',
            'exchange': 'HKG',
            'source': 'fallback'
        }

    except Exception as e:
        logger.error(f"❌ 获取港股信息失败: {e}")
        return {
            'symbol': symbol,
            'name': f'港股{symbol}',
            'currency': 'HKD',
            'exchange': 'HKG',
            'source': 'error',
            'error': str(e)
        }
