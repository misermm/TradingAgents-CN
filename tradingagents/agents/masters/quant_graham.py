from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_earnings_stability(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    eps_positive_years = safe_float(
        data.get("eps_positive_years") or data.get("EPS正年份")
        or data.get("profitable_years") or data.get("盈利年数")
    )
    total_years = safe_float(
        data.get("total_years") or data.get("总年数")
        or data.get("years_examined"), default=10
    )
    if eps_positive_years is not None:
        max_score += 3
        if total_years > 0 and eps_positive_years > 0:
            positive_ratio = eps_positive_years / total_years
            if positive_ratio >= 0.9:
                score += 3
                details.append(f"EPS正年份占比{positive_ratio:.0%}, 高度稳定")
            elif positive_ratio >= 0.7:
                score += 2
                details.append(f"EPS正年份占比{positive_ratio:.0%}, 较稳定")
            elif positive_ratio >= 0.5:
                score += 1
                details.append(f"EPS正年份占比{positive_ratio:.0%}, 一般")
    else:
        net_margin = safe_float(
            data.get("net_margin") or data.get("净利润率")
            or data.get("netMargin")
        )
        if net_margin is not None:
            max_score += 2
            if net_margin > 0.10:
                score += 2
                details.append(f"高净利润率({net_margin:.1%})暗示稳定盈利")
            elif net_margin > 0:
                score += 1
                details.append("正净利润率")

    eps_growth = safe_float(
        data.get("eps_growth") or data.get("EPS增长率")
        or data.get("earnings_growth") or data.get("净利润增长率")
    )
    if eps_growth is not None:
        max_score += 1
        if eps_growth > 0.033:
            score += 1
            details.append(f"EPS增长达标: {eps_growth:.1%}")
        elif eps_growth > 0:
            score += 0.5
            details.append(f"EPS小幅增长: {eps_growth:.1%}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_financial_strength(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    current_ratio = safe_float(
        data.get("current_ratio") or data.get("流动比率")
        or data.get("currentRatio")
    )
    if current_ratio is not None:
        max_score += 2
        if current_ratio >= 2.0:
            score += 2
            details.append(f"强流动比率: {current_ratio:.2f}")
        elif current_ratio >= 1.5:
            score += 1
            details.append(f"中等流动比率: {current_ratio:.2f}")

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

    dividend_yield = safe_float(
        data.get("dividend_yield") or data.get("股息率")
        or data.get("dividendYield")
    )
    dividend_years = safe_float(
        data.get("dividend_years") or data.get("分红年数")
        or data.get("consecutive_dividend_years")
    )
    if dividend_years is not None:
        max_score += 1
        if dividend_years >= 20:
            score += 1
            details.append(f"长期分红记录: {dividend_years:.0f}年")
        elif dividend_years >= 10:
            score += 0.5
            details.append(f"持续分红: {dividend_years:.0f}年")
        elif dividend_yield is not None and dividend_yield > 0:
            score += 0.5
            details.append(f"有分红: {dividend_yield:.1%}")
    elif dividend_yield is not None:
        max_score += 1
        if dividend_yield > 0:
            score += 0.5
            details.append(f"有分红: {dividend_yield:.1%}")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_graham_valuation(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    current_assets = safe_float(
        data.get("current_assets") or data.get("流动资产")
        or data.get("totalCurrentAssets")
    )
    total_liabilities = safe_float(
        data.get("total_liabilities") or data.get("总负债")
        or data.get("totalLiabilities")
    )
    market_cap = safe_float(
        data.get("market_cap") or data.get("市值")
        or data.get("marketCapitalization")
    )

    if current_assets is not None and total_liabilities is not None:
        net_current_assets = current_assets - total_liabilities
        if market_cap is not None and market_cap > 0:
            max_score += 4
            net_current_ratio = net_current_assets / market_cap
            if net_current_ratio > 1.0:
                score += 4
                details.append(f"Net-Net深度折价: 流动资产-负债/市值={net_current_ratio:.2f}")
            elif net_current_ratio > 0.66:
                score += 3
                details.append(f"Net-Net显著折价: {net_current_ratio:.2f}")
            elif net_current_ratio > 0.33:
                score += 2
                details.append(f"Net-Net轻度折价: {net_current_ratio:.2f}")
            elif net_current_ratio > 0:
                score += 1
                details.append(f"Net-Net接近: {net_current_ratio:.2f}")
        elif net_current_assets > 0:
            max_score += 2
            score += 2
            details.append("正净流动资产")

    eps = safe_float(
        data.get("eps") or data.get("EPS") or data.get("每股收益")
        or data.get("earningsPerShare")
    )
    bvps = safe_float(
        data.get("book_value_per_share") or data.get("每股净资产")
        or data.get("bookValuePerShare") or data.get("bvps")
    )
    price = safe_float(
        data.get("price") or data.get("股价") or data.get("current_price")
    )

    if eps is not None and bvps is not None and eps > 0 and bvps > 0:
        graham_number = (22.5 * eps * bvps) ** 0.5
        if price is not None and price > 0:
            max_score += 3
            graham_ratio = graham_number / price
            if graham_ratio > 1.5:
                score += 3
                details.append(f"Graham Number深度低估: {graham_number:.2f}/价格{price:.2f}")
            elif graham_ratio > 1.0:
                score += 2
                details.append(f"Graham Number低估: {graham_number:.2f}/价格{price:.2f}")
            elif graham_ratio > 0.67:
                score += 1
                details.append(f"Graham Number接近: {graham_number:.2f}/价格{price:.2f}")
        else:
            details.append(f"Graham Number: {graham_number:.2f}")

        eps_growth = safe_float(
            data.get("eps_growth") or data.get("EPS增长率")
            or data.get("earnings_growth") or data.get("净利润增长率")
        )
        bond_yield = safe_float(data.get("bond_yield") or data.get("国债收益率"), default=4.4)
        if eps_growth is not None and eps_growth > 0 and bond_yield > 0:
            graham_value = eps * (8.5 + 2 * min(eps_growth * 100, 25)) * 4.4 / bond_yield
            if price is not None and price > 0:
                max_score += 3
                value_ratio = graham_value / price
                if value_ratio > 1.5:
                    score += 3
                    details.append(f"格雷厄姆公式深度低估: V={graham_value:.2f}/价格{price:.2f}")
                elif value_ratio > 1.0:
                    score += 2
                    details.append(f"格雷厄姆公式低估: V={graham_value:.2f}/价格{price:.2f}")
                elif value_ratio > 0.67:
                    score += 1
                    details.append(f"格雷厄姆公式接近: V={graham_value:.2f}/价格{price:.2f}")
            else:
                details.append(f"格雷厄姆公式估值: V={graham_value:.2f}")
    else:
        pb_ratio = safe_float(
            data.get("pb_ratio") or data.get("市净率")
            or data.get("priceToBookRatio")
        )
        pe_ratio = safe_float(
            data.get("pe_ratio") or data.get("市盈率")
            or data.get("priceToEarningsRatio") or data.get("P/E")
        )
        if pb_ratio is not None and pe_ratio is not None and pb_ratio > 0 and pe_ratio > 0:
            max_score += 2
            graham_combo = pe_ratio * pb_ratio
            if graham_combo < 15:
                score += 2
                details.append(f"PE×PB={graham_combo:.1f}, 低于格雷厄姆阈值22.5")
            elif graham_combo < 22.5:
                score += 1
                details.append(f"PE×PB={graham_combo:.1f}, 接近格雷厄姆阈值")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def graham_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    earnings = analyze_earnings_stability(data)
    financial = analyze_financial_strength(data)
    valuation = analyze_graham_valuation(data)

    margin_score = 0
    margin_max = 0
    margin_details = []

    eps = safe_float(data.get("eps") or data.get("EPS") or data.get("每股收益"))
    bvps = safe_float(data.get("book_value_per_share") or data.get("每股净资产"))
    price = safe_float(data.get("price") or data.get("股价"))

    if eps is not None and bvps is not None and price is not None and eps > 0 and bvps > 0 and price > 0:
        margin_max += 2
        graham_number = (22.5 * eps * bvps) ** 0.5
        safety_margin = (graham_number - price) / price
        if safety_margin > 0.50:
            margin_score += 2
            margin_details.append(f"安全边际>50%: {safety_margin:.1%}")
        elif safety_margin > 0.20:
            margin_score += 1
            margin_details.append(f"安全边际>20%: {safety_margin:.1%}")

    pe_ratio = safe_float(data.get("pe_ratio") or data.get("市盈率"))
    if pe_ratio is not None:
        margin_max += 1
        if 0 < pe_ratio < 10:
            margin_score += 1
            margin_details.append(f"低PE({pe_ratio:.1f})提供安全边际")
        elif 10 <= pe_ratio < 15:
            margin_score += 0.5

    pb_ratio = safe_float(data.get("pb_ratio") or data.get("市净率"))
    if pb_ratio is not None:
        margin_max += 1
        if 0 < pb_ratio < 1.0:
            margin_score += 1
            margin_details.append(f"低PB({pb_ratio:.2f})提供安全边际")
        elif 1.0 <= pb_ratio < 1.5:
            margin_score += 0.5

    if margin_max == 0:
        margin_max = 1

    margin_analysis = {
        "score": margin_score,
        "max_score": margin_max,
        "signal": score_to_signal(margin_score, margin_max),
        "details": "; ".join(margin_details) if margin_details else "数据不足",
    }

    total_score = earnings["score"] + financial["score"] + valuation["score"] + margin_score
    max_score = earnings["max_score"] + financial["max_score"] + valuation["max_score"] + margin_max
    evidence_table = []

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率") or data.get("netMargin"))
    if net_margin is not None:
        evidence_table.append(make_evidence_row("盈利稳定性", "利润率为正且较高", "net_margin", f"{net_margin:.1%}", 2 if net_margin > 0.10 else 1 if net_margin > 0 else 0, 2, "无法取得长期EPS序列时，用利润率近似盈利稳定性"))

    current_ratio = safe_float(data.get("current_ratio") or data.get("流动比率") or data.get("currentRatio"))
    if current_ratio is not None:
        evidence_table.append(make_evidence_row("财务实力", "流动比率门槛", "current_ratio", round(current_ratio, 2), 2 if current_ratio >= 2.0 else 1 if current_ratio >= 1.5 else 0, 2, "格雷厄姆偏好强流动性"))

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率") or data.get("debt_ratio"))
    if de_ratio is not None:
        evidence_table.append(make_evidence_row("财务实力", "低负债约束", "debt_ratio", round(de_ratio, 2), 2 if de_ratio < 0.5 else 1 if de_ratio < 1.0 else 0, 2, "低负债能提供安全边际"))

    pe_ratio = safe_float(data.get("pe_ratio") or data.get("市盈率") or data.get("P/E"))
    pb_ratio = safe_float(data.get("pb_ratio") or data.get("市净率"))
    if pe_ratio is not None and pb_ratio is not None and pe_ratio > 0 and pb_ratio > 0:
        combo = pe_ratio * pb_ratio
        evidence_table.append(make_evidence_row("估值分析", "PE*PB组合", "pe*pb", round(combo, 2), 2 if combo < 15 else 1 if combo < 22.5 else 0, 2, "格雷厄姆经典估值组合"))

    if pe_ratio is not None:
        evidence_table.append(make_evidence_row("安全边际", "低PE安全边际", "pe_ratio", round(pe_ratio, 2), 1 if 0 < pe_ratio < 10 else 0.5 if 10 <= pe_ratio < 15 else 0, 1, "低PE提供防守空间"))

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "盈利稳定性": earnings,
            "财务实力": financial,
            "估值分析": valuation,
            "安全边际": margin_analysis,
        },
        "evidence_table": evidence_table,
        "details": (
            f"盈利稳定性{earnings['score']:.1f}/{earnings['max_score']:.0f}, "
            f"财务实力{financial['score']:.1f}/{financial['max_score']:.0f}, "
            f"估值{valuation['score']:.1f}/{valuation['max_score']:.0f}, "
            f"安全边际{margin_score:.1f}/{margin_max:.0f}"
        ),
    }

    result["formatted_summary"] = format_quantitative_summary("格雷厄姆", result)
    return result
