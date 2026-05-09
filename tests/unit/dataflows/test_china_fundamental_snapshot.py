from tradingagents.dataflows.china_fundamental_snapshot import (
    build_china_announcement_signals,
    build_china_fundamental_snapshot,
    collect_china_free_source_payloads,
    format_china_fundamental_snapshot_report,
    validate_data_consistency,
    apply_consistency_fixes,
)
from tradingagents.agents.masters.quantitative_base import extract_financial_data


def test_snapshot_prefers_more_reliable_free_source_per_field():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "baostock",
                "data": {"pe_ttm": 9.8, "pb": 0.72, "roe": "N/A"},
                "updated_at": "2026-05-03 09:30:00",
            },
            {
                "source": "eastmoney",
                "data": {"pe_ttm": 8.6, "roe": 11.2, "net_profit": 464.5},
                "updated_at": "2026-05-03 10:00:00",
                "report_period": "2025Q4",
            },
        ],
    )

    assert snapshot["fields"]["pe_ttm"]["value"] == 8.6
    assert snapshot["fields"]["pe_ttm"]["source"] == "eastmoney"
    assert snapshot["fields"]["pb"]["value"] == 0.72
    assert snapshot["fields"]["pb"]["source"] == "baostock"
    assert snapshot["fields"]["roe"]["status"] == "present"
    assert snapshot["quality"]["present_count"] >= 3


def test_snapshot_prefers_newer_report_period_over_source_priority():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {"net_profit": 300.0},
                "updated_at": "2026-05-03 10:00:00",
                "report_period": "2024Q4",
            },
            {
                "source": "akshare",
                "data": {"net_profit": 420.0},
                "updated_at": "2026-05-03 09:00:00",
                "report_period": "2025Q4",
            },
        ],
    )

    assert snapshot["fields"]["net_profit"]["value"] == 420.0
    assert snapshot["fields"]["net_profit"]["source"] == "akshare"
    assert snapshot["fields"]["net_profit"]["report_period"] == "2025Q4"
    assert "newer_report_period" in snapshot["fields"]["net_profit"]["selection_reason"]


def test_snapshot_prefers_newer_updated_at_when_report_period_missing():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "akshare",
                "data": {"price": 10.1},
                "updated_at": "2026-05-03 09:58:00",
            },
            {
                "source": "baostock",
                "data": {"price": 10.3},
                "updated_at": "2026-05-03 10:01:00",
            },
        ],
    )

    assert snapshot["fields"]["price"]["value"] == 10.3
    assert snapshot["fields"]["price"]["source"] == "baostock"
    assert snapshot["fields"]["price"]["updated_at"] == "2026-05-03 10:01:00"


def test_snapshot_marks_estimated_and_missing_fields_separately():
    snapshot = build_china_fundamental_snapshot(
        "000002",
        [
            {
                "source": "akshare",
                "data": {
                    "revenue": "行业估算",
                    "net_profit": None,
                    "free_cash_flow": "--",
                    "debt_ratio": 68.1,
                },
            }
        ],
    )

    assert snapshot["fields"]["revenue"]["status"] == "estimated"
    assert snapshot["fields"]["net_profit"]["status"] == "missing"
    assert snapshot["fields"]["free_cash_flow"]["status"] == "missing"
    assert "revenue" in snapshot["quality"]["estimated_fields"]
    assert "net_profit" in snapshot["quality"]["missing_required_fields"]


