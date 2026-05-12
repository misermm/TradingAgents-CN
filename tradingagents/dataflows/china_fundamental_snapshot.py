"""
A-share free-source fundamental snapshot fusion.

This module builds a field-level snapshot from free public sources such as
Eastmoney, AKShare, and BaoStock. It keeps source provenance and quality
metadata next to every field so master analysts can distinguish real
disclosures from missing or estimated values.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

logger = logging.getLogger(__name__)


FREE_SOURCE_PRIORITY = {
    "eastmoney": 100,
    "akshare": 80,
    "akshare_direct": 78,
    "sina_finance": 76,
    "akshare_indicator_lg": 75,
    "baostock_direct": 72,
    "baostock": 70,
    "mongodb": 60,
    "cache": 50,
    "text": 40,
}


FIELD_SPECS: Dict[str, Dict[str, Any]] = {
    "price": {"label": "最新价格", "aliases": ["price", "close", "current_price", "latest_price", "最新价", "收盘价"], "required": False},
    "pe": {"label": "静态市盈率", "aliases": ["pe", "PE", "pe_dynamic", "price_to_earnings", "市盈率", "P/E"], "required": False},
    "pe_ttm": {"label": "PE_TTM", "aliases": ["pe_ttm", "PE_TTM", "pe_ratio", "市盈率TTM", "滚动市盈率"], "required": True},
    "eps": {"label": "每股收益", "aliases": ["eps", "EPS", "basic_eps", "每股收益", "earningsPerShare", "基本每股收益"], "required": True},
    "pb": {"label": "PB", "aliases": ["pb", "PB", "price_to_book", "pb_mrq", "市净率"], "required": True},
    "book_value_per_share": {"label": "每股净资产", "aliases": ["bvps", "book_value_per_share", "每股净资产", "bookValuePerShare", "bps"], "required": True},
    "total_mv": {"label": "总市值", "aliases": ["total_mv", "market_cap", "总市值"], "required": False},
    "revenue": {"label": "营业收入", "aliases": ["revenue", "total_revenue", "operating_revenue", "营业收入", "营业总收入", "营收"], "required": True},
    "revenue_yoy": {"label": "营收同比", "aliases": ["revenue_yoy", "revenue_growth", "YYZSRTBZZ", "营业收入同比增长率", "营业总收入同比增长率"], "required": False},
    "net_profit": {"label": "净利润", "aliases": ["net_profit", "net_income", "净利润"], "required": True},
    "net_profit_yoy": {"label": "净利润同比", "aliases": ["net_profit_yoy", "profit_growth", "GSJLRTBZZ", "净利润同比增长率"], "required": False},
    "equity_yoy": {"label": "净资产同比", "aliases": ["equity_yoy", "YOYEquity", "净资产同比增长率"], "required": False},
    "deducted_net_profit": {"label": "扣非净利润", "aliases": ["deducted_net_profit", "KCFJCXSYJLR", "扣非净利润", "扣除非经常性损益后的净利润"], "required": False},
    "deducted_net_profit_trend": {"label": "扣非净利润趋势", "aliases": ["deducted_net_profit_trend", "扣非净利润趋势"], "required": False},
    "roe": {"label": "ROE", "aliases": ["roe", "return_on_equity", "净资产收益率", "ROE"], "required": True},
    "roa": {"label": "ROA", "aliases": ["roa", "return_on_assets", "总资产收益率"], "required": False},
    "roic": {"label": "ROIC", "aliases": ["roic", "投入资本回报率", "资本回报率"], "required": False},
    "roe_trend": {"label": "ROE趋势", "aliases": ["roe_trend", "ROE趋势"], "required": False},
    "gross_margin": {"label": "毛利率", "aliases": ["gross_margin", "毛利率"], "required": False},
    "gross_margin_trend": {"label": "毛利率趋势", "aliases": ["gross_margin_trend", "毛利率趋势"], "required": False},
    "net_margin": {"label": "净利率", "aliases": ["net_margin", "net_profit_margin", "净利率", "净利润率"], "required": False},
    "operating_cash_flow": {"label": "经营现金流", "aliases": ["operating_cash_flow", "n_cashflow_act", "经营现金流", "经营活动现金流", "经营活动产生的现金流量净额"], "required": False},
    "operating_cash_flow_per_share": {"label": "每股经营现金流", "aliases": ["operating_cash_flow_per_share", "每股经营性现金流", "每股经营性现金流(元)"], "required": False},
    "free_cash_flow": {"label": "自由现金流", "aliases": ["free_cash_flow", "fcf", "自由现金流"], "required": False},
    "free_cash_flow_trend": {"label": "自由现金流趋势", "aliases": ["free_cash_flow_trend", "自由现金流趋势"], "required": False},
    "capital_expenditure": {"label": "资本开支", "aliases": ["capital_expenditure", "capex", "购建固定资产、无形资产和其他长期资产支付的现金"], "required": False},
    "debt_ratio": {"label": "资产负债率", "aliases": ["debt_ratio", "资产负债率", "负债率"], "required": True},
    "debt_ratio_trend": {"label": "资产负债率趋势", "aliases": ["debt_ratio_trend", "资产负债率趋势"], "required": False},
    "total_assets": {"label": "总资产", "aliases": ["total_assets", "总资产", "资产总计", "资产合计", "totalAssets"], "required": True},
    "total_liabilities": {"label": "总负债", "aliases": ["total_liabilities", "总负债", "负债合计", "负债总计", "totalLiabilities"], "required": True},
    "current_assets": {"label": "流动资产", "aliases": ["current_assets", "流动资产", "流动资产合计", "totalCurrentAssets"], "required": False},
    "current_liabilities": {"label": "流动负债", "aliases": ["current_liabilities", "流动负债", "流动负债合计", "totalCurrentLiabilities"], "required": False},
    "current_ratio": {"label": "流动比率", "aliases": ["current_ratio", "流动比率"], "required": False},
    "quick_ratio": {"label": "速动比率", "aliases": ["quick_ratio", "速动比率", "quickRatio"], "required": False},
    "current_ratio_trend": {"label": "流动比率趋势", "aliases": ["current_ratio_trend", "流动比率趋势"], "required": False},
    "accounts_receivable": {"label": "应收账款", "aliases": ["accounts_receivable", "应收账款"], "required": False},
    "contract_liabilities": {"label": "\u5408\u540c\u8d1f\u503a", "aliases": ["contract_liabilities", "\u5408\u540c\u8d1f\u503a", "\u5408\u540c\u8d1f\u503a\u5408\u8ba1"], "required": False},
    "contract_assets": {"label": "\u5408\u540c\u8d44\u4ea7", "aliases": ["contract_assets", "\u5408\u540c\u8d44\u4ea7"], "required": False},
    "accounts_payable": {"label": "\u5e94\u4ed8\u8d26\u6b3e", "aliases": ["accounts_payable", "\u5e94\u4ed8\u8d26\u6b3e", "\u5e94\u4ed8\u7968\u636e\u53ca\u5e94\u4ed8\u8d26\u6b3e"], "required": False},
    "receivables_to_revenue_change": {"label": "应收占营收变化", "aliases": ["receivables_to_revenue_change", "应收占营收变化"], "required": False},
    "inventory": {"label": "存货", "aliases": ["inventory", "存货"], "required": False},
    "inventory_to_revenue_change": {"label": "存货占营收变化", "aliases": ["inventory_to_revenue_change", "存货占营收变化"], "required": False},
    "contract_liabilities_to_revenue_change": {"label": "\u5408\u540c\u8d1f\u503a\u5360\u8425\u6536\u53d8\u5316", "aliases": ["contract_liabilities_to_revenue_change", "\u5408\u540c\u8d1f\u503a\u5360\u8425\u6536\u53d8\u5316"], "required": False},
    "contract_assets_to_revenue_change": {"label": "\u5408\u540c\u8d44\u4ea7\u5360\u8425\u6536\u53d8\u5316", "aliases": ["contract_assets_to_revenue_change", "\u5408\u540c\u8d44\u4ea7\u5360\u8425\u6536\u53d8\u5316"], "required": False},
    "accounts_payable_to_revenue_change": {"label": "\u5e94\u4ed8\u8d26\u6b3e\u5360\u8425\u6536\u53d8\u5316", "aliases": ["accounts_payable_to_revenue_change", "\u5e94\u4ed8\u8d26\u6b3e\u5360\u8425\u6536\u53d8\u5316"], "required": False},
    "goodwill": {"label": "商誉", "aliases": ["goodwill", "商誉"], "required": False},
    "cashflow_to_profit_ratio": {"label": "现金流覆盖净利润", "aliases": ["cashflow_to_profit_ratio", "现金流覆盖净利润", "ocf_to_profit_ratio"], "required": False},
    "dividend_yield": {"label": "股息率", "aliases": ["dividend_yield", "股息率"], "required": False},
    "dividend_events": {"label": "分红公告数", "aliases": ["dividend_events", "分红公告数", "分红", "权益分派"], "required": False},
    "dividend_cash_per_10_shares": {"label": "每10股派现金额", "aliases": ["dividend_cash_per_10_shares", "每10股派现金额", "每10股派发现金红利"], "required": False},
    "dividend_record_date": {"label": "股权登记日", "aliases": ["dividend_record_date", "股权登记日"], "required": False},
    "dividend_ex_date": {"label": "除权除息日", "aliases": ["dividend_ex_date", "除权除息日", "除息日"], "required": False},
    "buyback_events": {"label": "回购公告数", "aliases": ["buyback_events", "回购公告数", "回购"], "required": False},
    "buyback_amount_min": {"label": "回购金额下限", "aliases": ["buyback_amount_min", "回购金额下限"], "required": False},
    "buyback_amount_max": {"label": "回购金额上限", "aliases": ["buyback_amount_max", "回购金额上限"], "required": False},
    "buyback_period_months": {"label": "回购期限(月)", "aliases": ["buyback_period_months", "回购期限", "回购期限(月)"], "required": False},
    "pledge_risk_events": {"label": "质押风险公告数", "aliases": ["pledge_risk_events", "质押风险公告数", "质押"], "required": False},
    "pledge_ratio": {"label": "质押比例", "aliases": ["pledge_ratio", "质押比例", "质押占比"], "required": False},
    "litigation_risk_events": {"label": "诉讼风险公告数", "aliases": ["litigation_risk_events", "诉讼风险公告数", "诉讼", "仲裁"], "required": False},
    "related_party_transaction_events": {"label": "关联交易公告数", "aliases": ["related_party_transaction_events", "关联交易公告数", "关联交易"], "required": False},
    "management_change_events": {"label": "管理层变更公告数", "aliases": ["management_change_events", "管理层变更公告数", "董事长", "高管", "管理层"], "required": False},
    "insider_increase_events": {"label": "管理层增持公告数", "aliases": ["insider_increase_events", "管理层增持公告数", "高管增持", "董监高增持"], "required": False},
    "insider_decrease_events": {"label": "管理层减持公告数", "aliases": ["insider_decrease_events", "管理层减持公告数", "高管减持", "董监高减持"], "required": False},
    "earnings_positive_events": {"label": "业绩利好公告数", "aliases": ["earnings_positive_events", "业绩利好公告数", "业绩预增", "业绩预盈", "扭亏"], "required": False},
    "earnings_negative_events": {"label": "业绩利空公告数", "aliases": ["earnings_negative_events", "业绩利空公告数", "业绩预减", "业绩预亏", "首亏", "续亏"], "required": False},
    "earnings_guidance_change_pct_min": {"label": "业绩预告同比下限", "aliases": ["earnings_guidance_change_pct_min", "业绩预告同比下限"], "required": False},
    "earnings_guidance_change_pct_max": {"label": "业绩预告同比上限", "aliases": ["earnings_guidance_change_pct_max", "业绩预告同比上限"], "required": False},
    "earnings_guidance_net_profit_min": {"label": "业绩预告净利润下限", "aliases": ["earnings_guidance_net_profit_min", "业绩预告净利润下限"], "required": False},
    "earnings_guidance_net_profit_max": {"label": "业绩预告净利润上限", "aliases": ["earnings_guidance_net_profit_max", "业绩预告净利润上限"], "required": False},
    "earnings_guidance_revenue_min": {"label": "\u4e1a\u7ee9\u9884\u544a\u8425\u6536\u4e0b\u9650", "aliases": ["earnings_guidance_revenue_min", "\u4e1a\u7ee9\u9884\u544a\u8425\u6536\u4e0b\u9650"], "required": False},
    "earnings_guidance_revenue_max": {"label": "\u4e1a\u7ee9\u9884\u544a\u8425\u6536\u4e0a\u9650", "aliases": ["earnings_guidance_revenue_max", "\u4e1a\u7ee9\u9884\u544a\u8425\u6536\u4e0a\u9650"], "required": False},
    "earnings_guidance_revenue_change_pct_min": {"label": "业绩预告营收同比下限", "aliases": ["earnings_guidance_revenue_change_pct_min", "业绩预告营收同比下限"], "required": False},
    "earnings_guidance_revenue_change_pct_max": {"label": "业绩预告营收同比上限", "aliases": ["earnings_guidance_revenue_change_pct_max", "业绩预告营收同比上限"], "required": False},
    "regulatory_penalty_events": {"label": "监管处罚公告数", "aliases": ["regulatory_penalty_events", "监管处罚公告数", "监管处罚", "立案调查", "警示函"], "required": False},
    "regulatory_penalty_severity": {"label": "监管处罚严重度", "aliases": ["regulatory_penalty_severity", "监管处罚严重度"], "required": False},
    "regulatory_penalty_amount_max": {"label": "\u76d1\u7ba1\u5904\u7f5a\u91d1\u989d\u4e0a\u9650", "aliases": ["regulatory_penalty_amount_max", "\u76d1\u7ba1\u5904\u7f5a\u91d1\u989d\u4e0a\u9650"], "required": False},
    "goodwill_impairment_events": {"label": "商誉减值公告数", "aliases": ["goodwill_impairment_events", "商誉减值公告数", "商誉减值"], "required": False},
    "related_party_transaction_amount_max": {"label": "关联交易金额上限", "aliases": ["related_party_transaction_amount_max", "关联交易金额上限"], "required": False},
    "goodwill_impairment_amount_max": {"label": "商誉减值金额上限", "aliases": ["goodwill_impairment_amount_max", "商誉减值金额上限"], "required": False},
    "asset_impairment_events": {"label": "\u8d44\u4ea7\u51cf\u503c\u516c\u544a\u6570", "aliases": ["asset_impairment_events", "\u8d44\u4ea7\u51cf\u503c\u516c\u544a\u6570", "\u8d44\u4ea7\u51cf\u503c", "\u4fe1\u7528\u51cf\u503c"], "required": False},
    "asset_impairment_amount_max": {"label": "\u8d44\u4ea7\u51cf\u503c\u91d1\u989d\u4e0a\u9650", "aliases": ["asset_impairment_amount_max", "\u8d44\u4ea7\u51cf\u503c\u91d1\u989d\u4e0a\u9650"], "required": False},
    "shareholder_return_summary": {"label": "股东回报公告摘要", "aliases": ["shareholder_return_summary", "股东回报", "分红回购摘要", "资本配置"], "required": False},
    "governance_risk_summary": {"label": "治理风险公告摘要", "aliases": ["governance_risk_summary", "治理风险", "质押诉讼关联交易摘要"], "required": False},
    "management_alignment_summary": {"label": "管理层增减持摘要", "aliases": ["management_alignment_summary", "管理层增减持摘要", "高管增减持"], "required": False},
    "earnings_guidance_summary": {"label": "业绩预告摘要", "aliases": ["earnings_guidance_summary", "业绩预告摘要", "业绩快报摘要"], "required": False},
}


MISSING_MARKERS = {"", "N/A", "n/a", "NA", "none", "None", "null", "--", "-", "无", "未知", "缺失", "暂无", "暂不可用"}
ESTIMATED_MARKERS = ("行业估算", "估算", "推算", "estimated", "estimate", "industry estimate")
PERCENT_FIELDS = {
    "roe",
    "roa",
    "roic",
    "gross_margin",
    "net_margin",
    "debt_ratio",
    "dividend_yield",
    "revenue_yoy",
    "net_profit_yoy",
    "pledge_ratio",
    "earnings_guidance_change_pct_min",
    "earnings_guidance_change_pct_max",
    "earnings_guidance_revenue_change_pct_min",
    "earnings_guidance_revenue_change_pct_max",
}

ANNOUNCEMENT_SIGNAL_SPECS = {
    "dividend_events": ("分红", "派息", "现金红利", "利润分配", "权益分派"),
    "buyback_events": ("回购", "股份回购"),
    "pledge_risk_events": ("质押", "解除质押", "股份冻结"),
    "litigation_risk_events": ("诉讼", "仲裁", "立案", "判决"),
    "related_party_transaction_events": ("关联交易",),
    "management_change_events": ("董事长", "总经理", "高管", "董事", "监事", "辞职", "聘任"),
}

INSIDER_KEYWORDS = ("高管", "高级管理人员", "董监高", "董事", "监事", "经理", "实控人", "实际控制人", "控股股东")
REGULATORY_KEYWORDS = ("处罚", "监管函", "警示函", "立案", "调查", "问询函", "通报批评", "行政监管", "立案告知书")
GOODWILL_KEYWORDS = ("商誉减值",)
ASSET_IMPAIRMENT_KEYWORDS = ("\u8d44\u4ea7\u51cf\u503c", "\u4fe1\u7528\u51cf\u503c", "\u51cf\u503c\u51c6\u5907", "\u8ba1\u63d0\u51cf\u503c", "\u574f\u8d26\u51c6\u5907")
EARNINGS_GUIDANCE_KEYWORDS = ("业绩预告", "业绩快报", "预增", "预减", "预盈", "预亏", "首亏", "续亏", "扭亏")
POSITIVE_EARNINGS_KEYWORDS = ("预增", "预盈", "扭亏", "续盈", "大幅增长", "增长", "盈利")
NEGATIVE_EARNINGS_KEYWORDS = ("预减", "预亏", "首亏", "续亏", "下滑", "下降", "亏损")
FINANCIAL_STATEMENT_KEYS = (
    "latest",
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "cashflow_statement",
    "main_indicators",
    "financial_statement",
)
REPORT_PERIOD_KEYS = (
    "report_period",
    "REPORT_DATE",
    "report_date",
    "报表日期",
    "公告日期",
    "END_DATE",
    "date",
)
REGULATORY_SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
REGULATORY_SEVERITY_PATTERNS = (
    ("critical", ("立案调查", "立案告知书")),
    ("high", ("行政处罚", "处罚决定", "公开谴责", "公开认责")),
    ("medium", ("警示函", "监管函", "通报批评")),
    ("low", ("问询函", "工作函", "关注函")),
)


def _normalize_source(source: Optional[str]) -> str:
    return (source or "unknown").strip().lower()


def _value_status(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in MISSING_MARKERS:
            return "missing"
        lowered = stripped.lower()
        if any(marker.lower() in lowered for marker in ESTIMATED_MARKERS):
            return "estimated"
    return "present"


def _values_conflict(v1: Any, v2: Any) -> bool:
    if v1 == v2:
        return False
    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
        max_abs = max(abs(v1), abs(v2))
        if max_abs == 0:
            return False
        return abs(v1 - v2) / max_abs > 0.2
    return str(v1) != str(v2)


def _coerce_number(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip().replace(",", "")
    match = re.fullmatch(r"[-+]?\d+(?:\.\d+)?%?", stripped)
    if not match:
        return value
    number = float(stripped.rstrip("%"))
    return int(number) if number.is_integer() else number


def _flatten_mapping(data: Mapping[str, Any]) -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for key, value in data.items():
        normalized_key = str(key).strip()
        if normalized_key == "periods":
            continue
        if normalized_key == "latest" and isinstance(value, Mapping):
            flattened.update(_flatten_mapping(value))
        elif isinstance(value, Mapping):
            flattened.update(_flatten_mapping(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    nested = _flatten_mapping(item)
                    for nested_key, nested_value in nested.items():
                        if nested_key not in flattened:
                            flattened[nested_key] = nested_value
        else:
            if normalized_key not in flattened:
                flattened[normalized_key] = value
    return flattened


def get_eastmoney_direct_provider():
    from tradingagents.dataflows.providers.china.eastmoney_direct import EastMoneyDirectProvider

    return EastMoneyDirectProvider()


def get_akshare_provider():
    from tradingagents.dataflows.providers.china.akshare import get_akshare_provider as _get_provider

    return _get_provider()


def get_baostock_provider():
    from tradingagents.dataflows.providers.china.baostock import get_baostock_provider as _get_provider

    return _get_provider()


def _run_maybe_async(value: Any) -> Any:
    if not inspect.isawaitable(value):
        return value
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(value)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(value)
    finally:
        loop.close()


def _safe_provider_call(provider: Any, method_name: str, symbol: str) -> Any:
    method = getattr(provider, method_name, None)
    if not callable(method):
        return None
    try:
        return _run_maybe_async(method(symbol))
    except Exception as e:
        source_name = getattr(provider, "__class__", type(provider)).__name__
        logger.debug(f"_safe_provider_call: {source_name}.{method_name}({symbol}) 失败: {e}")
        return None


def _cleanup_provider(provider: Any) -> None:
    for method_name in ("disconnect", "close", "shutdown"):
        method = getattr(provider, method_name, None)
        if not callable(method):
            continue
        try:
            _run_maybe_async(method())
        except Exception as e:
            logger.debug(f"执行方法 {method_name} 失败（已忽略）: {e}")
        return


def _merge_provider_data(*parts: Any) -> Dict[str, Any]:
    """合并多个数据源的数据，空值不覆盖已有有效值"""
    merged: Dict[str, Any] = {}
    for part in parts:
        if isinstance(part, Mapping):
            for key, value in part.items():
                # 空值（None、空字符串、"N/A"）不覆盖已有有效值
                if value is None or value == "" or value == "N/A":
                    continue
                if key not in merged or merged[key] is None or merged[key] == "" or merged[key] == "N/A":
                    merged[key] = value
    return merged


def _extract_report_period(data: Any) -> Optional[str]:
    if not isinstance(data, Mapping):
        return None
    for key in REPORT_PERIOD_KEYS:
        value = data.get(key)
        if value not in (None, "", "N/A"):
            return str(value)[:10]
    return None


def _iter_statement_rows(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                yield item


def _expand_financial_statement_payloads(source_payloads: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    expanded: List[Mapping[str, Any]] = list(source_payloads)
    for payload in source_payloads:
        data = payload.get("data")
        if not isinstance(data, Mapping):
            continue
        for statement_key in FINANCIAL_STATEMENT_KEYS:
            value = data.get(statement_key)
            for row in _iter_statement_rows(value):
                report_period = payload.get("report_period") or _extract_report_period(row)
                expanded.append({
                    "source": payload.get("source", "unknown"),
                    "data": row,
                    "updated_at": payload.get("updated_at"),
                    "report_period": report_period,
                })
    return expanded


def _announcement_text(item: Mapping[str, Any]) -> str:
    return " ".join(str(item.get(key, "") or "") for key in ("title", "content", "summary"))


def _short_announcement_titles(items: List[Mapping[str, Any]], keywords: Iterable[str], limit: int = 3) -> str:
    titles: List[str] = []
    for item in items:
        text = _announcement_text(item)
        if any(keyword in text for keyword in keywords):
            title = str(item.get("title") or text).strip()
            if title:
                titles.append(title[:80])
        if len(titles) >= limit:
            break
    return "；".join(titles)


def _number_text_to_float(value: str, unit: str = "") -> Optional[float]:
    try:
        number = float(value.replace(",", ""))
    except (TypeError, ValueError):
        return None
    if "亿" in unit:
        return number * 100000000
    if "万" in unit:
        return number * 10000
    return number


def _extract_amount_values(text: str) -> List[float]:
    values = [
        _number_text_to_float(match.group(1), match.group(2))
        for match in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*(亿元|万元|元)", text)
    ]
    return [value for value in values if value is not None]


def _parse_dividend_cash_per_10_shares(text: str) -> Optional[float]:
    patterns = [
        r"每\s*10\s*股[^，。；;]*?(?:派发|派送)?[^，。；;]*?现金红利\s*([0-9]+(?:\.[0-9]+)?)\s*元",
        r"每\s*10\s*股\s*派\s*([0-9]+(?:\.[0-9]+)?)\s*元",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _number_text_to_float(match.group(1))
    return None


def _parse_buyback_amount_range(text: str) -> Dict[str, float]:
    numeric_values = _extract_amount_values(text)
    if not numeric_values:
        return {}
    return {
        "buyback_amount_min": min(numeric_values),
        "buyback_amount_max": max(numeric_values),
    }


def _normalize_cn_date(year: str, month: str, day: str) -> str:
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _parse_labeled_cn_date(text: str, label: str) -> Optional[str]:
    match = re.search(rf"{label}\s*[：: ]\s*(\d{{4}})年(\d{{1,2}})月(\d{{1,2}})日", text)
    if match:
        return _normalize_cn_date(match.group(1), match.group(2), match.group(3))
    match = re.search(rf"{label}\s*[：: ]\s*(\d{{4}})[-/](\d{{1,2}})[-/](\d{{1,2}})", text)
    if match:
        return _normalize_cn_date(match.group(1), match.group(2), match.group(3))
    return None


def _parse_buyback_period_months(text: str) -> Optional[int]:
    match = re.search(r"回购期限[^0-9一二三四五六七八九十半]{0,20}([0-9]+)\s*个?月", text)
    if match:
        return int(match.group(1))
    match = re.search(r"([0-9]+)\s*个?月内", text)
    if match and "回购" in text:
        return int(match.group(1))
    return None


def _parse_pledge_ratio(text: str) -> Optional[float]:
    patterns = [
        r"(?:质押比例|质押占比|占其所持股份比例)[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)\s*%",
        r"质押[^%]{0,24}([0-9]+(?:\.[0-9]+)?)\s*%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _number_text_to_float(match.group(1))
    return None


def _parse_regulatory_penalty_severity(text: str) -> Optional[str]:
    if not _contains_any(text, REGULATORY_KEYWORDS):
        return None
    for severity, keywords in REGULATORY_SEVERITY_PATTERNS:
        if _contains_any(text, keywords):
            return severity
    return "medium"


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_positive_earnings_guidance(text: str) -> bool:
    return _contains_any(text, EARNINGS_GUIDANCE_KEYWORDS) and _contains_any(text, POSITIVE_EARNINGS_KEYWORDS)


def _is_negative_earnings_guidance(text: str) -> bool:
    return _contains_any(text, EARNINGS_GUIDANCE_KEYWORDS) and _contains_any(text, NEGATIVE_EARNINGS_KEYWORDS)


def _parse_earnings_guidance_change_range(text: str) -> Dict[str, float]:
    if not _contains_any(text, EARNINGS_GUIDANCE_KEYWORDS):
        return {}
    snippets = [
        match.group(0)
        for match in re.finditer(r"(?:净利润|利润总额|亏损)[^\n\r，。；;]{0,40}", text)
    ]
    percent_values: List[float] = []
    for snippet in snippets:
        percent_values.extend(float(match.group(1)) for match in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*%", snippet))
    if not percent_values:
        percent_values = [float(match.group(1)) for match in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*%", text)]
    if not percent_values:
        return {}
    signed_values = [-value for value in percent_values] if _is_negative_earnings_guidance(text) and not _is_positive_earnings_guidance(text) else percent_values
    return {
        "earnings_guidance_change_pct_min": min(signed_values),
        "earnings_guidance_change_pct_max": max(signed_values),
    }


def _parse_earnings_guidance_revenue_change_range(text: str) -> Dict[str, float]:
    if not _contains_any(text, EARNINGS_GUIDANCE_KEYWORDS):
        return {}
    snippets = [
        match.group(0)
        for match in re.finditer(r"(?:营业总?收入|营业收入|营收)[^\n\r，。；;]{0,40}", text)
    ]
    percent_values: List[float] = []
    for snippet in snippets:
        percent_values.extend(float(match.group(1)) for match in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*%", snippet))
    if not percent_values:
        return {}
    signed_values = [-value for value in percent_values] if _is_negative_earnings_guidance(text) and not _is_positive_earnings_guidance(text) else percent_values
    return {
        "earnings_guidance_revenue_change_pct_min": min(signed_values),
        "earnings_guidance_revenue_change_pct_max": max(signed_values),
    }


def _parse_earnings_guidance_profit_range(text: str) -> Dict[str, float]:
    if not _contains_any(text, EARNINGS_GUIDANCE_KEYWORDS):
        return {}
    snippets = [
        match.group(0)
        for match in re.finditer(r"(?:\u51c0\u5229\u6da6|\u5229\u6da6\u603b\u989d|\u4e8f\u635f)[^\n\r\uff0c\u3002\uff1b;]{0,40}", text)
    ]
    amount_values: List[float] = []
    for snippet in snippets:
        amount_values.extend(_extract_amount_values(snippet))
    if not amount_values:
        return {}
    signed_values = [-value for value in amount_values] if "\u4e8f\u635f" in text and "\u626d\u4e8f" not in text else amount_values
    return {
        "earnings_guidance_net_profit_min": min(signed_values),
        "earnings_guidance_net_profit_max": max(signed_values),
    }




def _parse_earnings_guidance_revenue_range(text: str) -> Dict[str, float]:
    if not _contains_any(text, EARNINGS_GUIDANCE_KEYWORDS):
        return {}
    snippets = [
        match.group(0)
        for match in re.finditer(r"(?:\u8425\u4e1a\u603b?\u6536\u5165|\u8425\u4e1a\u6536\u5165|\u8425\u6536)[^\n\r\uff0c\u3002\uff1b;]{0,40}", text)
    ]
    revenue_values: List[float] = []
    for snippet in snippets:
        revenue_values.extend(_extract_amount_values(snippet))
    if not revenue_values:
        return {}
    return {
        "earnings_guidance_revenue_min": min(revenue_values),
        "earnings_guidance_revenue_max": max(revenue_values),
    }
def _apply_announcement_metrics(signals: Dict[str, Any], announcement_items: List[Mapping[str, Any]]) -> None:
    dividend_values: List[float] = []
    dividend_record_dates: List[str] = []
    dividend_ex_dates: List[str] = []
    buyback_ranges: List[Dict[str, float]] = []
    buyback_periods: List[int] = []
    pledge_values: List[float] = []
    related_party_amounts: List[float] = []
    goodwill_amounts: List[float] = []
    asset_impairment_amounts: List[float] = []
    regulatory_penalty_amounts: List[float] = []
    insider_increase_count = 0
    insider_decrease_count = 0
    earnings_positive_count = 0
    earnings_negative_count = 0
    regulatory_penalty_count = 0
    regulatory_penalty_severities: List[str] = []
    goodwill_impairment_count = 0
    asset_impairment_count = 0
    earnings_change_ranges: List[Dict[str, float]] = []
    earnings_profit_ranges: List[Dict[str, float]] = []
    earnings_revenue_ranges: List[Dict[str, float]] = []
    earnings_revenue_change_ranges: List[Dict[str, float]] = []

    for item in announcement_items:
        text = _announcement_text(item)
        if _contains_any(text, ANNOUNCEMENT_SIGNAL_SPECS["dividend_events"]):
            value = _parse_dividend_cash_per_10_shares(text)
            if value is not None:
                dividend_values.append(value)
            record_date = _parse_labeled_cn_date(text, "股权登记日")
            if record_date:
                dividend_record_dates.append(record_date)
            ex_date = _parse_labeled_cn_date(text, "除权除息日") or _parse_labeled_cn_date(text, "除息日")
            if ex_date:
                dividend_ex_dates.append(ex_date)
        if _contains_any(text, ANNOUNCEMENT_SIGNAL_SPECS["buyback_events"]):
            buyback_range = _parse_buyback_amount_range(text)
            if buyback_range:
                buyback_ranges.append(buyback_range)
            buyback_period = _parse_buyback_period_months(text)
            if buyback_period is not None:
                buyback_periods.append(buyback_period)
        if _contains_any(text, ANNOUNCEMENT_SIGNAL_SPECS["pledge_risk_events"]):
            pledge_ratio = _parse_pledge_ratio(text)
            if pledge_ratio is not None:
                pledge_values.append(pledge_ratio)
        if _contains_any(text, ANNOUNCEMENT_SIGNAL_SPECS["related_party_transaction_events"]):
            related_party_amounts.extend(_extract_amount_values(text))
        if _contains_any(text, INSIDER_KEYWORDS):
            if "增持" in text:
                insider_increase_count += 1
            if "减持" in text:
                insider_decrease_count += 1
        if _is_positive_earnings_guidance(text):
            earnings_positive_count += 1
        if _is_negative_earnings_guidance(text):
            earnings_negative_count += 1
        guidance_change_range = _parse_earnings_guidance_change_range(text)
        if guidance_change_range:
            earnings_change_ranges.append(guidance_change_range)
        guidance_profit_range = _parse_earnings_guidance_profit_range(text)
        if guidance_profit_range:
            earnings_profit_ranges.append(guidance_profit_range)
        guidance_revenue_range = _parse_earnings_guidance_revenue_range(text)
        if guidance_revenue_range:
            earnings_revenue_ranges.append(guidance_revenue_range)
        guidance_revenue_change_range = _parse_earnings_guidance_revenue_change_range(text)
        if guidance_revenue_change_range:
            earnings_revenue_change_ranges.append(guidance_revenue_change_range)
        if _contains_any(text, REGULATORY_KEYWORDS):
            regulatory_penalty_count += 1
            severity = _parse_regulatory_penalty_severity(text)
            if severity:
                regulatory_penalty_severities.append(severity)
            regulatory_penalty_amounts.extend(_extract_amount_values(text))
        if _contains_any(text, GOODWILL_KEYWORDS):
            goodwill_impairment_count += 1
            goodwill_amounts.extend(_extract_amount_values(text))
        if _contains_any(text, ASSET_IMPAIRMENT_KEYWORDS) and not _contains_any(text, GOODWILL_KEYWORDS):
            asset_impairment_count += 1
            asset_impairment_amounts.extend(_extract_amount_values(text))

    if dividend_values:
        signals["dividend_cash_per_10_shares"] = max(dividend_values)
    if dividend_record_dates:
        signals["dividend_record_date"] = max(dividend_record_dates)
    if dividend_ex_dates:
        signals["dividend_ex_date"] = max(dividend_ex_dates)
    if buyback_ranges:
        signals["buyback_amount_min"] = min(item["buyback_amount_min"] for item in buyback_ranges)
        signals["buyback_amount_max"] = max(item["buyback_amount_max"] for item in buyback_ranges)
    if buyback_periods:
        signals["buyback_period_months"] = max(buyback_periods)
    if pledge_values:
        signals["pledge_ratio"] = max(pledge_values)
    if related_party_amounts:
        signals["related_party_transaction_amount_max"] = max(related_party_amounts)
    if insider_increase_count > 0:
        signals["insider_increase_events"] = insider_increase_count
    if insider_decrease_count > 0:
        signals["insider_decrease_events"] = insider_decrease_count
    if earnings_positive_count > 0:
        signals["earnings_positive_events"] = earnings_positive_count
    if earnings_negative_count > 0:
        signals["earnings_negative_events"] = earnings_negative_count
    if earnings_change_ranges:
        signals["earnings_guidance_change_pct_min"] = min(item["earnings_guidance_change_pct_min"] for item in earnings_change_ranges)
        signals["earnings_guidance_change_pct_max"] = max(item["earnings_guidance_change_pct_max"] for item in earnings_change_ranges)
    if earnings_profit_ranges:
        signals["earnings_guidance_net_profit_min"] = min(item["earnings_guidance_net_profit_min"] for item in earnings_profit_ranges)
        signals["earnings_guidance_net_profit_max"] = max(item["earnings_guidance_net_profit_max"] for item in earnings_profit_ranges)
    if earnings_revenue_ranges:
        signals["earnings_guidance_revenue_min"] = min(item["earnings_guidance_revenue_min"] for item in earnings_revenue_ranges)
        signals["earnings_guidance_revenue_max"] = max(item["earnings_guidance_revenue_max"] for item in earnings_revenue_ranges)
    if earnings_revenue_change_ranges:
        signals["earnings_guidance_revenue_change_pct_min"] = min(item["earnings_guidance_revenue_change_pct_min"] for item in earnings_revenue_change_ranges)
        signals["earnings_guidance_revenue_change_pct_max"] = max(item["earnings_guidance_revenue_change_pct_max"] for item in earnings_revenue_change_ranges)
    if regulatory_penalty_count > 0:
        signals["regulatory_penalty_events"] = regulatory_penalty_count
    if regulatory_penalty_severities:
        signals["regulatory_penalty_severity"] = max(
            regulatory_penalty_severities,
            key=lambda item: REGULATORY_SEVERITY_RANK.get(item, 0),
        )
    if regulatory_penalty_amounts:
        signals["regulatory_penalty_amount_max"] = max(regulatory_penalty_amounts)
    if goodwill_impairment_count > 0:
        signals["goodwill_impairment_events"] = goodwill_impairment_count
    if goodwill_amounts:
        signals["goodwill_impairment_amount_max"] = max(goodwill_amounts)
    if asset_impairment_count > 0:
        signals["asset_impairment_events"] = asset_impairment_count
    if asset_impairment_amounts:
        signals["asset_impairment_amount_max"] = max(asset_impairment_amounts)


def build_china_announcement_signals(items: List[Mapping[str, Any]]) -> Dict[str, Any]:
    announcement_items = [
        item
        for item in items
        if str(item.get("type", "")).lower() in {"announcement", "company_announcement"}
        or "公告" in _announcement_text(item)
    ]
    signals: Dict[str, Any] = {}
    for field_name, keywords in ANNOUNCEMENT_SIGNAL_SPECS.items():
        count = sum(1 for item in announcement_items if _contains_any(_announcement_text(item), keywords))
        if count > 0:
            signals[field_name] = count

    _apply_announcement_metrics(signals, announcement_items)

    shareholder_summary = _short_announcement_titles(
        announcement_items,
        ANNOUNCEMENT_SIGNAL_SPECS["dividend_events"] + ANNOUNCEMENT_SIGNAL_SPECS["buyback_events"],
    )
    if shareholder_summary:
        signals["shareholder_return_summary"] = shareholder_summary

    governance_summary = _short_announcement_titles(
        announcement_items,
        ANNOUNCEMENT_SIGNAL_SPECS["pledge_risk_events"]
        + ANNOUNCEMENT_SIGNAL_SPECS["litigation_risk_events"]
        + ANNOUNCEMENT_SIGNAL_SPECS["related_party_transaction_events"]
        + ANNOUNCEMENT_SIGNAL_SPECS["management_change_events"]
        + REGULATORY_KEYWORDS
        + GOODWILL_KEYWORDS,
    )
    if governance_summary:
        signals["governance_risk_summary"] = governance_summary

    management_alignment_summary = _short_announcement_titles(
        announcement_items,
        INSIDER_KEYWORDS + ("增持", "减持"),
    )
    if management_alignment_summary:
        signals["management_alignment_summary"] = management_alignment_summary

    earnings_guidance_summary = _short_announcement_titles(announcement_items, EARNINGS_GUIDANCE_KEYWORDS)
    if earnings_guidance_summary:
        signals["earnings_guidance_summary"] = earnings_guidance_summary

    return signals


def collect_china_announcement_payload(symbol: str, days: int = 90, limit: int = 50) -> Optional[Dict[str, Any]]:
    manager = None
    try:
        from app.services.data_sources.manager import DataSourceManager

        manager = DataSourceManager()
        items, source = manager.get_news_with_fallback(
            code=symbol,
            days=days,
            limit=limit,
            include_announcements=True,
        )
    except Exception:
        return None
    finally:
        if manager is not None:
            try:
                manager.close()
            except Exception:
                pass
    if not items:
        return None
    signals = build_china_announcement_signals(items)
    if not signals:
        return None
    return {
        "source": source or "announcement",
        "data": signals,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report_period": f"recent_{days}d",
    }


def _akshare_safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        import pandas as pd
        if pd.isna(value):
            return None
    except (ImportError, TypeError, ValueError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _set_if_valid(data: Dict[str, Any], key: str, value: Any) -> None:
    if value is not None and key not in data:
        data[key] = value


def _to_baostock_code(symbol: str) -> str:
    s = str(symbol).strip()
    if s.startswith("6") or s.startswith("5"):
        return f"sh.{s}"
    if s.startswith("0") or s.startswith("3"):
        return f"sz.{s}"
    if s.startswith("8") or s.startswith("4"):
        return f"bj.{s}"
    return f"sz.{s}"


def _collect_baostock_payload(symbol: str) -> Optional[Dict[str, Any]]:
    """
    从BaoStock获取核心财务数据，作为主要数据源。
    """
    try:
        import baostock as bs
        lg = bs.login()
        if lg.error_code != '0':
            logger.warning(f"BaoStock login failed: {lg.error_msg}")
            return None

        data: Dict[str, Any] = {}
        bs_code = _to_baostock_code(symbol)
        year = datetime.now().year
        
        # 优先获取最新季报/年报
        for y in range(year, year - 3, -1):
            for q in [4, 3, 2, 1]:
                # 查询利润表
                rs_profit = bs.query_profit_data(code=bs_code, year=y, quarter=q)
                if rs_profit.error_code == '0' and rs_profit.next():
                    profit_data = rs_profit.get_row_data()
                    field_map = dict(zip(rs_profit.fields, profit_data))
                    _set_if_valid(data, "net_profit", _akshare_safe_float(field_map.get("netProfit"))) # 归母净利润
                    _set_if_valid(data, "eps", _akshare_safe_float(field_map.get("epsTTM")))
                    _set_if_valid(data, "revenue", _akshare_safe_float(field_map.get("MBRevenue"))) # 营业总收入
                    _set_if_valid(data, "roe", _akshare_safe_float(field_map.get("roeAvg"))) # 使用加权ROE
                    _set_if_valid(data, "net_margin", _akshare_safe_float(field_map.get("npMargin")))
                    _set_if_valid(data, "gross_margin", _akshare_safe_float(field_map.get("gpMargin")))
                    data["report_period"] = f"{y}Q{q}"

                # 查询资产负债表
                rs_balance = bs.query_balance_data(code=bs_code, year=y, quarter=q)
                if rs_balance.error_code == '0' and rs_balance.next():
                    balance_data = rs_balance.get_row_data()
                    field_map = dict(zip(rs_balance.fields, balance_data))
                    _set_if_valid(data, "debt_ratio", _akshare_safe_float(field_map.get("liabilityToAsset")))
                    _set_if_valid(data, "current_ratio", _akshare_safe_float(field_map.get("currentRatio")))
                    _set_if_valid(data, "quick_ratio", _akshare_safe_float(field_map.get("quickRatio")))

                # 查询成长能力
                rs_growth = bs.query_growth_data(code=bs_code, year=y, quarter=q)
                if rs_growth.error_code == '0' and rs_growth.next():
                    growth_data = rs_growth.get_row_data()
                    field_map = dict(zip(rs_growth.fields, growth_data))
                    _set_if_valid(data, "equity_yoy", _akshare_safe_float(field_map.get("YOYEquity")))
                    _set_if_valid(data, "net_profit_yoy", _akshare_safe_float(field_map.get("YOYNI")))

                # 查询现金流量表
                rs_cash = bs.query_cash_flow_data(code=bs_code, year=y, quarter=q)
                if rs_cash.error_code == '0' and rs_cash.next():
                    cash_data = rs_cash.get_row_data()
                    field_map = dict(zip(rs_cash.fields, cash_data))
                    _set_if_valid(data, "operating_cash_flow", _akshare_safe_float(field_map.get("CFO")))

                if data: # 如果获取到任何数据，就以此为准，不再查询更早的季度
                    bs.logout()
                    logger.info(f"BaoStock fetch for {symbol} successful for period {y}Q{q}. Fields: {list(data.keys())}")
                    return {
                        "source": "baostock_direct",
                        "data": data,
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "report_period": data.get("report_period"),
                        "data_period_type": "single_quarter",  # BaoStock返回单季度数据
                    }
        
        bs.logout()
        logger.warning(f"BaoStock could not find any recent financial data for {symbol}")
        return None
    except Exception as e:
        logger.error(f"BaoStock payload collection failed for {symbol}: {e}")
        return None

def _collect_akshare_direct_payload(symbol: str, updated_at: str, existing_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    从AKShare获取财务指标作为BaoStock的补充。
    只填充BaoStock未能提供的数据。
    """
    try:
        import akshare as ak
    except ImportError:
        logger.warning("akshare not installed, skip akshare_direct")
        return None

    data: Dict[str, Any] = {}
    
    try:
        # 使用东方财富的财务指标，字段更全
        df = ak.stock_financial_analysis_indicator(symbol=symbol, start_year=str(datetime.now().year - 1))
        if df is not None and not df.empty:
            # 获取最新的一行数据 (通常是最新季度)
            row = df.iloc[0]
            
            # 定义字段映射和优先级，优先使用BaoStock的数据
            field_map = {
                "eps": ["摊薄每股收益(元)", "加权每股收益(元)"],
                "book_value_per_share": ["每股净资产_调整前(元)", "每股净资产_调整后(元)"],
                "roe": ["加权净资产收益率(%)", "净资产收益率(%)"],
                "gross_margin": ["销售毛利率(%)"],
                "net_margin": ["销售净利率(%)"],
                "debt_ratio": ["资产负债率(%)"],
                "current_ratio": ["流动比率"],
                "operating_cash_flow_per_share": ["每股经营性现金流(元)"],
                # 注意：这里的净利润是“扣非净利润”，仅在BaoStock完全失败时作为参考
                "deducted_net_profit": ["扣除非经常性损益后的净利润(元)"],
            }

            for field, ak_names in field_map.items():
                if field not in existing_data: # 只填充缺失值
                    for ak_name in ak_names:
                        value = _akshare_safe_float(row.get(ak_name))
                        if value is not None:
                            _set_if_valid(data, field, value)
                            break # 找到一个有效值就跳出

            # 补充总资产等BaoStock可能缺失的字段
            if "total_assets" not in existing_data:
                 _set_if_valid(data, "total_assets", _akshare_safe_float(row.get("总资产(元)")))

            report_date = row.get("日期")
            if report_date is not None:
                data["report_period"] = str(report_date)

            logger.info(f"akshare_direct: Supplemented {len(data)} fields for {symbol}.")
    except Exception as e:
        logger.warning(f"akshare_direct: stock_financial_analysis_indicator failed: {e}")

    if not data:
        return None

    return {
        "source": "akshare_direct",
        "data": data,
        "updated_at": updated_at,
        "report_period": data.get("report_period"),
    }


