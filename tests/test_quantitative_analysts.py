import pytest
from tradingagents.agents.masters.quant_buffett import buffett_quantitative_analysis
from tradingagents.agents.masters.quant_lynch import lynch_quantitative_analysis
from tradingagents.agents.masters.quant_graham import graham_quantitative_analysis
from tradingagents.agents.masters.quant_munger import munger_quantitative_analysis
from tradingagents.agents.masters.quant_damodaran import damodaran_quantitative_analysis
from tradingagents.agents.masters.quant_wood import wood_quantitative_analysis
from tradingagents.agents.masters.quant_ackman import ackman_quantitative_analysis
from tradingagents.agents.masters.quant_fisher import fisher_quantitative_analysis
from tradingagents.agents.masters.quant_druckenmiller import druckenmiller_quantitative_analysis
from tradingagents.agents.masters.quant_munger import munger_quantitative_analysis
from tradingagents.agents.masters.quantitative_base import (
    extract_financial_data, safe_float, score_to_signal
)


MOCK_RAW_DATA = """
基本面分析报告
==================
净资产收益率(ROE): 31.2%
资产负债率: 0.35
营业利润率: 25.6%
流动比率: 1.85
净利润率: 22.1%
毛利率: 91.2%
每股收益(EPS): 42.5
每股净资产: 136.2
股价: 1800.0
市盈率(PE): 42.4
市净率(PB): 13.2
营收增长率: 18.5%
净利润增长率: 15.3%
自由现金流(FCF): 95000000000
总市值: 2200000000000
总负债: 450000000000
流动资产: 850000000000
股息率: 0.8%
分红年数: 15
PEG: 1.2
EPS增长率: 0.153
研发费用率: 3.5%
"""


class TestQuantitativeBase:
    def test_safe_float_normal(self):
        assert safe_float("3.14") == 3.14

    def test_safe_float_percentage(self):
        assert abs(safe_float("31.2%") - 0.312) < 0.001

    def test_safe_float_comma_number(self):
        assert safe_float("1,234.56") == 1234.56

    def test_safe_float_invalid(self):
        assert safe_float("N/A") is None
        assert safe_float("N/A", default=-1.0) == -1.0

    def test_score_to_signal(self):
        assert score_to_signal(7, 10) == "bullish"
        assert score_to_signal(5, 10) == "neutral"
        assert score_to_signal(2, 10) == "bearish"

    def test_extract_financial_data(self):
        data = extract_financial_data(MOCK_RAW_DATA)
        assert isinstance(data, dict)
        assert "ROE" in data or "roe" in data

    def test_extract_financial_data_expands_a_share_three_statement_aliases(self):
        raw_data = """
        扣除非经常性损益后的净利润: 108
        经营活动产生的现金流量净额: 180
        购建固定资产、无形资产和其他长期资产支付的现金: 50
        资产总计: 2500
        负债合计: 1500
        流动资产合计: 900
        流动负债合计: 450
        应收账款: 80
        存货: 60
        商誉: 25
        """

        data = extract_financial_data(raw_data)

        assert data["deducted_net_profit"] == 108
        assert data["operating_cash_flow"] == 180
        assert data["capital_expenditure"] == 50
        assert data["total_assets"] == 2500
        assert data["total_liabilities"] == 1500
        assert data["current_assets"] == 900
        assert data["current_liabilities"] == 450
        assert data["accounts_receivable"] == 80
        assert data["inventory"] == 60
        assert data["goodwill"] == 25

    def test_extract_financial_data_ignores_snapshot_inline_provenance(self):
        raw_data = """
        net_profit: 120.0  # 数据来源: eastmoney | source: eastmoney; report_period: 2025Q4
        net_margin: 12.0  # 数据来源: akshare | source: akshare; report_period: 2025Q4
        free_cash_flow: 130.0  # 数据来源: akshare | source: akshare; report_period: 2025Q4
        """

        data = extract_financial_data(raw_data)

        assert data["net_profit"] == 120.0
        assert data["net_margin"] == 12.0
        assert data["free_cash_flow"] == 130.0

    def test_extract_financial_data_expands_a_share_announcement_metric_aliases(self):
        raw_data = """
        每10股派现金额: 3.5
        股权登记日: 2026-05-20
        除权除息日: 2026-05-21
        回购金额下限: 100000000
        回购金额上限: 200000000
        回购期限(月): 12
        质押比例: 12.34%
        """

        data = extract_financial_data(raw_data)

        assert data["dividend_cash_per_10_shares"] == 3.5
        assert data["dividend_record_date"] == "2026-05-20"
        assert data["dividend_ex_date"] == "2026-05-21"
        assert data["buyback_amount_min"] == 100000000
        assert data["buyback_amount_max"] == 200000000
        assert data["buyback_period_months"] == 12
        assert abs(data["pledge_ratio"] - 0.1234) < 0.0001

    def test_extract_financial_data_expands_a_share_trend_quality_aliases(self):
        raw_data = """
        ROE趋势: improving
        毛利率趋势: stable
        自由现金流趋势: improving
        扣非净利润趋势: stable
        资产负债率趋势: improving
        流动比率趋势: improving
        现金流覆盖净利润: 1.2
        应收占营收变化: 1.0
        存货占营收变化: -0.5
        """

        data = extract_financial_data(raw_data)

        assert data["roe_trend"] == "improving"
        assert data["gross_margin_trend"] == "stable"
        assert data["free_cash_flow_trend"] == "improving"
        assert data["deducted_net_profit_trend"] == "stable"
        assert data["debt_ratio_trend"] == "improving"
        assert data["current_ratio_trend"] == "improving"
        assert data["cashflow_to_profit_ratio"] == 1.2
        assert data["receivables_to_revenue_change"] == 1.0
        assert data["inventory_to_revenue_change"] == -0.5


