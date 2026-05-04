from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_growth_momentum(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth")
    )
    if revenue_growth is not None:
        max_score += 3
        if revenue_growth > 0.30:
            score += 3
            details.append(f"强劲营收增长: {revenue_growth:.1%}")
        elif revenue_growth > 0.15:
            score += 2
            details.append(f"稳健营收增长: {revenue_growth:.1%}")
        elif revenue_growth > 0.05:
            score += 1
            details.append(f"温和营收增长: {revenue_growth:.1%}")

    eps_growth = safe_float(
        data.get("eps_growth") or data.get("EPS增长率")
        or data.get("earnings_growth") or data.get("净利润增长率")
    )
    if eps_growth is not None:
        max_score += 3
        if eps_growth > 0.30:
            score += 3
            details.append(f"强劲EPS增长: {eps_growth:.1%}")
        elif eps_growth > 0.15:
            score += 2
            details.append(f"稳健EPS增长: {eps_growth:.1%}")
        elif eps_growth > 0.05:
            score += 1
            details.append(f"温和EPS增长: {eps_growth:.1%}")

    price_momentum_3m = safe_float(
        data.get("price_momentum_3m") or data.get("3个月动量")
        or data.get("priceChange3Month") or data.get("price_momentum")
    )
    price_momentum_6m = safe_float(
        data.get("price_momentum_6m") or data.get("6个月动量")
        or data.get("priceChange6Month")
    )
    price_momentum_12m = safe_float(
        data.get("price_momentum_12m") or data.get("12个月动量")
        or data.get("priceChange12Month") or data.get("price_change_ytd")
    )

    has_momentum_data = price_momentum_3m is not None or price_momentum_6m is not None or price_momentum_12m is not None
    if has_momentum_data:
        max_score += 3
        momentum_signals = 0
        if price_momentum_3m is not None and price_momentum_3m > 0.05:
            momentum_signals += 1
        if price_momentum_6m is not None and price_momentum_6m > 0.10:
            momentum_signals += 1
        if price_momentum_12m is not None and price_momentum_12m > 0.15:
            momentum_signals += 1

        if momentum_signals >= 3:
            score += 3
            m3 = f"+{price_momentum_3m:.1%}" if price_momentum_3m is not None else "N/A"
            m6 = f"+{price_momentum_6m:.1%}" if price_momentum_6m is not None else "N/A"
            m12 = f"+{price_momentum_12m:.1%}" if price_momentum_12m is not None else "N/A"
            details.append(f"强价格动量: 3M{m3}, 6M{m6}, 12M{m12}")
        elif momentum_signals >= 2:
            score += 2
            details.append("中等价格动量")
        elif momentum_signals >= 1:
            score += 1
            details.append("弱价格动量")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_risk_reward(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    de_ratio = safe_float(
        data.get("debt_to_equity") or data.get("资产负债率")
        or data.get("debt_ratio") or data.get("debtEquityRatio")
    )
    if de_ratio is not None:
        max_score += 3
        if de_ratio < 0.3:
            score += 3
            details.append("极低负债, 下行风险有限")
        elif de_ratio < 0.5:
            score += 2
            details.append(f"低负债: {de_ratio:.2f}")
        elif de_ratio < 1.0:
            score += 1
            details.append(f"中等负债: {de_ratio:.2f}")

    beta = safe_float(
        data.get("beta") or data.get("贝塔系数")
        or data.get("betaCoefficient")
    )
    volatility = safe_float(
        data.get("volatility") or data.get("波动率")
        or data.get("historicalVolatility")
    )

    if beta is not None:
        max_score += 3
        if beta < 0.8:
            score += 3
            details.append(f"低Beta: {beta:.2f}, 风险可控")
        elif beta < 1.2:
            score += 2
            details.append(f"中等Beta: {beta:.2f}")
        elif beta < 1.5:
            score += 1
            details.append(f"较高Beta: {beta:.2f}")
    elif volatility is not None:
        max_score += 3
        if volatility < 0.15:
            score += 3
            details.append(f"低波动率: {volatility:.1%}")
        elif volatility < 0.25:
            score += 2
            details.append(f"中等波动率: {volatility:.1%}")
        elif volatility < 0.40:
            score += 1
            details.append(f"较高波动率: {volatility:.1%}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_druckenmiller_valuation(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    pe_ratio = safe_float(
        data.get("pe_ratio") or data.get("市盈率")
        or data.get("priceToEarningsRatio") or data.get("P/E")
    )
    if pe_ratio is not None:
        max_score += 2
        if 0 < pe_ratio <= 15:
            score += 2
            details.append(f"低PE: {pe_ratio:.1f}")
        elif 15 < pe_ratio <= 25:
            score += 1
            details.append(f"合理PE: {pe_ratio:.1f}")

    p_fcf = safe_float(
        data.get("p_fcf") or data.get("市现率")
        or data.get("priceToFreeCashFlow") or data.get("P/FCF")
    )
    if p_fcf is not None:
        if p_fcf > 0:
            max_score += 2
            if p_fcf <= 15:
                score += 2
                details.append(f"低P/FCF: {p_fcf:.1f}")
            elif p_fcf <= 25:
                score += 1
                details.append(f"合理P/FCF: {p_fcf:.1f}")
    else:
        fcf_yield = safe_float(
            data.get("fcf_yield") or data.get("自由现金流收益率")
            or data.get("freeCashFlowYield")
        )
        if fcf_yield is not None:
            max_score += 2
            if fcf_yield > 0.08:
                score += 2
                details.append(f"高FCF收益率: {fcf_yield:.1%}")
            elif fcf_yield > 0.04:
                score += 1
                details.append(f"中等FCF收益率: {fcf_yield:.1%}")

    ev_ebitda = safe_float(
        data.get("ev_ebitda") or data.get("企业价值倍数")
        or data.get("evToEbitda") or data.get("EV/EBITDA")
    )
    if ev_ebitda is not None:
        if ev_ebitda > 0:
            max_score += 2
            if ev_ebitda <= 8:
                score += 2
                details.append(f"低EV/EBITDA: {ev_ebitda:.1f}")
            elif ev_ebitda <= 12:
                score += 1
                details.append(f"合理EV/EBITDA: {ev_ebitda:.1f}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def druckenmiller_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    growth_momentum = analyze_growth_momentum(data)
    risk_reward = analyze_risk_reward(data)
    valuation = analyze_druckenmiller_valuation(data)

    other_score = 0
    other_max = 0
    other_details = []

    earnings_surprise = safe_float(
        data.get("earnings_surprise") or data.get("盈利惊喜")
        or data.get("earningsSurprise")
    )
    if earnings_surprise is not None:
        other_max += 1
        if earnings_surprise > 0.10:
            other_score += 1
            other_details.append(f"大幅超预期: +{earnings_surprise:.1%}")
        elif earnings_surprise > 0:
            other_score += 0.5
            other_details.append("小幅超预期")

    analyst_revisions = safe_float(
        data.get("analyst_revisions") or data.get("分析师调整")
        or data.get("estimateRevisions")
    )
    if analyst_revisions is not None:
        other_max += 1
        if analyst_revisions > 0.10:
            other_score += 1
            other_details.append("分析师上调")
        elif analyst_revisions > 0:
            other_score += 0.5

    inst_flow = safe_float(
        data.get("institutional_flow") or data.get("机构资金流")
        or data.get("institutionalOwnershipChange")
    )
    if inst_flow is not None:
        other_max += 1
        if inst_flow > 0.05:
            other_score += 1
            other_details.append("机构资金流入")
        elif inst_flow > 0:
            other_score += 0.5

    relative_strength = safe_float(
        data.get("relative_strength") or data.get("相对强度")
        or data.get("relativeStrengthIndex")
    )
    if relative_strength is not None:
        other_max += 1
        if relative_strength > 0.70:
            other_score += 1
            other_details.append("行业相对强度高")
        elif relative_strength > 0.50:
            other_score += 0.5

    eps_growth = safe_float(data.get("eps_growth") or data.get("EPS增长率"))
    eps_growth_prev = safe_float(
        data.get("eps_growth_prev") or data.get("上年EPS增长率")
    )
    if eps_growth is not None and eps_growth_prev is not None:
        other_max += 1
        if eps_growth > eps_growth_prev and eps_growth > 0.10:
            other_score += 1
            other_details.append("EPS增长加速")

    other_score = min(other_score, other_max) if other_max > 0 else other_score
    if other_max == 0:
        other_max = 1

    other_analysis = {
        "score": other_score,
        "max_score": other_max,
        "signal": score_to_signal(other_score, other_max),
        "details": "; ".join(other_details) if other_details else "数据不足",
    }

    total_score = growth_momentum["score"] + risk_reward["score"] + valuation["score"] + other_score
    max_score = growth_momentum["max_score"] + risk_reward["max_score"] + valuation["max_score"] + other_max
    evidence_table = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth")
    )
    if revenue_growth is not None:
        evidence_table.append(make_evidence_row("增长动量", "营收增长动量", "revenue_growth", f"{revenue_growth:.1%}", 3 if revenue_growth > 0.30 else 2 if revenue_growth > 0.15 else 1 if revenue_growth > 0.05 else 0, 3, "德鲁肯米勒先看基本面加速是否成立。"))

    price_momentum_6m = safe_float(
        data.get("price_momentum_6m") or data.get("6个月动量")
        or data.get("priceChange6Month")
    )
    if price_momentum_6m is not None:
        evidence_table.append(make_evidence_row("增长动量", "价格确认趋势", "price_momentum_6m", f"{price_momentum_6m:.1%}", 1 if price_momentum_6m > 0.10 else 0, 1, "趋势交易需要价格与基本面同向验证。"))

    debt_ratio = safe_float(
        data.get("debt_to_equity") or data.get("资产负债率")
        or data.get("debt_ratio") or data.get("debtEquityRatio")
    )
    if debt_ratio is not None:
        evidence_table.append(make_evidence_row("风险回报", "低杠杆控制下行", "debt_ratio", round(debt_ratio, 2), 3 if debt_ratio < 0.3 else 2 if debt_ratio < 0.5 else 1 if debt_ratio < 1.0 else 0, 3, "德鲁肯米勒强调赔率优先，先管住下行风险。"))

    pe_ratio = safe_float(
        data.get("pe_ratio") or data.get("市盈率")
        or data.get("priceToEarningsRatio") or data.get("P/E")
    )
    if pe_ratio is not None:
        evidence_table.append(make_evidence_row("估值分析", "估值不能抵消趋势收益", "pe_ratio", round(pe_ratio, 2), 2 if 0 < pe_ratio <= 15 else 1 if pe_ratio <= 25 else 0, 2, "即使做趋势，也不愿为过高估值买单。"))

    analyst_revisions = safe_float(
        data.get("analyst_revisions") or data.get("分析师调整")
        or data.get("estimateRevisions")
    )
    if analyst_revisions is not None:
        evidence_table.append(make_evidence_row("宏观趋势", "盈利预期上修", "analyst_revisions", f"{analyst_revisions:.1%}", 1 if analyst_revisions > 0.10 else 0.5 if analyst_revisions > 0 else 0, 1, "预期上修通常是趋势持续的重要催化剂。"))

    guidance_max = safe_float(data.get("earnings_guidance_change_pct_max"))
    guidance_min = safe_float(data.get("earnings_guidance_change_pct_min"))
    if guidance_max is not None or guidance_min is not None:
        observed = f"{guidance_min if guidance_min is not None else 'N/A'}~{guidance_max if guidance_max is not None else 'N/A'}%"
        guidance_score = 2 if (guidance_max or 0) >= 20 else 1 if (guidance_max or 0) > 0 else 0
        evidence_table.append(make_evidence_row("宏观趋势", "业绩预告催化", "earnings_guidance_change_pct_max", observed, guidance_score, 2, "德鲁肯米勒看重基本面加速带来的趋势催化。"))

    penalty_severity = str(data.get("regulatory_penalty_severity") or "").strip().lower()
    if penalty_severity:
        penalty_score = 1 if penalty_severity in {"none", "low"} else 0.5 if penalty_severity == "medium" else 0
        evidence_table.append(make_evidence_row("风险回报", "监管风险折价", "regulatory_penalty_severity", penalty_severity, penalty_score, 1, "监管风险会破坏趋势赔率，必须纳入下行约束。"))

    revenue_guidance_change = safe_float(data.get("earnings_guidance_revenue_change_pct_max"))
    if revenue_guidance_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Catalyst",
                "Revenue Guidance Catalyst",
                "earnings_guidance_revenue_change_pct_max",
                f"{revenue_guidance_change:.1%}",
                1 if revenue_guidance_change > 0.10 else 0.5 if revenue_guidance_change > 0 else 0,
                1,
                "Forward revenue guidance can act as a near-term catalyst for trend-following growth trades.",
            )
        )

    contract_liabilities_change = safe_float(data.get("contract_liabilities_to_revenue_change"))
    if contract_liabilities_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Catalyst",
                "Order Intake Support",
                "contract_liabilities_to_revenue_change",
                round(contract_liabilities_change, 2),
                1 if contract_liabilities_change > 0 else 0.5 if contract_liabilities_change == 0 else 0,
                1,
                "Rising contract liabilities can support the case that demand momentum is being converted into orders.",
            )
        )

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "增长动量": growth_momentum,
            "风险回报": risk_reward,
            "估值分析": valuation,
            "宏观趋势": other_analysis,
        },
        "evidence_table": evidence_table,
        "details": (
            f"动量{growth_momentum['score']:.1f}/{growth_momentum['max_score']:.0f}, "
            f"风险{risk_reward['score']:.1f}/{risk_reward['max_score']:.0f}, "
            f"估值{valuation['score']:.1f}/{valuation['max_score']:.0f}, "
            f"其他{other_score:.1f}/{other_max:.0f}"
        ),
    }

    result["formatted_summary"] = format_quantitative_summary("德鲁肯米勒", result)
    return result