def _collect_indicator_lg_payload(symbol: str, updated_at: str) -> Optional[Dict[str, Any]]:
    try:
        import akshare as ak
    except ImportError:
        return None
    try:
        df = ak.stock_financial_analysis_indicator(symbol=symbol, start_year=str(datetime.now().year - 1))
        if df is None or df.empty:
            return None
        latest = df.iloc[0]
        data = {}
        eps_diluted = _akshare_safe_float(latest.get("摊薄每股收益(元)"))
        if eps_diluted is not None:
            data["eps"] = eps_diluted
        eps_weighted = _akshare_safe_float(latest.get("加权每股收益(元)"))
        if eps_weighted is not None:
            data["eps"] = eps_weighted
        bvps = _akshare_safe_float(latest.get("每股净资产_调整前(元)"))
        if bvps is not None:
            data["book_value_per_share"] = bvps
        ocf_per_share = _akshare_safe_float(latest.get("每股经营性现金流(元)"))
        if ocf_per_share is not None:
            data["operating_cash_flow_per_share"] = ocf_per_share
        roe_val = _akshare_safe_float(latest.get("加权净资产收益率(%)") or latest.get("净资产收益率(%)"))
        if roe_val is not None:
            data["roe"] = roe_val
        roa_val = _akshare_safe_float(latest.get("总资产利润率(%)"))
        if roa_val is not None:
            data["roa"] = roa_val
        net_margin = _akshare_safe_float(latest.get("销售净利率(%)"))
        if net_margin is not None:
            data["net_margin"] = net_margin
        gross_margin = _akshare_safe_float(latest.get("销售毛利率(%)"))
        if gross_margin is not None:
            data["gross_margin"] = gross_margin
        revenue_yoy = _akshare_safe_float(latest.get("主营业务收入增长率(%)"))
        if revenue_yoy is not None:
            data["revenue_yoy"] = revenue_yoy
        net_profit_yoy = _akshare_safe_float(latest.get("净利润增长率(%)"))
        if net_profit_yoy is not None:
            data["net_profit_yoy"] = net_profit_yoy
        current_ratio = _akshare_safe_float(latest.get("流动比率"))
        if current_ratio is not None:
            data["current_ratio"] = current_ratio
        total_assets = _akshare_safe_float(latest.get("总资产(元)"))
        if total_assets is not None:
            data["total_assets"] = total_assets
        debt_ratio = _akshare_safe_float(latest.get("资产负债率(%)"))
        if debt_ratio is not None:
            data["debt_ratio"] = debt_ratio
        if not data:
            return None
        return {
            "source": "akshare_indicator_lg",
            "data": data,
            "updated_at": updated_at,
            "report_period": None,
        }
    except Exception:
        return None


