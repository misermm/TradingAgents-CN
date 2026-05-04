"""Backward-compatible AKShare helpers."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from tradingagents.dataflows.interface import (
    get_hk_stock_data_akshare,
    get_hk_stock_info_akshare,
)
from tradingagents.dataflows.providers.china.akshare import AKShareProvider, get_akshare_provider


def get_stock_news_em(symbol: str):
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("akshare is not installed") from exc
    return ak.stock_news_em(symbol=symbol)


def get_china_stock_data_akshare(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    provider = get_akshare_provider()
    return provider.get_stock_data(symbol, start_date, end_date)


def format_hk_stock_data_akshare(symbol: str, df: pd.DataFrame, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    if df is None or df.empty:
        return f"港股 {symbol} 无可用数据"

    frame = df.copy().rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"])
        if start_date:
            frame = frame[frame["date"] >= pd.Timestamp(start_date)]
        if end_date:
            frame = frame[frame["date"] <= pd.Timestamp(end_date)]
    latest = frame.iloc[-1]
    latest_date = latest["date"].strftime("%Y-%m-%d") if "date" in latest else "N/A"
    return (
        f"港股 {symbol} AKShare 数据\n"
        f"日期: {latest_date}\n"
        f"价格: HK${float(latest.get('close', 0.0)):.2f}\n"
        f"最高: HK${float(latest.get('high', latest.get('close', 0.0))):.2f}\n"
        f"最低: HK${float(latest.get('low', latest.get('close', 0.0))):.2f}\n"
        f"成交量: {float(latest.get('volume', 0.0)):,.0f}"
    )


__all__ = [
    "AKShareProvider",
    "get_akshare_provider",
    "get_stock_news_em",
    "get_china_stock_data_akshare",
    "get_hk_stock_data_akshare",
    "get_hk_stock_info_akshare",
    "format_hk_stock_data_akshare",
]
