from __future__ import annotations

from typing import Dict, List, Optional

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


def calculate_ttm(quarterly_values: List[float]) -> Optional[float]:
    """
    TTM (Trailing Twelve Months) calculation.
    Sum the most recent 4 quarters of data.

    Example: 2025Q1 TTM = 2024Q2 + 2024Q3 + 2024Q4 + 2025Q1
    """
    if not quarterly_values:
        return None
    valid = [v for v in quarterly_values[:4] if v is not None]
    if not valid:
        return None
    return sum(valid)


def _cumulative_to_single(cumulative_values: List[float]) -> List[float]:
    """
    Convert cumulative report values to single-quarter values.

    AKShare financial reports (e.g. stock_profit_sheet_by_report_em) return
    cumulative data: Q1=Q1, Q2=Q1+Q2, Q3=Q1+Q2+Q3, Q4=Q1+Q2+Q3+Q4.
    This function converts them to single-quarter: Q1, Q2-Q1, Q3-Q2, Q4-Q3.
    """
    if not cumulative_values:
        return []
    single = []
    for i, val in enumerate(cumulative_values):
        if val is None:
            single.append(None)
            continue
        if i == 0:
            single.append(val)
        elif cumulative_values[i - 1] is not None:
            diff = val - cumulative_values[i - 1]
            single.append(diff if diff >= 0 else val)
        else:
            single.append(val)
    return single


def _is_annual_report(report_period: str) -> bool:
    """Check if the report period is an annual report (ends with -12-31)."""
    return report_period.endswith("-12-31") if report_period else False


def calculate_ttm_from_akshare(symbol: str) -> Dict[str, Optional[float]]:
    """
    Calculate TTM values from AKShare quarterly financial data.

    Returns dict with: revenue_ttm, net_profit_ttm, pe_ttm, operating_cashflow_ttm
    """
    result = {
        'revenue_ttm': None,
        'net_profit_ttm': None,
        'pe_ttm': None,
        'operating_cashflow_ttm': None,
    }

    try:
        import akshare as ak

        code6 = str(symbol).zfill(6)

        income_df = ak.stock_profit_sheet_by_report_em(symbol=code6)
        if income_df is not None and not income_df.empty and len(income_df) >= 1:
            revenue_cumulative = []
            net_profit_cumulative = []
            for i in range(min(8, len(income_df))):
                row = income_df.iloc[i]
                rev = _safe_float(row.get('营业总收入', row.get('营业收入', None)))
                np_val = _safe_float(row.get('净利润', None))
                revenue_cumulative.append(rev)
                net_profit_cumulative.append(np_val)

            revenue_single = _cumulative_to_single(revenue_cumulative)
            net_profit_single = _cumulative_to_single(net_profit_cumulative)

            result['revenue_ttm'] = calculate_ttm(revenue_single)
            result['net_profit_ttm'] = calculate_ttm(net_profit_single)

        cashflow_df = ak.stock_cash_flow_sheet_by_report_em(symbol=code6)
        if cashflow_df is not None and not cashflow_df.empty and len(cashflow_df) >= 1:
            ocf_cumulative = []
            for i in range(min(8, len(cashflow_df))):
                row = cashflow_df.iloc[i]
                ocf = _safe_float(row.get('经营活动产生的现金流量净额', None))
                ocf_cumulative.append(ocf)
            ocf_single = _cumulative_to_single(ocf_cumulative)
            result['operating_cashflow_ttm'] = calculate_ttm(ocf_single)

        spot_df = ak.stock_zh_a_spot_em()
        if spot_df is not None and not spot_df.empty:
            stock_row = spot_df[spot_df['代码'] == code6]
            if not stock_row.empty:
                total_mv = _safe_float(stock_row.iloc[0].get('总市值', None))
                if total_mv and result['net_profit_ttm'] and result['net_profit_ttm'] != 0:
                    result['pe_ttm'] = total_mv / result['net_profit_ttm']

        logger.debug(f"TTM for {code6}: revenue={result['revenue_ttm']}, net_profit={result['net_profit_ttm']}, pe_ttm={result['pe_ttm']}")

    except Exception as e:
        logger.debug(f"TTM calculation failed for {symbol}: {e}")

    return result
