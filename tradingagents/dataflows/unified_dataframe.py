"""
统一DataFrame标准化层
集中处理各数据源Provider返回的DataFrame列名映射、类型转换、单位标准化、数据验证
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "Open": "open", "High": "high", "Low": "low", "Close": "close",
    "Volume": "vol", "Amount": "amount", "Symbol": "code", "symbol": "code",
    "Date": "date", "open": "open", "high": "high", "low": "low", "close": "close",
    "vol": "vol", "volume": "vol", "amount": "amount", "code": "code",
    "date": "date", "trade_date": "date",
    "日期": "date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close",
    "成交量": "vol", "成交额": "amount", "涨跌幅": "pct_change", "涨跌额": "change",
    "换手率": "turnover", "pe": "pe", "PE": "pe", "pb": "pb", "PB": "pb",
    "总市值": "market_cap", "流通市值": "circulating_market_cap",
    "turn": "turnover", "pctChg": "pct_change",
    "preclose": "pre_close", "pre_close": "pre_close",
}

NUMERIC_COLUMNS = [
    "open", "high", "low", "close", "vol", "amount",
    "pct_change", "change", "turnover", "pe", "pb",
    "market_cap", "circulating_market_cap", "pre_close",
]

WAN_TO_YI = 10000.0


def get_tushare_adapter():
    from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
    return get_tushare_provider()


def get_akshare_provider():
    from tradingagents.dataflows.providers.china.akshare import get_akshare_provider as _get_provider
    return _get_provider()


def get_baostock_provider():
    from tradingagents.dataflows.providers.china.baostock import get_baostock_provider as _get_provider
    return _get_provider()


def get_data_source_manager():
    from tradingagents.dataflows.data_source_manager import get_data_source_manager as _get_manager
    return _get_manager()


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化DataFrame列名

    将各种来源的列名(英文/中文/混合)统一为标准英文列名
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    rename_map = {}
    for col in out.columns:
        if col in COLUMN_MAP:
            mapped = COLUMN_MAP[col]
            if mapped != col:
                rename_map[col] = mapped

    if rename_map:
        out = out.rename(columns=rename_map)

    return out


def standardize_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化DataFrame数据类型

    - date列转为datetime
    - 数值列转为float
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "date" in out.columns:
        try:
            out["date"] = pd.to_datetime(out["date"], errors="coerce")
        except Exception as e:
            logger.debug(f"日期列转换失败: {e}")

    for col in NUMERIC_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
            # 处理无穷大值，转为NaN
            out[col] = out[col].replace([np.inf, -np.inf], np.nan)

    return out


def standardize_units(df: pd.DataFrame, market: str = "cn") -> pd.DataFrame:
    """
    标准化DataFrame单位

    A股惯例:
    - 市值统一为亿元
    - 成交额统一为元（如果来源是万元则转换）

    Args:
        df: DataFrame
        market: 市场 (cn/us/hk)
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if market == "cn":
        if "market_cap" in out.columns:
            cap = out["market_cap"]
            if cap.max() < 1e6:
                out["market_cap"] = cap * WAN_TO_YI / 1e8
            else:
                out["market_cap"] = cap / 1e8

        if "circulating_market_cap" in out.columns:
            cap = out["circulating_market_cap"]
            if cap.max() < 1e6:
                out["circulating_market_cap"] = cap * WAN_TO_YI / 1e8
            else:
                out["circulating_market_cap"] = cap / 1e8

    return out


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    填充缺失值

    - 数值列: 前向填充，仍为NaN则填0
    - 估值指标列(pe/pb等): 前向填充，保留NaN（避免0误导分析）
    - date列: 不填充
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    # 估值指标列：缺失时保留NaN而非填0，避免误导估值分析
    valuation_columns = {"pe", "pb", "pe_ttm", "pb_mrq", "ps_ttm", "pcf_ttm",
                         "market_cap", "circulating_market_cap", "eps", "bps", "roe"}

    for col in NUMERIC_COLUMNS:
        if col in out.columns:
            out[col] = out[col].ffill()
            out[col] = out[col].bfill()
            if col not in valuation_columns:
                remaining_nan = out[col].isna().sum()
                if remaining_nan > 0:
                    logger.warning(f"⚠️ [缺失值填充] 列 '{col}' 仍有 {remaining_nan} 个NaN，将填0")
                out[col] = out[col].fillna(0)

    return out


