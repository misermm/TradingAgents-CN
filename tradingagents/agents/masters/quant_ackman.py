from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal, format_quantitative_summary, make_evidence_row
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def analyze_business_quality(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth")
    )
    if revenue_growth is not None:
        max_score += 2
        if revenue_growth > 0.15:
            score += 2
            details.append(f"强营收增长: {revenue_growth:.1%}")
        elif revenue_growth > 0.05:
            score += 1
            details.append(f"温和营收增长: {revenue_growth:.1%}")

    net_margin = safe_float(
        data.get("net_margin") or data.get("净利润率")
        or data.get("netMargin")
    )
    if net_margin is not None:
        max_score += 2
        if net_margin > 0.15:
            score += 2
            details.append(f"高净利润率: {net_margin:.1%}")
        elif net_margin > 0.08:
            score += 1
            details.append(f"中等利润率: {net_margin:.1%}")

    roe = safe_float(
        data.get("ROE") or data.get("净资产收益率")
        or data.get("return_on_equity")
    )
    if roe is not None:
        max_score += 2
        if roe > 0.20:
            score += 2
            details.append(f"强ROE: {roe:.1%}")
        elif roe > 0.12:
            score += 1
            details.append(f"中等ROE: {roe:.1%}")

    fcf = safe_float(
        data.get("free_cash_flow") or data.get("自由现金流")
        or data.get("fcf") or data.get("freeCashFlow")
    )
    if fcf is not None:
        max_score += 1
        if fcf > 0:
            score += 1
            details.append("正自由现金流")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_financial_discipline(data: dict) -> dict:
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

    dividend_yield = safe_float(
        data.get("dividend_yield") or data.get("股息率")
        or data.get("dividendYield")
    )
    buyback_yield = safe_float(
        data.get("buyback_yield") or data.get("回购收益率")
        or data.get("shareRepurchaseYield")
    )
    if dividend_yield is not None or buyback_yield is not None:
        max_score += 2
        dv = dividend_yield if dividend_yield is not None else 0
        bv = buyback_yield if buyback_yield is not None else 0
        total_shareholder_yield = dv + bv
        if total_shareholder_yield > 0.06:
            score += 2
            details.append(f"高股东回报率: {total_shareholder_yield:.1%}")
        elif total_shareholder_yield > 0.03:
            score += 1
            details.append(f"中等股东回报率: {total_shareholder_yield:.1%}")
        elif dv > 0 or bv > 0:
            score += 0.5
            details.append("有股东回报")

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def analyze_activism_potential(data: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth")
    )
    net_margin = safe_float(
        data.get("net_margin") or data.get("净利润率")
        or data.get("netMargin")
    )
    if revenue_growth is not None and net_margin is not None:
        max_score += 2
        if revenue_growth > 0.10 and net_margin < 0.05:
            score += 2
            details.append("高增长+低利润率=显著运营改善空间")
        elif revenue_growth > 0.05 and net_margin < 0.08:
            score += 1
            details.append("增长+低利润率=潜在改善机会")

    roe = safe_float(data.get("ROE") or data.get("净资产收益率"))
    if roe is not None and revenue_growth is not None:
        max_score += 0.5
        if 0 < roe < 0.10 and revenue_growth > 0.05:
            score += 0.5
            details.append(f"低ROE({roe:.1%})+增长=改善潜力")

    score = min(score, max_score) if max_score > 0 else score

    if max_score == 0:
        max_score = 1

    return {
        "score": score,
        "max_score": max_score,
        "signal": score_to_signal(score, max_score),
        "details": "; ".join(details) if details else "数据不足",
    }


