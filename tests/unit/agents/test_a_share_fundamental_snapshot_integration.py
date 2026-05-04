from unittest import mock

from tradingagents.agents.utils.agent_utils import Toolkit


def test_a_share_fundamental_tool_appends_free_source_snapshot_report():
    market_info = {
        "is_china": True,
        "is_hk": False,
        "is_us": False,
        "market_name": "A股",
        "currency_name": "人民币",
        "currency_symbol": "¥",
    }

    with mock.patch("tradingagents.utils.stock_utils.StockUtils.get_market_info", return_value=market_info), \
         mock.patch("tradingagents.dataflows.interface.get_china_stock_data_unified") as market_data, \
         mock.patch("tradingagents.dataflows.optimized_china_data.OptimizedChinaDataProvider") as provider_cls:
        market_data.return_value = "price: 12.34\npe_ttm: 8.6\npb: 0.72"
        provider = provider_cls.return_value
        provider._generate_fundamentals_report.return_value = (
            "revenue: 1648.7\n"
            "net_profit: 464.5\n"
            "roe: 11.2\n"
            "free_cash_flow: 420.0\n"
            "debt_ratio: 91.4"
        )

        result = Toolkit.get_stock_fundamentals_unified.invoke(
            {
                "ticker": "000001",
                "start_date": "2026-04-30",
                "end_date": "2026-05-03",
                "curr_date": "2026-05-03",
            }
        )

    assert "A股免费数据融合质量报告" in result
    assert "数据质量评分" in result
    assert "net_profit: 464.5" in result
    assert "free_cash_flow: 420.0" in result