def test_snapshot_maps_a_share_three_statement_fields_and_derived_metrics():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "akshare",
                "data": {
                    "income_statement": [
                        {
                            "营业总收入": 1000.0,
                            "净利润": 120.0,
                            "扣除非经常性损益后的净利润": 108.0,
                        }
                    ],
                    "balance_sheet": [
                        {
                            "资产总计": 2500.0,
                            "负债合计": 1500.0,
                            "流动资产合计": 900.0,
                            "流动负债合计": 450.0,
                            "应收账款": 80.0,
                            "合同负债": 150.0,
                            "存货": 60.0,
                            "\u5408\u540c\u8d44\u4ea7": 110.0,
                            "\u5e94\u4ed8\u8d26\u6b3e": 140.0,
                            "商誉": 25.0,
                        }
                    ],
                    "cash_flow": [
                        {
                            "经营活动产生的现金流量净额": 180.0,
                            "购建固定资产、无形资产和其他长期资产支付的现金": 50.0,
                        }
                    ],
                },
                "report_period": "2025Q4",
            }
        ],
    )

    assert snapshot["fields"]["revenue"]["value"] == 1000.0
    assert snapshot["fields"]["deducted_net_profit"]["value"] == 108.0
    assert snapshot["fields"]["operating_cash_flow"]["value"] == 180.0
    assert snapshot["fields"]["free_cash_flow"]["value"] == 130.0
    assert snapshot["fields"]["debt_ratio"]["value"] == 60.0
    assert snapshot["fields"]["current_ratio"]["value"] == 2.0
    assert snapshot["fields"]["net_margin"]["value"] == 12.0
    assert snapshot["fields"]["accounts_receivable"]["value"] == 80.0
    assert snapshot["fields"]["contract_liabilities"]["value"] == 150.0
    assert snapshot["fields"]["contract_assets"]["value"] == 110.0
    assert snapshot["fields"]["accounts_payable"]["value"] == 140.0
    assert snapshot["fields"]["inventory"]["value"] == 60.0
    assert snapshot["fields"]["goodwill"]["value"] == 25.0


def test_snapshot_builds_a_share_financial_trend_quality_fields():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "periods": [
                        {
                            "report_date": "2025-12-31",
                            "roe": 18.0,
                            "gross_margin": 32.0,
                            "revenue": 1000.0,
                            "net_profit": 150.0,
                            "deducted_net_profit": 135.0,
                            "accounts_receivable": 120.0,
                            "contract_liabilities": 200.0,
                            "inventory": 90.0,
                            "contract_assets": 70.0,
                            "accounts_payable": 160.0,
                            "operating_cash_flow": 180.0,
                            "free_cash_flow": 140.0,
                            "debt_ratio": 52.0,
                            "current_ratio": 2.1,
                        },
                        {
                            "report_date": "2024-12-31",
                            "roe": 16.0,
                            "gross_margin": 30.0,
                            "revenue": 900.0,
                            "net_profit": 120.0,
                            "deducted_net_profit": 110.0,
                            "accounts_receivable": 99.0,
                            "contract_liabilities": 135.0,
                            "inventory": 81.0,
                            "contract_assets": 45.0,
                            "accounts_payable": 108.0,
                            "operating_cash_flow": 132.0,
                            "free_cash_flow": 95.0,
                            "debt_ratio": 55.0,
                            "current_ratio": 1.8,
                        },
                    ]
                },
                "report_period": "2025Q4",
            }
        ],
    )

    assert snapshot["fields"]["roe_trend"]["value"] == "improving"
    assert snapshot["fields"]["gross_margin_trend"]["value"] == "improving"
    assert snapshot["fields"]["free_cash_flow_trend"]["value"] == "improving"
    assert snapshot["fields"]["deducted_net_profit_trend"]["value"] == "improving"
    assert snapshot["fields"]["debt_ratio_trend"]["value"] == "improving"
    assert snapshot["fields"]["current_ratio_trend"]["value"] == "improving"
    assert snapshot["fields"]["cashflow_to_profit_ratio"]["value"] == 1.2
    assert snapshot["fields"]["receivables_to_revenue_change"]["value"] == 1.0
    assert snapshot["fields"]["inventory_to_revenue_change"]["value"] == 0.0
    assert snapshot["fields"]["contract_liabilities_to_revenue_change"]["value"] == 5.0
    assert snapshot["fields"]["contract_assets_to_revenue_change"]["value"] == 2.0
    assert snapshot["fields"]["accounts_payable_to_revenue_change"]["value"] == 4.0


def test_snapshot_report_formats_percentage_fields_for_master_quant_rules():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "revenue": 1000,
                    "net_profit": 120,
                    "roe": 11.2,
                    "gross_margin": 30.5,
                    "debt_ratio": 60,
                    "operating_cash_flow": 180,
                    "free_cash_flow": 130,
                    "pe_ttm": 8.6,
                    "pb": 0.7,
                },
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)
    data = extract_financial_data(report)

    assert "roe: 11.2%" in report
    assert "debt_ratio: 60%" in report
    assert abs(data["roe"] - 0.112) < 0.0001
    assert abs(data["debt_ratio"] - 0.6) < 0.0001