def collect_china_free_source_payloads(symbol: str) -> List[Dict[str, Any]]:
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    provider_specs = [
        ("eastmoney", get_eastmoney_direct_provider),
        ("akshare", get_akshare_provider),
        ("baostock", get_baostock_provider),
    ]
    payloads: List[Dict[str, Any]] = []
    for source, factory in provider_specs:
        try:
            provider = factory()
        except Exception:
            continue
        try:
            quote_data = _safe_provider_call(provider, "get_stock_quotes", symbol)
            financial_data = _safe_provider_call(provider, "get_financial_data", symbol)
            basic_info = _safe_provider_call(provider, "get_stock_basic_info", symbol)
            data = _merge_provider_data(quote_data, financial_data, basic_info)
            if data:
                report_period = data.get("report_period")
                latest = data.get("latest")
                if isinstance(latest, Mapping):
                    report_period = report_period or _extract_report_period(latest)
                payloads.append(
                    {
                        "source": source,
                        "data": data,
                        "updated_at": updated_at,
                        "report_period": report_period,
                    }
                )
        finally:
            _cleanup_provider(provider)

    indicator_lg_payload = _collect_indicator_lg_payload(symbol, updated_at)
    if indicator_lg_payload:
        payloads.append(indicator_lg_payload)

    announcement_payload = collect_china_announcement_payload(symbol)
    if announcement_payload:
        payloads.append(announcement_payload)

    required_fields = [name for name, spec in FIELD_SPECS.items() if spec.get("required")]
    present_required = set()
    for payload in payloads:
        payload_data = payload.get("data", {})
        if isinstance(payload_data, Mapping):
            flattened = _flatten_mapping(payload_data)
            for field_name in required_fields:
                if field_name in present_required:
                    continue
                spec = FIELD_SPECS[field_name]
                raw_value = _extract_field(flattened, spec["aliases"])
                if _value_status(raw_value) == "present":
                    present_required.add(field_name)

    required_coverage = len(present_required) / len(required_fields) if required_fields else 1.0
    # 无论覆盖率如何，都优先尝试BaoStock获取更准确的财务报表数据
    baostock_payload = _collect_baostock_payload(symbol)
    if baostock_payload:
        payloads.insert(0, baostock_payload) # 插入到最前面，确保最高优先级
        # 更新已存在字段，以便akshare补充逻辑正确工作
        flattened_baostock = _flatten_mapping(baostock_payload.get("data", {}))
        for field_name in required_fields:
            if field_name in present_required:
                continue
            spec = FIELD_SPECS[field_name]
            raw_value = _extract_field(flattened_baostock, spec["aliases"])
            if _value_status(raw_value) == "present":
                present_required.add(field_name)
        required_coverage = len(present_required) / len(required_fields) if required_fields else 1.0

    if required_coverage < 0.85: # 提高覆盖率要求
        missing_fields = [name for name in required_fields if name not in present_required]
        logger.info(f"{symbol} 必需字段覆盖率 {required_coverage:.0%} < 85%，缺失: {missing_fields}，启用 akshare_direct 兜底")
        
        # 获取所有已存在的数据，传给akshare补充函数
        all_existing_data = {}
        for p in payloads:
            all_existing_data.update(p.get("data", {}))

        direct_payload = _collect_akshare_direct_payload(symbol, updated_at, all_existing_data)
        if direct_payload:
            payloads.append(direct_payload)
            logger.info(f"{symbol} akshare_direct 兜底数据已添加，字段: {list(direct_payload.get('data', {}).keys())}")

    return payloads


