from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_moat_strength(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    roic = safe_float(
        data.get("ROIC") or data.get("投入资本回报率")
        or data.get("return_on_invested_capital") or data.get("roic")
    )
    if roic is not None:
        max_score += 3
        if roic > 0.25:
            score += 3
            details.append(f"卓越ROIC: {roic:.1%}")
        elif roic > 0.15:
            score += 2
            details.append(f"强ROIC: {roic:.1%}")
        elif roic > 0.10:
            score += 1
            details.append(f"中等ROIC: {roic:.1%}")

    gross_margin = safe_float(
        data.get("gross_margin") or data.get("毛利率")
        or data.get("grossMargin")
    )
    gross_margin_trend = safe_float(
        data.get("gross_margin_trend") or data.get("毛利率趋势")
        or data.get("grossMarginChange")
    )
    if gross_margin is not None:
        max_score += 2
        if gross_margin > 0.60:
            score += 2
            details.append(f"高毛利率暗示强定价权: {gross_margin:.1%}")
        elif gross_margin > 0.40:
            score += 1
            if gross_margin_trend is not None and gross_margin_trend > 0:
                score += 0.5
                details.append(f"毛利率上升中: +{gross_margin_trend:.1%}")
            details.append(f"中等毛利率: {gross_margin:.1%}")

    capex_ratio = safe_float(
        data.get("capex_ratio") or data.get("资本支出比率")
        or data.get("capitalExpenditureRatio")
    )
    asset_turnover = safe_float(
        data.get("asset_turnover") or data.get("资产周转率")
        or data.get("assetTurnover")
    )
    if capex_ratio is not None or asset_turnover is not None:
        max_score += 2
        if capex_ratio is not None and asset_turnover is not None:
            if capex_ratio < 0.05 and asset_turnover > 1.0:
                score += 2
                details.append("轻资产模式, 低资本密度")
            elif capex_ratio < 0.10 or asset_turnover > 0.5:
                score += 1
                details.append("中等资本密度")
        elif capex_ratio is not None and capex_ratio < 0.10:
            score += 1
            details.append("中等资本密度")
        elif asset_turnover is not None and asset_turnover > 0.5:
            score += 1
            details.append("中等资本密度")
    else:
        fcf = safe_float(data.get("free_cash_flow") or data.get("自由现金流"))
        revenue = safe_float(data.get("revenue") or data.get("营收"))
        if fcf is not None and revenue is not None and revenue > 0 and fcf > 0:
            max_score += 2
            fcf_margin = fcf / revenue
            if fcf_margin > 0.20:
                score += 2
                details.append(f"高FCF利润率({fcf_margin:.1%})暗示轻资产")
            elif fcf_margin > 0.10:
                score += 1
                details.append(f"中等FCF利润率: {fcf_margin:.1%}")

    intangible_ratio = safe_float(
        data.get("intangible_ratio") or data.get("无形资产占比")
        or data.get("intangibleAssetsRatio")
    )
    rd_ratio = safe_float(
        data.get("rd_ratio") or data.get("研发费用率")
        or data.get("researchAndDevelopmentRatio") or data.get("R&D比率")
    )
    if intangible_ratio is not None or rd_ratio is not None:
        max_score += 2
        if (intangible_ratio is not None and intangible_ratio > 0.20) or (rd_ratio is not None and rd_ratio > 0.10):
            score += 2
            details.append("显著无形资产/研发投入暗示护城河")
        elif (intangible_ratio is not None and intangible_ratio > 0.05) or (rd_ratio is not None and rd_ratio > 0.03):
            score += 1
            details.append("一定无形资产/研发投入")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_munger_management(data: dict) -> dict:
    max_score = 0
    details = []

    fcf_part = 0
    fcf = safe_float(
        data.get("free_cash_flow") or data.get("自由现金流")
        or data.get("fcf") or data.get("freeCashFlow")
    )
    net_income = safe_float(
        data.get("net_income") or data.get("净利润")
        or data.get("netIncome")
    )
    if fcf is not None and net_income is not None:
        max_score += 3
        if fcf > 0 and net_income > 0:
            fcf_ni_ratio = fcf / net_income
            if fcf_ni_ratio > 1.2:
                fcf_part = 3
                details.append(f"卓越盈利质量: FCF/NI={fcf_ni_ratio:.2f}")
            elif fcf_ni_ratio > 0.9:
                fcf_part = 2
                details.append(f"良好盈利质量: FCF/NI={fcf_ni_ratio:.2f}")
            elif fcf_ni_ratio > 0.6:
                fcf_part = 1
                details.append(f"一般盈利质量: FCF/NI={fcf_ni_ratio:.2f}")
    else:
        roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
        if roe is not None:
            max_score += 1
            if roe > 0.20:
                fcf_part = 1
                details.append(f"高ROE({roe:.1%})部分反映管理效率")

    debt_part_score = 0
    de_ratio = safe_float(
        data.get("debt_to_equity") or data.get("资产负债率")
        or data.get("debt_ratio") or data.get("debtEquityRatio")
    )
    interest_coverage = safe_float(
        data.get("interest_coverage") or data.get("利息覆盖率")
        or data.get("interestCoverageRatio")
    )
    if de_ratio is not None:
        max_score += 3
        if de_ratio < 0.3:
            debt_part_score = 3
            details.append("极低负债, 优秀债务管理")
        elif de_ratio < 0.5:
            debt_part_score = 2
            details.append(f"低负债: {de_ratio:.2f}")
        elif de_ratio < 1.0:
            debt_part_score = 1
            details.append(f"中等负债: {de_ratio:.2f}")

        if interest_coverage is not None and interest_coverage > 10:
            debt_part_score = min(debt_part_score + 0.5, 3)
            details.append(f"利息覆盖率高: {interest_coverage:.1f}x")

    score = fcf_part + debt_part_score

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_predictability(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    op_margin = safe_float(
        data.get("operating_margin") or data.get("营业利润率")
        or data.get("operatingMargin")
    )
    net_margin = safe_float(
        data.get("net_margin") or data.get("净利润率")
        or data.get("netMargin")
    )
    margin_stability = safe_float(
        data.get("margin_stability") or data.get("利润率稳定性")
        or data.get("marginVolatility")
    )

    if margin_stability is not None:
        max_score += 3
        if margin_stability < 0.02:
            score += 3
            details.append("利润率高度稳定")
        elif margin_stability < 0.05:
            score += 2
            details.append("利润率较稳定")
        elif margin_stability < 0.10:
            score += 1
            details.append("利润率波动中等")
    else:
        if op_margin is not None and net_margin is not None:
            max_score += 3
            if op_margin > 0.25 and net_margin > 0.15:
                score += 3
                details.append(f"高且可能稳定的利润率: 营业{op_margin:.1%}, 净{net_margin:.1%}")
            elif op_margin > 0.15 and net_margin > 0.08:
                score += 2
                details.append(f"中等利润率: 营业{op_margin:.1%}, 净{net_margin:.1%}")
            elif op_margin > 0.08:
                score += 1
                details.append(f"一般利润率: 营业{op_margin:.1%}")
        elif op_margin is not None:
            max_score += 1
            if op_margin > 0.15:
                score += 1
                details.append(f"一般利润率: 营业{op_margin:.1%}")

    revenue_stability = safe_float(
        data.get("revenue_stability") or data.get("收入稳定性")
        or data.get("revenueVolatility")
    )
    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
    )
    if revenue_stability is not None:
        max_score += 2
        if revenue_stability < 0.05:
            score += 2
            details.append("收入高度可预测")
        elif revenue_stability < 0.10:
            score += 1
            details.append("收入较可预测")
    elif revenue_growth is not None:
        max_score += 2
        if 0.05 < revenue_growth < 0.20:
            score += 2
            details.append(f"稳健增长暗示可预测: {revenue_growth:.1%}")
        elif revenue_growth > 0:
            score += 1
            details.append(f"正增长: {revenue_growth:.1%}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def munger_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    moat = analyze_moat_strength(data)
    management = analyze_munger_management(data)
    predictability = analyze_predictability(data)

    valuation_score = 0
    valuation_max = 0
    valuation_details = []

    pe_ratio = safe_float(data.get("pe_ratio") or data.get("市盈率") or data.get("P/E"))
    if pe_ratio is not None:
        valuation_max += 2
        if 0 < pe_ratio <= 15:
            valuation_score += 2
            valuation_details.append(f"低PE: {pe_ratio:.1f}")
        elif 15 < pe_ratio <= 25:
            valuation_score += 1
            valuation_details.append(f"合理PE: {pe_ratio:.1f}")

    fcf_yield = safe_float(
        data.get("fcf_yield") or data.get("自由现金流收益率")
        or data.get("freeCashFlowYield")
    )
    if fcf_yield is not None:
        valuation_max += 2
        if fcf_yield > 0.08:
            valuation_score += 2
            valuation_details.append(f"高FCF收益率: {fcf_yield:.1%}")
        elif fcf_yield > 0.04:
            valuation_score += 1
            valuation_details.append(f"中等FCF收益率: {fcf_yield:.1%}")

    roic = safe_float(data.get("ROIC") or data.get("投入资本回报率"))
    wacc = safe_float(data.get("WACC") or data.get("加权平均资本成本"))
    if roic is not None and wacc is not None and roic > 0 and wacc > 0:
        valuation_max += 1
        spread = roic - wacc
        if spread > 0.10:
            valuation_score += 1
            valuation_details.append(f"ROIC-WACC利差大: {spread:.1%}")

    if valuation_max == 0:
        valuation_max = 1

    valuation_analysis = {
        "score": valuation_score,
        "max_score": valuation_max,
        "signal": score_to_signal(valuation_score, valuation_max),
        "details": "; ".join(valuation_details) if valuation_details else "数据不足",
    }

    total_score = moat["score"] + management["score"] + predictability["score"] + valuation_score
    max_score = moat["max_score"] + management["max_score"] + predictability["max_score"] + valuation_max
    evidence_table = []

    roic = safe_float(data.get("ROIC") or data.get("投入资本回报率"))
    if roic is not None:
        evidence_table.append(make_evidence_row(
            "护城河强度",
            "ROIC持续高于资本成本",
            "roic",
            f"{roic:.1%}",
            3 if roic > 0.25 else 2 if roic > 0.15 else 1 if roic > 0.10 else 0,
            3,
            "芒格偏好高回报、可长期复利的企业。"
        ))

    gross_margin = safe_float(
        data.get("gross_margin") or data.get("毛利率")
        or data.get("grossMargin")
    )
    if gross_margin is not None:
        evidence_table.append(make_evidence_row(
            "护城河强度",
            "毛利率体现定价权",
            "gross_margin",
            f"{gross_margin:.1%}",
            2 if gross_margin > 0.60 else 1 if gross_margin > 0.40 else 0,
            2,
            "高毛利通常意味着更强的品牌、渠道或产品壁垒。"
        ))

    fcf = safe_float(
        data.get("free_cash_flow") or data.get("自由现金流")
        or data.get("fcf") or data.get("freeCashFlow")
    )
    net_income = safe_float(
        data.get("net_income") or data.get("净利润")
        or data.get("netIncome")
    )
    if fcf is not None and net_income is not None and net_income > 0:
        fcf_ratio = fcf / net_income
        evidence_table.append(make_evidence_row(
            "管理层评估",
            "现金流兑现盈利",
            "fcf/net_income",
            round(fcf_ratio, 2),
            3 if fcf_ratio > 1.2 else 2 if fcf_ratio > 0.9 else 1 if fcf_ratio > 0.6 else 0,
            3,
            "芒格不接受只停留在报表利润上的经营成果。"
        ))

    debt_ratio = safe_float(
        data.get("debt_to_equity") or data.get("资产负债率")
        or data.get("debt_ratio") or data.get("debtEquityRatio")
    )
    if debt_ratio is not None:
        evidence_table.append(make_evidence_row(
            "管理层评估",
            "债务纪律",
            "debt_ratio",
            round(debt_ratio, 2),
            3 if debt_ratio < 0.3 else 2 if debt_ratio < 0.5 else 1 if debt_ratio < 1.0 else 0,
            3,
            "低杠杆更符合芒格对稳健资本配置的要求。"
        ))

    pe_ratio = safe_float(data.get("pe_ratio") or data.get("市盈率") or data.get("P/E"))
    if pe_ratio is not None:
        evidence_table.append(make_evidence_row(
            "估值分析",
            "价格不能脱离基本面",
            "pe_ratio",
            round(pe_ratio, 2),
            2 if 0 < pe_ratio <= 15 else 1 if pe_ratio <= 25 else 0,
            2,
            "再好的公司也要有合理买入价格。"
        ))

    fcf_yield = safe_float(
        data.get("fcf_yield") or data.get("自由现金流收益率")
        or data.get("freeCashFlowYield")
    )
    if fcf_yield is not None:
        evidence_table.append(make_evidence_row(
            "估值分析",
            "FCF收益率具备吸引力",
            "fcf_yield",
            f"{fcf_yield:.1%}",
            2 if fcf_yield > 0.08 else 1 if fcf_yield > 0.04 else 0,
            2,
            "现金回报率是判断价格是否合理的直接证据。"
        ))

    penalty_severity = str(data.get("regulatory_penalty_severity") or "").strip().lower()
    if penalty_severity:
        penalty_score = 2 if penalty_severity in {"none", "low"} else 1 if penalty_severity == "medium" else 0
        evidence_table.append(make_evidence_row(
            "管理层评估",
            "监管记录约束管理层质量",
            "regulatory_penalty_severity",
            penalty_severity,
            penalty_score,
            2,
            "芒格把品格和理性资本配置放在很高权重，严重处罚会显著减分。"
        ))

    management_alignment = safe_float(data.get("insider_increase_events"))
    insider_decrease = safe_float(data.get("insider_decrease_events"))
    if management_alignment is not None or insider_decrease is not None:
        increase_count = management_alignment or 0.0
        decrease_count = insider_decrease or 0.0
        alignment_score = 1 if increase_count > decrease_count else 0.5 if decrease_count == 0 else 0
        evidence_table.append(make_evidence_row(
            "管理层评估",
            "内部人行为一致性",
            "management_alignment_summary",
            f"increase={increase_count:.0f}, decrease={decrease_count:.0f}",
            alignment_score,
            1,
            "芒格重视管理层是否与长期股东站在同一边。"
        ))

    revenue_guidance_change = safe_float(data.get("earnings_guidance_revenue_change_pct_max"))
    if revenue_guidance_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Business Quality",
                "Revenue Guidance Validation",
                "earnings_guidance_revenue_change_pct_max",
                f"{revenue_guidance_change:.1%}",
                1 if revenue_guidance_change > 0.10 else 0.5 if revenue_guidance_change > 0 else 0,
                1,
                "Forward revenue guidance helps validate whether business quality is still translating into growth.",
            )
        )

    contract_assets_change = safe_float(data.get("contract_assets_to_revenue_change"))
    if contract_assets_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Business Quality",
                "Contract Assets Expansion Risk",
                "contract_assets_to_revenue_change",
                round(contract_assets_change, 2),
                1 if contract_assets_change < 0 else 0.5 if contract_assets_change == 0 else 0,
                1,
                "Rising contract assets can indicate weaker collection discipline or delivery pressure.",
            )
        )

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "护城河强度": moat,
            "管理层评估": management,
            "可预测性": predictability,
            "估值分析": valuation_analysis,
        },
        "evidence_table": evidence_table,
        "details": (
            f"护城河{moat['score']:.1f}/{moat['max_score']:.0f}, "
            f"管理{management['score']:.1f}/{management['max_score']:.0f}, "
            f"可预测性{predictability['score']:.1f}/{predictability['max_score']:.0f}, "
            f"估值{valuation_score:.1f}/{valuation_max:.0f}"
        ),
    }

    result["formatted_summary"] = format_quantitative_summary("芒格", result)
    return result