class TestBuffettQuant:
    def test_returns_valid_structure(self):
        result = buffett_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result
        assert "sub_analyses" in result
        assert "formatted_summary" in result
        assert result["signal"] in ("bullish", "neutral", "bearish")
        assert result["score"] >= 0
        assert result["max_score"] > 0

    def test_sub_analyses_keys(self):
        result = buffett_quantitative_analysis(MOCK_RAW_DATA)
        assert "基本面分析" in result["sub_analyses"]
        assert "护城河评估" in result["sub_analyses"]
        assert "管理层评估" in result["sub_analyses"]

    def test_evidence_table_present(self):
        result = buffett_quantitative_analysis(MOCK_RAW_DATA)
        assert "evidence_table" in result
        assert isinstance(result["evidence_table"], list)
        assert any(row["area"] == "基本面分析" for row in result["evidence_table"])
        assert "| 证据维度 | 规则 | 字段 |" in result["formatted_summary"]


class TestLynchQuant:
    def test_returns_valid_structure(self):
        result = lynch_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result
        assert result["signal"] in ("bullish", "neutral", "bearish")

    def test_weighted_signal(self):
        result = lynch_quantitative_analysis(MOCK_RAW_DATA)
        assert "weighted_score" in result
        assert "weighted_max" in result

    def test_sub_analyses_keys(self):
        result = lynch_quantitative_analysis(MOCK_RAW_DATA)
        assert "增长分析" in result["sub_analyses"]
        assert "估值分析" in result["sub_analyses"]
        assert "PEG调整" in result["sub_analyses"]


class TestGrahamQuant:
    def test_returns_valid_structure(self):
        result = graham_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result

    def test_graham_number_calculated(self):
        result = graham_quantitative_analysis(MOCK_RAW_DATA)
        valuation = result["sub_analyses"]["估值分析"]
        assert valuation["max_score"] > 0

    def test_sub_analyses_keys(self):
        result = graham_quantitative_analysis(MOCK_RAW_DATA)
        assert "盈利稳定性" in result["sub_analyses"]
        assert "财务实力" in result["sub_analyses"]
        assert "估值分析" in result["sub_analyses"]
        assert "安全边际" in result["sub_analyses"]