def _extract_from_text(text: str, aliases: Iterable[str]) -> Optional[Any]:
    for line in text.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if not any(alias.lower() in normalized.lower() for alias in aliases):
            continue
        for sep in (":", "："):
            if sep in normalized:
                return normalized.split(sep, 1)[1].strip()
        return normalized
    return None


def _extract_field(data: Any, aliases: List[str]) -> Optional[Any]:
    if isinstance(data, Mapping):
        flattened = _flatten_mapping(data)
        lowered = {str(key).lower(): value for key, value in flattened.items()}
        for alias in aliases:
            if alias in flattened:
                return flattened[alias]
            value = lowered.get(alias.lower())
            if value is not None:
                return value
        # Fallback for line-item style payloads:
        # [{"item": "营业总收入", "value": ...}] or {"name":"负债合计","amount":...}
        alias_set = {str(alias).strip().lower() for alias in aliases if str(alias).strip()}
        for key, value in flattened.items():
            key_text = str(key).strip().lower()
            alias_hit = key_text in alias_set
            if not alias_hit:
                # Avoid short-alias false positives like alias "pe" matching "report_period".
                for alias in alias_set:
                    if len(alias) < 3:
                        continue
                    if alias in key_text:
                        alias_hit = True
                        break
            if alias_hit:
                if value not in (None, "", "N/A"):
                    return value
            if isinstance(value, str):
                value_text = value.strip().lower()
                if value_text in alias_set:
                    # Find sibling numeric-like value in the original mapping.
                    if isinstance(data, Mapping):
                        for candidate_key in ("value", "amount", "val", "数值", "金额", "本期", "最新值"):
                            candidate_val = data.get(candidate_key)
                            if candidate_val not in (None, "", "N/A"):
                                return candidate_val
            if isinstance(value, Mapping):
                nested = _extract_field(value, aliases)
                if nested is not None:
                    return nested
            if isinstance(value, list):
                for item in value:
                    nested = _extract_field(item, aliases)
                    if nested is not None:
                        return nested
    elif isinstance(data, str):
        return _extract_from_text(data, aliases)
    return None


