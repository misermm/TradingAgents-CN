from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_lynch_growth(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth") or data.get("revenue_growth_rate")
    )
    if revenue_growth is not None:
        max_score += 3
        if revenue_growth > 0.30:
            score += 3
            details.append(f"高速营收增长: {revenue_growth:.1%}")
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
            details.append(f"高速EPS增长: {eps_growth:.1%}")
        elif eps_growth > 0.15:
            score += 2
            details.append(f"稳健EPS增长: {eps_growth:.1%}")
        elif eps_growth > 0.05:
            score += 1
            details.append(f"温和EPS增长: {eps_growth:.1%}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_lynch_fundamentals(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    de_ratio = safe_float(
        data.get("debt_to_equity") or data.get("资产负债率")
        or data.get("debt_ratio") or data.get("debtEquityRatio")
    )
    if de_ratio is not None:
        max_score += 2
        if de_ratio < 0.5:
            score += 2
            details.append("低负债水平")
        elif de_ratio < 1.0:
            score += 1
            details.append(f"中等负债: {de_ratio:.2f}")

    op_margin = safe_float(
        data.get("operating_margin") or data.get("营业利润率")
        or data.get("operatingMargin")
    )
    if op_margin is not None:
        max_score += 2
        if op_margin > 0.15:
            score += 2
            details.append(f"强营业利润率: {op_margin:.1%}")
        elif op_margin > 0.08:
            score += 1
            details.append(f"中等利润率: {op_margin:.1%}")

    fcf = safe_float(
        data.get("free_cash_flow") or data.get("自由现金流")
        or data.get("fcf") or data.get("freeCashFlow")
    )
    fcf_per_share = safe_float(
        data.get("fcf_per_share") or data.get("每股自由现金流")
        or data.get("freeCashFlowPerShare")
    )
    if fcf is not None or fcf_per_share is not None:
        max_score += 2
        if (fcf is not None and fcf > 0) or (fcf_per_share is not None and fcf_per_share > 0):
            score += 2
            details.append("正自由现金流")
        elif fcf is not None and fcf == 0 and fcf_per_share is not None and fcf_per_share == 0:
            ocf = safe_float(data.get("operating_cash_flow") or data.get("经营现金流"))
            capex = safe_float(data.get("capital_expenditure") or data.get("资本支出"))
            if ocf is not None and capex is not None:
                if ocf > 0 and capex > 0 and (ocf - capex) > 0:
                    score += 2
                    details.append("推算正自由现金流")
                elif ocf > 0:
                    score += 1
                    details.append("正经营现金流")
            elif ocf is not None and ocf > 0:
                score += 1
                details.append("正经营现金流")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_lynch_valuation(data: dict) -> dict:
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

    peg_ratio = safe_float(
        data.get("peg_ratio") or data.get("PEG")
        or data.get("priceToEarningsGrowthRatio") or data.get("PEG比率")
    )
    if peg_ratio is not None:
        if peg_ratio > 0:
            max_score += 3
            if peg_ratio < 0.5:
                score += 3
                details.append(f"极低PEG: {peg_ratio:.2f}, 严重低估")
            elif peg_ratio < 1.0:
                score += 2
                details.append(f"PEG<1: {peg_ratio:.2f}, 低估")
            elif peg_ratio < 1.5:
                score += 1
                details.append(f"合理PEG: {peg_ratio:.2f}")
    if peg_ratio is None or peg_ratio <= 0:
        if pe_ratio is not None and pe_ratio > 0:
            eps_growth = safe_float(
                data.get("eps_growth") or data.get("EPS增长率")
                or data.get("earnings_growth")
            )
            if eps_growth is not None and eps_growth > 0:
                max_score += 2
                calc_peg = pe_ratio / (eps_growth * 100)
                if calc_peg < 1.0:
                    score += 2
                    details.append(f"推算PEG<1: {calc_peg:.2f}")
                elif calc_peg < 1.5:
                    score += 1
                    details.append(f"推算合理PEG: {calc_peg:.2f}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def lynch_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    growth = analyze_lynch_growth(data)
    fundamentals = analyze_lynch_fundamentals(data)
    valuation = analyze_lynch_valuation(data)

    growth_weight = 0.30
    valuation_weight = 0.25
    fundamentals_weight = 0.20
    other_weight = 0.25

    other_score = 0
    other_max = 0
    peg_ratio = safe_float(
        data.get("peg_ratio") or data.get("PEG")
        or data.get("priceToEarningsGrowthRatio")
    )
    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
    )
    if peg_ratio is not None and revenue_growth is not None:
        other_max += 2
        if 0 < peg_ratio < 1.0 and revenue_growth > 0.10:
            other_score += 2
        elif peg_ratio < 1.5 and revenue_growth > 0.05:
            other_score += 1

    dividend_growth = safe_float(
        data.get("dividend_growth") or data.get("股息增长率")
    )
    if dividend_growth is not None:
        other_max += 1
        if dividend_growth > 0.10:
            other_score += 1
        elif dividend_growth > 0:
            other_score += 0.5

    inst_ownership = safe_float(
        data.get("institutional_ownership") or data.get("机构持仓比例")
    )
    if inst_ownership is not None:
        other_max += 1
        if 0 < inst_ownership < 0.30:
            other_score += 1
        elif inst_ownership < 0.50:
            other_score += 0.5

    if other_max == 0:
        other_max = 1

    other_analysis = {
        "score": other_score,
        "max_score": other_max,
        "signal": score_to_signal(other_score, other_max),
        "details": f"PEG调整: {other_score:.1f}/{other_max}",
    }

    weighted_score = (
        growth["score"] * growth_weight
        + valuation["score"] * valuation_weight
        + fundamentals["score"] * fundamentals_weight
        + other_score * other_weight
    )
    weighted_max = (
        growth["max_score"] * growth_weight
        + valuation["max_score"] * valuation_weight
        + fundamentals["max_score"] * fundamentals_weight
        + other_max * other_weight
    )

    total_score = growth["score"] + fundamentals["score"] + valuation["score"] + other_score
    max_score = growth["max_score"] + fundamentals["max_score"] + valuation["max_score"] + other_max

    weighted_signal = score_to_signal(weighted_score, weighted_max) if weighted_max > 0 else "neutral"
    evidence_table = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth") or data.get("revenue_growth_rate")
    )
    if revenue_growth is not None:
        evidence_table.append(make_evidence_row("增长分析", "收入增长速度", "revenue_growth", f"{revenue_growth:.1%}", 3 if revenue_growth > 0.30 else 2 if revenue_growth > 0.15 else 1 if revenue_growth > 0.05 else 0, 3, "林奇偏好能持续扩张的成长股。"))

    eps_growth = safe_float(
        data.get("eps_growth") or data.get("EPS增长率")
        or data.get("earnings_growth") or data.get("净利润增长率")
    )
    if eps_growth is not None:
        evidence_table.append(make_evidence_row("增长分析", "盈利增长速度", "eps_growth", f"{eps_growth:.1%}", 3 if eps_growth > 0.30 else 2 if eps_growth > 0.15 else 1 if eps_growth > 0.05 else 0, 3, "盈利增长比故事更重要。"))

    debt_ratio = safe_float(
        data.get("debt_to_equity") or data.get("资产负债率")
        or data.get("debt_ratio") or data.get("debtEquityRatio")
    )
    if debt_ratio is not None:
        evidence_table.append(make_evidence_row("基本面分析", "低负债保障成长", "debt_ratio", round(debt_ratio, 2), 2 if debt_ratio < 0.5 else 1 if debt_ratio < 1.0 else 0, 2, "林奇不希望杠杆吞掉成长带来的回报。"))

    peg_ratio = safe_float(
        data.get("peg_ratio") or data.get("PEG")
        or data.get("priceToEarningsGrowthRatio") or data.get("PEG比率")
    )
    if peg_ratio is not None and peg_ratio > 0:
        evidence_table.append(make_evidence_row("估值分析", "PEG 衡量成长价格比", "peg_ratio", round(peg_ratio, 2), 3 if peg_ratio < 0.5 else 2 if peg_ratio < 1.0 else 1 if peg_ratio < 1.5 else 0, 3, "PEG 是林奇最核心的定价约束。"))

    inst_ownership = safe_float(
        data.get("institutional_ownership") or data.get("机构持仓比例")
    )
    if inst_ownership is not None:
        evidence_table.append(make_evidence_row("PEG调整", "机构持仓拥挤度", "institutional_ownership", f"{inst_ownership:.1%}", 1 if 0 < inst_ownership < 0.30 else 0.5 if inst_ownership < 0.50 else 0, 1, "林奇喜欢尚未完全被机构挖掘的公司。"))

    guidance_max = safe_float(data.get("earnings_guidance_change_pct_max"))
    guidance_min = safe_float(data.get("earnings_guidance_change_pct_min"))
    if guidance_max is not None or guidance_min is not None:
        observed = f"{guidance_min if guidance_min is not None else 'N/A'}~{guidance_max if guidance_max is not None else 'N/A'}%"
        guidance_score = 2 if (guidance_max or 0) >= 20 else 1 if (guidance_max or 0) > 0 else 0
        evidence_table.append(make_evidence_row("增长分析", "业绩预告确认成长", "earnings_guidance_change_pct_max", observed, guidance_score, 2, "林奇偏好能持续兑现成长预期的公司。"))

    revenue_guidance_change = safe_float(data.get("earnings_guidance_revenue_change_pct_max"))
    if revenue_guidance_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Growth",
                "Revenue Guidance Confirmation",
                "earnings_guidance_revenue_change_pct_max",
                f"{revenue_guidance_change:.1%}",
                1 if revenue_guidance_change > 0.10 else 0.5 if revenue_guidance_change > 0 else 0,
                1,
                "Lynch-style growth investing benefits when forward revenue guidance confirms the growth story.",
            )
        )

    accounts_payable_change = safe_float(data.get("accounts_payable_to_revenue_change"))
    if accounts_payable_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Working Capital",
                "Supplier Financing Pressure",
                "accounts_payable_to_revenue_change",
                round(accounts_payable_change, 2),
                1 if accounts_payable_change <= 0 else 0.5 if accounts_payable_change <= 2 else 0,
                1,
                "A sharp rise in payables versus revenue can indicate pressure on operating quality.",
            )
        )

    result = {
        "signal": weighted_signal,
        "score": total_score,
        "max_score": max_score,
        "weighted_score": round(weighted_score, 2),
        "weighted_max": round(weighted_max, 2),
        "sub_analyses": {
            "增长分析": growth,
            "基本面分析": fundamentals,
            "估值分析": valuation,
            "PEG调整": other_analysis,
        },
        "evidence_table": evidence_table,
        "details": (
            f"增长{growth['score']:.1f}/{growth['max_score']:.0f}, "
            f"估值{valuation['score']:.1f}/{valuation['max_score']:.0f}, "
            f"基本面{fundamentals['score']:.1f}/{fundamentals['max_score']:.0f}, "
            f"其他{other_score:.1f}/{other_max:.0f}"
        ),
    }

    result["formatted_summary"] = format_quantitative_summary("林奇", result)
    return result