class TestMungerQuant:
    def test_returns_valid_structure(self):
        result = munger_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result

    def test_sub_analyses_keys(self):
        result = munger_quantitative_analysis(MOCK_RAW_DATA)
        assert "护城河强度" in result["sub_analyses"]
        assert "管理层评估" in result["sub_analyses"]
        assert "可预测性" in result["sub_analyses"]


def test_graham_evidence_table_present():
    result = graham_quantitative_analysis(MOCK_RAW_DATA)
    assert "evidence_table" in result
    assert isinstance(result["evidence_table"], list)
    assert any(row["field"] == "pe*pb" for row in result["evidence_table"])
    assert "证据维度" in result["formatted_summary"]


def test_munger_evidence_table_present():
    result = munger_quantitative_analysis(MOCK_RAW_DATA)
    assert "evidence_table" in result
    assert isinstance(result["evidence_table"], list)
    assert any(row["field"] == "gross_margin" for row in result["evidence_table"])
    assert "证据维度" in result["formatted_summary"]


class TestDamodaranQuant:
    def test_returns_valid_structure(self):
        result = damodaran_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result

    def test_sub_analyses_keys(self):
        result = damodaran_quantitative_analysis(MOCK_RAW_DATA)
        assert "生命周期定位" in result["sub_analyses"]
        assert "估值分析" in result["sub_analyses"]
        assert "不确定性评估" in result["sub_analyses"]

    def test_evidence_table_present(self):
        result = damodaran_quantitative_analysis(MOCK_RAW_DATA)
        assert "evidence_table" in result
        assert isinstance(result["evidence_table"], list)
        assert any(row["field"] == "revenue_growth" for row in result["evidence_table"])
        assert "证据维度" in result["formatted_summary"]


class TestWoodQuant:
    def test_returns_valid_structure(self):
        result = wood_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result

    def test_sub_analyses_keys(self):
        result = wood_quantitative_analysis(MOCK_RAW_DATA)
        assert "颠覆性潜力" in result["sub_analyses"]
        assert "创新增长" in result["sub_analyses"]


class TestAckmanQuant:
    def test_returns_valid_structure(self):
        result = ackman_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result

    def test_sub_analyses_keys(self):
        result = ackman_quantitative_analysis(MOCK_RAW_DATA)
        assert "商业质量" in result["sub_analyses"]
        assert "财务纪律" in result["sub_analyses"]


class TestFisherQuant:
    def test_returns_valid_structure(self):
        result = fisher_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result

    def test_sub_analyses_keys(self):
        result = fisher_quantitative_analysis(MOCK_RAW_DATA)
        assert "增长质量" in result["sub_analyses"]
        assert "利润率稳定性" in result["sub_analyses"]


class TestDruckenmillerQuant:
    def test_returns_valid_structure(self):
        result = druckenmiller_quantitative_analysis(MOCK_RAW_DATA)
        assert "signal" in result
        assert "score" in result
        assert "max_score" in result

    def test_sub_analyses_keys(self):
        result = druckenmiller_quantitative_analysis(MOCK_RAW_DATA)
        assert "增长动量" in result["sub_analyses"]
        assert "风险回报" in result["sub_analyses"]


def test_ackman_evidence_table_present():
    result = ackman_quantitative_analysis(MOCK_RAW_DATA)
    assert "evidence_table" in result
    assert isinstance(result["evidence_table"], list)
    assert any(row["field"] == "shareholder_yield" for row in result["evidence_table"])
    assert "shareholder_yield" in result["formatted_summary"]


def test_fisher_evidence_table_present():
    result = fisher_quantitative_analysis(MOCK_RAW_DATA)
    assert "evidence_table" in result
    assert isinstance(result["evidence_table"], list)
    assert any(row["field"] == "roe" for row in result["evidence_table"])
    assert "peg_ratio" in result["formatted_summary"]


def test_druckenmiller_evidence_table_present():
    result = druckenmiller_quantitative_analysis(MOCK_RAW_DATA)
    assert "evidence_table" in result
    assert isinstance(result["evidence_table"], list)
    assert any(row["field"] == "revenue_growth" for row in result["evidence_table"])
    assert "revenue_growth" in result["formatted_summary"]