def _status_rank(status: str) -> int:
    if status == "present":
        return 2
    if status == "conflict":
        return 1
    if status == "estimated":
        return 1
    return 0


def _parse_report_period(value: Any) -> tuple[int, int, int]:
    if not value:
        return (0, 0, 0)
    text = str(value).strip()
    match = re.match(r"(\d{4})Q([1-4])$", text, flags=re.IGNORECASE)
    if match:
        return (3, int(match.group(1)), int(match.group(2)))
    match = re.match(r"(\d{4})[-/](\d{2})[-/](\d{2})$", text)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return (2, year * 10000 + month * 100 + day, 0)
    match = re.match(r"recent_(\d+)d$", text, flags=re.IGNORECASE)
    if match:
        days = int(match.group(1))
        return (1, max(0, 10000 - days), 0)
    return (0, 0, 0)


def _parse_updated_at(value: Any) -> tuple[int, int]:
    if not value:
        return (0, 0)
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return (1, int(parsed.timestamp()))
        except ValueError:
            continue
    return (0, 0)


def _candidate_rank(candidate: Mapping[str, Any]) -> tuple[int, tuple[int, int, int], tuple[int, int], int]:
    return (
        _status_rank(str(candidate.get("status", ""))),
        _parse_report_period(candidate.get("report_period")),
        _parse_updated_at(candidate.get("updated_at")),
        FREE_SOURCE_PRIORITY.get(_normalize_source(str(candidate.get("source", "unknown"))), 10),
    )


def _selection_reason(best: Mapping[str, Any], candidates: List[Mapping[str, Any]]) -> str:
    if not candidates:
        return "default_only_candidate"

    best_status = _status_rank(str(best.get("status", "")))
    best_period = _parse_report_period(best.get("report_period"))
    best_updated_at = _parse_updated_at(best.get("updated_at"))
    best_priority = FREE_SOURCE_PRIORITY.get(_normalize_source(str(best.get("source", "unknown"))), 10)

    reasons: List[str] = []
    if any(_status_rank(str(candidate.get("status", ""))) < best_status for candidate in candidates):
        reasons.append("better_status")
    if any(_parse_report_period(candidate.get("report_period")) < best_period for candidate in candidates):
        reasons.append("newer_report_period")
    if any(_parse_updated_at(candidate.get("updated_at")) < best_updated_at for candidate in candidates):
        reasons.append("newer_updated_at")
    if any(
        FREE_SOURCE_PRIORITY.get(_normalize_source(str(candidate.get("source", "unknown"))), 10) < best_priority
        for candidate in candidates
    ):
        reasons.append("higher_source_priority")
    return ",".join(reasons) if reasons else "tie_break_selected"


def _numeric_field_value(fields: Mapping[str, Mapping[str, Any]], field_name: str) -> Optional[float]:
    field = fields.get(field_name, {})
    if field.get("status") != "present":
        return None
    value = field.get("value")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").replace("%", "").strip())
        except ValueError:
            return None
    return None


def _derived_field_template(fields: Mapping[str, Mapping[str, Any]], dependencies: List[str]) -> Dict[str, Any]:
    present_dependencies = [fields[name] for name in dependencies if fields.get(name, {}).get("status") == "present"]
    source = next((field.get("source") for field in present_dependencies if field.get("source")), "derived")
    report_period = next((field.get("report_period") for field in present_dependencies if field.get("report_period")), None)
    updated_at = next((field.get("updated_at") for field in present_dependencies if field.get("updated_at")), None)
    return {
        "source": source,
        "report_period": report_period,
        "updated_at": updated_at,
        "selection_reason": f"derived_from:{','.join(dependencies)}",
    }


def _set_derived_field(fields: Dict[str, Dict[str, Any]], field_name: str, value: Any, dependencies: List[str]) -> None:
    if field_name not in fields or fields[field_name].get("status") == "present":
        return
    metadata = _derived_field_template(fields, dependencies)
    fields[field_name].update(
        {
            "value": round(value, 4) if isinstance(value, float) else value,
            "status": "present",
            "source": f"{metadata['source']}:derived",
            "report_period": metadata["report_period"],
            "updated_at": metadata["updated_at"],
            "selection_reason": metadata["selection_reason"],
        }
    )


def _trend_direction(current: Optional[float], previous: Optional[float]) -> Optional[str]:
    if current is None or previous is None:
        return None
    if current > previous:
        return "improving"
    if current < previous:
        return "weakening"
    return "stable"


def _inverse_trend_direction(current: Optional[float], previous: Optional[float]) -> Optional[str]:
    if current is None or previous is None:
        return None
    if current < previous:
        return "improving"
    if current > previous:
        return "weakening"
    return "stable"


def _period_numeric_value(period: Mapping[str, Any], aliases: Iterable[str]) -> Optional[float]:
    flattened = _flatten_mapping(period)
    lowered = {str(key).lower(): value for key, value in flattened.items()}
    for alias in aliases:
        if alias in flattened:
            value = flattened[alias]
        else:
            value = lowered.get(alias.lower())
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(",", "").replace("%", "").strip())
            except ValueError:
                continue
    return None


