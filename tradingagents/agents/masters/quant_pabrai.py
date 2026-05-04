from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_pabrai_asymmetry(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    pb = safe_float(data.get("PB") or data.get("pb") or data.get("市净率"))
    if pb is not None:
        max_score += 2
        if 0 < pb < 1.0:
            score += 2
            details.append(f"PB<1({pb:.2f})→下行保护强")
        elif 1.0 <= pb < 1.5:
            score += 1
            details.append(f"PB合理({pb:.2f})")

    pe = safe_float(data.get("PE") or data.get("pe") or data.get("市盈率"))
    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if pe is not None and revenue_growth is not None and pe > 0 and revenue_growth > 0:
        max_score += 2
        peg = pe / (revenue_growth * 100) if revenue_growth * 100 > 0 else 999
        if peg < 0.5:
            score += 2
            details.append(f"PEG极低({peg:.2f})→不对称机会")
        elif peg < 1.0:
            score += 1
            details.append(f"PEG合理({peg:.2f})")

    fcf = safe_float(data.get("free_cash_flow") or data.get("自由现金流"))
    if fcf is not None:
        max_score += 1
        if fcf > 0:
            score += 1
            details.append("正自由现金流→安全")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_pabrai_low_risk(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if de_ratio is not None:
        max_score += 2
        if de_ratio < 0.3:
            score += 2
            details.append("极低负债→破产风险极低")
        elif de_ratio < 0.5:
            score += 1
            details.append("低负债")

    current_ratio = safe_float(data.get("current_ratio") or data.get("流动比率"))
    if current_ratio is not None:
        max_score += 1
        if current_ratio > 2.0:
            score += 1
            details.append(f"强流动性({current_ratio:.2f})")
        elif current_ratio > 1.5:
            score += 0.5

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        max_score += 1
        if net_margin > 0.10:
            score += 1
            details.append(f"高利润率({net_margin:.1%})→持续经营能力强")

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 1
        if roe > 0.10:
            score += 1
            details.append(f"正ROE({roe:.1%})→资本保全")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_pabrai_value_gap(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    pe = safe_float(data.get("PE") or data.get("pe") or data.get("市盈率"))
    if pe is not None:
        max_score += 2
        if 0 < pe < 10:
            score += 2
            details.append(f"低PE({pe:.1f})→价值缺口大")
        elif 10 <= pe < 15:
            score += 1

    dividend = safe_float(data.get("dividend_yield") or data.get("股息率"))
    if dividend is not None:
        max_score += 1
        if dividend > 0.03:
            score += 1
            details.append(f"高股息({dividend:.1%})→价值支撑")

    gross_margin = safe_float(data.get("gross_margin") or data.get("毛利率"))
    if gross_margin is not None:
        max_score += 1
        if gross_margin > 0.30:
            score += 1
            details.append(f"高毛利率({gross_margin:.1%})→定价权")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def pabrai_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    asymmetry = analyze_pabrai_asymmetry(data)
    low_risk = analyze_pabrai_low_risk(data)
    value_gap = analyze_pabrai_value_gap(data)

    total_score = asymmetry["score"] + low_risk["score"] + value_gap["score"]
    max_score = asymmetry["max_score"] + low_risk["max_score"] + value_gap["max_score"]

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "不对称机会": asymmetry,
            "低风险验证": low_risk,
            "价值缺口": value_gap,
        },
        "details": f"不对称{asymmetry['score']:.1f}/{asymmetry['max_score']:.1f}, 低风险{low_risk['score']:.1f}/{low_risk['max_score']:.1f}, 价值缺口{value_gap['score']:.1f}/{value_gap['max_score']:.1f}",
    }

    result["formatted_summary"] = format_quantitative_summary("帕伯莱", result)
    return result
