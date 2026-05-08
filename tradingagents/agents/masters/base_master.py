from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler
from tradingagents.agents.utils.instrument_utils import build_instrument_context
from tradingagents.llm_clients import create_llm_client
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module

logger = get_logger("default")


QUANTITATIVE_ANALYZERS: Dict[str, Any] = {}


def _init_quantitative_analyzers() -> None:
    global QUANTITATIVE_ANALYZERS
    if QUANTITATIVE_ANALYZERS:
        return
    quant_modules = [
        ("warren_buffett", "quant_buffett", "buffett_quantitative_analysis"),
        ("peter_lynch", "quant_lynch", "lynch_quantitative_analysis"),
        ("ben_graham", "quant_graham", "graham_quantitative_analysis"),
        ("charlie_munger", "quant_munger", "munger_quantitative_analysis"),
        ("cathie_wood", "quant_wood", "wood_quantitative_analysis"),
        ("bill_ackman", "quant_ackman", "ackman_quantitative_analysis"),
        ("phil_fisher", "quant_fisher", "fisher_quantitative_analysis"),
        ("stanley_druckenmiller", "quant_druckenmiller", "druckenmiller_quantitative_analysis"),
        ("aswath_damodaran", "quant_damodaran", "damodaran_quantitative_analysis"),
        ("michael_burry", "quant_burry", "burry_quantitative_analysis"),
        ("mohnish_pabrai", "quant_pabrai", "pabrai_quantitative_analysis"),
        ("nassim_taleb", "quant_taleb", "taleb_quantitative_analysis"),
        ("rakesh_jhunjhunwala", "quant_jhunjhunwala", "jhunjhunwala_quantitative_analysis"),
    ]
    for master_id, module_name, func_name in quant_modules:
        try:
            mod = __import__(f"tradingagents.agents.masters.{module_name}", fromlist=[func_name])
            QUANTITATIVE_ANALYZERS[master_id] = getattr(mod, func_name)
        except ImportError:
            continue


MASTER_ANALYST_CONFIG = {
    "warren_buffett": {"name_cn": "巴菲特", "name_en": "Warren Buffett", "report_key": "warren_buffett_report", "counter_key": "warren_buffett_tool_call_count", "max_tool_calls": 2},
    "peter_lynch": {"name_cn": "彼得·林奇", "name_en": "Peter Lynch", "report_key": "peter_lynch_report", "counter_key": "peter_lynch_tool_call_count", "max_tool_calls": 2},
    "ben_graham": {"name_cn": "格雷厄姆", "name_en": "Ben Graham", "report_key": "ben_graham_report", "counter_key": "ben_graham_tool_call_count", "max_tool_calls": 2},
    "charlie_munger": {"name_cn": "芒格", "name_en": "Charlie Munger", "report_key": "charlie_munger_report", "counter_key": "charlie_munger_tool_call_count", "max_tool_calls": 2},
    "cathie_wood": {"name_cn": "凯瑟琳·伍德", "name_en": "Cathie Wood", "report_key": "cathie_wood_report", "counter_key": "cathie_wood_tool_call_count", "max_tool_calls": 2},
    "bill_ackman": {"name_cn": "阿克曼", "name_en": "Bill Ackman", "report_key": "bill_ackman_report", "counter_key": "bill_ackman_tool_call_count", "max_tool_calls": 2},
    "phil_fisher": {"name_cn": "费舍尔", "name_en": "Phil Fisher", "report_key": "phil_fisher_report", "counter_key": "phil_fisher_tool_call_count", "max_tool_calls": 2},
    "stanley_druckenmiller": {"name_cn": "德鲁肯米勒", "name_en": "Stanley Druckenmiller", "report_key": "stanley_druckenmiller_report", "counter_key": "stanley_druckenmiller_tool_call_count", "max_tool_calls": 2},
    "aswath_damodaran": {"name_cn": "达莫达兰", "name_en": "Aswath Damodaran", "report_key": "aswath_damodaran_report", "counter_key": "aswath_damodaran_tool_call_count", "max_tool_calls": 2},
    "michael_burry": {"name_cn": "布瑞", "name_en": "Michael Burry", "report_key": "michael_burry_report", "counter_key": "michael_burry_tool_call_count", "max_tool_calls": 2},
    "mohnish_pabrai": {"name_cn": "帕伯莱", "name_en": "Mohnish Pabrai", "report_key": "mohnish_pabrai_report", "counter_key": "mohnish_pabrai_tool_call_count", "max_tool_calls": 2},
    "nassim_taleb": {"name_cn": "塔勒布", "name_en": "Nassim Taleb", "report_key": "nassim_taleb_report", "counter_key": "nassim_taleb_tool_call_count", "max_tool_calls": 2},
    "rakesh_jhunjhunwala": {"name_cn": "朱朱瓦拉", "name_en": "Rakesh Jhunjhunwala", "report_key": "rakesh_jhunjhunwala_report", "counter_key": "rakesh_jhunjhunwala_tool_call_count", "max_tool_calls": 2},
}


