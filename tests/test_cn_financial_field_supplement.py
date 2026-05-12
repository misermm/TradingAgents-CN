from tradingagents.dataflows.china_fundamental_snapshot import (
    build_china_fundamental_snapshot,
)
from tradingagents.graph.cn_fact_snapshot import build_cn_fact_snapshot
from tradingagents.graph.report_audit import reconcile_cn_decision


def test_nested_financial_statement_rows_supplement_core_fields():
    snapshot = build_china_fundamental_snapshot(
        "000002",
        [
            {
                "source": "sina_finance",
                "updated_at": "2026-05-11 10:00:00",
                "data": {
                    "income_statement": [
                        {"报表日期": "2025-12-31", "营业总收入": "1000000000"}
                    ],
                    "cash_flow": [
                        {"报表日期": "2025-12-31", "经营活动产生的现金流量净额": "250000000"}
                    ],
                    "balance_sheet": [
                        {"报表日期": "2025-12-31", "负债合计": "600000000"}
                    ],
                },
            }
        ],
    )

    fields = snapshot["fields"]
    assert fields["revenue"]["status"] == "present"
    assert fields["revenue"]["value"] == 1000000000
    assert fields["revenue"]["source"] == "sina_finance"
    assert fields["revenue"]["report_period"] == "2025-12-31"
    assert fields["operating_cash_flow"]["value"] == 250000000
    assert fields["total_liabilities"]["value"] == 600000000


def test_financial_supplement_does_not_override_same_period_higher_priority_source():
    snapshot = build_china_fundamental_snapshot(
        "000002",
        [
            {
                "source": "eastmoney",
                "updated_at": "2026-05-11 10:00:00",
                "report_period": "2025-12-31",
                "data": {"latest": {"report_date": "2025-12-31", "revenue": 120}},
            },
            {
                "source": "sina_finance",
                "updated_at": "2026-05-11 10:00:00",
                "data": {
                    "income_statement": [
                        {"报表日期": "2025-12-31", "营业总收入": 90}
                    ]
                },
            },
        ],
    )

    revenue = snapshot["fields"]["revenue"]
    assert revenue["value"] == 120
    assert revenue["source"] == "eastmoney"
    assert "eastmoney" in snapshot["sources_used"]
    assert "sina_finance" not in snapshot["sources_used"]


def test_reconcile_audits_raw_decision_even_when_result_has_no_decision_field():
    decision = reconcile_cn_decision(
        {
            "reports": {"final_trade_decision": "最终建议：买入。"},
            "cn_fact_snapshot": {
                "current_price": 4.0,
                "quality": {"grade": "B", "missing_fields": [], "conflicts": []},
            },
        },
        {"action": "买入", "confidence": 0.8, "target_price": 20.0},
    )

    assert "TARGET_PRICE_INVALID" in {issue["code"] for issue in decision["audit"]["issues"]}
    assert decision["action"] == "持有"
    assert decision["confidence"] <= 0.45


def test_extract_required_fields_from_line_item_list_payload():
    snapshot = build_china_fundamental_snapshot(
        "000002",
        [
            {
                "source": "akshare_direct",
                "updated_at": "2026-05-12 09:00:00",
                "report_period": "2025-12-31",
                "data": {
                    "financial_statement": [
                        {"item": "营业总收入", "value": "1234567890"},
                        {"item": "负债合计", "value": "888888888"},
                    ]
                },
            }
        ],
    )

    assert snapshot["fields"]["revenue"]["status"] == "present"
    assert snapshot["fields"]["total_liabilities"]["status"] == "present"


def test_cn_fact_snapshot_prefers_market_report_current_price():
    cn_fact = build_cn_fact_snapshot(
        ticker="000002",
        market_info={"is_china": True, "stock_name": "万科A"},
        fundamental_snapshot={
            "fields": {
                "price": {"value": 4.06, "source": "eastmoney"},
            },
            "quality": {},
            "sources_used": ["eastmoney"],
        },
        trade_date="2026-05-12",
        market_report="当前价格：3.91 元，短期偏强。",
    )

    assert cn_fact["current_price"] == 3.91
    assert cn_fact["price_source"] == "market_report"


def test_short_alias_pe_does_not_match_report_period_key():
    snapshot = build_china_fundamental_snapshot(
        "000002",
        [
            {
                "source": "akshare_direct",
                "updated_at": "2026-05-12 09:00:00",
                "data": {
                    "report_period": "2025-03-31",
                    "income_statement": [{"report_period": "2025-03-31"}],
                },
            }
        ],
    )

    assert snapshot["fields"]["pe"]["status"] == "missing"


def test_derive_total_liabilities_from_total_assets_and_debt_ratio():
    snapshot = build_china_fundamental_snapshot(
        "000002",
        [
            {
                "source": "akshare_indicator_lg",
                "updated_at": "2026-05-12 09:00:00",
                "report_period": "2025-12-31",
                "data": {
                    "total_assets": 1000.0,
                    "debt_ratio": 77.0,
                },
            }
        ],
    )

    field = snapshot["fields"]["total_liabilities"]
    assert field["status"] == "present"
    assert field["source"].endswith(":derived")
    assert field["value"] == 770.0


def test_conflict_detection_skips_mismatched_report_periods():
    snapshot = build_china_fundamental_snapshot(
        "000002",
        [
            {
                "source": "baostock_direct",
                "updated_at": "2026-05-12 10:00:00",
                "report_period": "2026Q1",
                "data": {"net_profit_yoy": 5.0},
            },
            {
                "source": "akshare_indicator_lg",
                "updated_at": "2026-05-12 10:00:00",
                "report_period": "2025-12-31",
                "data": {"net_profit_yoy": -2036.4279},
            },
        ],
    )

    assert "net_profit_yoy" not in snapshot["quality"]["conflict_fields"]