def test_announcement_signals_classify_a_share_governance_events():
    signals = build_china_announcement_signals(
        [
            {"title": "2025年度利润分配预案 每10股派发现金红利3元", "type": "announcement"},
            {"title": "关于以集中竞价方式回购公司股份的公告", "type": "announcement"},
            {"title": "控股股东部分股份质押公告", "type": "announcement"},
            {"title": "重大诉讼进展公告", "type": "announcement"},
            {"title": "关联交易公告", "type": "announcement"},
            {"title": "董事长辞职及聘任高级管理人员公告", "type": "announcement"},
            {"title": "普通行业新闻", "type": "news"},
        ]
    )

    assert signals["dividend_events"] == 1
    assert signals["buyback_events"] == 1
    assert signals["pledge_risk_events"] == 1
    assert signals["litigation_risk_events"] == 1
    assert signals["related_party_transaction_events"] == 1
    assert signals["management_change_events"] == 1
    assert "利润分配预案" in signals["shareholder_return_summary"]


def test_announcement_signals_parse_dividend_buyback_and_pledge_metrics():
    signals = build_china_announcement_signals(
        [
            {"title": "2025年度利润分配预案 每10股派发现金红利3.5元（含税）", "type": "announcement"},
            {"title": "关于回购公司股份方案的公告 回购资金总额不低于人民币1亿元且不超过人民币2亿元", "type": "announcement"},
            {"title": "控股股东股份质押公告 本次质押占其所持股份比例12.34%", "type": "announcement"},
        ]
    )

    assert signals["dividend_cash_per_10_shares"] == 3.5
    assert signals["buyback_amount_min"] == 100000000.0
    assert signals["buyback_amount_max"] == 200000000.0
    assert signals["pledge_ratio"] == 12.34


def test_announcement_signals_parse_governance_and_guidance_extensions():
    signals = build_china_announcement_signals(
        [
            {"title": "关于董事长增持公司股份计划的公告", "type": "announcement"},
            {"title": "关于高级管理人员减持股份计划的公告", "type": "announcement"},
            {"title": "2025年年度业绩预增公告 预计净利润同比增长50%", "type": "announcement"},
            {"title": "2025年半年度业绩预亏公告", "type": "announcement"},
            {"title": "收到中国证监会立案告知书的公告 罚款500万元", "type": "announcement"},
            {"title": "关于计提商誉减值准备的公告 本次计提商誉减值准备1.2亿元", "type": "announcement"},
            {"title": "关于计提资产减值准备的公告 本次计提资产减值准备8000万元", "type": "announcement"},
            {"title": "关联交易公告 预计交易金额不超过5000万元", "type": "announcement"},
        ]
    )

    assert signals["insider_increase_events"] == 1
    assert signals["insider_decrease_events"] == 1
    assert signals["earnings_positive_events"] == 1
    assert signals["earnings_negative_events"] == 1
    assert signals["regulatory_penalty_events"] == 1
    assert signals["regulatory_penalty_severity"] == "critical"
    assert signals["regulatory_penalty_amount_max"] == 5000000.0
    assert signals["goodwill_impairment_events"] == 1
    assert signals["goodwill_impairment_amount_max"] == 120000000.0
    assert signals["asset_impairment_events"] == 1
    assert signals["asset_impairment_amount_max"] == 80000000.0
    assert signals["related_party_transaction_amount_max"] == 50000000.0
    assert "增持公司股份计划" in signals["management_alignment_summary"]
    assert "业绩预增公告" in signals["earnings_guidance_summary"]
    assert signals["earnings_guidance_change_pct_min"] == 50.0
    assert signals["earnings_guidance_change_pct_max"] == 50.0