def validate_dataframe(df: pd.DataFrame, symbol: str = "") -> Tuple[bool, List[str]]:
    """
    验证DataFrame数据质量

    Returns:
        (is_valid, issues)
    """
    if df is None or df.empty:
        return False, ["DataFrame为空"]

    issues = []

    if "close" not in df.columns:
        issues.append("缺少close列")
    else:
        close = df["close"]
        if close.isna().all():
            issues.append("close列全为NaN")
        elif isinstance(close.iloc[0], (int, float)):
            if (close <= 0).any():
                issues.append("close列存在非正数")

    if "date" in df.columns:
        try:
            dates = pd.to_datetime(df["date"], errors="coerce")
            if dates.isna().all():
                issues.append("date列无法解析")
        except Exception:
            issues.append("date列解析失败")

    is_valid = len(issues) == 0
    if not is_valid:
        logger.warning(f"⚠️ [数据验证] {symbol}: {issues}")

    return is_valid, issues


def compute_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算派生列

    - pct_change: 涨跌幅(如果缺失)
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "pct_change" not in out.columns and "close" in out.columns:
        out["pct_change"] = out["close"].pct_change() * 100.0

    return out


def standardize_dataframe(
    df: pd.DataFrame,
    market: str = "cn",
    symbol: str = "",
) -> pd.DataFrame:
    """
    统一DataFrame标准化入口

    执行完整的标准化流水线:
    1. 列名标准化
    2. 数据类型标准化
    3. 单位标准化
    4. 缺失值填充
    5. 派生列计算
    6. 日期排序

    Args:
        df: 原始DataFrame
        market: 市场 (cn/us/hk)
        symbol: 股票代码(用于日志)

    Returns:
        标准化后的DataFrame
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = standardize_columns(df)
    out = standardize_types(out)
    out = standardize_units(out, market)
    out = fill_missing_values(out)
    out = compute_derived_columns(out)

    if "date" in out.columns:
        try:
            out = out.sort_values("date").reset_index(drop=True)
        except Exception as e:
            logger.debug(f"按日期排序失败: {e}")

    is_valid, issues = validate_dataframe(out, symbol)
    if is_valid:
        logger.debug(f"✅ [标准化] {symbol}: {len(out)}行, 列={list(out.columns)}")
    else:
        logger.warning(f"⚠️ [标准化] {symbol} 数据验证发现问题: {issues}")

    return out


def get_china_daily_df_unified(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch China daily data through configured sources and return a standardized DataFrame.

    This compatibility wrapper keeps callers on the unified DataFrame contract
    while provider internals continue to evolve.
    """
    manager = get_data_source_manager()
    source_order = []
    current = getattr(getattr(manager, "current_source", None), "value", None)
    if current:
        source_order.append(current)
    for source in getattr(manager, "available_sources", []) or []:
        value = getattr(source, "value", source)
        if value not in source_order:
            source_order.append(value)
    for source in ("tushare", "akshare", "baostock"):
        if source not in source_order:
            source_order.append(source)

    provider_factories = {
        "tushare": get_tushare_adapter,
        "akshare": get_akshare_provider,
        "baostock": get_baostock_provider,
    }

    for source in source_order:
        factory = provider_factories.get(source)
        if not factory:
            continue
        try:
            provider = factory()
            df = provider.get_stock_data(symbol, start_date, end_date)
            if isinstance(df, pd.DataFrame) and not df.empty:
                standardized = standardize_dataframe(df, market="cn", symbol=symbol)
                if not standardized.empty:
                    return standardized
        except Exception as exc:
            logger.warning(f"⚠️ [统一DataFrame] {source} 获取失败: {exc}")

    return pd.DataFrame()