def test_lynch_evidence_table_present():
    result = lynch_quantitative_analysis(MOCK_RAW_DATA)
    assert "evidence_table" in result
    assert isinstance(result["evidence_table"], list)
    assert any(row["field"] == "peg_ratio" for row in result["evidence_table"])
    assert "peg_ratio" in result["formatted_summary"]


def test_wood_evidence_table_present():
    result = wood_quantitative_analysis(MOCK_RAW_DATA)
    assert "evidence_table" in result
    assert isinstance(result["evidence_table"], list)
    assert any(row["field"] == "rd_ratio" for row in result["evidence_table"])
    assert "rd_ratio" in result["formatted_summary"]


GOVERNANCE_EXTENSION_RAW_DATA = """
ROE: 18%
debt_ratio: 0.35
net_margin: 22%
revenue_growth: 18%
free_cash_flow: 120
net_profit: 100
dividend_yield: 1.2%
buyback_amount_max: 200000000
insider_increase_events: 2
insider_decrease_events: 0
regulatory_penalty_severity: critical
goodwill_impairment_amount_max: 120000000
related_party_transaction_amount_max: 50000000
earnings_guidance_change_pct_min: -10%
earnings_guidance_change_pct_max: 35%
price_momentum_6m: 18%
"""


def test_buffett_governance_extension_evidence_present():
    result = buffett_quantitative_analysis(GOVERNANCE_EXTENSION_RAW_DATA)
    fields = {row["field"] for row in result["evidence_table"]}
    assert "management_alignment_summary" in fields
    assert "regulatory_penalty_severity" in fields
    assert "goodwill_impairment_amount_max" in fields


def test_fisher_governance_extension_evidence_present():
    result = fisher_quantitative_analysis(GOVERNANCE_EXTENSION_RAW_DATA)
    fields = {row["field"] for row in result["evidence_table"]}
    assert "regulatory_penalty_severity" in fields
    assert "related_party_transaction_amount_max" in fields
    assert "earnings_guidance_change_pct_max" in fields


def test_lynch_guidance_extension_evidence_present():
    result = lynch_quantitative_analysis(GOVERNANCE_EXTENSION_RAW_DATA)
    fields = {row["field"] for row in result["evidence_table"]}
    assert "earnings_guidance_change_pct_max" in fields


def test_druckenmiller_governance_extension_evidence_present():
    result = druckenmiller_quantitative_analysis(GOVERNANCE_EXTENSION_RAW_DATA)
    fields = {row["field"] for row in result["evidence_table"]}
    assert "earnings_guidance_change_pct_max" in fields
    assert "regulatory_penalty_severity" in fields


def test_ackman_governance_extension_evidence_present():
    result = ackman_quantitative_analysis(GOVERNANCE_EXTENSION_RAW_DATA)
    fields = {row["field"] for row in result["evidence_table"]}
    assert "buyback_amount_max" in fields
    assert "related_party_transaction_amount_max" in fields
    assert "regulatory_penalty_severity" in fields


def test_munger_governance_extension_evidence_present():
    result = munger_quantitative_analysis(GOVERNANCE_EXTENSION_RAW_DATA)
    fields = {row["field"] for row in result["evidence_table"]}
    assert "regulatory_penalty_severity" in fields
    assert "management_alignment_summary" in fields


class TestEmptyData:
    @pytest.mark.parametrize("analyzer", [
        buffett_quantitative_analysis,
        lynch_quantitative_analysis,
        graham_quantitative_analysis,
        munger_quantitative_analysis,
        damodaran_quantitative_analysis,
        wood_quantitative_analysis,
        ackman_quantitative_analysis,
        fisher_quantitative_analysis,
        druckenmiller_quantitative_analysis,
    ])
    def test_empty_input_no_crash(self, analyzer):
        result = analyzer("")
        assert "signal" in result
        assert "score" in result
        assert result["score"] >= 0