def test_announcement_signals_parse_earnings_guidance_numeric_ranges():
    signals = build_china_announcement_signals(
        [
            {"title": "2025\u5e74\u534a\u5e74\u5ea6\u4e1a\u7ee9\u9884\u589e\u516c\u544a \u9884\u8ba1\u51c0\u5229\u6da6\u540c\u6bd4\u589e\u957f50%\u81f380%\uff0c\u51c0\u5229\u6da6\u4e3a1.2\u4ebf\u5143\u81f31.5\u4ebf\u5143\uff0c\u8425\u4e1a\u6536\u516512\u4ebf\u5143\u81f315\u4ebf\u5143", "type": "announcement"},
            {"title": "2025\u5e74\u4e09\u5b63\u5ea6\u4e1a\u7ee9\u9884\u4e8f\u516c\u544a \u9884\u8ba1\u51c0\u5229\u6da6\u540c\u6bd4\u4e0b\u964d20%-35%\uff0c\u4e8f\u635f3000\u4e07\u5143\u81f35000\u4e07\u5143\uff0c\u8425\u65368\u4ebf\u5143\u81f39\u4ebf\u5143", "type": "announcement"},
        ]
    )

    assert signals["earnings_guidance_change_pct_min"] == -35.0
    assert signals["earnings_guidance_change_pct_max"] == 80.0
    assert signals["earnings_guidance_net_profit_min"] == -50000000.0
    assert signals["earnings_guidance_net_profit_max"] == 150000000.0
    assert signals["earnings_guidance_revenue_min"] == 800000000.0
    assert signals["earnings_guidance_revenue_max"] == 1500000000.0


def test_announcement_signals_parse_dividend_and_buyback_dates():
    signals = build_china_announcement_signals(
        [
            {
                "title": "2025年度权益分派实施公告 股权登记日：2026年5月20日 除权除息日：2026年5月21日",
                "type": "announcement",
            },
            {
                "title": "关于回购公司股份方案的公告 回购期限为自董事会审议通过之日起12个月内",
                "type": "announcement",
            },
        ]
    )

    assert signals["dividend_record_date"] == "2026-05-20"
    assert signals["dividend_ex_date"] == "2026-05-21"
    assert signals["buyback_period_months"] == 12


def test_snapshot_exposes_announcement_signals_for_master_quality():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "akshare",
                "data": build_china_announcement_signals(
                    [
                        {"title": "年度权益分派实施公告", "type": "announcement"},
                        {"title": "股份回购进展公告", "type": "announcement"},
                    ]
                ),
                "report_period": "recent_90d",
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)

    assert snapshot["fields"]["dividend_events"]["value"] == 1
    assert snapshot["fields"]["buyback_events"]["value"] == 1
    assert "dividend_events: 1" in report
    assert "buyback_events: 1" in report


def test_snapshot_exposes_parsed_announcement_metrics_to_master_report():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "akshare",
                "data": build_china_announcement_signals(
                    [
                        {"title": "利润分配方案 每10股派发现金红利2元", "type": "announcement"},
                        {"title": "回购金额不低于5000万元且不超过1亿元", "type": "announcement"},
                        {"title": "股东股份质押公告 质押比例8.5%", "type": "announcement"},
                    ]
                ),
                "report_period": "recent_90d",
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)

    assert snapshot["fields"]["dividend_cash_per_10_shares"]["value"] == 2
    assert snapshot["fields"]["buyback_amount_min"]["value"] == 50000000.0
    assert snapshot["fields"]["buyback_amount_max"]["value"] == 100000000.0
    assert snapshot["fields"]["pledge_ratio"]["value"] == 8.5
    assert "dividend_cash_per_10_shares: 2" in report
    assert "pledge_ratio: 8.5%" in report


def test_snapshot_exposes_extended_governance_fields_to_master_report():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "akshare",
                "data": build_china_announcement_signals(
                    [
                        {"title": "关于董事长增持公司股份计划的公告", "type": "announcement"},
                        {"title": "关于高级管理人员减持股份计划的公告", "type": "announcement"},
                        {"title": "2025年年度业绩预增公告", "type": "announcement"},
                        {"title": "\u6536\u5230\u4e2d\u56fd\u8bc1\u76d1\u4f1a\u7acb\u6848\u544a\u77e5\u4e66\u7684\u516c\u544a \u7f5a\u6b3e500\u4e07\u5143", "type": "announcement"},
                        {"title": "关于计提商誉减值准备的公告 本次计提商誉减值准备1.2亿元", "type": "announcement"},
                    ]
                ),
                "report_period": "recent_90d",
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)

    assert snapshot["fields"]["insider_increase_events"]["value"] == 1
    assert snapshot["fields"]["earnings_positive_events"]["value"] == 1
    assert snapshot["fields"]["regulatory_penalty_events"]["value"] == 1
    assert snapshot["fields"]["regulatory_penalty_severity"]["value"] == "critical"
    assert snapshot["fields"]["regulatory_penalty_amount_max"]["value"] == 5000000.0
    assert snapshot["fields"]["goodwill_impairment_amount_max"]["value"] == 120000000.0
    assert "insider_increase_events: 1" in report
    assert "goodwill_impairment_amount_max: 120000000.0" in report
    assert "regulatory_penalty_severity: critical" in report


