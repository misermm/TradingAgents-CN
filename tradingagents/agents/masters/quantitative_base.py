import json
import re
from typing import Dict, Any, Optional, Callable, List
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

_FIELD_ALIASES = {
    "净资产收益率(roe)": ["ROE", "净资产收益率", "return_on_equity", "roe"],
    "净资产收益率": ["ROE", "return_on_equity", "roe"],
    "资产负债率": ["debt_ratio", "debt_to_equity"],
    "市盈率(pe)": ["PE", "pe", "pe_dynamic", "price_to_earnings", "pe_ratio"],
    "市盈率": ["PE", "pe", "pe_dynamic", "price_to_earnings", "pe_ratio"],
    "市盈率TTM": ["PE_TTM", "pe_ttm", "滚动市盈率"],
    "滚动市盈率": ["PE_TTM", "pe_ttm", "市盈率TTM"],
    "市净率(pb)": ["PB", "pb", "price_to_book", "pb_ratio"],
    "市净率": ["PB", "pb", "price_to_book", "pb_ratio"],
    "毛利率": ["gross_margin", "grossMargin", "gross_profit_margin"],
    "净利润率": ["net_margin", "netMargin", "net_profit_margin", "净利率"],
    "净利率": ["net_margin", "netMargin", "net_profit_margin", "净利润率"],
    "营业利润率": ["operating_margin", "operatingMargin"],
    "流动比率": ["current_ratio"],
    "速动比率": ["quick_ratio"],
    "股息率": ["dividend_yield", "dividend_yield_ratio"],
    "股息收益率": ["dividend_yield"],
    "每10股派现金额": ["dividend_cash_per_10_shares", "cash_dividend_per_10_shares"],
    "每10股派发现金红利": ["dividend_cash_per_10_shares", "cash_dividend_per_10_shares"],
    "股权登记日": ["dividend_record_date"],
    "除权除息日": ["dividend_ex_date"],
    "除息日": ["dividend_ex_date"],
    "回购金额下限": ["buyback_amount_min"],
    "回购金额上限": ["buyback_amount_max"],
    "回购期限": ["buyback_period_months"],
    "回购期限(月)": ["buyback_period_months"],
    "质押比例": ["pledge_ratio"],
    "质押占比": ["pledge_ratio"],
    "营收增长率": ["revenue_growth", "revenue_growth_rate"],
    "ROE趋势": ["roe_trend"],
    "毛利率趋势": ["gross_margin_trend"],
    "自由现金流趋势": ["free_cash_flow_trend"],
    "扣非净利润趋势": ["deducted_net_profit_trend"],
    "资产负债率趋势": ["debt_ratio_trend"],
    "流动比率趋势": ["current_ratio_trend"],
    "现金流覆盖净利润": ["cashflow_to_profit_ratio", "ocf_to_profit_ratio"],
    "应收占营收变化": ["receivables_to_revenue_change"],
    "存货占营收变化": ["inventory_to_revenue_change"],
    "总市值": ["total_mv", "market_cap"],
    "市销率(ps)": ["PS", "ps", "price_to_sales"],
    "roa": ["ROA", "return_on_assets", "总资产收益率"],
    "roe": ["ROE", "净资产收益率", "return_on_equity"],
    "自由现金流": ["free_cash_flow", "fcf", "free_cash_flow_per_share", "每股企业自由现金流量"],
    "每股企业自由现金流量": ["free_cash_flow_per_share", "fcf_per_share", "free_cash_flow", "fcf"],
    "经营现金流量净额": ["operating_cash_flow", "ocf", "经营现金流"],
    "经营活动产生的现金流量净额": ["operating_cash_flow", "ocf", "经营现金流", "经营现金流量净额"],
    "购建固定资产、无形资产和其他长期资产支付的现金": ["capital_expenditure", "capex", "资本开支", "资本支出"],
    "净利润": ["net_income", "net_profit"],
    "扣除非经常性损益后的净利润": ["deducted_net_profit", "扣非净利润"],
    "扣非净利润": ["deducted_net_profit"],
    "营业收入": ["revenue", "total_revenue"],
    "营业总收入": ["revenue", "total_revenue", "operating_revenue"],
    "资产总计": ["total_assets", "总资产"],
    "资产合计": ["total_assets", "总资产"],
    "负债合计": ["total_liabilities", "总负债"],
    "负债总计": ["total_liabilities", "总负债"],
    "流动资产合计": ["current_assets", "流动资产"],
    "流动负债合计": ["current_liabilities", "流动负债"],
    "应收账款": ["accounts_receivable"],
    "存货": ["inventory"],
    "商誉": ["goodwill"],
    "投入资本回报率": ["ROIC", "roic", "return_on_invested_capital"],
    "资本回报率": ["ROIC", "roic", "return_on_invested_capital"],
    "每股收益(eps)": ["EPS", "eps", "earningsPerShare", "basic_eps"],
    "每股收益": ["EPS", "eps", "earningsPerShare", "basic_eps"],
    "每股净资产": ["book_value_per_share", "bvps", "bps", "bookValuePerShare"],
    "总资产": ["total_assets", "totalAssets", "资产总计"],
    "总负债": ["total_liabilities", "totalLiabilities", "负债合计"],
    "流动资产": ["current_assets", "totalCurrentAssets", "流动资产合计"],
    "流动负债": ["current_liabilities", "totalCurrentLiabilities", "流动负债合计"],
}


