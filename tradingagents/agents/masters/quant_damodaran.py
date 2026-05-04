from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_damodaran_lifecycle(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if revenue_growth is not None:
        max_score += 2
        if revenue_growth > 0.20:
            score += 2
            details.append(f"高增长({revenue_growth:.1%})→成长期")
        elif revenue_growth > 0.05:
            score += 1
            details.append(f"中等增长({revenue_growth:.1%})→成熟期")
        elif revenue_growth > 0:
            score += 0.5
            details.append("低增长→成熟/衰退期")

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        max_score += 1
        if net_margin > 0.15:
            score += 1
            details.append(f"高利润率({net_margin:.1%})→盈利模式确立")
        elif net_margin > 0.05:
            score += 0.5

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 1
        if roe > 0.15:
            score += 1
            details.append(f"ROE {roe:.1%}→资本效率高")
        elif roe > 0.08:
            score += 0.5

    op_margin = safe_float(data.get("operating_margin") or data.get("营业利润率"))
    if op_margin is not None:
        max_score += 1
        if op_margin > 0.10:
            score += 1
            details.append("营业利润率稳定")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_damodaran_valuation(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    pe = safe_float(data.get("PE") or data.get("pe") or data.get("市盈率"))
    if pe is not None:
        max_score += 2
        if 0 < pe < 15:
            score += 2
            details.append(f"低PE({pe:.1f})→可能低估")
        elif 15 <= pe < 25:
            score += 1
            details.append(f"合理PE({pe:.1f})")
        elif pe >= 25:
            score += 0.5
            details.append(f"高PE({pe:.1f})→需验证增长")

    fcf = safe_float(data.get("free_cash_flow") or data.get("自由现金流"))
    if fcf is not None:
        max_score += 1
        if fcf > 0:
            score += 1
            details.append("正自由现金流→DCF可行")

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if de_ratio is not None:
        max_score += 1
        if de_ratio < 0.3:
            score += 1
            details.append("低负债→WACC低")
        elif de_ratio < 0.6:
            score += 0.5

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if revenue_growth is not None:
        max_score += 1
        if revenue_growth > 0.10:
            score += 1
            details.append(f"增长驱动({revenue_growth:.1%})")

    gross_margin = safe_float(data.get("gross_margin") or data.get("毛利率"))
    if gross_margin is not None:
        max_score += 1
        if gross_margin > 0.40:
            score += 1
            details.append(f"高毛利率({gross_margin:.1%})→定价权强")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_damodaran_uncertainty(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if revenue_growth is not None:
        max_score += 1
        if revenue_growth > 0.20:
            score += 1
            details.append("高增长→高不确定性")
        elif revenue_growth < 0.05:
            score += 1
            details.append("低增长→低不确定性(可预测)")

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        max_score += 1
        if net_margin > 0.10:
            score += 1
            details.append("利润率稳定→可预测性高")

    de_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if de_ratio is not None:
        max_score += 1
        if de_ratio < 0.4:
            score += 1
            details.append("低负债→生存风险低")

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        max_score += 1
        if roe > 0.12:
            score += 1
            details.append(f"ROE {roe:.1%}→资本回报可预测")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def damodaran_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    lifecycle = analyze_damodaran_lifecycle(data)
    valuation = analyze_damodaran_valuation(data)
    uncertainty = analyze_damodaran_uncertainty(data)

    total_score = lifecycle["score"] + valuation["score"] + uncertainty["score"]
    max_score = lifecycle["max_score"] + valuation["max_score"] + uncertainty["max_score"]
    evidence_table = []

    revenue_growth = safe_float(data.get("revenue_growth") or data.get("营收增长率"))
    if revenue_growth is not None:
        evidence_table.append(make_evidence_row(
            "生命周期定位",
            "增长率判断阶段",
            "revenue_growth",
            f"{revenue_growth:.1%}",
            2 if revenue_growth > 0.20 else 1 if revenue_growth > 0.05 else 0.5 if revenue_growth > 0 else 0,
            2,
            "达莫达兰先判断公司处于成长、成熟还是衰退阶段。"
        ))

    net_margin = safe_float(data.get("net_margin") or data.get("净利润率"))
    if net_margin is not None:
        evidence_table.append(make_evidence_row(
            "生命周期定位",
            "利润率验证盈利模式",
            "net_margin",
            f"{net_margin:.1%}",
            1 if net_margin > 0.15 else 0.5 if net_margin > 0.05 else 0,
            1,
            "增长必须和盈利质量一起看，否则生命周期判断会失真。"
        ))

    pe_ratio = safe_float(data.get("PE") or data.get("pe") or data.get("市盈率"))
    if pe_ratio is not None:
        evidence_table.append(make_evidence_row(
            "估值分析",
            "PE约束市场预期",
            "pe_ratio",
            round(pe_ratio, 2),
            2 if 0 < pe_ratio < 15 else 1 if 15 <= pe_ratio < 25 else 0.5 if pe_ratio >= 25 else 0,
            2,
            "达莫达兰会先看市场把增长预期定在什么价格上。"
        ))

    debt_ratio = safe_float(data.get("debt_to_equity") or data.get("资产负债率"))
    if debt_ratio is not None:
        evidence_table.append(make_evidence_row(
            "估值分析",
            "低负债降低资本成本",
            "debt_ratio",
            round(debt_ratio, 2),
            1 if debt_ratio < 0.3 else 0.5 if debt_ratio < 0.6 else 0,
            1,
            "资本结构直接影响折现率和估值区间。"
        ))

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None:
        evidence_table.append(make_evidence_row(
            "不确定性评估",
            "资本回报可预测性",
            "roe",
            f"{roe:.1%}",
            1 if roe > 0.12 else 0,
            1,
            "较稳定的资本回报意味着估值假设更容易落地。"
        ))

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "生命周期定位": lifecycle,
            "估值分析": valuation,
            "不确定性评估": uncertainty,
        },
        "evidence_table": evidence_table,
        "details": f"生命周期{lifecycle['score']:.1f}/{lifecycle['max_score']:.1f}, 估值{valuation['score']:.1f}/{valuation['max_score']:.1f}, 不确定性{uncertainty['score']:.1f}/{uncertainty['max_score']:.1f}",
    }

    result["formatted_summary"] = format_quantitative_summary("达莫达兰", result)
    return result