MASTER_DATA_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "warren_buffett": {
        "min_completeness": 0.75,
        "strict_estimates_as_missing": True,
        "required_groups": [
            {"name": "净利润及增长率", "aliases": ["净利润", "net_income", "net_profit", "净利润增长率", "profit_growth", "net_income_growth"]},
            {"name": "自由现金流", "aliases": ["自由现金流", "free_cash_flow", "fcf", "free_cash_flow_trend", "经营现金流量净额", "operating_cash_flow"]},
            {"name": "资产负债详情", "aliases": ["资产负债率", "debt_ratio", "debt_ratio_trend", "debt_to_equity", "负债率", "流动比率", "current_ratio", "current_ratio_trend"]},
            {"name": "ROE历史趋势", "aliases": ["ROE", "roe", "净资产收益率", "return_on_equity", "ROE历史趋势", "roe_trend"]},
            {
                "name": "管理层信息",
                "aliases": [
                    "管理层信息", "管理层", "资本配置", "股东回报", "分红", "回购",
                    "shareholder_return_summary", "governance_risk_summary",
                    "dividend_events", "buyback_events", "management_change_events",
                    "dividend_cash_per_10_shares", "buyback_amount_min", "buyback_amount_max",
                    "dividend_record_date", "dividend_ex_date", "buyback_period_months",
                    "management_alignment_summary", "insider_increase_events", "insider_decrease_events",
                    "earnings_guidance_summary", "earnings_positive_events", "earnings_negative_events",
                    "earnings_guidance_change_pct_min", "earnings_guidance_change_pct_max",
                    "earnings_guidance_net_profit_min", "earnings_guidance_net_profit_max",
                    "regulatory_penalty_events", "goodwill_impairment_events", "goodwill_impairment_amount_max",
                ],
            },
            {"name": "护城河定性分析", "aliases": ["护城河", "竞争优势", "品牌价值", "成本优势", "转换成本", "moat"]},
        ],
    }
}


_GENERIC_MASTER_REQUIRED_GROUPS = [
    {"name": "revenue_growth", "aliases": ["revenue", "sales", "revenue_growth", "sales_growth", "营业收入", "营收", "收入增长"]},
    {
        "name": "earnings_growth",
        "aliases": [
            "net_income", "net_profit", "profit_growth", "earnings_growth", "净利润", "利润增长",
            "earnings_guidance_summary", "earnings_positive_events", "earnings_negative_events",
            "earnings_guidance_change_pct_min", "earnings_guidance_change_pct_max",
            "earnings_guidance_net_profit_min", "earnings_guidance_net_profit_max",
        ],
    },
    {"name": "valuation", "aliases": ["pe", "pe_ratio", "p/e", "pb", "pb_ratio", "p/b", "dcf", "intrinsic_value", "估值", "市盈率", "市净率"]},
    {"name": "balance_sheet", "aliases": ["debt_ratio", "debt_to_equity", "current_ratio", "cash", "资产负债率", "负债率", "流动比率"]},
    {"name": "free_cash_flow", "aliases": ["free_cash_flow", "fcf", "operating_cash_flow", "自由现金流", "经营现金流"]},
]