def _extract_periods(payload_data: Any) -> List[Mapping[str, Any]]:
    if not isinstance(payload_data, Mapping):
        return []
    periods = payload_data.get("periods")
    if isinstance(periods, list) and periods:
        return [item for item in periods if isinstance(item, Mapping)]

    merged_period: Dict[str, Any] = {}
    for key in ("income_statement", "balance_sheet", "cash_flow", "main_indicators"):
        value = payload_data.get(key)
        if isinstance(value, list) and value and isinstance(value[0], Mapping):
            merged_period.update(value[0])
    return [merged_period] if merged_period else []


def _apply_trend_fields(fields: Dict[str, Dict[str, Any]], source_payloads: List[Mapping[str, Any]]) -> None:
    for payload in source_payloads:
        periods = _extract_periods(payload.get("data"))
        if len(periods) < 2:
            continue

        current_period = periods[0]
        previous_period = periods[1]
        metadata = {
            "source": _normalize_source(str(payload.get("source", "unknown"))),
            "report_period": payload.get("report_period"),
            "updated_at": payload.get("updated_at"),
        }
        def _safe_trend(cur, prev, inverse=False):
            if cur is None or prev is None or cur == 0 or prev == 0:
                return None
            return _inverse_trend_direction(cur, prev) if inverse else _trend_direction(cur, prev)

        trend_specs: Dict[str, Any] = {
            "roe_trend": _safe_trend(_period_numeric_value(current_period, FIELD_SPECS["roe"]["aliases"]), _period_numeric_value(previous_period, FIELD_SPECS["roe"]["aliases"])),
            "gross_margin_trend": _safe_trend(_period_numeric_value(current_period, FIELD_SPECS["gross_margin"]["aliases"]), _period_numeric_value(previous_period, FIELD_SPECS["gross_margin"]["aliases"])),
            "free_cash_flow_trend": _safe_trend(_period_numeric_value(current_period, FIELD_SPECS["free_cash_flow"]["aliases"]), _period_numeric_value(previous_period, FIELD_SPECS["free_cash_flow"]["aliases"])),
            "deducted_net_profit_trend": _safe_trend(_period_numeric_value(current_period, FIELD_SPECS["deducted_net_profit"]["aliases"]), _period_numeric_value(previous_period, FIELD_SPECS["deducted_net_profit"]["aliases"])),
            "debt_ratio_trend": _safe_trend(_period_numeric_value(current_period, FIELD_SPECS["debt_ratio"]["aliases"]), _period_numeric_value(previous_period, FIELD_SPECS["debt_ratio"]["aliases"]), inverse=True),
            "current_ratio_trend": _safe_trend(_period_numeric_value(current_period, FIELD_SPECS["current_ratio"]["aliases"]), _period_numeric_value(previous_period, FIELD_SPECS["current_ratio"]["aliases"])),
        }

        current_revenue = _period_numeric_value(current_period, FIELD_SPECS["revenue"]["aliases"])
        previous_revenue = _period_numeric_value(previous_period, FIELD_SPECS["revenue"]["aliases"])
        current_profit = _period_numeric_value(current_period, FIELD_SPECS["net_profit"]["aliases"])
        current_ocf = _period_numeric_value(current_period, FIELD_SPECS["operating_cash_flow"]["aliases"])
        current_receivables = _period_numeric_value(current_period, FIELD_SPECS["accounts_receivable"]["aliases"])
        previous_receivables = _period_numeric_value(previous_period, FIELD_SPECS["accounts_receivable"]["aliases"])
        current_contract_liabilities = _period_numeric_value(current_period, FIELD_SPECS["contract_liabilities"]["aliases"])
        previous_contract_liabilities = _period_numeric_value(previous_period, FIELD_SPECS["contract_liabilities"]["aliases"])
        current_contract_assets = _period_numeric_value(current_period, FIELD_SPECS["contract_assets"]["aliases"])
        previous_contract_assets = _period_numeric_value(previous_period, FIELD_SPECS["contract_assets"]["aliases"])
        current_accounts_payable = _period_numeric_value(current_period, FIELD_SPECS["accounts_payable"]["aliases"])
        previous_accounts_payable = _period_numeric_value(previous_period, FIELD_SPECS["accounts_payable"]["aliases"])
        current_inventory = _period_numeric_value(current_period, FIELD_SPECS["inventory"]["aliases"])
        previous_inventory = _period_numeric_value(previous_period, FIELD_SPECS["inventory"]["aliases"])

        if current_ocf is not None and current_profit is not None and current_profit != 0:
            trend_specs["cashflow_to_profit_ratio"] = round(current_ocf / current_profit, 4)
        if current_revenue is not None and current_revenue != 0 and previous_revenue is not None and previous_revenue != 0:
            if current_receivables is not None and previous_receivables is not None:
                current_ratio = current_receivables / current_revenue
                previous_ratio = previous_receivables / previous_revenue
                trend_specs["receivables_to_revenue_change"] = round((current_ratio - previous_ratio) * 100, 4)
            if current_inventory is not None and previous_inventory is not None:
                current_ratio = current_inventory / current_revenue
                previous_ratio = previous_inventory / previous_revenue
                trend_specs["inventory_to_revenue_change"] = round((current_ratio - previous_ratio) * 100, 4)
            if current_contract_liabilities is not None and previous_contract_liabilities is not None:
                current_ratio = current_contract_liabilities / current_revenue
                previous_ratio = previous_contract_liabilities / previous_revenue
                trend_specs["contract_liabilities_to_revenue_change"] = round((current_ratio - previous_ratio) * 100, 4)
            if current_contract_assets is not None and previous_contract_assets is not None:
                current_ratio = current_contract_assets / current_revenue
                previous_ratio = previous_contract_assets / previous_revenue
                trend_specs["contract_assets_to_revenue_change"] = round((current_ratio - previous_ratio) * 100, 4)
            if current_accounts_payable is not None and previous_accounts_payable is not None:
                current_ratio = current_accounts_payable / current_revenue
                previous_ratio = previous_accounts_payable / previous_revenue
                trend_specs["accounts_payable_to_revenue_change"] = round((current_ratio - previous_ratio) * 100, 4)

        for field_name, value in trend_specs.items():
            if value is None or field_name not in fields or fields[field_name].get("status") == "present":
                continue
            fields[field_name].update(
                {
                    "value": value,
                    "status": "present",
                    "source": f"{metadata['source']}:derived",
                    "report_period": metadata["report_period"],
                    "updated_at": metadata["updated_at"],
                    "selection_reason": f"derived_from_periods:{payload.get('source', 'unknown')}",
                }
            )
        break


def _apply_derived_fields(fields: Dict[str, Dict[str, Any]]) -> None:
    operating_cash_flow = _numeric_field_value(fields, "operating_cash_flow")
    capital_expenditure = _numeric_field_value(fields, "capital_expenditure")
    if operating_cash_flow is not None and capital_expenditure is not None:
        _set_derived_field(fields, "free_cash_flow", operating_cash_flow - abs(capital_expenditure), ["operating_cash_flow", "capital_expenditure"])

    total_assets = _numeric_field_value(fields, "total_assets")
    total_liabilities = _numeric_field_value(fields, "total_liabilities")
    debt_ratio = _numeric_field_value(fields, "debt_ratio")
    if total_liabilities is None and total_assets is not None and total_assets > 0 and debt_ratio is not None:
        ratio = debt_ratio / 100.0 if abs(debt_ratio) > 1 else debt_ratio
        if 0 <= ratio <= 1.5:
            _set_derived_field(fields, "total_liabilities", total_assets * ratio, ["total_assets", "debt_ratio"])
            total_liabilities = _numeric_field_value(fields, "total_liabilities")
    if total_assets is not None and total_assets != 0:
        if total_liabilities is not None:
            _set_derived_field(fields, "debt_ratio", total_liabilities / total_assets * 100, ["total_liabilities", "total_assets"])
        net_profit = _numeric_field_value(fields, "net_profit")
        if net_profit is not None:
            _set_derived_field(fields, "roa", net_profit / total_assets * 100, ["net_profit", "total_assets"])

    current_assets = _numeric_field_value(fields, "current_assets")
    current_liabilities = _numeric_field_value(fields, "current_liabilities")
    if current_assets is not None and current_liabilities is not None and current_liabilities != 0:
        _set_derived_field(fields, "current_ratio", current_assets / current_liabilities, ["current_assets", "current_liabilities"])

    revenue = _numeric_field_value(fields, "revenue")
    net_profit = _numeric_field_value(fields, "net_profit")
    if revenue is not None and revenue != 0 and net_profit is not None:
        _set_derived_field(fields, "net_margin", net_profit / revenue * 100, ["net_profit", "revenue"])

    price = _numeric_field_value(fields, "price")
    book_value_per_share = _numeric_field_value(fields, "book_value_per_share")
    if price is not None and book_value_per_share is not None and book_value_per_share != 0:
        _set_derived_field(fields, "pb", price / book_value_per_share, ["price", "book_value_per_share"])

    eps = _numeric_field_value(fields, "eps")
    if price is not None and eps is not None and eps > 0:
        _set_derived_field(fields, "pe_ttm", price / eps, ["price", "eps"])