def test_announcement_signals_parse_penalty_and_asset_impairment_amounts():
    signals = build_china_announcement_signals(
        [
            {"title": "收到行政处罚决定书 罚款500万元", "type": "announcement"},
            {"title": "关于计提资产减值准备的公告 本次计提资产减值准备8000万元", "type": "announcement"},
        ]
    )

    assert signals["regulatory_penalty_amount_max"] == 5000000.0
    assert signals["asset_impairment_events"] == 1
    assert signals["asset_impairment_amount_max"] == 80000000.0


def test_snapshot_exposes_earnings_guidance_numeric_ranges_to_master_report():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "akshare",
                "data": build_china_announcement_signals(
                    [
                        {"title": "2025\u5e74\u534a\u5e74\u5ea6\u4e1a\u7ee9\u9884\u589e\u516c\u544a \u9884\u8ba1\u51c0\u5229\u6da6\u540c\u6bd4\u589e\u957f50%\u81f380%\uff0c\u51c0\u5229\u6da6\u4e3a1.2\u4ebf\u5143\u81f31.5\u4ebf\u5143\uff0c\u8425\u4e1a\u6536\u516512\u4ebf\u5143\u81f315\u4ebf\u5143", "type": "announcement"},
                    ]
                ),
                "report_period": "recent_90d",
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)

    assert snapshot["fields"]["earnings_guidance_change_pct_min"]["value"] == 50.0
    assert snapshot["fields"]["earnings_guidance_change_pct_max"]["value"] == 80.0
    assert snapshot["fields"]["earnings_guidance_net_profit_min"]["value"] == 120000000.0
    assert snapshot["fields"]["earnings_guidance_net_profit_max"]["value"] == 150000000.0
    assert snapshot["fields"]["earnings_guidance_revenue_min"]["value"] == 1200000000.0
    assert snapshot["fields"]["earnings_guidance_revenue_max"]["value"] == 1500000000.0
    assert "earnings_guidance_change_pct_max: 80%" in report
    assert "earnings_guidance_revenue_max: 1500000000.0" in report


def test_snapshot_exposes_announcement_dates_to_master_report():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "akshare",
                "data": build_china_announcement_signals(
                    [
                        {
                            "title": "权益分派实施公告 股权登记日：2026年5月20日 除权除息日：2026年5月21日",
                            "type": "announcement",
                        },
                        {"title": "回购期限为自董事会审议通过之日起6个月内", "type": "announcement"},
                    ]
                ),
                "report_period": "recent_90d",
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)

    assert snapshot["fields"]["dividend_record_date"]["value"] == "2026-05-20"
    assert snapshot["fields"]["dividend_ex_date"]["value"] == "2026-05-21"
    assert snapshot["fields"]["buyback_period_months"]["value"] == 6
    assert "dividend_record_date: 2026-05-20" in report
    assert "buyback_period_months: 6" in report


def test_snapshot_report_includes_selection_reason_metadata():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {"net_profit": 300.0},
                "updated_at": "2026-05-03 10:00:00",
                "report_period": "2024Q4",
            },
            {
                "source": "akshare",
                "data": {"net_profit": 420.0},
                "updated_at": "2026-05-03 09:00:00",
                "report_period": "2025Q4",
            },
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)

    assert snapshot["fields"]["net_profit"]["selection_reason"] == "newer_report_period"
    assert "selection_reason: newer_report_period" in report


