from tradingagents.dataflows.china_fundamental_snapshot import (
    build_china_announcement_signals,
    build_china_fundamental_snapshot,
    format_china_fundamental_snapshot_report,
)


def test_announcement_signals_parse_earnings_guidance_revenue_change_ranges():
    signals = build_china_announcement_signals(
        [
            {
                "title": "2025\u5e74\u534a\u5e74\u5ea6\u4e1a\u7ee9\u9884\u589e\u516c\u544a "
                "\u9884\u8ba1\u51c0\u5229\u6da6\u540c\u6bd4\u589e\u957f50%\u81f380%\uff0c"
                "\u8425\u4e1a\u6536\u5165\u540c\u6bd4\u589e\u957f20%\u81f330%\uff0c"
                "\u51c0\u5229\u6da6\u4e3a1.2\u4ebf\u5143\u81f31.5\u4ebf\u5143\uff0c"
                "\u8425\u4e1a\u6536\u516512\u4ebf\u5143\u81f315\u4ebf\u5143",
                "type": "announcement",
            },
            {
                "title": "2025\u5e74\u4e09\u5b63\u5ea6\u4e1a\u7ee9\u9884\u4e8f\u516c\u544a "
                "\u9884\u8ba1\u51c0\u5229\u6da6\u540c\u6bd4\u4e0b\u964d20%-35%\uff0c"
                "\u8425\u6536\u540c\u6bd4\u4e0b\u964d10%-15%\uff0c"
                "\u4e8f\u635f3000\u4e07\u5143\u81f35000\u4e07\u5143\uff0c"
                "\u8425\u65368\u4ebf\u5143\u81f39\u4ebf\u5143",
                "type": "announcement",
            },
        ]
    )

    assert signals["earnings_guidance_change_pct_min"] == -35.0
    assert signals["earnings_guidance_change_pct_max"] == 80.0
    assert signals["earnings_guidance_revenue_change_pct_min"] == -15.0
    assert signals["earnings_guidance_revenue_change_pct_max"] == 30.0


def test_snapshot_exposes_earnings_guidance_revenue_change_ranges_to_master_report():
    snapshot = build_china_fundamental_snapshot(
        "000001",
        [
            {
                "source": "akshare",
                "data": build_china_announcement_signals(
                    [
                        {
                            "title": "2025\u5e74\u534a\u5e74\u5ea6\u4e1a\u7ee9\u9884\u589e\u516c\u544a "
                            "\u9884\u8ba1\u51c0\u5229\u6da6\u540c\u6bd4\u589e\u957f50%\u81f380%\uff0c"
                            "\u8425\u4e1a\u6536\u5165\u540c\u6bd4\u589e\u957f20%\u81f330%\uff0c"
                            "\u51c0\u5229\u6da6\u4e3a1.2\u4ebf\u5143\u81f31.5\u4ebf\u5143\uff0c"
                            "\u8425\u4e1a\u6536\u516512\u4ebf\u5143\u81f315\u4ebf\u5143",
                            "type": "announcement",
                        }
                    ]
                ),
                "report_period": "recent_90d",
            }
        ],
    )

    report = format_china_fundamental_snapshot_report(snapshot)

    assert snapshot["fields"]["earnings_guidance_revenue_change_pct_min"]["value"] == 20.0
    assert snapshot["fields"]["earnings_guidance_revenue_change_pct_max"]["value"] == 30.0
    assert "earnings_guidance_revenue_change_pct_max: 30%" in report
