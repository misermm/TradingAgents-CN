#!/usr/bin/env python3
"""
A股数据服务模块

从 interface.py 拆分出的中国市场数据获取逻辑
"""

import time
from datetime import datetime
from typing import Annotated

from tradingagents.utils.logging_init import setup_dataflow_logging

logger = setup_dataflow_logging()


def get_china_stock_data_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"],
    start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
) -> str:
    try:
        from .data_source_manager import get_data_source_manager

        logger.debug(f"📊 [Tushare] 获取{ticker}股票数据...")
        logger.info(f"🔍 [股票代码追踪] get_china_stock_data_tushare 接收到的股票代码: '{ticker}' (类型: {type(ticker)})")

        manager = get_data_source_manager()
        return manager.get_china_stock_data_tushare(ticker, start_date, end_date)

    except Exception as e:
        logger.error(f"❌ [Tushare] 获取股票数据失败: {e}")
        return f"❌ 获取{ticker}股票数据失败: {e}"


def get_china_stock_info_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"]
) -> str:
    try:
        from .data_source_manager import get_data_source_manager

        logger.debug(f"📊 [Tushare] 获取{ticker}股票信息...")
        logger.info(f"🔍 [股票代码追踪] get_china_stock_info_tushare 接收到的股票代码: '{ticker}' (类型: {type(ticker)})")

        manager = get_data_source_manager()
        info = manager._get_tushare_stock_info(ticker)

        if info and isinstance(info, dict):
            return f"""股票代码: {info.get('symbol', ticker)}
股票名称: {info.get('name', '未知')}
所属行业: {info.get('industry', '未知')}
上市日期: {info.get('list_date', '未知')}
交易所: {info.get('exchange', '未知')}"""
        else:
            return f"❌ 未找到{ticker}的股票信息"

    except Exception as e:
        logger.error(f"❌ [Tushare] 获取股票信息失败: {e}")
        return f"❌ 获取{ticker}股票信息失败: {e}"


def get_china_stock_fundamentals_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"]
) -> str:
    try:
        from .data_source_manager import get_data_source_manager

        logger.debug(f"📊 获取{ticker}基本面数据...")
        logger.info(f"🔍 [股票代码追踪] 重定向到data_source_manager.get_fundamentals_data")

        manager = get_data_source_manager()
        return manager.get_fundamentals_data(ticker)

    except Exception as e:
        logger.error(f"❌ 获取基本面数据失败: {e}")
        return f"❌ 获取{ticker}基本面数据失败: {e}"


def get_china_stock_data_unified(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"],
    start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
) -> str:
    from tradingagents.utils.dataflow_utils import get_trading_date_range

    original_start_date = start_date
    original_end_date = end_date

    try:
        from app.core.config import get_settings
        settings = get_settings()
        lookback_days = settings.MARKET_ANALYST_LOOKBACK_DAYS
    except Exception as e:
        lookback_days = 30
        logger.warning(f"⚠️ [配置验证] 无法获取配置，使用默认值: {lookback_days}天")

    start_date, end_date = get_trading_date_range(end_date, lookback_days=lookback_days)

    logger.info(f"📅 [智能日期] 原始输入: {original_start_date} 至 {original_end_date}")
    logger.info(f"📅 [智能日期] 回溯天数: {lookback_days}天")
    logger.info(f"📅 [智能日期] 计算结果: {start_date} 至 {end_date}")

    logger.info(f"📊 [统一接口] 开始获取中国股票数据",
               extra={
                   'function': 'get_china_stock_data_unified',
                   'ticker': ticker,
                   'start_date': start_date,
                   'end_date': end_date,
                   'event_type': 'unified_data_call_start'
               })

    logger.info(f"🔍 [股票代码追踪] get_china_stock_data_unified 接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})")

    start_time = time.time()

    try:
        from .data_source_manager import get_china_stock_data_unified as _get_data

        result = _get_data(ticker, start_date, end_date)

        duration = time.time() - start_time
        result_length = len(result) if result else 0
        is_success = result and "❌" not in result and "错误" not in result

        if is_success:
            logger.info(f"✅ [统一接口] 中国股票数据获取成功",
                       extra={
                           'function': 'get_china_stock_data_unified',
                           'ticker': ticker,
                           'duration': duration,
                           'result_length': result_length,
                           'event_type': 'unified_data_call_success'
                       })
        else:
            logger.warning(f"⚠️ [统一接口] 中国股票数据质量异常",
                          extra={
                              'function': 'get_china_stock_data_unified',
                              'ticker': ticker,
                              'duration': duration,
                              'event_type': 'unified_data_call_warning'
                          })

        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ [统一接口] 获取股票数据失败: {e}",
                    extra={
                        'function': 'get_china_stock_data_unified',
                        'ticker': ticker,
                        'duration': duration,
                        'error': str(e),
                        'event_type': 'unified_data_call_error'
                    }, exc_info=True)
        return f"❌ 获取{ticker}股票数据失败: {e}"


