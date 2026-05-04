from tradingagents.agents.masters.base_master import evaluate_master_data_requirements


def test_generic_earnings_requirement_accepts_guidance_numeric_fields():
    source_data = """
    revenue: 1000.0
    earnings_guidance_change_pct_min: 20  # 数据来源: akshare | source: akshare; report_period: recent_90d
    earnings_guidance_change_pct_max: 35  # 数据来源: akshare | source: akshare; report_period: recent_90d
    pe_ttm: 12
    free_cash_flow: 80
    """

    result = evaluate_master_data_requirements("peter_lynch", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["earnings_growth"]["status"] == "present"
    assert fields["earnings_growth"]["source"] == "akshare"