def ackman_quantitative_analysis(raw_data: str) -> dict:
    data = extract_financial_data(raw_data)

    quality = analyze_business_quality(data)
    discipline = analyze_financial_discipline(data)
    activism = analyze_activism_potential(data)

    valuation_score = 0
    valuation_max = 0
    valuation_details = []

    pe_ratio = safe_float(
        data.get("pe_ratio") or data.get("市盈率") or data.get("P/E")
    )
    if pe_ratio is not None:
        valuation_max += 2
        if 0 < pe_ratio <= 15:
            valuation_score += 2
            valuation_details.append(f"低PE: {pe_ratio:.1f}")
        elif 15 < pe_ratio <= 25:
            valuation_score += 1
            valuation_details.append(f"合理PE: {pe_ratio:.1f}")

    ev_ebitda = safe_float(
        data.get("ev_ebitda") or data.get("企业价值倍数")
        or data.get("evToEbitda") or data.get("EV/EBITDA")
    )
    if ev_ebitda is not None:
        valuation_max += 2
        if 0 < ev_ebitda <= 10:
            valuation_score += 2
            valuation_details.append(f"低EV/EBITDA: {ev_ebitda:.1f}")
        elif 10 < ev_ebitda <= 15:
            valuation_score += 1
            valuation_details.append(f"合理EV/EBITDA: {ev_ebitda:.1f}")

    iv_discount = safe_float(
        data.get("iv_discount") or data.get("内在价值折价")
        or data.get("intrinsicValueDiscount")
    )
    if iv_discount is not None:
        valuation_max += 1
        if iv_discount > 0.20:
            valuation_score += 1
            valuation_details.append(f"显著折价: {iv_discount:.1%}")

    if valuation_max == 0:
        valuation_max = 1

    valuation_analysis = {
        "score": valuation_score,
        "max_score": valuation_max,
        "signal": score_to_signal(valuation_score, valuation_max),
        "details": "; ".join(valuation_details) if valuation_details else "数据不足",
    }

    total_score = quality["score"] + discipline["score"] + activism["score"] + valuation_score
    max_score = quality["max_score"] + discipline["max_score"] + activism["max_score"] + valuation_max
    evidence_table = []

    revenue_growth = safe_float(
        data.get("revenue_growth") or data.get("营收增长率")
        or data.get("revenueGrowth")
    )
    if revenue_growth is not None:
        evidence_table.append(make_evidence_row("商业质量", "营收增长支撑业务扩张", "revenue_growth", f"{revenue_growth:.1%}", 2 if revenue_growth > 0.15 else 1 if revenue_growth > 0.05 else 0, 2, "阿克曼偏好还能继续放大的高质量业务。"))

    net_margin = safe_float(
        data.get("net_margin") or data.get("净利润率")
        or data.get("netMargin")
    )
    if net_margin is not None:
        evidence_table.append(make_evidence_row("商业质量", "高净利率体现商业模式", "net_margin", f"{net_margin:.1%}", 2 if net_margin > 0.15 else 1 if net_margin > 0.08 else 0, 2, "阿克曼强调高质量业务要有足够盈利能力。"))

    debt_ratio = safe_float(
        data.get("debt_to_equity") or data.get("资产负债率")
        or data.get("debt_ratio") or data.get("debtEquityRatio")
    )
    if debt_ratio is not None:
        evidence_table.append(make_evidence_row("财务纪律", "低杠杆维持主动权", "debt_ratio", round(debt_ratio, 2), 2 if debt_ratio < 0.5 else 1 if debt_ratio < 1.0 else 0, 2, "激进投资前提是公司先别被资产负债表卡死。"))

    pe_ratio = safe_float(
        data.get("pe_ratio") or data.get("市盈率") or data.get("P/E")
    )
    if pe_ratio is not None:
        evidence_table.append(make_evidence_row("估值分析", "买入价格保留回报空间", "pe_ratio", round(pe_ratio, 2), 2 if 0 < pe_ratio <= 15 else 1 if pe_ratio <= 25 else 0, 2, "阿克曼依然要求在可接受价格介入。"))

    shareholder_yield = 0.0
    shareholder_evidence = False
    dividend_yield = safe_float(
        data.get("dividend_yield") or data.get("股息率")
        or data.get("dividendYield")
    )
    buyback_yield = safe_float(
        data.get("buyback_yield") or data.get("回购收益率")
        or data.get("shareRepurchaseYield")
    )
    if dividend_yield is not None:
        shareholder_yield += dividend_yield
        shareholder_evidence = True
    if buyback_yield is not None:
        shareholder_yield += buyback_yield
        shareholder_evidence = True
    if shareholder_evidence:
        evidence_table.append(make_evidence_row("财务纪律", "股东回报政策", "shareholder_yield", f"{shareholder_yield:.1%}", 2 if shareholder_yield > 0.06 else 1 if shareholder_yield > 0.03 else 0.5 if shareholder_yield > 0 else 0, 2, "资本回报是阿克曼判断治理质量的重要抓手。"))

    buyback_amount_max = safe_float(data.get("buyback_amount_max"))
    if buyback_amount_max is not None:
        evidence_table.append(make_evidence_row("财务纪律", "回购承诺力度", "buyback_amount_max", round(buyback_amount_max, 2), 1 if buyback_amount_max > 0 else 0, 1, "阿克曼偏好能把资本配置动作落实到回购方案的公司。"))

    related_party_amount = safe_float(data.get("related_party_transaction_amount_max"))
    if related_party_amount is not None:
        evidence_table.append(make_evidence_row("财务纪律", "关联交易约束", "related_party_transaction_amount_max", round(related_party_amount, 2), 1 if related_party_amount <= 0 else 0, 1, "大额关联交易会削弱阿克曼对治理和资本配置的判断。"))

    penalty_severity = str(data.get("regulatory_penalty_severity") or "").strip().lower()
    if penalty_severity:
        penalty_score = 1 if penalty_severity in {"none", "low"} else 0.5 if penalty_severity == "medium" else 0
        evidence_table.append(make_evidence_row("激进主义潜力", "监管风险可控", "regulatory_penalty_severity", penalty_severity, penalty_score, 1, "激进投资需要先排除会持续消耗治理资源的监管问题。"))

    accounts_payable_change = safe_float(data.get("accounts_payable_to_revenue_change"))
    if accounts_payable_change is not None:
        evidence_table.append(
            make_evidence_row(
                "Quality",
                "Payables Discipline",
                "accounts_payable_to_revenue_change",
                round(accounts_payable_change, 2),
                1 if accounts_payable_change <= 0 else 0.5 if accounts_payable_change <= 2 else 0,
                1,
                "A large payable build can weaken confidence in normalized free cash flow quality.",
            )
        )

    asset_impairment = safe_float(data.get("asset_impairment_amount_max"))
    if asset_impairment is not None:
        evidence_table.append(
            make_evidence_row(
                "Quality",
                "Asset Impairment Risk",
                "asset_impairment_amount_max",
                round(asset_impairment, 2),
                1 if asset_impairment <= 0 else 0,
                1,
                "Large impairment charges often contradict a clean high-quality compounder thesis.",
            )
        )

    result = {
        "signal": score_to_signal(total_score, max_score),
        "score": total_score,
        "max_score": max_score,
        "sub_analyses": {
            "商业质量": quality,
            "财务纪律": discipline,
            "激进主义潜力": activism,
            "估值分析": valuation_analysis,
        },
        "evidence_table": evidence_table,
        "details": (
            f"质量{quality['score']:.1f}/{quality['max_score']:.0f}, "
            f"纪律{discipline['score']:.1f}/{discipline['max_score']:.0f}, "
            f"激进主义{activism['score']:.1f}/{activism['max_score']:.0f}, "
            f"估值{valuation_score:.1f}/{valuation_max:.0f}"
        ),
    }

    result["formatted_summary"] = format_quantitative_summary("阿克曼", result)
    return result
