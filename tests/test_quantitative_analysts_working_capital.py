from tradingagents.agents.masters.quant_buffett import buffett_quantitative_analysis


def test_buffett_quantitative_analysis_includes_working_capital_evidence():
    report = """
contract_liabilities_to_revenue_change: 5.0
contract_assets_to_revenue_change: -1.5
"""

    result = buffett_quantitative_analysis(report)
    fields = {row["field"] for row in result.get("evidence_table", [])}

    assert "contract_liabilities_to_revenue_change" in fields
    assert "contract_assets_to_revenue_change" in fields