def get_china_stock_info_unified(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"]
) -> str:
    try:
        from .data_source_manager import get_china_stock_info_unified as _get_info

        logger.info(f"📊 [统一接口] 获取{ticker}基本信息...")

        info = _get_info(ticker)

        if info and info.get('name'):
            result = f"股票代码: {ticker}\n"
            result += f"股票名称: {info.get('name', '未知')}\n"
            result += f"所属地区: {info.get('area', '未知')}\n"
            result += f"所属行业: {info.get('industry', '未知')}\n"
            result += f"上市市场: {info.get('market', '未知')}\n"
            result += f"上市日期: {info.get('list_date', '未知')}\n"
            cp = info.get('current_price')
            pct = info.get('change_pct')
            vol = info.get('volume')
            if cp is not None:
                result += f"当前价格: {cp}\n"
            if pct is not None:
                try:
                    pct_str = f"{float(pct):+.2f}%"
                except Exception:
                    pct_str = str(pct)
                result += f"涨跌幅: {pct_str}\n"
            if vol is not None:
                result += f"成交量: {vol}\n"
            result += f"数据来源: {info.get('source', 'unknown')}\n"
            return result
        else:
            return f"❌ 未能获取{ticker}的基本信息"

    except Exception as e:
        logger.error(f"❌ [统一接口] 获取股票信息失败: {e}")
        return f"❌ 获取{ticker}股票信息失败: {e}"


def switch_china_data_source(
    source: Annotated[str, "数据源名称：tushare, akshare, baostock"]
) -> str:
    try:
        from .data_source_manager import get_data_source_manager, ChinaDataSource

        source_mapping = {
            'tushare': ChinaDataSource.TUSHARE,
            'akshare': ChinaDataSource.AKSHARE,
            'baostock': ChinaDataSource.BAOSTOCK,
        }

        if source.lower() not in source_mapping:
            return f"❌ 不支持的数据源: {source}。支持的数据源: {list(source_mapping.keys())}"

        manager = get_data_source_manager()
        target_source = source_mapping[source.lower()]

        if manager.set_current_source(target_source):
            return f"✅ 数据源已切换到: {source}"
        else:
            return f"❌ 数据源切换失败: {source} 不可用"

    except Exception as e:
        logger.error(f"❌ 数据源切换失败: {e}")
        return f"❌ 数据源切换失败: {e}"


def get_current_china_data_source() -> str:
    try:
        from .data_source_manager import get_data_source_manager

        manager = get_data_source_manager()
        current = manager.get_current_source()
        available = manager.available_sources

        result = f"当前数据源: {current.value}\n"
        result += f"可用数据源: {[s.value for s in available]}\n"
        result += f"默认数据源: {manager.default_source.value}\n"

        return result

    except Exception as e:
        logger.error(f"❌ 获取数据源信息失败: {e}")
        return f"❌ 获取数据源信息失败: {e}"