def _expand_aliases(data: Dict[str, Any]) -> Dict[str, Any]:
    expanded = dict(data)
    for key, value in data.items():
        key_lower = key.lower().strip()
        for alias_key, aliases in _FIELD_ALIASES.items():
            if key_lower == alias_key.lower() or key_lower == alias_key.lower().replace(" ", ""):
                for alias in aliases:
                    if alias not in expanded:
                        expanded[alias] = value
                break
        match = re.match(r'^(.+?)\((\w+)\)$', key)
        if match:
            cn_name = match.group(1)
            en_abbr = match.group(2)
            if cn_name not in expanded:
                expanded[cn_name] = value
            if en_abbr.upper() not in expanded:
                expanded[en_abbr.upper()] = value
            if en_abbr.lower() not in expanded:
                expanded[en_abbr.lower()] = value
    return expanded


def extract_financial_data(raw_data: str) -> Dict[str, Any]:
    if not raw_data or not isinstance(raw_data, str):
        return {}
    data = {}
    try:
        parsed = json.loads(raw_data)
        if isinstance(parsed, dict):
            data = parsed
    except (json.JSONDecodeError, TypeError):
        pass

    lines = raw_data.replace(',', '\n').replace('，', '\n').split('\n') if raw_data else []
    for line in lines:
        line = line.strip()
        line = re.sub(r'^[-*#|>]+\s*', '', line).strip()
        if not line:
            continue
        for sep in [':', '：']:
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip().lstrip('- ').strip()
                key = re.sub(r'\*+', '', key).strip()
                key = re.sub(r'[\[\(（【].*?[\]\)）】]', '', key).strip()
                value = value.strip()
                if '#' in value:
                    value = value.split('#', 1)[0].strip()
                for suffix in [',', '，', '。', '倍', '元', '万', '亿']:
                    value = value.rstrip(suffix)
                value = value.strip()
                is_pct = value.endswith('%')
                if is_pct:
                    value = value.rstrip('%').strip()
                try:
                    if '.' in value:
                        num_val = float(value)
                    else:
                        num_val = int(value)
                    data[key] = num_val / 100.0 if is_pct else num_val
                except (ValueError, TypeError):
                    if value not in ('', 'N/A', '-', '无', '未知', '行业估算'):
                        data[key] = value
                break

    data = _expand_aliases(data)

    return data


def safe_float(value, default=None) -> Optional[float]:
    if value is None:
        return default
    try:
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = str(value).replace(',', '').replace('%', '').replace('，', '').strip()
        if cleaned in ('', '-', 'N/A', '无', '未知'):
            return default
        result = float(cleaned)
        if '%' in str(value):
            result = result / 100.0
        return result
    except (ValueError, TypeError):
        return default


def score_to_signal(score: float, max_score: float, bullish_threshold=0.7, bearish_threshold=0.3) -> str:
    ratio = score / max_score if max_score > 0 else 0
    if ratio >= bullish_threshold:
        return "bullish"
    elif ratio <= bearish_threshold:
        return "bearish"
    return "neutral"


def evidence_verdict(score: float, max_score: float) -> str:
    if max_score <= 0:
        return "info"
    if score >= max_score:
        return "pass"
    if score > 0:
        return "partial"
    return "fail"


def make_evidence_row(
    area: str,
    rule: str,
    field: str,
    observed: Any,
    score: float,
    max_score: float,
    reason: str,
) -> Dict[str, Any]:
    return {
        "area": area,
        "rule": rule,
        "field": field,
        "observed": observed,
        "score": score,
        "max_score": max_score,
        "verdict": evidence_verdict(score, max_score),
        "reason": reason,
    }


def format_quantitative_summary(analysis_name: str, results: Dict[str, Any]) -> str:
    signal = results.get("signal", "neutral")
    score = results.get("score", 0)
    max_score = results.get("max_score", 1)
    details = results.get("details", "")

    signal_cn = {"bullish": "看涨", "bearish": "看跌", "neutral": "中性"}.get(signal, "中性")

    summary = f"\n## 📊 {analysis_name}量化评分\n"
    summary += f"**综合信号**: {signal_cn} | **评分**: {score:.1f}/{max_score:.1f}\n\n"

    sub_analyses = results.get("sub_analyses", {})
    if sub_analyses:
        summary += "| 分析维度 | 评分 | 信号 | 关键发现 |\n"
        summary += "|---------|------|------|----------|\n"
        for name, sub in sub_analyses.items():
            sub_score = sub.get("score", 0)
            sub_max = sub.get("max_score", 1)
            sub_signal = sub.get("signal", "neutral")
            sub_signal_cn = {"bullish": "看涨", "bearish": "看跌", "neutral": "中性"}.get(sub_signal, "中性")
            sub_details = sub.get("details", "")[:60]
            summary += f"| {name} | {sub_score:.1f}/{sub_max:.1f} | {sub_signal_cn} | {sub_details} |\n"
        summary += "\n"

    evidence_table: List[Dict[str, Any]] = results.get("evidence_table", [])
    if evidence_table:
        summary += "| 证据维度 | 规则 | 字段 | 观测值 | 判定 | 得分 |\n"
        summary += "|---------|------|------|--------|------|------|\n"
        for row in evidence_table:
            summary += (
                f"| {row.get('area', '')} | {row.get('rule', '')} | {row.get('field', '')} | "
                f"{row.get('observed', '')} | {row.get('verdict', '')} | "
                f"{row.get('score', 0):.1f}/{row.get('max_score', 0):.1f} |\n"
            )
        summary += "\n"

    if details:
        summary += f"**详细说明**: {details}\n"

    return summary
