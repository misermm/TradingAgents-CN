from tradingagents.agents.masters.base_master import (
    MASTER_DATA_REQUIREMENTS,
    evaluate_master_data_requirements,
    _build_data_insufficient_report,
    apply_quantitative_quality_guard,
)


def test_buffett_data_requirements_mark_na_and_estimated_fields_missing():
    source_data = """
    净利润及增长率: N/A
    自由现金流: N/A
    资产负债详情: N/A
    ROE历史趋势: 行业估算
    管理层信息: 缺失
    护城河定性分析: 缺失
    """

    result = evaluate_master_data_requirements("warren_buffett", source_data)

    assert result["is_sufficient"] is False
    assert result["present_count"] == 0
    assert "净利润及增长率" in result["missing_required"]
    assert "自由现金流" in result["missing_required"]
    assert "ROE历史趋势" in result["missing_required"]


def test_buffett_data_insufficient_report_blocks_trading_recommendation():
    result = evaluate_master_data_requirements("warren_buffett", "净利润: N/A\n自由现金流: N/A")

    report = _build_data_insufficient_report(
        master_id="warren_buffett",
        company_name="万科A",
        ticker="000002",
        current_date="2026-05-03",
        data_quality=result,
    )

    assert "数据不足" in report
    assert "不生成买入/持有/卖出倾向" in report
    assert "净利润及增长率" in report


def test_buffett_data_requirements_accept_real_core_fields():
    source_data = """
    净利润: 120.5
    净利润增长率: 8.2%
    自由现金流: 58.3
    资产负债率: 61.4%
    ROE: 15.1%
    管理层信息: 分红稳定，资本配置审慎
    护城河定性分析: 品牌与规模优势稳定
    """

    result = evaluate_master_data_requirements("warren_buffett", source_data)

    assert result["is_sufficient"] is True
    assert result["missing_required"] == []


def test_all_registered_masters_have_data_requirements():
    from tradingagents.agents.masters.base_master import MASTER_ANALYST_CONFIG

    assert set(MASTER_DATA_REQUIREMENTS) == set(MASTER_ANALYST_CONFIG)


def test_field_quality_distinguishes_present_missing_and_estimated_values():
    source_data = """
    revenue: 800.0
    profit_growth: industry estimate
    free_cash_flow: N/A
    pe_ratio: 12.5
    """

    result = evaluate_master_data_requirements("peter_lynch", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["revenue_growth"]["status"] == "present"
    assert fields["earnings_growth"]["status"] == "estimated"
    assert fields["free_cash_flow"]["status"] == "missing"
    assert result["estimated_required"] == ["earnings_growth"]
    assert result["missing_required"] == ["free_cash_flow"]


def test_field_quality_keeps_free_source_provenance_from_a_share_snapshot():
    source_data = """
    net_profit: 464.5  # 数据来源: eastmoney | source: eastmoney; report_period: 2025Q4; updated_at: 2026-05-03 10:00:00
    free_cash_flow: 420.0  # 数据来源: akshare | source: akshare; report_period: 2025Q4; updated_at: 2026-05-03 10:01:00
    pe_ttm: 8.6  # 数据来源: eastmoney | source: eastmoney; report_period: 2025Q4; updated_at: 2026-05-03 10:00:00
    """

    result = evaluate_master_data_requirements("peter_lynch", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["earnings_growth"]["source"] == "eastmoney"
    assert fields["earnings_growth"]["report_period"] == "2025Q4"
    assert fields["earnings_growth"]["updated_at"] == "2026-05-03 10:00:00"
    assert fields["free_cash_flow"]["source"] == "akshare"


def test_field_quality_keeps_selection_reason_from_a_share_snapshot():
    source_data = """
    net_profit: 464.5  # 数据来源: eastmoney | source: eastmoney; report_period: 2025Q4; updated_at: 2026-05-03 10:00:00; selection_reason: better_status,newer_report_period
    free_cash_flow: 420.0  # 数据来源: akshare | source: akshare; report_period: 2025Q4; updated_at: 2026-05-03 10:01:00; selection_reason: better_status,higher_source_priority
    pe_ttm: 8.6  # 数据来源: eastmoney | source: eastmoney; report_period: 2025Q4; updated_at: 2026-05-03 10:00:00
    """

    result = evaluate_master_data_requirements("peter_lynch", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["earnings_growth"]["selection_reason"] == "better_status,newer_report_period"
    assert fields["free_cash_flow"]["selection_reason"] == "better_status,higher_source_priority"


def test_quantitative_quality_guard_dampens_signal_when_estimated_fields_exist():
    quant_result = {
        "signal": "bullish",
        "formatted_summary": "base summary",
    }
    data_quality = {
        "is_applicable": True,
        "completeness": 0.8,
        "estimated_required": ["earnings_growth"],
        "missing_required": [],
    }

    guarded = apply_quantitative_quality_guard(quant_result, data_quality)

    assert guarded["signal"] == "neutral"
    assert guarded["quality_guard"]["original_signal"] == "bullish"
    assert "estimated_required_fields" in guarded["quality_guard"]["reasons"]
    assert "signal_adjustment: bullish -> neutral" in guarded["formatted_summary"]


def test_buffett_management_requirement_accepts_free_announcement_signals():
    source_data = """
    net_profit: 120.0
    free_cash_flow: 80.0
    debt_ratio: 45%
    roe: 15%
    shareholder_return_summary: 年度权益分派实施公告；股份回购进展公告  # 数据来源: akshare | source: akshare; report_period: recent_90d
    moat: 品牌和规模优势稳定
    """

    result = evaluate_master_data_requirements("warren_buffett", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["管理层信息"]["status"] == "present"
    assert fields["管理层信息"]["source"] == "akshare"
    assert "管理层信息" not in result["missing_required"]


def test_capital_return_requirement_accepts_parsed_announcement_metrics():
    source_data = """
    net_profit: 120.0
    pe_ttm: 12
    debt_ratio: 45%
    dividend_cash_per_10_shares: 3.5  # 数据来源: akshare | source: akshare; report_period: recent_90d
    buyback_amount_max: 200000000  # 数据来源: akshare | source: akshare; report_period: recent_90d
    """

    result = evaluate_master_data_requirements("bill_ackman", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["capital_return"]["status"] == "present"
    assert fields["capital_return"]["source"] == "akshare"
    assert "capital_return" not in result["missing_required"]


def test_capital_return_requirement_accepts_announcement_timing_fields():
    source_data = """
    net_profit: 120.0
    pe_ttm: 12
    debt_ratio: 45%
    dividend_record_date: 2026-05-20  # 数据来源: akshare | source: akshare; report_period: recent_90d
    dividend_ex_date: 2026-05-21  # 数据来源: akshare | source: akshare; report_period: recent_90d
    buyback_period_months: 12  # 数据来源: akshare | source: akshare; report_period: recent_90d
    """

    result = evaluate_master_data_requirements("bill_ackman", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["capital_return"]["status"] == "present"
    assert fields["capital_return"]["source"] == "akshare"


def test_buffett_roe_history_requirement_accepts_trend_field():
    source_data = """
    net_profit: 120.0
    free_cash_flow: 80.0
    debt_ratio: 45%
    roe_trend: improving  # 数据来源: eastmoney:derived | source: eastmoney; report_period: 2025Q4
    shareholder_return_summary: 年度权益分派实施公告
    moat: 品牌和规模优势稳定
    """

    result = evaluate_master_data_requirements("warren_buffett", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["ROE历史趋势"]["status"] == "present"
    assert fields["ROE历史趋势"]["source"] == "eastmoney"
