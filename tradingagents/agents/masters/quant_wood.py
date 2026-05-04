from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_disruptive_potential(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth")
    )
    revenue_growth_prev = safe_float(
        data.get("revenue_growth_prev") or data.get("上年营收增长率")
        or data.get("revenueGrowthPrevious")
    )
    if revenue_growth is not None:
        max_score += 2
        if revenue_growth > 0.30 and (revenue_growth_prev is not None and revenue_growth > revenue_growth_prev):
            score += 2
            details.append(f"营收加速增长: {revenue_growth:.1%}")
        elif revenue_growth > 0.15:
            score += 1
            details.append(f"高营收增长: {revenue_growth:.1%}")

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
        if gross_margin > 0.60 and (gross_margin_trend is not None and gross_margin_trend > 0):
            score += 2
            details.append(f"高且扩张的毛利率: {gross_margin:.1%}")
        elif gross_margin > 0.40:
            score += 1
            details.append(f"较高毛利率: {gross_margin:.1%}")

    rd_ratio = safe_float(
        data.get("rd_ratio") or data.get("研发费用率")
        or data.get("researchAndDevelopmentRatio") or data.get("R&D比率")
        or data.get("rd_to_revenue")
    )
    if rd_ratio is not None:
        max_score += 3
        if rd_ratio > 0.20:
            score += 3
            details.append(f"极高R&D投入: {rd_ratio:.1%}")
        elif rd_ratio > 0.10:
            score += 2
            details.append(f"高R&D投入: {rd_ratio:.1%}")
        elif rd_ratio > 0.05:
            score += 1
            details.append(f"中等R&D投入: {rd_ratio:.1%}")

    op_margin_trend = safe_float(
        data.get("operating_margin_trend") or data.get("营业利润率趋势")
        or data.get("operatingMarginChange")
    )
    if op_margin_trend is not None and revenue_growth is not None:
        max_score += 2
        if op_margin_trend > 0.05 and revenue_growth > 0.15:
            score += 2
            details.append("显著经营杠杆效应")
        elif op_margin_trend > 0 and revenue_growth > 0.10:
            score += 1
            details.append("经营杠杆初现")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_innovation_growth(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    rd_growth = safe_float(
        data.get("rd_growth") or data.get("研发费用增长率")
        or data.get("researchAndDevelopmentGrowth")
    )
    if rd_growth is not None:
        max_score += 3
        if rd_growth > 0.30:
            score += 3
            details.append(f"R&D高速增长: {rd_growth:.1%}")
        elif rd_growth > 0.15:
            score += 2
            details.append(f"R&D稳健增长: {rd_growth:.1%}")
        elif rd_growth > 0:
            score += 1
            details.append(f"R&D正增长: {rd_growth:.1%}")

    fcf = safe_float(
        data.get("free_cash_flow") or data.get("自由现金流")
        or data.get("fcf") or data.get("freeCashFlow")
    )
    fcf_trend = safe_float(
        data.get("fcf_trend") or data.get("自由现金流趋势")
        or data.get("freeCashFlowChange")
    )
    if fcf is not None or fcf_trend is not None:
        max_score += 3
        if fcf is not None and fcf > 0 and fcf_trend is not None and fcf_trend > 0:
            score += 3
            details.append("FCF正且增长, 拐点确认")
        elif fcf is not None and fcf > 0:
            score += 2
            details.append("FCF已转正")
        elif fcf_trend is not None and fcf_trend > 0:
            score += 1
            details.append("FCF改善中")

    op_margin = safe_float(
        data.get("operating_margin") or data.get("营业利润率")
        or data.get("operatingMargin")
    )
    op_margin_trend = safe_float(
        data.get("operating_margin_trend") or data.get("营业利润率趋势")
        or data.get("operatingMarginChange")
    )
    if op_margin is not None or op_margin_trend is not None:
        max_score += 3
        if op_margin is not None and op_margin > 0 and op_margin_trend is not None and op_margin_trend > 0.03:
            score += 3
            details.append(f"利润率快速改善: {op_margin:.1%}, 趋势+{op_margin_trend:.1%}")
        elif op_margin is not None and op_margin > 0:
            score += 2
            details.append(f"正营业利润率: {op_margin:.1%}")
        elif op_margin_trend is not None and op_margin_trend > 0:
            score += 1
            details.append("利润率改善中")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_wood_valuation(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
    )
    pe_ratio = safe_float(
        data.get("pe_ratio") or data.get("市盈率") or data.get("P/E")
    )
    peg_ratio = safe_float(
        data.get("peg_ratio") or data.get("PEG")
        or data.get("priceToEarningsGrowthRatio")
    )

    if revenue_growth is not None:
        if revenue_growth > 0.30:
            if peg_ratio is not None:
                max_score += 3
                if 0 < peg_ratio < 1.5:
                    score += 3
                    details.append(f"高增长({revenue_growth:.1%})且PEG合理({peg_ratio:.2f})")
                elif 0 < peg_ratio < 2.0:
                    score += 2
                    details.append(f"高增长({revenue_growth:.1%}), PEG可接受({peg_ratio:.2f})")
                else:
                    score += 1
                    details.append(f"高增长但估值偏高: PEG={peg_ratio:.2f}")
        elif revenue_growth > 0.15:
            if peg_ratio is not None:
                max_score += 2
                if 0 < peg_ratio < 1.0:
                    score += 2
                    details.append(f"中高增长且PEG低: {peg_ratio:.2f}")
                elif 0 < peg_ratio < 1.5:
                    score += 1
                    details.append(f"中高增长, PEG合理: {peg_ratio:.2f}")
    if (revenue_growth is None or revenue_growth <= 0.15) and pe_ratio is not None:
        max_score += 1
        if 0 < pe_ratio < 25:
            score += 1
            details.append(f"PE合理: {pe_ratio:.1f}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def wood_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    disruptive = analyze_disruptive_potential(data)
    innovation = analyze_innovation_growth(data)
    valuation = analyze_wood_valuation(data)

    theme_score = 0
    theme_max = 0
    theme_details = []

    rd_ratio = safe_float(
        data.get("rd_ratio") or data.get("研发费用率")
        or data.get("R&D比率")
    )
    if rd_ratio is not None:
        theme_max += 1
        if rd_ratio > 0.15:
            theme_score += 1
            theme_details.append("高研发投入契合创新主题")

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    gross_margin = safe_float(data.get("gross_margin") or data.get("毛利率"))
    if revenue_growth is not None and gross_margin is not None:
        theme_max += 1
        if revenue_growth > 0.30 and gross_margin > 0.50:
            theme_score += 1
            theme_details.append("高增长+高毛利暗示平台/网络效应")

    user_growth = safe_float(
        data.get("user_growth") or data.get("用户增长率")
        or data.get("subscriber_growth") or data.get("订阅者增长率")
    )
    if user_growth is not None:
        theme_max += 1
        if user_growth > 0.20:
            theme_score += 1
            theme_details.append(f"用户高增长: {user_growth:.1%}")

    tam_growth = safe_float(
        data.get("tam_growth") or data.get("市场空间增长率")
        or data.get("totalAddressableMarketGrowth")
    )
    if tam_growth is not None:
        theme_max += 1
        if tam_growth > 0.15:
            theme_score += 1
            theme_details.append(f"TAM快速扩张: {tam_growth:.1%}")

    if theme_max == 0:
        theme_max = 1

    theme_analysis = {
        "score": theme_score,
        "max_score": theme_max,
        "signal": score_to_signal(theme_score, theme_max),
        "details": "; ".join(theme_details) if theme_details else "数据不足",
    }

    total_score = disruptive["score"] + innovation["score"] + valuation["score"] + theme_score
    max_score = disruptive["max_score"] + innovation["max_score"] + valuation["max_score"] + theme_max
    evidence_table = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth")
    )
    if revenue_growth is not None:
        evidence_table.append(make_evidence_row("颠覆性潜力", "高增长验证赛道爆发力", "revenue_growth", f"{revenue_growth:.1%}", 2 if revenue_growth > 0.30 else 1 if revenue_growth > 0.15 else 0, 2, "木头姐优先关注能够打破旧产业均衡的高成长公司。"))

    gross_margin = safe_float(
        data.get("gross_margin") or data.get("毛利率")
        or data.get("grossMargin")
    )
    if gross_margin is not None:
        evidence_table.append(make_evidence_row("颠覆性潜力", "高毛利支撑平台型商业模式", "gross_margin", f"{gross_margin:.1%}", 2 if gross_margin > 0.60 else 1 if gross_margin > 0.40 else 0, 2, "高毛利通常意味着软件化、平台化或强产品差异化。"))

    rd_ratio = safe_float(
        data.get("rd_ratio") or data.get("研发费用率")
        or data.get("researchAndDevelopmentRatio") or data.get("rd_to_revenue")
    )
    if rd_ratio is not None:
        evidence_table.append(make_evidence_row("创新增长", "研发投入强度", "rd_ratio", f"{rd_ratio:.1%}", 3 if rd_ratio > 0.20 else 2 if rd_ratio > 0.10 else 1 if rd_ratio > 0.05 else 0, 3, "木头姐把持续高研发视为颠覆式创新的核心前提。"))

    peg_ratio = safe_float(
        data.get("peg_ratio") or data.get("PEG")
        or data.get("priceToEarningsGrowthRatio")
    )
    if peg_ratio is not None and peg_ratio > 0:
        evidence_table.append(make_evidence_row("估值分析", "高增长下估值可承受性", "peg_ratio", round(peg_ratio, 2), 3 if peg_ratio < 1.5 and (revenue_growth or 0) > 0.30 else 2 if peg_ratio < 2.0 and (revenue_growth or 0) > 0.30 else 1 if peg_ratio < 1.5 else 0, 3, "即使押注创新，木头姐也会关注增长能否覆盖当前定价。"))

    user_growth = safe_float(
        data.get("user_growth") or data.get("用户增长率")
        or data.get("subscriber_growth") or data.get("订阅者增长率")
    )
    if user_growth is not None:
        evidence_table.append(make_evidence_row("主题契合度", "用户扩张验证网络效应", "user_growth", f"{user_growth:.1%}", 1 if user_growth > 0.20 else 0, 1, "创新主题需要用户侧快速扩张来证明渗透率提升。"))

    revenue_guidance_change = safe_float(data.get("earnings_guidance_revenue_change_pct_max"))
    if revenue_guidance_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Innovation Growth",
                "Revenue Guidance Acceleration",
                "earnings_guidance_revenue_change_pct_max",
                f"{revenue_guidance_change:.1%}",
                1 if revenue_guidance_change > 0.20 else 0.5 if revenue_guidance_change > 0.10 else 0,
                1,
                "Forward revenue guidance is a direct signal for whether the disruptive growth thesis is still accelerating.",
            )
        )

    contract_liabilities_change = safe_float(data.get("contract_liabilities_to_revenue_change"))
    if contract_liabilities_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Innovation Growth",
                "Order Pipeline Support",
                "contract_liabilities_to_revenue_change",
                round(contract_liabilities_change, 2),
                1 if contract_liabilities_change > 0 else 0.5 if contract_liabilities_change == 0 else 0,
                1,
                "Rising contract liabilities can indicate stronger advance orders behind the growth narrative.",
            )
        )

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "颠覆性潜力": disruptive,
            "创新增长": innovation,
            "估值分析": valuation,
            "主题契合度": theme_analysis,
        },
        "evidence_table": evidence_table,
        "details": (
            f"颠覆性{disruptive['score']:.1f}/{disruptive['max_score']:.0f}, "
            f"创新{innovation['score']:.1f}/{innovation['max_score']:.0f}, "
            f"估值{valuation['score']:.1f}/{valuation['max_score']:.0f}, "
            f"主题{theme_score:.1f}/{theme_max:.0f}"
        ),
    }

    result["formatted_summary"] = format_quantitative_summary("伍德", result)
    return result
