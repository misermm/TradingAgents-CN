from tradingagents.agents.masters.base_master import evaluate_master_data_requirements


def test_fisher_management_requirement_accepts_extended_governance_fields():
    source_data = """
    revenue: 1000.0
    net_profit: 120.0
    rd_ratio: 12%
    management_alignment_summary: 董事长增持公司股份计划公告  # 数据来源: akshare | source: akshare; report_period: recent_90d
    insider_increase_events: 1  # 数据来源: akshare | source: akshare; report_period: recent_90d
    earnings_positive_events: 1  # 数据来源: akshare | source: akshare; report_period: recent_90d
    regulatory_penalty_events: 0  # 数据来源: akshare | source: akshare; report_period: recent_90d
    goodwill_impairment_amount_max: 0  # 数据来源: akshare | source: akshare; report_period: recent_90d
    """

    result = evaluate_master_data_requirements("phil_fisher", source_data)

    fields = {field["name"]: field for field in result["field_quality"]}
    assert fields["management_quality"]["status"] == "present"
    assert fields["management_quality"]["source"] == "akshare"
    assert "management_quality" not in result["missing_required"]
