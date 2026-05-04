from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from tradingagents.utils.logging_init import get_logger

logger = get_logger('agents')


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if pd.isna(v):
            return None
        return v
    except Exception:
        return None


def _get_tushare_snapshot(symbol: str) -> Dict[str, Optional[float]]:
    try:
        from .tushare import get_tushare_provider
        provider = get_tushare_provider()
        if not getattr(provider, 'connected', False):
            return {}
        info = provider.get_stock_info(symbol)
        ts_code = info.get('ts_code') if isinstance(info, dict) else None
        if not ts_code:
            return {}
        api = provider.api
        if api is None:
            return {}
        db = api.daily_basic(ts_code=ts_code, fields='ts_code,trade_date,pe,pb,total_mv')
        pe = pb = mv = None
        if db is not None and not db.empty:
            db = db.sort_values('trade_date').iloc[-1]
            pe = _safe_float(db.get('pe'))
            pb = _safe_float(db.get('pb'))
            mv = _safe_float(db.get('total_mv'))
        roe = None
        try:
            fi = api.fina_indicator(ts_code=ts_code, fields='ts_code,end_date,roe')
            if fi is not None and not fi.empty:
                fi = fi.sort_values('end_date').iloc[-1]
                roe = _safe_float(fi.get('roe'))
        except Exception:
            pass
        return {
            'pe': pe,
            'pb': pb,
            'market_cap': mv,
            'roe': roe,
        }
    except Exception as e:
        logger.debug(f"[fund_snapshot] tushare snapshot failed: {e}")
        return {}


def _get_akshare_snapshot(symbol: str) -> Dict[str, Optional[float]]:
    try:
        import akshare as ak
        code6 = str(symbol).zfill(6)

        spot_df = ak.stock_zh_a_spot_em()
        if spot_df is None or spot_df.empty:
            return {}

        stock_row = spot_df[spot_df['代码'] == code6]
        if stock_row.empty:
            return {}

        row = stock_row.iloc[0]
        pe = _safe_float(row.get('市盈率-动态', None))
        pb = _safe_float(row.get('市净率', None))
        total_mv_raw = _safe_float(row.get('总市值', None))
        market_cap = total_mv_raw / 1e8 if total_mv_raw else None

        roe = None
        try:
            fi_df = ak.stock_financial_analysis_indicator(symbol=code6)
            if fi_df is not None and not fi_df.empty:
                latest = fi_df.iloc[0]
                for col in fi_df.columns:
                    if '净资产收益率' in str(col):
                        roe = _safe_float(latest.get(col))
                        break
        except Exception:
            pass

        result = {
            'pe': pe,
            'pb': pb,
            'market_cap': market_cap,
            'roe': roe,
        }

        if any(v is not None for v in result.values()):
            logger.debug(f"[fund_snapshot] AKShare snapshot for {code6}: pe={pe}, pb={pb}, mv={market_cap}, roe={roe}")
            return result
        return {}
    except Exception as e:
        logger.debug(f"[fund_snapshot] AKShare snapshot failed: {e}")
        return {}


def get_cn_fund_snapshot(symbol: str) -> Dict[str, Optional[float]]:
    """
    Get A-share fundamental snapshot (pe/pb/roe/market_cap).
    Priority: Tushare -> AKShare -> empty dict.
    """
    snap = _get_tushare_snapshot(symbol)
    if snap:
        return snap
    snap = _get_akshare_snapshot(symbol)
    if snap:
        return snap
    return {}