def validate_data_consistency(snapshot_data: dict) -> list:
    inconsistencies = []
    fields = snapshot_data.get("fields", {})

    def _num(name: str) -> Optional[float]:
        return _numeric_field_value(fields, name)

    def _val(name: str) -> Any:
        f = fields.get(name, {})
        return f.get("value") if f.get("status") in ("present", "conflict") else None

    def _status(name: str) -> str:
        return fields.get(name, {}).get("status", "missing")

    eps = _num("eps")
    pe = _num("pe")
    pe_ttm = _num("pe_ttm")
    if eps is not None and eps < 0:
        for pe_name, pe_val in [("pe", pe), ("pe_ttm", pe_ttm)]:
            if pe_val is not None and pe_val > 0:
                inconsistencies.append({
                    "rule": "PE_vs_EPS_sign",
                    "fields": [pe_name, "eps"],
                    "description": f"EPS为负({eps:.4g})但{FIELD_SPECS[pe_name]['label']}为正({pe_val:.4g})，负EPS不可能有正PE",
                    "conflict_values": {pe_name: pe_val, "eps": eps},
                    "suggested_fix": {pe_name: "N/A"},
                })

    if eps is not None and eps > 0:
        for pe_name, pe_val in [("pe", pe), ("pe_ttm", pe_ttm)]:
            if pe_val is not None and pe_val < 0:
                inconsistencies.append({
                    "rule": "PE_vs_EPS_sign",
                    "fields": [pe_name, "eps"],
                    "description": f"EPS为正({eps:.4g})但{FIELD_SPECS[pe_name]['label']}为负({pe_val:.4g})，正EPS不应有负PE",
                    "conflict_values": {pe_name: pe_val, "eps": eps},
                    "suggested_fix": {pe_name: "N/A"},
                })

    pb = _num("pb")
    book_value_per_share = _num("book_value_per_share")
    price = _num("price")
    if pb is not None and book_value_per_share is not None and price is not None and book_value_per_share != 0:
        expected_pb = price / book_value_per_share
        if abs(expected_pb) > 0.01:
            deviation = abs(pb - expected_pb) / abs(expected_pb)
            if deviation > 0.5:
                inconsistencies.append({
                    "rule": "PB_vs_price_and_bvps",
                    "fields": ["pb", "price", "book_value_per_share"],
                    "description": f"PB({pb:.4g})与 price/bvps 计算值({expected_pb:.4g})偏差{deviation:.0%}，可能数据错误",
                    "conflict_values": {"pb": pb, "price": price, "book_value_per_share": book_value_per_share, "expected_pb": round(expected_pb, 4)},
                    "suggested_fix": {"pb": round(expected_pb, 4)},
                })

    if pb is not None and pb > 100:
        if book_value_per_share is not None and book_value_per_share != 0 and price is not None:
            expected_pb = price / book_value_per_share
            if expected_pb < 50:
                inconsistencies.append({
                    "rule": "PB_abnormally_high",
                    "fields": ["pb", "price", "book_value_per_share"],
                    "description": f"PB异常高({pb:.4g})，但 price/bvps 计算值为{expected_pb:.4g}，可能计算错误",
                    "conflict_values": {"pb": pb, "expected_pb": round(expected_pb, 4)},
                    "suggested_fix": {"pb": round(expected_pb, 4)},
                })
        elif book_value_per_share is not None and abs(book_value_per_share) < 0.01:
            inconsistencies.append({
                "rule": "PB_abnormally_high_near_zero_bvps",
                "fields": ["pb", "book_value_per_share"],
                "description": f"PB异常高({pb:.4g})，每股净资产接近零({book_value_per_share:.4g})，PB无实际参考意义",
                "conflict_values": {"pb": pb, "book_value_per_share": book_value_per_share},
                "suggested_fix": {"pb": "N/A"},
            })
        else:
            inconsistencies.append({
                "rule": "PB_abnormally_high",
                "fields": ["pb"],
                "description": f"PB异常高({pb:.4g})，超过A股合理上限100，可能数据错误",
                "conflict_values": {"pb": pb},
                "suggested_fix": {"pb": "N/A"},
            })

    roe = _num("roe")
    net_margin = _num("net_margin")
    debt_ratio = _num("debt_ratio")
    if roe is not None and net_margin is not None:
        if roe < 0 and net_margin > 0:
            inconsistencies.append({
                "rule": "ROE_vs_net_margin_sign",
                "fields": ["roe", "net_margin"],
                "description": f"ROE为负({roe:.4g}%)但净利率为正({net_margin:.4g}%)，可能存在巨额净资产负值或数据矛盾",
                "conflict_values": {"roe": roe, "net_margin": net_margin},
                "suggested_fix": {"roe": "需验证"},
            })
        elif roe > 0 and net_margin < 0:
            inconsistencies.append({
                "rule": "ROE_vs_net_margin_sign",
                "fields": ["roe", "net_margin"],
                "description": f"ROE为正({roe:.4g}%)但净利率为负({net_margin:.4g}%)，可能存在负净资产导致ROE失真或数据矛盾",
                "conflict_values": {"roe": roe, "net_margin": net_margin},
                "suggested_fix": {"roe": "需验证"},
            })

    if roe is not None and debt_ratio is not None and net_margin is not None:
        if net_margin > 0 and debt_ratio > 80 and roe < 0:
            inconsistencies.append({
                "rule": "ROE_vs_margin_and_leverage",
                "fields": ["roe", "net_margin", "debt_ratio"],
                "description": f"净利率为正({net_margin:.4g}%)且资产负债率{debt_ratio:.4g}%但ROE为负({roe:.4g}%)，可能净资产为负导致ROE失真",
                "conflict_values": {"roe": roe, "net_margin": net_margin, "debt_ratio": debt_ratio},
                "suggested_fix": {"roe": "需验证，可能因负净资产失真"},
            })

    operating_cash_flow = _num("operating_cash_flow")
    free_cash_flow = _num("free_cash_flow")
    net_profit_val = _num("net_profit")
    if operating_cash_flow is not None and net_profit_val is not None:
        if operating_cash_flow < 0 and net_profit_val > 0:
            inconsistencies.append({
                "rule": "cashflow_vs_profit_sign",
                "fields": ["operating_cash_flow", "net_profit"],
                "description": f"经营现金流为负({operating_cash_flow:.4g})但净利润为正({net_profit_val:.4g})，盈利质量存疑",
                "conflict_values": {"operating_cash_flow": operating_cash_flow, "net_profit": net_profit_val},
                "suggested_fix": {},
            })
        if operating_cash_flow > 0 and net_profit_val < 0:
            inconsistencies.append({
                "rule": "cashflow_vs_profit_sign",
                "fields": ["operating_cash_flow", "net_profit"],
                "description": f"经营现金流为正({operating_cash_flow:.4g})但净利润为负({net_profit_val:.4g})，可能存在非现金损失",
                "conflict_values": {"operating_cash_flow": operating_cash_flow, "net_profit": net_profit_val},
                "suggested_fix": {},
            })

    if free_cash_flow is not None and operating_cash_flow is not None:
        if free_cash_flow > 0 and operating_cash_flow < 0:
            inconsistencies.append({
                "rule": "fcf_vs_ocf_sign",
                "fields": ["free_cash_flow", "operating_cash_flow"],
                "description": f"自由现金流为正({free_cash_flow:.4g})但经营现金流为负({operating_cash_flow:.4g})，数据矛盾",
                "conflict_values": {"free_cash_flow": free_cash_flow, "operating_cash_flow": operating_cash_flow},
                "suggested_fix": {"free_cash_flow": "需验证"},
            })

    net_profit_raw = _val("net_profit")
    if net_profit_raw is not None and eps is not None:
        try:
            np_val = float(net_profit_raw) if not isinstance(net_profit_raw, (int, float)) else net_profit_raw
            if np_val > 0 and eps < 0:
                inconsistencies.append({
                    "rule": "EPS_vs_net_profit_sign",
                    "fields": ["eps", "net_profit"],
                    "description": f"净利润为正({np_val:.4g})但EPS为负({eps:.4g})，数据矛盾",
                    "conflict_values": {"eps": eps, "net_profit": np_val},
                    "suggested_fix": {"eps": "需验证"},
                })
            elif np_val < 0 and eps > 0:
                inconsistencies.append({
                    "rule": "EPS_vs_net_profit_sign",
                    "fields": ["eps", "net_profit"],
                    "description": f"净利润为负({np_val:.4g})但EPS为正({eps:.4g})，数据矛盾",
                    "conflict_values": {"eps": eps, "net_profit": np_val},
                    "suggested_fix": {"eps": "需验证"},
                })
        except (ValueError, TypeError):
            pass

    total_assets = _num("total_assets")
    total_liabilities = _num("total_liabilities")
    if total_assets is not None and total_liabilities is not None:
        if total_liabilities > total_assets:
            if book_value_per_share is not None and book_value_per_share > 0:
                inconsistencies.append({
                    "rule": "liabilities_exceed_assets_but_positive_bvps",
                    "fields": ["total_assets", "total_liabilities", "book_value_per_share"],
                    "description": f"总负债({total_liabilities:.4g})超过总资产({total_assets:.4g})，但每股净资产为正({book_value_per_share:.4g})，数据矛盾",
                    "conflict_values": {"total_assets": total_assets, "total_liabilities": total_liabilities, "book_value_per_share": book_value_per_share},
                    "suggested_fix": {"book_value_per_share": "需验证"},
                })

    _STALE_THRESHOLD_DAYS = 90
    stale_fields = []
    current_timestamp = int(datetime.now().timestamp())
    for field_name, field_data in fields.items():
        updated_at = field_data.get("updated_at")
        if not updated_at:
            continue
        parsed = _parse_updated_at(updated_at)
        if parsed[0] == 1:
            days_old = (current_timestamp - parsed[1]) / 86400
            if days_old > _STALE_THRESHOLD_DAYS:
                stale_fields.append((field_name, int(days_old)))

    if stale_fields:
        stale_descriptions = [f"{fields[fn].get('label', fn)}: {d}天前" for fn, d in stale_fields]
        inconsistencies.append({
            "rule": "stale_data_detected",
            "fields": [fn for fn, _ in stale_fields],
            "description": f"以下字段数据可能已过期: {', '.join(stale_descriptions)}，建议更新数据",
            "conflict_values": {fn: f"{d}天前" for fn, d in stale_fields},
            "suggested_fix": {},
        })

    return inconsistencies


def apply_consistency_fixes(snapshot_data: dict) -> dict:
    inconsistencies = validate_data_consistency(snapshot_data)
    if not inconsistencies:
        return snapshot_data

    fields = snapshot_data.get("fields", {})
    fixed_snapshot = dict(snapshot_data)
    fixed_fields = {k: dict(v) for k, v in fields.items()}
    fixed_snapshot["fields"] = fixed_fields

    for issue in inconsistencies:
        suggested_fix = issue.get("suggested_fix", {})
        for field_name, fix_value in suggested_fix.items():
            if field_name not in fixed_fields:
                continue
            field = fixed_fields[field_name]
            if fix_value == "N/A":
                field["value"] = None
                field["status"] = "corrected_to_na"
                field["correction_reason"] = issue["description"]
            elif fix_value == "需验证" or (isinstance(fix_value, str) and "需验证" in fix_value):
                field["status"] = "needs_verification"
                field["verification_reason"] = issue["description"]
            elif isinstance(fix_value, (int, float)):
                field["value"] = fix_value
                field["status"] = "corrected"
                field["original_value"] = field.get("value")
                field["correction_reason"] = issue["description"]

    fixed_snapshot["consistency_issues"] = inconsistencies
    return fixed_snapshot


def build_china_fundamental_snapshot(symbol: str, source_payloads: List[Mapping[str, Any]]) -> Dict[str, Any]:
    candidate_payloads = _expand_financial_statement_payloads(source_payloads)
    fields: Dict[str, Dict[str, Any]] = {}
    all_candidates: Dict[str, List[Dict[str, Any]]] = {}
    for field_name, spec in FIELD_SPECS.items():
        best: Optional[Dict[str, Any]] = None
        candidates: List[Dict[str, Any]] = []
        for payload in candidate_payloads:
            source = _normalize_source(str(payload.get("source", "unknown")))
            raw_value = _extract_field(payload.get("data", {}), spec["aliases"])
            status = _value_status(raw_value)
            candidate = {
                "name": field_name,
                "label": spec["label"],
                "value": _coerce_number(raw_value) if status == "present" else raw_value,
                "status": status,
                "source": source,
                "updated_at": payload.get("updated_at"),
                "report_period": payload.get("report_period"),
                "required": bool(spec.get("required")),
            }
            candidates.append(candidate)
            if best is None or _candidate_rank(candidate) > _candidate_rank(best):
                best = candidate
        if best is not None:
            best = dict(best)
            best["selection_reason"] = _selection_reason(best, [candidate for candidate in candidates if candidate != best])
        fields[field_name] = best or {
            "name": field_name,
            "label": spec["label"],
            "value": None,
            "status": "missing",
            "source": "none",
            "updated_at": None,
            "report_period": None,
            "selection_reason": "no_candidate",
            "required": bool(spec.get("required")),
        }
        all_candidates[field_name] = candidates

    _apply_derived_fields(fields)
    _apply_trend_fields(fields, source_payloads)

    conflict_fields: List[str] = []
    for field_name, candidates in all_candidates.items():
        present_candidates = [c for c in candidates if c["status"] == "present"]
        if len(present_candidates) < 2:
            continue
        source_values: Dict[str, Any] = {}
        for c in present_candidates:
            if c["source"] not in source_values:
                source_values[c["source"]] = c["value"]
        if len(source_values) < 2:
            continue
        has_conflict = False
        sources = list(source_values.keys())
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                if _values_conflict(source_values[sources[i]], source_values[sources[j]]):
                    has_conflict = True
                    break
            if has_conflict:
                break
        if has_conflict:
            conflict_fields.append(field_name)
            fields[field_name]["status"] = "conflict"
            fields[field_name]["conflict_values"] = source_values

    required_fields = [name for name, spec in FIELD_SPECS.items() if spec.get("required")]
    present_required = [name for name in required_fields if fields[name]["status"] == "present"]
    missing_required = [name for name in required_fields if fields[name]["status"] == "missing"]
    estimated_fields = [name for name, field in fields.items() if field["status"] == "estimated"]
    conflict_required = [name for name in conflict_fields if name in required_fields]
    present_count = sum(1 for field in fields.values() if field["status"] == "present")

    required_coverage = len(present_required) / len(required_fields) if required_fields else 1.0
    overall_coverage = present_count / len(fields) if fields else 0.0

    if required_coverage >= 0.9:
        quality_grade = "A"
    elif required_coverage >= 0.75:
        quality_grade = "B"
    elif required_coverage >= 0.6:
        quality_grade = "C"
    elif required_coverage >= 0.4:
        quality_grade = "D"
    else:
        quality_grade = "F"

    source_field_map: Dict[str, List[str]] = {}
    for fname, finfo in fields.items():
        if finfo["status"] in ("present", "conflict"):
            src = finfo.get("source", "unknown")
            source_field_map.setdefault(src, []).append(fname)

    quality = {
        "score": round(overall_coverage, 4),
        "required_score": round(required_coverage, 4),
        "quality_grade": quality_grade,
        "present_count": present_count,
        "total_count": len(fields),
        "present_required_count": len(present_required),
        "required_count": len(required_fields),
        "missing_required_fields": missing_required,
        "estimated_fields": estimated_fields,
        "conflict_fields": conflict_fields,
        "is_sufficient": required_coverage >= 0.75 and len(conflict_required) == 0,
        "source_field_map": source_field_map,
    }

    sources_used = sorted({field["source"] for field in fields.values() if field["status"] in ("present", "conflict")})
    return {
        "symbol": symbol,
        "market": "china_a",
        "fields": fields,
        "quality": quality,
        "sources_used": sources_used,
    }


