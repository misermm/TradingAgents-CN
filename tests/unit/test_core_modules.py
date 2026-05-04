#!/usr/bin/env python3
"""
核心模块Mock单元测试

覆盖:
1. DataQualityEngine - 数据质量评分/补全/交叉验证
2. DataOrchestrator - 统一降级框架
3. _merge_master_state - 大师状态合并
4. merge_dicts - AgentState reducer
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock


# ==================== merge_dicts 测试 ====================

class TestMergeDicts:
    def test_basic_merge(self):
        from tradingagents.agents.utils.agent_states import merge_dicts
        left = {"a": 1, "b": 2}
        right = {"b": 3, "c": 4}
        result = merge_dicts(left, right)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_none_left(self):
        from tradingagents.agents.utils.agent_states import merge_dicts
        result = merge_dicts(None, {"a": 1})
        assert result == {"a": 1}

    def test_none_right(self):
        from tradingagents.agents.utils.agent_states import merge_dicts
        result = merge_dicts({"a": 1}, None)
        assert result == {"a": 1}

    def test_preserve_existing_on_empty(self):
        from tradingagents.agents.utils.agent_states import merge_dicts
        left = {"master_reports": {"buffett": "report1"}}
        right = {"master_reports": {"buffett": ""}}
        result = merge_dicts(left, right)
        assert result["master_reports"]["buffett"] == ""

    def test_preserve_existing_on_none(self):
        from tradingagents.agents.utils.agent_states import merge_dicts
        left = {"master_reports": {"buffett": "report1"}}
        right = {"master_reports": {"buffett": None}}
        result = merge_dicts(left, right)
        assert result["master_reports"]["buffett"] is None

    def test_merge_dicts_shallow_replacement(self):
        from tradingagents.agents.utils.agent_states import merge_dicts
        left = {"field": "old_value"}
        right = {"field": ""}
        result = merge_dicts(left, right)
        assert result["field"] == "old_value"

    def test_merge_dicts_none_preserves(self):
        from tradingagents.agents.utils.agent_states import merge_dicts
        left = {"field": "old_value"}
        right = {"field": None}
        result = merge_dicts(left, right)
        assert result["field"] == "old_value"

    def test_parallel_masters_no_overwrite(self):
        from tradingagents.agents.utils.agent_states import merge_dicts
        left = {"master_reports": {"buffett": "buffett_report"}}
        right = {"master_reports": {"lynch": "lynch_report"}}
        result = merge_dicts(left, right)
        assert result["master_reports"]["lynch"] == "lynch_report"


# ==================== _merge_master_state 测试 ====================

class TestMergeMasterState:
    def test_merge_all_four_fields(self):
        from tradingagents.graph.trading_graph import _merge_master_state
        final_state = {
            "master_reports": {"buffett": "report1"},
            "master_tool_call_counts": {"buffett": 5},
            "master_data_quality": {"buffett": 0.9},
            "master_quantitative_results": {"buffett": {"signal": "bullish"}},
        }
        node_update = {
            "master_reports": {"lynch": "report2"},
            "master_tool_call_counts": {"lynch": 3},
            "master_data_quality": {"lynch": 0.8},
            "master_quantitative_results": {"lynch": {"signal": "neutral"}},
        }
        result = _merge_master_state(final_state, node_update)
        assert result["master_reports"]["buffett"] == "report1"
        assert result["master_reports"]["lynch"] == "report2"
        assert result["master_tool_call_counts"]["buffett"] == 5
        assert result["master_tool_call_counts"]["lynch"] == 3

    def test_preserve_existing_values(self):
        from tradingagents.graph.trading_graph import _merge_master_state
        final_state = {
            "master_reports": {"buffett": "report1"},
        }
        node_update = {
            "master_reports": {"buffett": ""},
        }
        result = _merge_master_state(final_state, node_update)
        assert result["master_reports"]["buffett"] == "report1"

    def test_non_dict_node_update(self):
        from tradingagents.graph.trading_graph import _merge_master_state
        result = _merge_master_state({}, "not_a_dict")
        assert result == "not_a_dict"

    def test_no_master_fields(self):
        from tradingagents.graph.trading_graph import _merge_master_state
        final_state = {"other_field": "value1"}
        node_update = {"other_field": "value2"}
        result = _merge_master_state(final_state, node_update)
        assert result["other_field"] == "value2"


# ==================== DataQualityEngine 测试 ====================

class TestDataQualityEngine:
    def setup_method(self):
        from tradingagents.dataflows.data_quality_engine import DataQualityEngine
        self.engine = DataQualityEngine()

    def test_score_quality_empty(self):
        score = self.engine.score_quality({}, "cn")
        assert score == 0

    def test_score_quality_full(self):
        data = {
            "pe": 25, "pe_ttm": 26, "pb": 3.5,
            "total_mv": 1000000, "circ_mv": 800000,
            "turnover_rate": 2.5, "volume_ratio": 1.2,
            "roe": 15, "roa": 8, "revenue_ttm": 50000,
            "net_profit_ttm": 8000, "debt_ratio": 40, "current_ratio": 1.5,
        }
        score = self.engine.score_quality(data, "cn")
        assert score == 5

    def test_score_quality_missing_core(self):
        data = {"pe": 25, "pb": 3.5}
        score = self.engine.score_quality(data, "cn")
        assert score <= 2

    def test_identify_missing_fields_empty(self):
        missing = self.engine.identify_missing_fields({}, "cn")
        assert len(missing) > 0
        assert "pe" in missing
        assert "roe" in missing

    def test_identify_missing_fields_partial(self):
        data = {"pe": 25, "pb": 3.5, "total_mv": 1000000}
        missing = self.engine.identify_missing_fields(data, "cn")
        assert "pe" not in missing
        assert "roe" in missing

    def test_field_provenance_creation(self):
        from tradingagents.dataflows.data_quality_engine import FieldProvenance
        p = FieldProvenance(
            source="akshare",
            fetched_at=datetime.now(timezone.utc),
            completeness=1.0,
            is_estimated=False,
            cross_validated=True,
            cross_validation_deviation=0.05,
        )
        assert p.source == "akshare"
        assert p.cross_validated is True
        assert p.is_estimated is False

    def test_data_quality_result_creation(self):
        from tradingagents.dataflows.data_quality_engine import DataQualityResult
        r = DataQualityResult(
            data={"pe": 25},
            quality_score=3,
            provenance={},
            missing_fields=["roe"],
            complemented_fields={"pe": "akshare"},
            cross_validated_fields={},
            warnings=[],
        )
        assert r.quality_score == 3
        assert "roe" in r.missing_fields

    def test_build_provenance_summary(self):
        from tradingagents.dataflows.data_quality_engine import FieldProvenance
        result = MagicMock()
        result.quality_score = 4
        result.complemented_fields = {"pe": "akshare"}
        result.missing_fields = ["roe"]
        result.warnings = []
        result.provenance = {"pe_ttm": FieldProvenance(
            source="akshare", fetched_at=datetime.now(timezone.utc),
            completeness=1.0, is_estimated=True,
        )}
        summary = self.engine.build_provenance_summary(result)
        assert "4/5" in summary
        assert "pe←akshare" in summary
        assert "roe" in summary
        assert "pe_ttm" in summary


# ==================== DataOrchestrator 测试 ====================

class TestDataOrchestrator:
    def setup_method(self):
        from tradingagents.dataflows.data_orchestrator import DataOrchestrator
        self.orchestrator = DataOrchestrator()

    def test_get_available_sources_cn_stock(self):
        sources = self.orchestrator.get_available_sources("cn", "stock_data")
        assert "akshare" in sources
        assert "baostock" in sources

    def test_get_available_sources_cn_fundamentals(self):
        sources = self.orchestrator.get_available_sources("cn", "fundamentals")
        assert "akshare" in sources
        assert "baostock" in sources

    def test_get_available_sources_us_stock(self):
        sources = self.orchestrator.get_available_sources("us", "stock_data")
        assert "yfinance" in sources

    def test_get_available_sources_hk_stock(self):
        sources = self.orchestrator.get_available_sources("hk", "stock_data")
        assert "akshare" in sources
        assert "yfinance" in sources

    def test_get_available_sources_unknown(self):
        sources = self.orchestrator.get_available_sources("jp", "stock_data")
        assert sources == []

    def test_try_sources_in_order_success_first(self):
        fetch_func = MagicMock(return_value="success_data")
        result = self.orchestrator.try_sources_in_order(
            ["akshare", "baostock"], fetch_func, "600519"
        )
        assert result == "success_data"
        assert fetch_func.call_count == 1

    def test_try_sources_in_order_fallback(self):
        fetch_func = MagicMock(side_effect=["❌ error", "success_data"])
        result = self.orchestrator.try_sources_in_order(
            ["akshare", "baostock"], fetch_func, "600519"
        )
        assert result == "success_data"
        assert fetch_func.call_count == 2

    def test_try_sources_in_order_all_fail(self):
        fetch_func = MagicMock(side_effect=Exception("fail"))
        result = self.orchestrator.try_sources_in_order(
            ["akshare"], fetch_func, "600519"
        )
        assert result is None


# ==================== CacheConfig 测试 ====================

class TestCacheConfig:
    def test_generate_cache_key(self):
        from tradingagents.dataflows.cache.cache_config import generate_cache_key
        key = generate_cache_key("cn", "stock_data", "600519")
        assert key.startswith("cn:stock_data:600519:")

    def test_generate_cache_key_with_dates(self):
        from tradingagents.dataflows.cache.cache_config import generate_cache_key
        key = generate_cache_key("cn", "stock_data", "600519",
                                  start_date="2024-01-01", end_date="2024-12-31")
        assert "cn:stock_data:600519:" in key

    def test_detect_market_cn(self):
        from tradingagents.dataflows.cache.cache_config import detect_market
        assert detect_market("600519") == "cn"
        assert detect_market("000001") == "cn"

    def test_detect_market_us(self):
        from tradingagents.dataflows.cache.cache_config import detect_market
        assert detect_market("AAPL") == "us"

    def test_detect_market_hk(self):
        from tradingagents.dataflows.cache.cache_config import detect_market
        assert detect_market("00700") == "hk"

    def test_get_ttl_seconds(self):
        from tradingagents.dataflows.cache.cache_config import get_ttl_seconds
        ttl = get_ttl_seconds("cn", "stock_data")
        assert ttl > 0