_MASTER_REQUIREMENT_OVERRIDES = {
    "peter_lynch": [_GENERIC_MASTER_REQUIRED_GROUPS[0], _GENERIC_MASTER_REQUIRED_GROUPS[1], _GENERIC_MASTER_REQUIRED_GROUPS[2], _GENERIC_MASTER_REQUIRED_GROUPS[4]],
    "ben_graham": [
        _GENERIC_MASTER_REQUIRED_GROUPS[1],
        _GENERIC_MASTER_REQUIRED_GROUPS[2],
        _GENERIC_MASTER_REQUIRED_GROUPS[3],
        {"name": "eps_and_bvps", "aliases": ["eps", "EPS", "每股收益", "basic_eps", "earningsPerShare", "book_value_per_share", "每股净资产", "bvps", "bps", "bookValuePerShare"]},
        {"name": "ncav_components", "aliases": ["current_assets", "流动资产", "流动资产合计", "totalCurrentAssets", "total_liabilities", "总负债", "负债合计", "totalLiabilities", "total_assets", "总资产", "资产总计", "totalAssets", "current_liabilities", "流动负债", "流动负债合计"]},
        {"name": "revenue_and_profit", "aliases": ["revenue", "营业收入", "营业总收入", "营收", "net_profit", "净利润", "net_income"]},
    ],
    "charlie_munger": [
        _GENERIC_MASTER_REQUIRED_GROUPS[1],
        _GENERIC_MASTER_REQUIRED_GROUPS[3],
        _GENERIC_MASTER_REQUIRED_GROUPS[4],
        {"name": "quality_moat", "aliases": ["roe", "roic", "roe_trend", "gross_margin_trend", "free_cash_flow_trend", "moat", "competitive_advantage", "ROE", "ROIC", "护城河", "竞争优势"]},
    ],
    "cathie_wood": [
        {"name": "innovation_growth", "aliases": ["revenue_growth", "研发", "r&d", "innovation", "market_size", "TAM"]},
        _GENERIC_MASTER_REQUIRED_GROUPS[0],
        _GENERIC_MASTER_REQUIRED_GROUPS[2],
    ],
    "bill_ackman": [
        _GENERIC_MASTER_REQUIRED_GROUPS[1],
        _GENERIC_MASTER_REQUIRED_GROUPS[2],
        _GENERIC_MASTER_REQUIRED_GROUPS[3],
        {
            "name": "capital_return",
            "aliases": [
                "dividend", "buyback", "shareholder_return", "分红", "回购", "股东回报",
                "dividend_events", "buyback_events", "shareholder_return_summary",
                "dividend_cash_per_10_shares", "buyback_amount_min", "buyback_amount_max",
                "dividend_record_date", "dividend_ex_date", "buyback_period_months",
            ],
        },
    ],
    "phil_fisher": [
        _GENERIC_MASTER_REQUIRED_GROUPS[0],
        _GENERIC_MASTER_REQUIRED_GROUPS[1],
        {"name": "research_product", "aliases": ["研发", "product", "pipeline", "innovation", "产品", "研发投入"]},
        {
            "name": "management_quality",
            "aliases": [
                "management", "管理层", "治理", "capital_allocation",
                "management_change_events", "governance_risk_summary", "pledge_ratio",
                "cashflow_to_profit_ratio", "receivables_to_revenue_change", "inventory_to_revenue_change",
                "deducted_net_profit_trend", "free_cash_flow_trend",
                "management_alignment_summary", "insider_increase_events", "insider_decrease_events",
                "earnings_guidance_summary", "earnings_positive_events", "earnings_negative_events",
                "earnings_guidance_change_pct_min", "earnings_guidance_change_pct_max",
                "earnings_guidance_net_profit_min", "earnings_guidance_net_profit_max",
                "regulatory_penalty_events", "goodwill_impairment_events", "goodwill_impairment_amount_max",
                "related_party_transaction_amount_max",
            ],
        },
    ],
    "stanley_druckenmiller": [
        {"name": "price_momentum", "aliases": ["price", "close", "pct_chg", "momentum", "trend", "价格", "涨跌幅", "趋势"]},
        {"name": "macro_context", "aliases": ["macro", "rate", "policy", "fx", "宏观", "利率", "政策", "汇率"]},
        _GENERIC_MASTER_REQUIRED_GROUPS[2],
    ],
    "aswath_damodaran": [
        _GENERIC_MASTER_REQUIRED_GROUPS[0],
        _GENERIC_MASTER_REQUIRED_GROUPS[1],
        _GENERIC_MASTER_REQUIRED_GROUPS[2],
        _GENERIC_MASTER_REQUIRED_GROUPS[4],
        {"name": "cost_of_capital", "aliases": ["wacc", "discount_rate", "cost_of_capital", "折现率", "资本成本", "cashflow_to_profit_ratio", "debt_ratio_trend", "current_ratio_trend"]},
    ],
    "michael_burry": [
        _GENERIC_MASTER_REQUIRED_GROUPS[2],
        _GENERIC_MASTER_REQUIRED_GROUPS[3],
        {"name": "short_interest_or_risk", "aliases": ["short", "short_interest", "risk", "fraud", "做空", "风险", "异常"]},
    ],
    "mohnish_pabrai": [_GENERIC_MASTER_REQUIRED_GROUPS[2], _GENERIC_MASTER_REQUIRED_GROUPS[3], _GENERIC_MASTER_REQUIRED_GROUPS[4]],
    "nassim_taleb": [
        {"name": "tail_risk", "aliases": ["volatility", "drawdown", "leverage", "tail_risk", "波动", "回撤", "杠杆", "尾部风险"]},
        _GENERIC_MASTER_REQUIRED_GROUPS[3],
        {"name": "liquidity", "aliases": ["volume", "turnover", "liquidity", "成交量", "换手率", "流动性"]},
    ],
    "rakesh_jhunjhunwala": [
        _GENERIC_MASTER_REQUIRED_GROUPS[0],
        _GENERIC_MASTER_REQUIRED_GROUPS[1],
        _GENERIC_MASTER_REQUIRED_GROUPS[2],
        {"name": "market_leadership", "aliases": ["market_share", "leader", "brand", "市占率", "龙头", "品牌"]},
    ],
}