def _format_field_value(field_name: str, value: Any) -> str:
    if value is None:
        return ""
    if field_name not in PERCENT_FIELDS or not isinstance(value, (int, float)):
        return str(value)
    # 数据源返回的百分比字段已经是百分比形式（如 15.5 表示 15.5%），直接添加 % 后缀
    return f"{value:g}%"


def format_china_fundamental_snapshot_report(snapshot: Mapping[str, Any]) -> str:
    quality = snapshot.get("quality", {})
    fields = snapshot.get("fields", {})
    lines = [
        "## A股免费数据融合质量报告",
        f"股票代码: {snapshot.get('symbol', '')}",
        f"数据质量等级: {quality.get('quality_grade', 'F')} (必需字段覆盖率: {quality.get('required_score', 0):.1%})",
        f"数据质量评分: {quality.get('present_count', 0)}/{quality.get('total_count', 0)} (必需字段 {quality.get('present_required_count', 0)}/{quality.get('required_count', 0)})",
        f"是否足够支撑分析: {'是' if quality.get('is_sufficient') else '否'}",
        f"免费数据源: {', '.join(snapshot.get('sources_used', [])) or '无'}",
    ]

    source_field_map = quality.get("source_field_map", {})
    if source_field_map:
        lines.append("")
        lines.append("### 数据源覆盖详情")
        for src, field_names in sorted(source_field_map.items()):
            lines.append(f"  - {src}: {len(field_names)} 个字段 ({', '.join(field_names[:5])}{'...' if len(field_names) > 5 else ''})")

    conflict_fields_list = quality.get("conflict_fields", [])
    if conflict_fields_list:
        lines.extend(["", "⚠️ 数据矛盾警告: 以下字段在不同数据源间存在显著差异"])
        for fname in conflict_fields_list:
            field = fields.get(fname, {})
            conflict_values = field.get("conflict_values", {})
            parts = [f"{src}={_format_field_value(fname, val)}" for src, val in conflict_values.items()]
            lines.append(f"  - {field.get('label', fname)}: {' vs '.join(parts)}")

    missing_required = quality.get("missing_required_fields", [])
    if missing_required:
        missing_labels = [fields.get(name, {}).get("label", name) for name in missing_required]
        lines.extend(["", f"⚠️ 必需字段缺失: {', '.join(missing_labels)} — 建议使用付费数据源获取完整数据"])

    lines.extend([
        "",
        "| 字段 | 规范别名 | 值 | 状态 | 数据来源 | 报告期 | 更新时间 | 选中原因 |",
        "|------|----------|----|------|----------|--------|----------|----------|",
    ])

    for field_name, field in fields.items():
        lines.append(
            f"| {field.get('label', field_name)} | {field_name} | {_format_field_value(field_name, field.get('value'))} | "
            f"{field.get('status')} | {field.get('source')} | {field.get('report_period') or ''} | {field.get('updated_at') or ''} | {field.get('selection_reason') or ''} |"
        )

    lines.extend(["", "### 大师分析可读字段"])
    for field_name, field in fields.items():
        metadata = (
            f"source: {field.get('source')}; report_period: {field.get('report_period') or ''}; "
            f"updated_at: {field.get('updated_at') or ''}; selection_reason: {field.get('selection_reason') or ''}"
        )
        if field.get("status") == "conflict":
            conflict_values = field.get("conflict_values", {})
            parts = [f"{src}={_format_field_value(field_name, val)}" for src, val in conflict_values.items()]
            lines.append(f"{field_name}: ⚠️矛盾({', '.join(parts)})  # 数据来源: conflict")
        elif field.get("status") == "corrected_to_na":
            lines.append(f"{field_name}: N/A(已修正)  # 修正原因: {field.get('correction_reason', '')}")
        elif field.get("status") == "needs_verification":
            lines.append(f"{field_name}: {_format_field_value(field_name, field.get('value'))}⚠️待验证  # 验证原因: {field.get('verification_reason', '')}")
        elif field.get("status") == "corrected":
            lines.append(f"{field_name}: {_format_field_value(field_name, field.get('value'))}(已修正)  # 修正原因: {field.get('correction_reason', '')}")
        elif field.get("status") == "present":
            lines.append(f"{field_name}: {_format_field_value(field_name, field.get('value'))}  # 数据来源: {field.get('source')} | {metadata}")
        elif field.get("status") == "estimated":
            lines.append(f"{field_name}: 行业估算  # 数据来源: {field.get('source')} | {metadata}")
        else:
            lines.append(f"{field_name}: N/A  # {metadata}")

    if missing_required:
        lines.extend(["", f"缺失必需字段: {', '.join(missing_required)}"])
    if quality.get("estimated_fields"):
        lines.append(f"估算字段: {', '.join(quality['estimated_fields'])}")
    if conflict_fields_list:
        lines.append(f"矛盾字段: {', '.join(conflict_fields_list)}")

    consistency_issues = snapshot.get("consistency_issues", [])
    if not consistency_issues:
        consistency_issues = validate_data_consistency(dict(snapshot))

    if consistency_issues:
        lines.extend(["", "### ⚠️ 数据一致性验证"])
        lines.append(f"发现 {len(consistency_issues)} 项数据一致性问题：")
        for i, issue in enumerate(consistency_issues, 1):
            conflict_parts = [f"{k}={v}" for k, v in issue.get("conflict_values", {}).items()]
            fix_parts = [f"{k}→{v}" for k, v in issue.get("suggested_fix", {}).items()]
            lines.append(f"  {i}. [{issue['rule']}] {issue['description']}")
            if conflict_parts:
                lines.append(f"     冲突值: {', '.join(conflict_parts)}")
            if fix_parts:
                lines.append(f"     建议修正: {', '.join(fix_parts)}")
    else:
        lines.extend(["", "### ✅ 数据一致性验证", "所有关键字段数据一致性检查通过，未发现矛盾。"])

    return "\n".join(lines)


_QUANT_NAME_MAP: Dict[str, List[str]] = {
    "roe": ["ROE"],
    "roa": ["roa"],
    "roic": ["roic"],
    "net_margin": ["net_margin"],
    "gross_margin": ["gross_margin"],
    "debt_ratio": ["debt_ratio"],
    "pe_ttm": ["pe_ttm", "pe_ratio"],
    "pb": ["pb"],
    "free_cash_flow": ["free_cash_flow"],
    "operating_cash_flow": ["operating_cash_flow"],
    "revenue_yoy": ["revenue_growth"],
    "net_profit_yoy": ["eps_growth"],
    "dividend_yield": ["dividend_yield"],
    "current_ratio": ["current_ratio"],
    "net_profit": ["net_income", "net_profit"],
    "revenue": ["revenue"],
    "total_assets": ["total_assets"],
    "total_liabilities": ["total_liabilities"],
    "current_assets": ["current_assets"],
    "current_liabilities": ["current_liabilities"],
    "capital_expenditure": ["capital_expenditure"],
    "book_value_per_share": ["book_value_per_share"],
    "eps": ["eps", "EPS"],
    "accounts_receivable": ["accounts_receivable"],
    "inventory": ["inventory"],
    "goodwill": ["goodwill"],
    "total_mv": ["market_cap"],
    "pledge_ratio": ["pledge_ratio"],
    "cashflow_to_profit_ratio": ["cashflow_to_profit_ratio"],
    "insider_increase_events": ["insider_increase_events"],
    "insider_decrease_events": ["insider_decrease_events"],
    "regulatory_penalty_severity": ["regulatory_penalty_severity"],
    "goodwill_impairment_amount_max": ["goodwill_impairment_amount_max"],
    "earnings_guidance_change_pct_min": ["earnings_guidance_change_pct_min"],
    "earnings_guidance_change_pct_max": ["earnings_guidance_change_pct_max"],
    "earnings_guidance_revenue_change_pct_min": ["earnings_guidance_revenue_change_pct_min"],
    "earnings_guidance_revenue_change_pct_max": ["earnings_guidance_revenue_change_pct_max"],
    "earnings_positive_events": ["earnings_positive_events"],
    "earnings_negative_events": ["earnings_negative_events"],
    "contract_liabilities_to_revenue_change": ["contract_liabilities_to_revenue_change"],
    "contract_assets_to_revenue_change": ["contract_assets_to_revenue_change"],
    "accounts_payable_to_revenue_change": ["accounts_payable_to_revenue_change"],
    "roe_trend": ["roe_trend"],
    "gross_margin_trend": ["gross_margin_trend"],
    "free_cash_flow_trend": ["free_cash_flow_trend"],
    "debt_ratio_trend": ["debt_ratio_trend"],
    "current_ratio_trend": ["current_ratio_trend"],
    "deducted_net_profit_trend": ["deducted_net_profit_trend"],
    "deducted_net_profit": ["deducted_net_profit"],
    "dividend_cash_per_10_shares": ["dividend_cash_per_10_shares"],
    "buyback_amount_min": ["buyback_amount_min"],
    "buyback_amount_max": ["buyback_amount_max"],
    "earnings_guidance_net_profit_min": ["earnings_guidance_net_profit_min"],
    "earnings_guidance_net_profit_max": ["earnings_guidance_net_profit_max"],
    "pe": ["pe_ratio"],
    "price": ["price"],
}

_QUANT_PERCENT_FIELDS = {
    "roe", "roa", "roic", "gross_margin", "net_margin", "debt_ratio",
    "dividend_yield", "revenue_yoy", "net_profit_yoy", "pledge_ratio",
    "earnings_guidance_change_pct_min", "earnings_guidance_change_pct_max",
    "earnings_guidance_revenue_change_pct_min", "earnings_guidance_revenue_change_pct_max",
}


def snapshot_to_quant_text(snapshot: Mapping[str, Any]) -> str:
    fields = snapshot.get("fields", {})
    if not fields:
        return ""

    lines: List[str] = []
    output_names: set = set()

    for snapshot_name, quant_names in _QUANT_NAME_MAP.items():
        field = fields.get(snapshot_name)
        if not field or field.get("status") not in ("present", "conflict", "corrected", "needs_verification"):
            continue

        value = field.get("value")
        if value is None:
            continue

        if snapshot_name in _QUANT_PERCENT_FIELDS and isinstance(value, (int, float)):
            if abs(value) > 1:
                value = value / 100.0

        if isinstance(value, float):
            formatted = f"{value:g}"
        else:
            formatted = str(value)

        status_tag = ""
        if field.get("status") == "corrected":
            status_tag = " [已修正]"
        elif field.get("status") == "needs_verification":
            status_tag = " [待验证]"

        for quant_name in quant_names:
            if quant_name not in output_names:
                lines.append(f"{quant_name}: {formatted}{status_tag}")
                output_names.add(quant_name)

    consistency_issues = snapshot.get("consistency_issues", [])
    if consistency_issues:
        lines.append("")
        lines.append("# 数据一致性警告:")
        for issue in consistency_issues:
            fix_parts = [f"{k}→{v}" for k, v in issue.get("suggested_fix", {}).items()]
            fix_text = f" 建议修正: {', '.join(fix_parts)}" if fix_parts else ""
            lines.append(f"# - [{issue['rule']}] {issue['description']}{fix_text}")

    return "\n".join(lines)
