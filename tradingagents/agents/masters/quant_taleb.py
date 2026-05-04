from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_taleb_fragility(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if de_ratio is not None:
        max_score += 2
        if de_ratio < 0.2:
            score += 2
            details.append("极低负债→反脆弱")
        elif de_ratio < 0.4:
            score += 1
            details.append("低负债→较稳健")
        elif de_ratio > 0.8:
            score += 0
            details.append(f"⚠️ 高负债({de_ratio:.2f})→脆弱")

    current_ratio = safe_float(data.get("current_ratio") or data.get("流动比率"))
    if current_ratio is not None:
        max_score += 1
        if current_ratio > 2.0:
            score += 1
            details.append(f"强流动性({current_ratio:.2f})")
        elif current_ratio > 1.5:
            score += 0.5

    fcf = safe_float(data.get("free_cash_flow") or data.get("自由现金流"))
    if fcf is not None:
        max_score += 1
        if fcf > 0:
            score += 1
            details.append("正FCF→抗冲击能力强")

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        max_score += 1
        if net_margin > 0.10:
            score += 1
            details.append(f"高利润率({net_margin:.1%})→缓冲厚")
        elif net_margin > 0:
            score += 0.5

    op_margin = safe_float(data.get("operating_margin") or data.get("营业利润率"))
    if op_margin is not None:
        max_score += 1
        if op_margin > 0.15:
            score += 1
            details.append("高营业利润率→可变成本占比可能低")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_taleb_antifragile(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if revenue_growth is not None:
        max_score += 1
        if revenue_growth > 0.15:
            score += 1
            details.append(f"高增长({revenue_growth:.1%})→可能从波动中获益")

    gross_margin = safe_float(data.get("gross_margin") or data.get("毛利率"))
    if gross_margin is not None:
        max_score += 1
        if gross_margin > 0.50:
            score += 1
            details.append(f"高毛利率({gross_margin:.1%})→定价权=可选性")

    dividend = safe_float(data.get("dividend_yield") or data.get("股息率"))
    if dividend is not None:
        max_score += 1
        if dividend > 0.02:
            score += 1
            details.append(f"有分红({dividend:.1%})→下行保护")

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 1
        if roe > 0.15:
            score += 1
            details.append(f"高ROE({roe:.1%})→资本效率=反脆弱特征")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_taleb_survival(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if de_ratio is not None:
        max_score += 2
        if de_ratio < 0.3:
            score += 2
            details.append("低负债→生存概率高")
        elif de_ratio < 0.5:
            score += 1

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        max_score += 1
        if net_margin > 0.05:
            score += 1
            details.append("盈利→可持续经营")

    current_ratio = safe_float(data.get("current_ratio") or data.get("流动比率"))
    if current_ratio is not None:
        max_score += 1
        if current_ratio > 1.5:
            score += 1
            details.append("流动性充足→短期安全")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def taleb_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    fragility = analyze_taleb_fragility(data)
    antifragile = analyze_taleb_antifragile(data)
    survival = analyze_taleb_survival(data)

    total_score = fragility["score"] + antifragile["score"] + survival["score"]
    max_score = fragility["max_score"] + antifragile["max_score"] + survival["max_score"]

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "脆弱性诊断": fragility,
            "反脆弱性评估": antifragile,
            "生存性检验": survival,
        },
        "details": f"脆弱性{fragility['score']:.1f}/{fragility['max_score']:.1f}, 反脆弱{antifragile['score']:.1f}/{antifragile['max_score']:.1f}, 生存性{survival['score']:.1f}/{survival['max_score']:.1f}",
    }

    result["formatted_summary"] = format_quantitative_summary("塔勒布", result)
    return result