for _master_id, _groups in _MASTER_REQUIREMENT_OVERRIDES.items():
    MASTER_DATA_REQUIREMENTS[_master_id] = {
        "min_completeness": 0.75,
        "required_groups": _groups,
    }


_MISSING_VALUE_MARKERS = ("N/A", "n/a", "NA", "none", "null", "unknown", "无", "未知", "缺失", "暂不可用", "暂无", "-", "--")
_ESTIMATED_VALUE_MARKERS = ("行业估算", "估算", "推算", "industry estimate", "estimated", "estimate")


def _value_status(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return "missing"
        if any(marker in normalized for marker in _ESTIMATED_VALUE_MARKERS):
            return "estimated"
        if any(marker in normalized for marker in _MISSING_VALUE_MARKERS):
            return "missing"
    return "present"


def _line_value_for_alias(line: str) -> str:
    normalized = line.strip()
    for sep in (":", "："):
        if sep in normalized:
            return normalized.split(sep, 1)[1].strip()
    return normalized


def _source_metadata_from_line(line: str) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    comment = line.split("#", 1)[1] if "#" in line else line
    for key in ("source", "report_period", "updated_at", "selection_reason"):
        match = re.search(rf"{key}\s*:\s*([^;|#]+)", comment, flags=re.IGNORECASE)
        if match:
            metadata[key] = match.group(1).strip()
    return metadata


def _field_quality_for_aliases(source_data: str, extracted_data: Dict[str, Any], group: Dict[str, Any]) -> Dict[str, Any]:
    aliases = group["aliases"]
    statuses: List[str] = []
    metadata: Dict[str, str] = {}
    for alias in aliases:
        if alias in extracted_data:
            statuses.append(_value_status(extracted_data.get(alias)))
    for line in source_data.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if not any(alias.lower() in normalized.lower() for alias in aliases):
            continue
        statuses.append(_value_status(_line_value_for_alias(normalized)))
        if not metadata:
            metadata = _source_metadata_from_line(normalized)
    if "present" in statuses:
        status = "present"
    elif "estimated" in statuses:
        status = "estimated"
    else:
        status = "missing"
    return {"name": group["name"], "status": status, "aliases": aliases, **metadata}


def evaluate_master_data_requirements(master_id: str, source_data: str) -> Dict[str, Any]:
    requirements = MASTER_DATA_REQUIREMENTS.get(master_id)
    if not requirements:
        return {
            "is_applicable": False,
            "is_sufficient": True,
            "completeness": 1.0,
            "present_count": 0,
            "required_count": 0,
            "missing_required": [],
            "estimated_required": [],
            "field_quality": [],
        }

    raw = source_data or ""
    try:
        from tradingagents.agents.masters.quantitative_base import extract_financial_data

        extracted_data = extract_financial_data(raw)
    except Exception:
        extracted_data = {}

    present_count = 0
    missing_required: List[str] = []
    estimated_required: List[str] = []
    field_quality: List[Dict[str, Any]] = []

    for group in requirements["required_groups"]:
        quality = _field_quality_for_aliases(raw, extracted_data, group)
        field_quality.append(quality)
        if quality["status"] == "present":
            present_count += 1
        elif quality["status"] == "estimated":
            estimated_required.append(group["name"])
        else:
            missing_required.append(group["name"])

    required_count = len(requirements["required_groups"])
    completeness = present_count / required_count if required_count else 1.0
    blocking_missing = list(missing_required)
    if requirements.get("strict_estimates_as_missing"):
        blocking_missing.extend(estimated_required)

    return {
        "is_applicable": True,
        "is_sufficient": completeness >= requirements["min_completeness"] and not blocking_missing,
        "completeness": completeness,
        "present_count": present_count,
        "required_count": required_count,
        "missing_required": blocking_missing,
        "estimated_required": estimated_required,
        "field_quality": field_quality,
    }


def _build_data_insufficient_report(master_id: str, company_name: str, ticker: str, current_date: str, data_quality: Dict[str, Any]) -> str:
    name_cn = MASTER_ANALYST_CONFIG.get(master_id, {}).get("name_cn", master_id)
    missing_rows = "\n".join(
        f"| {field} | 缺失或仅为估算 | 不可用于{name_cn}核心判断 |"
        for field in data_quality.get("missing_required", [])
    )
    return (
        f"## {name_cn}投资大师分析\n"
        f"⚠️ 重要声明\n"
        f"尊敬的投资者，我必须首先坦诚地说明：您提供的数据中，关于{company_name}（{ticker}）的关键字段存在明显缺失或估算。\n"
        f"这不符合我的投资原则，因此我不会基于不完整数据生成买入/持有/卖出倾向。\n\n"
        f"分析日期：{current_date}\n"
        f"数据完整度：{data_quality.get('present_count', 0)}/{data_quality.get('required_count', 0)}\n\n"
        f"| 必需数据项 | 当前状态 | 说明 |\n"
        f"|---|---|---|\n"
        f"{missing_rows}\n\n"
        f"结论：数据不足，不生成买入/持有/卖出倾向。"
    )


def _weaken_signal_toward_neutral(signal: str) -> str:
    if signal in {"bullish", "bearish"}:
        return "neutral"
    return signal


def apply_quantitative_quality_guard(quant_result: Optional[Dict[str, Any]], data_quality: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not quant_result or not data_quality or not data_quality.get("is_applicable"):
        return quant_result

    guarded = dict(quant_result)
    original_signal = str(guarded.get("signal", "neutral"))
    completeness = float(data_quality.get("completeness", 1.0) or 0.0)
    estimated_required = list(data_quality.get("estimated_required", []))
    missing_required = list(data_quality.get("missing_required", []))

    reasons: List[str] = []
    if estimated_required:
        reasons.append("estimated_required_fields")
    if completeness < 1.0:
        reasons.append("partial_completeness")
    if missing_required:
        reasons.append("missing_required_fields")

    degrade = bool(estimated_required) or completeness < 0.9
    guarded_signal = _weaken_signal_toward_neutral(original_signal) if degrade else original_signal
    guarded["signal"] = guarded_signal
    guarded["quality_guard"] = {
        "applied": bool(reasons),
        "original_signal": original_signal,
        "guarded_signal": guarded_signal,
        "reasons": reasons,
        "completeness": completeness,
        "estimated_required": estimated_required,
        "missing_required": missing_required,
    }

    if reasons:
        formatted_summary = guarded.get("formatted_summary", "") or ""
        reason_text = ", ".join(reasons)
        note = (
            "\n## Data Quality Guard\n"
            f"- completeness: {completeness:.2f}\n"
            f"- reasons: {reason_text}\n"
            f"- signal_adjustment: {original_signal} -> {guarded_signal}\n"
        )
        guarded["formatted_summary"] = f"{formatted_summary}{note}"
    return guarded


def _get_company_name_for_master(ticker: str, market_info: Dict[str, Any]) -> str:
    try:
        if market_info.get("is_china"):
            from tradingagents.dataflows.interface import get_china_stock_info_unified

            stock_info = get_china_stock_info_unified(ticker)
            if stock_info and "股票名称:" in stock_info:
                return stock_info.split("股票名称:")[1].split("\n")[0].strip()
            return f"股票代码{ticker}"
        if market_info.get("is_hk"):
            return f"港股{ticker.replace('.HK', '').replace('.hk', '')}"
        if market_info.get("is_us"):
            return ticker.upper()
        return f"股票{ticker}"
    except Exception:
        return f"股票{ticker}"


def _validate_report(report: str, _source_data: str, _name_cn: str) -> str:
    return report or ""


def _generate_report_from_prefetched(
    llm,
    name_cn: str,
    name_en: str,
    company_name: str,
    ticker: str,
    current_date: str,
    philosophy: str,
    framework: str,
    output_format: str,
    prefetched_data: str,
    quant_context: str,
    currency_info: str,
    market_info: Dict[str, Any],
    consistency_warnings: Optional[List[str]] = None,
) -> str:
    data_section = f"## 真实财务数据\n\n{prefetched_data[:8000]}\n"
    if quant_context:
        data_section += f"\n## 量化评分参考\n{quant_context}\n"
    if consistency_warnings:
        data_section += "\n## ⚠️ 数据一致性警告\n以下数据存在矛盾，请特别注意并在分析中标注：\n"
        for w in consistency_warnings:
            data_section += f"- {w}\n"
        data_section += "\n要求：对于上述矛盾数据，你必须在分析中明确指出矛盾之处，不得使用矛盾数据中的任何一方作为唯一依据。\n"
    analysis_prompt = (
        f"作为投资大师{name_cn}（{name_en}），基于以下真实数据，按照你的投资哲学对{company_name}"
        f"（股票代码：{ticker}，{market_info['market_name']}）进行分析。\n\n"
        f"{data_section}\n"
        f"投资哲学：\n{philosophy}\n\n"
        f"分析框架：\n{framework}\n\n"
        f"输出格式：\n{output_format}\n\n"
        f"要求：所有分析使用中文，货币使用{currency_info}，禁止编造数据。"
    )
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", f"你是投资大师{name_cn}（{name_en}），必须基于真实数据分析。"),
            ("human", "{analysis_request}"),
        ]
    )
    chain = prompt_template | llm
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            result = chain.invoke({"analysis_request": analysis_prompt})
            return _validate_report(result.content if hasattr(result, "content") else str(result), prefetched_data, name_cn)
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"[{name_cn}] LLM调用失败(第{attempt+1}次)，重试中: {type(e).__name__}: {str(e)[:100]}")
                import time
                time.sleep(2 * (attempt + 1))
            else:
                logger.error(f"[{name_cn}] LLM调用失败(已重试{max_retries}次): {type(e).__name__}: {str(e)[:200]}")
                return _validate_report(
                    f"## {name_cn}投资大师分析\n\n⚠️ LLM调用失败，无法生成详细分析报告。\n\n错误类型: {type(e).__name__}\n建议: 检查模型配置或切换到其他大模型。",
                    prefetched_data, name_cn
                )


