from tradingagents.agents.masters.quant_munger import munger_quantitative_analysis
from tradingagents.agents.masters.quant_wood import wood_quantitative_analysis


def test_munger_quantitative_analysis_includes_revenue_guidance_and_contract_assets_evidence():
    report = """
earnings_guidance_revenue_change_pct_max: 30%
contract_assets_to_revenue_change: -1.5
"""

    result = munger_quantitative_analysis(report)
    fields = {row["field"] for row in result.get("evidence_table", [])}

    assert "earnings_guidance_revenue_change_pct_max" in fields
    assert "contract_assets_to_revenue_change" in fields


def test_wood_quantitative_analysis_includes_revenue_guidance_and_contract_liabilities_evidence():
    report = """
earnings_guidance_revenue_change_pct_max: 30%
contract_liabilities_to_revenue_change: 5.0
"""

    result = wood_quantitative_analysis(report)
    fields = {row["field"] for row in result.get("evidence_table", [])}

    assert "earnings_guidance_revenue_change_pct_max" in fields
    assert "contract_liabilities_to_revenue_change" in fields
