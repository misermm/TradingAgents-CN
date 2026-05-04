from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_buffett_fundamentals(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    roe = safe_float(data.get("ROE") or data.get("净资产收益率") or data.get("return_on_equity"))
    if roe is not None:
        max_score += 2
        if roe > 0.15:
            score += 2
            details.append(f"强ROE: {roe:.1%}")
        elif roe > 0.10:
            score += 1
            details.append(f"中等ROE: {roe:.1%}")

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率") or data.get("debt_ratio"))
    if de_ratio is not None:
        max_score += 2
        if de_ratio < 0.5:
            score += 2
            details.append("保守债务水平")
        elif de_ratio < 1.0:
            score += 1
            details.append(f"中等负债: {de_ratio:.2f}")

    op_margin = safe_float(data.get("operating_margin") or data.get("营业利润率") or data.get("operatingMargin"))
    net_margin_val = safe_float(data.get("net_margin") or data.get("净利润率") or data.get("净利率") or data.get("netMargin"))
    if op_margin is not None:
        max_score += 2
        if op_margin > 0.15:
            score += 2
            details.append("强营业利润率")
        elif op_margin > 0.10:
            score += 1
            details.append(f"中等利润率: {op_margin:.1%}")
    elif net_margin_val is not None:
        max_score += 2
        if net_margin_val > 0.15:
            score += 2
            details.append(f"高净利润率: {net_margin_val:.1%}")
        elif net_margin_val > 0.10:
            score += 1
            details.append(f"中等净利润率: {net_margin_val:.1%}")

    current_ratio = safe_float(data.get("current_ratio") or data.get("流动比率"))
    if current_ratio is not None:
        max_score += 1
        if current_ratio > 1.5:
            score += 1
            details.append("良好流动性")
        elif current_ratio > 1.0:
            score += 0.5

    if net_margin_val is not None and op_margin is not None:
        max_score += 2
        if net_margin_val > 0.10:
            score += 2
            details.append(f"高净利润率: {net_margin_val:.1%}")
        elif net_margin_val > 0.05:
            score += 1

    gross_margin = safe_float(data.get("gross_margin") or data.get("毛利率") or data.get("grossMargin"))
    if gross_margin is not None:
        max_score += 1
        if gross_margin > 0.40:
            score += 1
            details.append(f"高毛利率: {gross_margin:.1%}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_buffett_moat(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 2
        if roe > 0.20:
            score += 2
            details.append(f"持续高ROE({roe:.1%})暗示护城河")
        elif roe > 0.15:
            score += 1
            details.append(f"中等ROE({roe:.1%})可能存在护城河")
        elif roe > 0.10:
            score += 0.5

    gross_margin = safe_float(data.get("gross_margin") or data.get("毛利率"))
    if gross_margin is not None:
        max_score += 1
        if gross_margin > 0.50:
            score += 1
            details.append(f"高毛利率({gross_margin:.1%})暗示定价权")
        elif gross_margin > 0.30:
            score += 0.5

    net_margin_val = safe_float(data.get("net_margin") or data.get("净利润率") or data.get("净利率"))
    op_margin = safe_float(data.get("operating_margin") or data.get("营业利润率"))
    profit_margin = op_margin if op_margin is not None else net_margin_val
    if profit_margin is not None:
        max_score += 1
        if profit_margin > 0.20:
            score += 1
            details.append("稳定高利润率暗示竞争壁垒")
        elif profit_margin > 0.10:
            score += 0.5

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if revenue_growth is not None:
        max_score += 1
        if revenue_growth > 0.10:
            score += 1
            details.append(f"持续增长({revenue_growth:.1%})暗示护城河加宽")
        elif revenue_growth > 0.05:
            score += 0.5

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_buffett_management(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 1
        if roe > 0.15:
            score += 1
            details.append(f"ROE {roe:.1%}表明资本配置有效")
        elif roe > 0.10:
            score += 0.5
            details.append(f"ROE {roe:.1%}资本配置尚可")

    fcf = safe_float(data.get("free_cash_flow") or data.get("自由现金流"))
    net_income = safe_float(data.get("net_income") or data.get("净利润"))
    if fcf is not None and net_income is not None:
        max_score += 1
        if fcf > 0 and net_income > 0:
            fcf_ratio = fcf / net_income
            if fcf_ratio > 1.0:
                score += 1
                details.append("FCF/NI>1, 盈利质量高")
            elif fcf_ratio > 0.7:
                score += 0.5
    elif net_income is not None and net_income > 0:
        net_margin_val = safe_float(data.get("net_margin") or data.get("净利润率") or data.get("净利率"))
        if net_margin_val is not None and net_margin_val > 0.10:
            max_score += 1
            score += 0.5
            details.append(f"高净利润率({net_margin_val:.1%})暗示盈利质量好")

    dividend = safe_float(data.get("dividend_yield") or data.get("股息率"))
    if dividend is not None:
        max_score += 1
        if dividend > 0:
            score += 1
            details.append(f"有分红记录({dividend:.1%})")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def buffett_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    fundamentals = analyze_buffett_fundamentals(data)
    moat = analyze_buffett_moat(data)
    management = analyze_buffett_management(data)

    total_score = fundamentals["score"] + moat["score"] + management["score"]
    max_score = fundamentals["max_score"] + moat["max_score"] + management["max_score"]
    evidence_table = []

    roe = safe_float(data.get("ROE") or data.get("净资产收益率") or data.get("return_on_equity"))
    if roe is not None:
        evidence_table.append(make_evidence_row("基本面分析", "ROE阈值", "roe", f"{roe:.1%}", 2 if roe > 0.15 else 1 if roe > 0.10 else 0, 2, "偏好长期高ROE企业"))

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率") or data.get("debt_ratio"))
    if de_ratio is not None:
        evidence_table.append(make_evidence_row("基本面分析", "债务约束", "debt_ratio", de_ratio, 2 if de_ratio < 0.5 else 1 if de_ratio < 1.0 else 0, 2, "债务越低越符合保守资本结构"))

    net_margin_val = safe_float(data.get("net_margin") or data.get("净利润率") or data.get("净利率") or data.get("netMargin"))
    if net_margin_val is not None:
        evidence_table.append(make_evidence_row("基本面分析", "利润率质量", "net_margin", f"{net_margin_val:.1%}", 2 if net_margin_val > 0.15 else 1 if net_margin_val > 0.10 else 0, 2, "稳定高利润率更接近消费/品牌型护城河"))

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if revenue_growth is not None:
        evidence_table.append(make_evidence_row("护城河评估", "增长验证护城河", "revenue_growth", f"{revenue_growth:.1%}", 1 if revenue_growth > 0.10 else 0.5 if revenue_growth > 0.05 else 0, 1, "持续增长可作为护城河扩张的外在验证"))

    fcf = safe_float(data.get("free_cash_flow") or data.get("自由现金流"))
    net_income = safe_float(data.get("net_income") or data.get("净利润"))
    if fcf is not None and net_income not in (None, 0):
        fcf_ratio = fcf / net_income
        evidence_table.append(make_evidence_row("管理层评估", "盈利兑现度", "fcf/net_income", round(fcf_ratio, 2), 1 if fcf_ratio > 1.0 else 0.5 if fcf_ratio > 0.7 else 0, 1, "现金流能否兑现利润反映资本配置与盈余质量"))

    dividend = safe_float(data.get("dividend_yield") or data.get("股息率"))
    if dividend is not None:
        evidence_table.append(make_evidence_row("管理层评估", "股东回报", "dividend_yield", f"{dividend:.1%}", 1 if dividend > 0 else 0, 1, "稳定分红是巴菲特风格的正面治理信号"))

    insider_increase = safe_float(data.get("insider_increase_events"))
    insider_decrease = safe_float(data.get("insider_decrease_events"))
    if insider_increase is not None or insider_decrease is not None:
        increase_count = insider_increase or 0.0
        decrease_count = insider_decrease or 0.0
        observed = f"increase={increase_count:.0f}, decrease={decrease_count:.0f}"
        score_value = 1 if increase_count > decrease_count else 0.5 if decrease_count == 0 else 0
        evidence_table.append(make_evidence_row("管理层评估", "管理层增减持", "management_alignment_summary", observed, score_value, 1, "内部人增减持是治理一致性的直接信号"))

    penalty_severity = str(data.get("regulatory_penalty_severity") or "").strip().lower()
    if penalty_severity:
        penalty_score = 1 if penalty_severity in {"none", "low"} else 0.5 if penalty_severity == "medium" else 0
        evidence_table.append(make_evidence_row("管理层评估", "监管处罚风险", "regulatory_penalty_severity", penalty_severity, penalty_score, 1, "严重监管处罚会直接削弱对管理层的信任"))

    goodwill_impairment = safe_float(data.get("goodwill_impairment_amount_max"))
    if goodwill_impairment is not None:
        evidence_table.append(make_evidence_row("管理层评估", "商誉减值约束", "goodwill_impairment_amount_max", round(goodwill_impairment, 2), 1 if goodwill_impairment <= 0 else 0, 1, "大额商誉减值常见于历史并购和资本配置失误"))

    contract_liabilities_change = safe_float(data.get("contract_liabilities_to_revenue_change"))
    if contract_liabilities_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Working Capital",
                "Contract Liabilities Conversion",
                "contract_liabilities_to_revenue_change",
                round(contract_liabilities_change, 2),
                1 if contract_liabilities_change > 0 else 0.5 if contract_liabilities_change == 0 else 0,
                1,
                "Rising contract liabilities can indicate order intake and advance collections.",
            )
        )

    contract_assets_change = safe_float(data.get("contract_assets_to_revenue_change"))
    if contract_assets_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Working Capital",
                "Contract Assets Expansion Risk",
                "contract_assets_to_revenue_change",
                round(contract_assets_change, 2),
                1 if contract_assets_change < 0 else 0.5 if contract_assets_change == 0 else 0,
                1,
                "Rising contract assets can indicate delayed collection or execution pressure.",
            )
        )

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "基本面分析": fundamentals,
            "护城河评估": moat,
            "管理层评估": management,
        },
        "evidence_table": evidence_table,
        "details": f"基本面{fundamentals['score']:.0f}/{fundamentals['max_score']:.0f}, 护城河{moat['score']:.1f}/{moat['max_score']:.1f}, 管理{management['score']:.1f}/{management['max_score']:.1f}",
    }

    result["formatted_summary"] = format_quantitative_summary("巴菲特", result)
    return result