def create_master_analyst(master_id: str, llm, toolkit, philosophy: str, framework: str, output_format: str, tools_list: Optional[List[Any]] = None):
    config = MASTER_ANALYST_CONFIG.get(master_id)
    if not config:
        logger.error(f"[MasterAnalyst] 未知的大师ID: {master_id}")
        def _fallback_node(state):
            return {}
        return _fallback_node
    name_cn = config["name_cn"]
    name_en = config["name_en"]
    max_tool_calls = config["max_tool_calls"]
    log_tag = f"[{name_cn}分析师]"

    if tools_list is None:
        tools_list = [toolkit.get_stock_fundamentals_unified]

    @log_analyst_module(master_id)
    def master_analyst_node(state):
        _init_quantitative_analyzers()
        quant_analyzer = QUANTITATIVE_ANALYZERS.get(master_id)
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        try:
            end_date_dt = datetime.strptime(current_date, "%Y-%m-%d")
            start_date = (end_date_dt - timedelta(days=10)).strftime("%Y-%m-%d")
        except Exception:
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)
        company_name = _get_company_name_for_master(ticker, market_info)
        instrument_context = build_instrument_context(ticker)
        currency_info = f"{market_info['currency_name']}（{market_info['currency_symbol']}）"

        prefetched_data = state.get("prefetched_fundamentals_data", "") or ""
        master_reports = state.get("master_reports", {})
        master_tool_counts = state.get("master_tool_call_counts", {})
        tool_call_count = master_tool_counts.get(master_id, 0)
        existing_report = master_reports.get(master_id, "")

        if existing_report and len(existing_report) > 100:
            logger.info(f"{log_tag} 报告已存在，跳过重复分析")
            return {}

        quant_context = ""
        quant_result: Optional[Dict[str, Any]] = None
        current_data_quality: Optional[Dict[str, Any]] = None
        raw_data_str = prefetched_data

        consistency_warnings: List[str] = []
        try:
            from tradingagents.dataflows.china_fundamental_snapshot import validate_data_consistency

            snapshot_data = state.get("fundamental_snapshot")
            if isinstance(snapshot_data, dict) and snapshot_data.get("fields"):
                issues = validate_data_consistency(snapshot_data)
                if issues:
                    for issue in issues:
                        fix_parts = [f"{k}→{v}" for k, v in issue.get("suggested_fix", {}).items()]
                        fix_text = f" 建议修正: {', '.join(fix_parts)}" if fix_parts else ""
                        consistency_warnings.append(f"[{issue['rule']}] {issue['description']}{fix_text}")
                        suggested_fix = issue.get("suggested_fix", {})
                        for fname, fix_val in suggested_fix.items():
                            if fix_val == "N/A":
                                pattern = rf"(?m)^({re.escape(fname)}\s*[:：]\s*)(.+)$"
                                raw_data_str = re.sub(pattern, rf"\1N/A(已修正)", raw_data_str)
                            elif isinstance(fix_val, (int, float)):
                                pattern = rf"(?m)^({re.escape(fname)}\s*[:：]\s*)(.+)$"
                                raw_data_str = re.sub(pattern, rf"\1{fix_val}(已修正)", raw_data_str)
                    logger.info(f"{log_tag} 数据一致性检查发现 {len(issues)} 项问题，已应用修正")
        except Exception as exc:
            logger.debug(f"{log_tag} 数据一致性检查跳过: {exc}")

        prefetched_quant = state.get("prefetched_quant_data", "") or ""

        if quant_analyzer:
            try:
                quant_input = prefetched_quant if prefetched_quant else raw_data_str
                if not quant_input:
                    unified_tool = tools_list[0] if tools_list else None
                    if unified_tool:
                        raw_data = unified_tool.invoke(
                            {
                                "ticker": ticker,
                                "start_date": start_date,
                                "end_date": current_date,
                                "curr_date": current_date,
                            }
                        )
                        quant_input = str(raw_data) if raw_data else ""
                if quant_input:
                    quant_result = quant_analyzer(quant_input)
                    quant_context = quant_result.get("formatted_summary", "")
            except Exception as exc:
                logger.warning(f"{log_tag} 量化评分计算失败(非致命): {exc}")

        data_quality_input = raw_data_str
        if data_quality_input:
            current_data_quality = evaluate_master_data_requirements(master_id, data_quality_input)
            quant_result = apply_quantitative_quality_guard(quant_result, current_data_quality)
            if quant_result:
                quant_context = quant_result.get("formatted_summary", "")
            if current_data_quality["is_applicable"] and not current_data_quality["is_sufficient"]:
                report = _build_data_insufficient_report(
                    master_id=master_id,
                    company_name=company_name,
                    ticker=ticker,
                    current_date=current_date,
                    data_quality=current_data_quality,
                )
                return {
                    "master_reports": {master_id: report},
                    "master_tool_call_counts": {master_id: tool_call_count + 1},
                    "master_data_quality": {master_id: current_data_quality},
                    "master_quantitative_results": {master_id: quant_result} if quant_result else {},
                }

        if prefetched_data and len(prefetched_data) > 50:
            try:
                report = _generate_report_from_prefetched(
                    llm,
                    name_cn,
                    name_en,
                    company_name,
                    ticker,
                    current_date,
                    philosophy,
                    framework,
                    output_format,
                    prefetched_data,
                    quant_context,
                    currency_info,
                    market_info,
                    consistency_warnings=consistency_warnings,
                )
            except Exception as e:
                logger.error(f"{log_tag} 生成报告失败: {type(e).__name__}: {str(e)[:200]}")
                report = f"## {name_cn}投资大师分析\n\n⚠️ 报告生成失败: {type(e).__name__}\n\n基于已有数据的简化分析：\n{prefetched_data[:2000]}"
            return {
                "master_reports": {master_id: report},
                "master_tool_call_counts": {master_id: tool_call_count},
                "master_data_quality": {master_id: current_data_quality} if current_data_quality else {},
                "master_quantitative_results": {master_id: quant_result} if quant_result else {},
            }

        tool_names = [getattr(tool, "name", getattr(tool, "__name__", str(tool))) for tool in tools_list]
        system_message = (
            f"你是投资大师{name_cn}（{name_en}）。\n\n"
            f"投资哲学：\n{philosophy}\n\n"
            f"分析框架：\n{framework}\n\n"
            f"分析目标：{company_name}（{ticker}，{market_info['market_name']}）\n{instrument_context}\n\n"
            f"输出格式：\n{output_format}\n\n"
            f"使用中文，投资建议只能是买入/持有/卖出，货币使用{currency_info}。"
        )

        if quant_context:
            system_message += f"\n\n量化评分参考：\n{quant_context}"

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "你是投资大师，必须基于真实数据进行分析。\n可用工具：{tool_names}。\n{system_message}\n当前日期：{current_date}\n分析目标：{company_name}（股票代码：{ticker}）。"),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        fresh_llm = llm
        try:
            model_name = getattr(llm, "model_name", "") or getattr(llm, "model", "")
            if model_name and "google" in str(model_name).lower():
                fresh_llm = create_llm_client(llm_provider="google", model_name=model_name)
        except Exception:
            fresh_llm = llm

        try:
            chain = prompt | fresh_llm.bind_tools(tools_list)
        except Exception:
            chain = prompt | fresh_llm

        try:
            result = chain.invoke(
                {
                    "messages": state["messages"],
                    "tool_names": ", ".join(tool_names),
                    "system_message": system_message,
                    "current_date": current_date,
                    "company_name": company_name,
                    "ticker": ticker,
                }
            )
        except Exception as e:
            logger.error(f"{log_tag} LLM调用失败(bind_tools模式): {type(e).__name__}: {str(e)[:200]}")
            report = f"## {name_cn}投资大师分析\n\n⚠️ LLM调用失败: {type(e).__name__}\n\n基于已有数据的简化分析：\n{raw_data_str[:2000] if raw_data_str else '数据不可用'}"
            return {
                "master_reports": {master_id: report},
                "messages": [],
                "master_tool_call_counts": {master_id: tool_call_count},
                "master_data_quality": {master_id: current_data_quality} if current_data_quality else {},
                "master_quantitative_results": {master_id: quant_result} if quant_result else {},
            }

        if isinstance(result, ToolMessage):
            return {"messages": [result], "master_tool_call_counts": {master_id: tool_call_count + 1}}

        if hasattr(result, "tool_calls") and result.tool_calls:
            if tool_call_count >= max_tool_calls:
                report = f"{name_cn}投资大师分析（股票代码：{ticker}）\n\n由于达到最大工具调用次数限制，使用简化分析模式。"
                return {
                    "master_reports": {master_id: report},
                    "master_tool_call_counts": {master_id: tool_call_count},
                    "master_data_quality": {master_id: current_data_quality} if current_data_quality else {},
                    "master_quantitative_results": {master_id: quant_result} if quant_result else {},
                }
            return {"messages": [result], "master_tool_call_counts": {master_id: tool_call_count + 1}}

        report = result.content if hasattr(result, "content") else str(result)
        report = _validate_report(report, raw_data_str or prefetched_data, name_cn)
        return {
            "master_reports": {master_id: report},
            "messages": [result],
            "master_tool_call_counts": {master_id: tool_call_count},
            "master_data_quality": {master_id: current_data_quality} if current_data_quality else {},
            "master_quantitative_results": {master_id: quant_result} if quant_result else {},
        }

    return master_analyst_node
