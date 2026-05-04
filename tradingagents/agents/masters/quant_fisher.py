from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_fisher_growth_quality(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_cagr = safe_float(
        data.get("revenue_cagr") or data.get("营收复合增长率")
        or data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth")
    )
    if revenue_cagr is not None:
        max_score += 3
        if revenue_cagr > 0.20:
            score += 3
            details.append(f"高营收CAGR: {revenue_cagr:.1%}")
        elif revenue_cagr > 0.10:
            score += 2
            details.append(f"中等营收CAGR: {revenue_cagr:.1%}")
        elif revenue_cagr > 0.05:
            score += 1
            details.append(f"温和营收CAGR: {revenue_cagr:.1%}")

    eps_cagr = safe_float(
        data.get("eps_cagr") or data.get("EPS复合增长率")
        or data.get("eps_growth") or data.get("EPS增长率")
        or data.get("earnings_growth") or data.get("净利润增长率")
    )
    if eps_cagr is not None:
        max_score += 3
        if eps_cagr > 0.20:
            score += 3
            details.append(f"高EPS CAGR: {eps_cagr:.1%}")
        elif eps_cagr > 0.10:
            score += 2
            details.append(f"中等EPS CAGR: {eps_cagr:.1%}")
        elif eps_cagr > 0.05:
            score += 1
            details.append(f"温和EPS CAGR: {eps_cagr:.1%}")

    rd_ratio = safe_float(
        data.get("rd_ratio") or data.get("研发费用率")
        or data.get("researchAndDevelopmentRatio") or data.get("R&D比率")
        or data.get("rd_to_revenue")
    )
    if rd_ratio is not None:
        max_score += 3
        if rd_ratio > 0.15:
            score += 3
            details.append(f"高R&D投入: {rd_ratio:.1%}, 创新驱动")
        elif rd_ratio > 0.08:
            score += 2
            details.append(f"中等R&D投入: {rd_ratio:.1%}")
        elif rd_ratio > 0.03:
            score += 1
            details.append(f"一定R&D投入: {rd_ratio:.1%}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_margins_stability(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    op_margin_trend = safe_float(
        data.get("operating_margin_trend") or data.get("营业利润率趋势")
        or data.get("operatingMarginChange")
    )
    if op_margin_trend is not None:
        max_score += 2
        if op_margin_trend > 0.03:
            score += 2
            details.append(f"营业利润率显著改善: +{op_margin_trend:.1%}")
        elif op_margin_trend > 0:
            score += 1
            details.append("营业利润率改善中")

    gross_margin = safe_float(
        data.get("gross_margin") or data.get("毛利率")
        or data.get("grossMargin")
    )
    if gross_margin is not None:
        max_score += 2
        if gross_margin > 0.50:
            score += 2
            details.append(f"高毛利率: {gross_margin:.1%}, 产品差异化强")
        elif gross_margin > 0.30:
            score += 1
            details.append(f"中等毛利率: {gross_margin:.1%}")

    margin_stability = safe_float(
        data.get("margin_stability") or data.get("利润率稳定性")
        or data.get("marginVolatility")
    )
    if margin_stability is not None:
        max_score += 2
        if margin_stability < 0.02:
            score += 2
            details.append("利润率高度稳定")
        elif margin_stability < 0.05:
            score += 1
            details.append("利润率较稳定")
    else:
        op_margin = safe_float(
            data.get("operating_margin") or data.get("营业利润率")
            or data.get("operatingMargin")
        )
        if op_margin is not None and gross_margin is not None:
            max_score += 1
            if op_margin > 0.15 and gross_margin > 0.40:
                score += 1
                details.append("较高利润率水平暗示一定稳定性")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_management_efficiency(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    roe = safe_float(
        data.get("ROE") or data.get("净资产收益率")
        or data.get("return_on_equity")
    )
    if roe is not None:
        max_score += 3
        if roe > 0.20:
            score += 3
            details.append(f"卓越ROE: {roe:.1%}, 资本配置高效")
        elif roe > 0.15:
            score += 2
            details.append(f"强ROE: {roe:.1%}")
        elif roe > 0.10:
            score += 1
            details.append(f"中等ROE: {roe:.1%}")

    de_ratio = safe_float(
        data.get("debt_to_equity") or data.get("资产负债率")
        or data.get("debt_ratio") or data.get("debtEquityRatio")
    )
    if de_ratio is not None:
        max_score += 2
        if de_ratio < 0.5:
            score += 2
            details.append("保守债务水平")
        elif de_ratio < 1.0:
            score += 1
            details.append(f"中等负债: {de_ratio:.2f}")

    fcf = safe_float(
        data.get("free_cash_flow") or data.get("自由现金流")
        or data.get("fcf") or data.get("freeCashFlow")
    )
    if fcf is not None:
        max_score += 1
        if fcf > 0:
            score += 1
            details.append("正自由现金流")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def fisher_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    growth = analyze_fisher_growth_quality(data)
    margins = analyze_margins_stability(data)
    management = analyze_management_efficiency(data)

    valuation_score = 0
    valuation_max = 0
    valuation_details = []

    pe_ratio = safe_float(
        data.get("pe_ratio") or data.get("市盈率") or data.get("P/E")
    )
    eps_growth = safe_float(
        data.get("eps_growth") or data.get("EPS增长率")
        or data.get("earnings_growth")
    )

    peg_ratio = safe_float(
        data.get("peg_ratio") or data.get("PEG")
        or data.get("priceToEarningsGrowthRatio")
    )
    if peg_ratio is not None:
        if peg_ratio > 0:
            valuation_max += 2
            if peg_ratio < 1.0:
                valuation_score += 2
                valuation_details.append(f"PEG<1: {peg_ratio:.2f}, 低估")
            elif peg_ratio < 1.5:
                valuation_score += 1
                valuation_details.append(f"合理PEG: {peg_ratio:.2f}")
    if peg_ratio is None or peg_ratio <= 0:
        if pe_ratio is not None and eps_growth is not None and pe_ratio > 0 and eps_growth > 0:
            valuation_max += 1
            calc_peg = pe_ratio / (eps_growth * 100)
            if calc_peg < 1.0:
                valuation_score += 1
                valuation_details.append(f"推算PEG<1: {calc_peg:.2f}")

    ps_ratio = safe_float(
        data.get("ps_ratio") or data.get("市销率")
        or data.get("priceToSalesRatio")
    )
    if ps_ratio is not None:
        valuation_max += 1
        if 0 < ps_ratio < 5:
            valuation_score += 1
            valuation_details.append(f"合理PS: {ps_ratio:.1f}")

    fcf_yield = safe_float(
        data.get("fcf_yield") or data.get("自由现金流收益率")
    )
    if fcf_yield is not None:
        valuation_max += 1
        if fcf_yield > 0.05:
            valuation_score += 1
            valuation_details.append(f"正FCF收益率: {fcf_yield:.1%}")

    if valuation_max == 0:
        valuation_max = 1

    valuation_analysis = {
        "score": valuation_score,
        "max_score": valuation_max,
        "signal": score_to_signal(valuation_score, valuation_max),
        "details": "; ".join(valuation_details) if valuation_details else "数据不足",
    }

    other_score = 0
    other_max = 0
    other_details = []

    employee_growth = safe_float(
        data.get("employee_growth") or data.get("员工增长率")
    )
    if employee_growth is not None:
        other_max += 0.5
        if employee_growth > 0:
            other_score += 0.5
            other_details.append("员工增长, 暗示良好关系")

    rd_ratio = safe_float(
        data.get("rd_ratio") or data.get("研发费用率") or data.get("R&D比率")
    )
    if rd_ratio is not None:
        other_max += 1
        if rd_ratio > 0.08:
            other_score += 1
            other_details.append("持续研发投入, 管理层有远见")

    op_margin = safe_float(data.get("operating_margin") or data.get("营业利润率"))
    if op_margin is not None:
        other_max += 1
        if op_margin > 0.15:
            other_score += 1
            other_details.append("良好成本控制")
        elif op_margin > 0:
            other_score += 0.5

    gross_margin = safe_float(data.get("gross_margin") or data.get("毛利率"))
    if gross_margin is not None:
        other_max += 0.5
        if gross_margin > 0.50:
            other_score += 0.5
            other_details.append("高毛利率暗示持续竞争优势")

    other_score = min(other_score, other_max) if other_max > 0 else other_score
    if other_max == 0:
        other_max = 1

    other_analysis = {
        "score": other_score,
        "max_score": other_max,
        "signal": score_to_signal(other_score, other_max),
        "details": "; ".join(other_details) if other_details else "数据不足",
    }

    total_score = growth["score"] + margins["score"] + management["score"] + valuation_score + other_score
    max_score = growth["max_score"] + margins["max_score"] + management["max_score"] + valuation_max + other_max
    evidence_table = []

    revenue_cagr = safe_float(
        data.get("revenue_cagr") or data.get("营收复合增长率")
        or data.get("revenue_growth") or data.get("营收增长率")
    )
    if revenue_cagr is not None:
        evidence_table.append(make_evidence_row("增长质量", "营收持续增长", "revenue_cagr", f"{revenue_cagr:.1%}", 3 if revenue_cagr > 0.20 else 2 if revenue_cagr > 0.10 else 1 if revenue_cagr > 0.05 else 0, 3, "费舍尔首先看企业是否具备长期成长空间。"))

    rd_ratio = safe_float(
        data.get("rd_ratio") or data.get("研发费用率")
        or data.get("researchAndDevelopmentRatio") or data.get("rd_to_revenue")
    )
    if rd_ratio is not None:
        evidence_table.append(make_evidence_row("增长质量", "研发投入支撑产品线", "rd_ratio", f"{rd_ratio:.1%}", 3 if rd_ratio > 0.15 else 2 if rd_ratio > 0.08 else 1 if rd_ratio > 0.03 else 0, 3, "研发投入是费舍尔验证创新能力的直接证据。"))

    gross_margin = safe_float(
        data.get("gross_margin") or data.get("毛利率")
        or data.get("grossMargin")
    )
    if gross_margin is not None:
        evidence_table.append(make_evidence_row("利润率稳定性", "毛利率支撑产品差异化", "gross_margin", f"{gross_margin:.1%}", 2 if gross_margin > 0.50 else 1 if gross_margin > 0.30 else 0, 2, "高毛利说明公司可能具备更强产品力和议价能力。"))

    roe = safe_float(
        data.get("ROE") or data.get("净资产收益率")
        or data.get("return_on_equity")
    )
    if roe is not None:
        evidence_table.append(make_evidence_row("管理层效率", "资本配置效率", "roe", f"{roe:.1%}", 3 if roe > 0.20 else 2 if roe > 0.15 else 1 if roe > 0.10 else 0, 3, "费舍尔强调优秀管理层应把资本用在高回报方向。"))

    peg_ratio = safe_float(
        data.get("peg_ratio") or data.get("PEG")
        or data.get("priceToEarningsGrowthRatio")
    )
    if peg_ratio is not None and peg_ratio > 0:
        evidence_table.append(make_evidence_row("估值分析", "成长价格匹配度", "peg_ratio", round(peg_ratio, 2), 2 if peg_ratio < 1.0 else 1 if peg_ratio < 1.5 else 0, 2, "高成长也需要合理估值，否则回报会被估值消耗。"))

    penalty_severity = str(data.get("regulatory_penalty_severity") or "").strip().lower()
    if penalty_severity:
        penalty_score = 2 if penalty_severity in {"none", "low"} else 1 if penalty_severity == "medium" else 0
        evidence_table.append(make_evidence_row("管理层效率", "监管处罚约束", "regulatory_penalty_severity", penalty_severity, penalty_score, 2, "费舍尔重视管理层声誉与执行力，严重处罚会削弱长期信任。"))

    related_party_amount = safe_float(data.get("related_party_transaction_amount_max"))
    if related_party_amount is not None:
        related_party_score = 1 if related_party_amount <= 0 else 0
        evidence_table.append(make_evidence_row("管理层效率", "关联交易克制", "related_party_transaction_amount_max", round(related_party_amount, 2), related_party_score, 1, "大额关联交易会削弱费舍尔对治理质量的判断。"))

    guidance_max = safe_float(data.get("earnings_guidance_change_pct_max"))
    guidance_min = safe_float(data.get("earnings_guidance_change_pct_min"))
    if guidance_max is not None or guidance_min is not None:
        observed = f"{guidance_min if guidance_min is not None else 'N/A'}~{guidance_max if guidance_max is not None else 'N/A'}%"
        guidance_score = 2 if (guidance_max or 0) >= 20 and (guidance_min is None or guidance_min > -10) else 1 if (guidance_max or 0) > 0 else 0
        evidence_table.append(make_evidence_row("增长质量", "业绩预告验证成长", "earnings_guidance_change_pct_max", observed, guidance_score, 2, "业绩预告能为费舍尔式成长判断提供更及时的经营验证。"))

    revenue_guidance_change = safe_float(data.get("earnings_guidance_revenue_change_pct_max"))
    if revenue_guidance_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Growth",
                "Revenue Guidance Momentum",
                "earnings_guidance_revenue_change_pct_max",
                f"{revenue_guidance_change:.1%}",
                1 if revenue_guidance_change > 0.15 else 0.5 if revenue_guidance_change > 0.05 else 0,
                1,
                "Forward revenue guidance helps validate whether demand expansion is still intact.",
            )
        )

    asset_impairment = safe_float(data.get("asset_impairment_amount_max"))
    if asset_impairment is not None:
        evidence_table.append(
            make_evidence_row(
                "Quality",
                "Asset Impairment Discipline",
                "asset_impairment_amount_max",
                round(asset_impairment, 2),
                1 if asset_impairment <= 0 else 0,
                1,
                "Large impairment charges weaken confidence in expansion quality and management execution.",
            )
        )

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "增长质量": growth,
            "利润率稳定性": margins,
            "管理层效率": management,
            "估值分析": valuation_analysis,
            "其他因素": other_analysis,
        },
        "evidence_table": evidence_table,
        "details": (
            f"增长{growth['score']:.1f}/{growth['max_score']:.0f}, "
            f"利润率{margins['score']:.1f}/{margins['max_score']:.0f}, "
            f"管理{management['score']:.1f}/{management['max_score']:.0f}, "
            f"估值{valuation_score:.1f}/{valuation_max:.0f}, "
            f"其他{other_score:.1f}/{other_max:.0f}"
        ),
    }

    result["formatted_summary"] = format_quantitative_summary("费舍尔", result)
    return result
