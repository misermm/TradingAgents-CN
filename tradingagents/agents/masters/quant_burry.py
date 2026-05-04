from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_burry_deep_value(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    pb = safe_float(data.get("PB") or data.get("pb") or data.get("市净率"))
    if pb is not None:
        max_score += 2
        if 0 < pb < 0.8:
            score += 2
            details.append(f"极低PB({pb:.2f})→深度价值")
        elif 0.8 <= pb < 1.2:
            score += 1
            details.append(f"低PB({pb:.2f})→低于账面")

    pe = safe_float(data.get("PE") or data.get("pe") or data.get("市盈率"))
    if pe is not None:
        max_score += 2
        if 0 < pe < 8:
            score += 2
            details.append(f"极低PE({pe:.1f})→严重低估")
        elif 8 <= pe < 15:
            score += 1
            details.append(f"低PE({pe:.1f})")

    fcf = safe_float(data.get("free_cash_flow") or data.get("自由现金流"))
    market_cap = safe_float(data.get("market_cap") or data.get("总市值"))
    if fcf is not None and market_cap is not None and fcf > 0 and market_cap > 0:
        max_score += 1
        fcf_yield = fcf / market_cap
        if fcf_yield > 0.10:
            score += 1
            details.append(f"高FCF收益率({fcf_yield:.1%})")
        elif fcf_yield > 0.05:
            score += 0.5

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        max_score += 1
        if net_margin > 0.05:
            score += 1
            details.append(f"正利润率({net_margin:.1%})")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_burry_safety(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    current_ratio = safe_float(data.get("current_ratio") or data.get("流动比率"))
    if current_ratio is not None:
        max_score += 2
        if current_ratio > 2.0:
            score += 2
            details.append(f"强流动性({current_ratio:.2f})")
        elif current_ratio > 1.5:
            score += 1
            details.append(f"良好流动性({current_ratio:.2f})")

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if de_ratio is not None:
        max_score += 2
        if de_ratio < 0.3:
            score += 2
            details.append("极低负债→安全边际高")
        elif de_ratio < 0.5:
            score += 1
            details.append("低负债")

    quick_ratio = safe_float(data.get("quick_ratio") or data.get("速动比率"))
    if quick_ratio is not None:
        max_score += 1
        if quick_ratio > 1.0:
            score += 1
            details.append("速动比率健康")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_burry_risk_signals(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        max_score += 2
        if net_margin < 0:
            score += 2
            details.append("⚠️ 亏损→高风险信号")
        elif net_margin < 0.03:
            score += 1
            details.append("低利润率→脆弱")

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if de_ratio is not None:
        max_score += 1
        if de_ratio > 1.0:
            score += 1
            details.append("⚠️ 高负债→会计风险")

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 1
        if roe < 0:
            score += 1
            details.append("⚠️ 负ROE→资本侵蚀")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(max_score - score, max_score),
        "details": "; ".join(details) if details else "风险信号较少",
    }


def burry_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    deep_value = analyze_burry_deep_value(data)
    safety = analyze_burry_safety(data)
    risk_signals = analyze_burry_risk_signals(data)

    total_score = deep_value["score"] + safety["score"] + risk_signals["score"]
    max_score = deep_value["max_score"] + safety["max_score"] + risk_signals["max_score"]

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "深度价值评估": deep_value,
            "安全边际": safety,
            "风险信号": risk_signals,
        },
        "details": f"深度价值{deep_value['score']:.1f}/{deep_value['max_score']:.1f}, 安全边际{safety['score']:.1f}/{safety['max_score']:.1f}, 风险信号{risk_signals['score']:.1f}/{risk_signals['max_score']:.1f}",
    }

    result["formatted_summary"] = format_quantitative_summary("布瑞", result)
    return result
