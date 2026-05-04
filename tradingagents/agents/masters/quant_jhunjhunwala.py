from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_jhunjhunwala_growth(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if revenue_growth is not None:
        max_score += 2
        if revenue_growth > 0.20:
            score += 2
            details.append(f"高增长({revenue_growth:.1%})→成长性强")
        elif revenue_growth > 0.10:
            score += 1
            details.append(f"中等增长({revenue_growth:.1%})")

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        max_score += 1
        if net_margin > 0.15:
            score += 1
            details.append(f"高利润率({net_margin:.1%})→盈利扩张空间")
        elif net_margin > 0.08:
            score += 0.5

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 1
        if roe > 0.15:
            score += 1
            details.append(f"高ROE({roe:.1%})→资本效率高")
        elif roe > 0.10:
            score += 0.5

    gross_margin = safe_float(data.get("gross_margin") or data.get("毛利率"))
    if gross_margin is not None:
        max_score += 1
        if gross_margin > 0.40:
            score += 1
            details.append(f"高毛利率({gross_margin:.1%})→定价权")

    pe = safe_float(data.get("PE") or data.get("pe") or data.get("市盈率"))
    if pe is not None and revenue_growth is not None and pe > 0 and revenue_growth > 0:
        max_score += 1
        peg = pe / (revenue_growth * 100) if revenue_growth * 100 > 0 else 999
        if peg < 1.0:
            score += 1
            details.append(f"PEG合理({peg:.2f})→估值匹配增长")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_jhunjhunwala_fundamentals(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if de_ratio is not None:
        max_score += 1
        if de_ratio < 0.4:
            score += 1
            details.append("低负债→财务稳健")
        elif de_ratio < 0.6:
            score += 0.5

    fcf = safe_float(data.get("free_cash_flow") or data.get("自由现金流"))
    if fcf is not None:
        max_score += 1
        if fcf > 0:
            score += 1
            details.append("正自由现金流")

    current_ratio = safe_float(data.get("current_ratio") or data.get("流动比率"))
    if current_ratio is not None:
        max_score += 1
        if current_ratio > 1.5:
            score += 1
            details.append(f"流动性好({current_ratio:.2f})")

    op_margin = safe_float(data.get("operating_margin") or data.get("营业利润率"))
    if op_margin is not None:
        max_score += 1
        if op_margin > 0.10:
            score += 1
            details.append(f"营业利润率({op_margin:.1%})→经营效率")

    dividend = safe_float(data.get("dividend_yield") or data.get("股息率"))
    if dividend is not None:
        max_score += 1
        if dividend > 0:
            score += 1
            details.append(f"有分红({dividend:.1%})→股东友好")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_jhunjhunwala_valuation(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    pe = safe_float(data.get("PE") or data.get("pe") or data.get("市盈率"))
    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if pe is not None and revenue_growth is not None and pe > 0 and revenue_growth > 0:
        max_score += 2
        peg = pe / (revenue_growth * 100) if revenue_growth * 100 > 0 else 999
        if peg < 0.5:
            score += 2
            details.append(f"PEG极低({peg:.2f})→成长低估")
        elif peg < 1.0:
            score += 1
            details.append(f"PEG合理({peg:.2f})")
    elif pe is not None:
        max_score += 1
        if 0 < pe < 20:
            score += 1
            details.append(f"PE合理({pe:.1f})")

    pb = safe_float(data.get("PB") or data.get("pb") or data.get("市净率"))
    if pb is not None:
        max_score += 1
        if 0 < pb < 2.0:
            score += 1
            details.append(f"PB合理({pb:.2f})")

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 1
        if roe > 0.12:
            score += 1
            details.append(f"ROE支撑估值({roe:.1%})")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def jhunjhunwala_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    growth = analyze_jhunjhunwala_growth(data)
    fundamentals = analyze_jhunjhunwala_fundamentals(data)
    valuation = analyze_jhunjhunwala_valuation(data)

    total_score = growth["score"] + fundamentals["score"] + valuation["score"]
    max_score = growth["max_score"] + fundamentals["max_score"] + valuation["max_score"]

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "成长性评估": growth,
            "基本面分析": fundamentals,
            "估值与时机": valuation,
        },
        "details": f"成长性{growth['score']:.1f}/{growth['max_score']:.1f}, 基本面{fundamentals['score']:.1f}/{fundamentals['max_score']:.1f}, 估值{valuation['score']:.1f}/{valuation['max_score']:.1f}",
    }

    result["formatted_summary"] = format_quantitative_summary("朱朱瓦拉", result)
    return result