def test_snapshot_report_exposes_quality_source_and_master_ready_aliases():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "price": 12.34,
                    "pe_ttm": 8.6,
                    "pb": 0.72,
                    "revenue": 1648.7,
                    "net_profit": 464.5,
                    "roe": 11.2,
                    "operating_cash_flow": 521.0,
                    "free_cash_flow": 420.0,
                    "debt_ratio": 91.4,
                },
                "updated_at": "2026-05-03 10:00:00",
                "report_period": "2025Q4",
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)

    assert "A股免费数据融合质量报告" in report
    assert "数据质量评分" in report
    assert "net_profit: 464.5" in report
    assert "free_cash_flow: 420.0" in report
    assert "数据来源: eastmoney" in report
    assert "source: eastmoney" in report
    assert "report_period: 2025Q4" in report


def test_collect_free_source_payloads_uses_available_sources_and_ignores_failures(monkeypatch):
    class EastMoney:
        async def get_stock_quotes(self, symbol):
            return {"pe_ttm": 8.6, "pb": 0.72}

        async def get_financial_data(self, symbol):
            return {"latest": {"net_profit": 464.5, "report_period": "2025Q4"}}

    class AKShare:
        async def get_stock_quotes(self, symbol):
            raise RuntimeError("temporary network error")

        async def get_financial_data(self, symbol):
            return {"main_indicators": [{"roe": 11.2, "revenue": 1648.7}]}

    class BaoStock:
        async def get_financial_data(self, symbol):
            return {"cash_flow_data": [{"operating_cash_flow": 521.0}]}

    monkeypatch.setattr("tradingagents.dataflows.china_fundamental_snapshot.get_eastmoney_direct_provider", lambda: EastMoney())
    monkeypatch.setattr("tradingagents.dataflows.china_fundamental_snapshot.get_akshare_provider", lambda: AKShare())
    monkeypatch.setattr("tradingagents.dataflows.china_fundamental_snapshot.get_baostock_provider", lambda: BaoStock())

    payloads = collect_china_free_source_payloads("000001")
    snapshot = build_china_fundamental_snapshot("000001", payloads)

    source_order = [payload["source"] for payload in payloads]
    assert source_order[:3] == ["eastmoney", "akshare", "baostock"]
    assert snapshot["fields"]["pe_ttm"]["source"] == "eastmoney"
    # roe source may be baostock_direct (now available) or akshare depending on data priority
    assert snapshot["fields"]["roe"]["source"] in ("baostock_direct", "akshare")
    # operating_cash_flow source may vary due to baostock_direct now being available
    assert snapshot["fields"]["operating_cash_flow"]["source"] in ("baostock", "baostock_direct", "akshare_indicator_lg")


def test_collect_free_source_payloads_disconnects_providers(monkeypatch):
    disconnect_calls = []

    class Provider:
        def __init__(self, name):
            self.name = name

        async def get_stock_quotes(self, symbol):
            return {"price": 10.0}

        async def disconnect(self):
            disconnect_calls.append(self.name)

    monkeypatch.setattr(
        "tradingagents.dataflows.china_fundamental_snapshot.get_eastmoney_direct_provider",
        lambda: Provider("eastmoney"),
    )
    monkeypatch.setattr(
        "tradingagents.dataflows.china_fundamental_snapshot.get_akshare_provider",
        lambda: Provider("akshare"),
    )
    monkeypatch.setattr(
        "tradingagents.dataflows.china_fundamental_snapshot.get_baostock_provider",
        lambda: Provider("baostock"),
    )
    monkeypatch.setattr(
        "tradingagents.dataflows.china_fundamental_snapshot.collect_china_announcement_payload",
        lambda symbol: None,
    )

    payloads = collect_china_free_source_payloads("000001")

    # 由于 indicator_lg 和可能的 akshare_direct（当覆盖率不足时），payloads 数量会变化
    source_names = [payload["source"] for payload in payloads]
    assert "eastmoney" in source_names
    assert "akshare" in source_names
    assert "baostock" in source_names
    assert disconnect_calls == ["eastmoney", "akshare", "baostock"]


