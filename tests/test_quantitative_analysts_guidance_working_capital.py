from tradingagents.agents.masters.quant_ackman import ackman_quantitative_analysis
from tradingagents.agents.masters.quant_druckenmiller import druckenmiller_quantitative_analysis
from tradingagents.agents.masters.quant_fisher import fisher_quantitative_analysis
from tradingagents.agents.masters.quant_lynch import lynch_quantitative_analysis


def test_fisher_quantitative_analysis_includes_revenue_guidance_and_impairment_evidence():
    report = """
earnings_guidance_revenue_change_pct_max: 30%
asset_impairment_amount_max: 80000000.0
"""

    result = fisher_quantitative_analysis(report)
    fields = {row["field"] for row in result.get("evidence_table", [])}

    assert "earnings_guidance_revenue_change_pct_max" in fields
    assert "asset_impairment_amount_max" in fields


def test_lynch_quantitative_analysis_includes_revenue_guidance_and_payables_evidence():
    report = """
earnings_guidance_revenue_change_pct_max: 30%
accounts_payable_to_revenue_change: 4.0
"""

    result = lynch_quantitative_analysis(report)
    fields = {row["field"] for row in result.get("evidence_table", [])}

    assert "earnings_guidance_revenue_change_pct_max" in fields
    assert "accounts_payable_to_revenue_change" in fields


def test_druckenmiller_quantitative_analysis_includes_revenue_guidance_and_contract_liability_evidence():
    report = """
earnings_guidance_revenue_change_pct_max: 30%
contract_liabilities_to_revenue_change: 5.0
"""

    result = druckenmiller_quantitative_analysis(report)
    fields = {row["field"] for row in result.get("evidence_table", [])}

    assert "earnings_guidance_revenue_change_pct_max" in fields
    assert "contract_liabilities_to_revenue_change" in fields


def test_ackman_quantitative_analysis_includes_payables_and_impairment_evidence():
    report = """
accounts_payable_to_revenue_change: 4.0
asset_impairment_amount_max: 80000000.0
"""

    result = ackman_quantitative_analysis(report)
    fields = {row["field"] for row in result.get("evidence_table", [])}

    assert "accounts_payable_to_revenue_change" in fields
    assert "asset_impairment_amount_max" in fields