def test_collect_free_source_payloads_appends_announcement_signals(monkeypatch):
    class EmptyProvider:
        pass

    class NewsManager:
        def get_news_with_fallback(self, code, days, limit, include_announcements):
            return (
                [
                    {"title": "年度权益分派实施公告", "type": "announcement"},
                    {"title": "关于股份回购进展公告", "type": "announcement"},
                ],
                "akshare",
            )

    monkeypatch.setattr("tradingagents.dataflows.china_fundamental_snapshot.get_eastmoney_direct_provider", lambda: EmptyProvider())
    monkeypatch.setattr("tradingagents.dataflows.china_fundamental_snapshot.get_akshare_provider", lambda: EmptyProvider())
    monkeypatch.setattr("tradingagents.dataflows.china_fundamental_snapshot.get_baostock_provider", lambda: EmptyProvider())
    monkeypatch.setattr("app.services.data_sources.manager.DataSourceManager", lambda: NewsManager())

    payloads = collect_china_free_source_payloads("000001")
    snapshot = build_china_fundamental_snapshot("000001", payloads)

    assert "akshare" in [payload["source"] for payload in payloads]
    assert snapshot["fields"]["dividend_events"]["value"] == 1
    assert snapshot["fields"]["buyback_events"]["value"] == 1


def test_validate_data_consistency_detects_positive_pe_with_negative_eps():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "eps": -0.5,
                    "pe": 8.0,
                    "pe_ttm": 7.5,
                    "net_profit": -100,
                },
            }
        ],
    )

    issues = validate_data_consistency(snapshot)
    pe_issues = [i for i in issues if i["rule"] == "PE_vs_EPS_sign"]
    assert len(pe_issues) >= 1
    assert any("pe" in i["fields"] for i in pe_issues)
    assert any("pe_ttm" in i["fields"] for i in pe_issues)
    for issue in pe_issues:
        assert issue["suggested_fix"].get("pe") == "N/A" or issue["suggested_fix"].get("pe_ttm") == "N/A"


def test_validate_data_consistency_detects_abnormally_high_pb():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "pb": 114.0,
                    "book_value_per_share": 0.005,
                    "price": 10.0,
                },
            }
        ],
    )

    issues = validate_data_consistency(snapshot)
    pb_issues = [i for i in issues if "PB" in i["rule"]]
    assert len(pb_issues) >= 1


def test_validate_data_consistency_detects_roe_net_margin_sign_conflict():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "roe": -3.13,
                    "net_margin": 5.2,
                    "net_profit": 50,
                    "revenue": 1000,
                },
            }
        ],
    )

    issues = validate_data_consistency(snapshot)
    roe_issues = [i for i in issues if i["rule"] == "ROE_vs_net_margin_sign"]
    assert len(roe_issues) == 1
    assert "roe" in roe_issues[0]["suggested_fix"]


def test_validate_data_consistency_detects_cashflow_profit_sign_conflict():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "operating_cash_flow": -200,
                    "net_profit": 100,
                },
            }
        ],
    )

    issues = validate_data_consistency(snapshot)
    cf_issues = [i for i in issues if i["rule"] == "cashflow_vs_profit_sign"]
    assert len(cf_issues) == 1


def test_validate_data_consistency_passes_for_consistent_data():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "eps": 0.5,
                    "pe_ttm": 8.6,
                    "pb": 0.72,
                    "book_value_per_share": 17.0,
                    "price": 12.24,
                    "roe": 11.2,
                    "net_margin": 12.0,
                    "net_profit": 120,
                    "revenue": 1000,
                    "operating_cash_flow": 180,
                },
            }
        ],
    )

    issues = validate_data_consistency(snapshot)
    assert len(issues) == 0


def test_apply_consistency_fixes_corrects_pe_to_na_when_eps_negative():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "eps": -0.5,
                    "pe": 8.0,
                    "pe_ttm": 7.5,
                },
            }
        ],
    )

    fixed = apply_consistency_fixes(snapshot)
    assert fixed["fields"]["pe"]["status"] == "corrected_to_na"
    assert fixed["fields"]["pe"]["value"] is None
    assert "consistency_issues" in fixed


def test_format_report_includes_consistency_validation_section():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "eps": -0.5,
                    "pe": 8.0,
                },
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)
    assert "数据一致性验证" in report


def test_format_report_shows_pass_when_no_issues():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "eastmoney",
                "data": {
                    "eps": 0.5,
                    "pe_ttm": 8.6,
                    "roe": 11.2,
                    "net_margin": 12.0,
                    "net_profit": 120,
                    "revenue": 1000,
                    "operating_cash_flow": 180,
                },
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)
    assert "数据一致性验证" in report
    assert "通过" in report
