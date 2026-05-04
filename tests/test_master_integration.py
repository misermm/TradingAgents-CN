import pytest
from unittest.mock import MagicMock, patch


class TestGraphSetupMasterIntegration:
    def test_separate_analysts_regular_only(self):
        from tradingagents.graph.setup import GraphSetup, REGULAR_ANALYST_IDS
        mock_setup = MagicMock(spec=GraphSetup)
        mock_setup._separate_analysts = GraphSetup._separate_analysts.__get__(mock_setup, GraphSetup)
        regular, masters = mock_setup._separate_analysts(["market", "fundamentals"])
        assert regular == ["market", "fundamentals"]
        assert masters == []

    def test_separate_analysts_master_only(self):
        from tradingagents.graph.setup import GraphSetup
        mock_setup = MagicMock(spec=GraphSetup)
        mock_setup._separate_analysts = GraphSetup._separate_analysts.__get__(mock_setup, GraphSetup)
        regular, masters = mock_setup._separate_analysts(["warren_buffett", "peter_lynch"])
        assert regular == []
        assert masters == ["warren_buffett", "peter_lynch"]

    def test_separate_analysts_mixed(self):
        from tradingagents.graph.setup import GraphSetup
        mock_setup = MagicMock(spec=GraphSetup)
        mock_setup._separate_analysts = GraphSetup._separate_analysts.__get__(mock_setup, GraphSetup)
        regular, masters = mock_setup._separate_analysts(
            ["market", "warren_buffett", "fundamentals", "peter_lynch"]
        )
        assert regular == ["market", "fundamentals"]
        assert masters == ["warren_buffett", "peter_lynch"]

    def test_separate_analysts_unknown(self):
        from tradingagents.graph.setup import GraphSetup
        mock_setup = MagicMock(spec=GraphSetup)
        mock_setup._separate_analysts = GraphSetup._separate_analysts.__get__(mock_setup, GraphSetup)
        regular, masters = mock_setup._separate_analysts(["market", "unknown_analyst"])
        assert regular == ["market"]
        assert masters == []

    def test_get_node_name_regular(self):
        from tradingagents.graph.setup import GraphSetup
        mock_setup = MagicMock(spec=GraphSetup)
        mock_setup._get_node_name = GraphSetup._get_node_name.__get__(mock_setup, GraphSetup)
        assert mock_setup._get_node_name("market") == "Market"
        assert mock_setup._get_node_name("fundamentals") == "Fundamentals"

    def test_get_node_name_master(self):
        from tradingagents.graph.setup import GraphSetup, MASTER_DISPLAY_NAMES
        mock_setup = MagicMock(spec=GraphSetup)
        mock_setup._get_node_name = GraphSetup._get_node_name.__get__(mock_setup, GraphSetup)
        assert mock_setup._get_node_name("warren_buffett") == "Warren Buffett"
        assert mock_setup._get_node_name("peter_lynch") == "Peter Lynch"
        assert mock_setup._get_node_name("stanley_druckenmiller") == "Stanley Druckenmiller"


class TestConditionalLogicMaster:
    def test_master_should_continue_methods_exist(self):
        from tradingagents.graph.conditional_logic import ConditionalLogic
        from tradingagents.agents.masters.base_master import MASTER_ANALYST_CONFIG
        logic = ConditionalLogic()
        for master_id in MASTER_ANALYST_CONFIG:
            method_name = f"should_continue_{master_id}"
            assert hasattr(logic, method_name), f"Missing method: {method_name}"
            method = getattr(logic, method_name)
            assert callable(method)


class TestPropagatorMasterState:
    def test_propagator_initializes_master_dict_fields(self):
        from tradingagents.graph.propagation import Propagator
        from tradingagents.agents.masters.base_master import MASTER_ANALYST_CONFIG
        mock_graph = MagicMock()
        propagator = Propagator(mock_graph)
        state = propagator.create_initial_state("000001", "2024-01-01")
        assert "master_reports" in state, "Missing master_reports dict"
        assert "master_tool_call_counts" in state, "Missing master_tool_call_counts dict"
        assert "master_data_quality" in state, "Missing master_data_quality dict"
        assert "master_quantitative_results" in state, "Missing master_quantitative_results dict"
        assert isinstance(state["master_reports"], dict), "master_reports should be a dict"
        assert isinstance(state["master_tool_call_counts"], dict), "master_tool_call_counts should be a dict"
        assert isinstance(state["master_data_quality"], dict), "master_data_quality should be a dict"
        assert isinstance(state["master_quantitative_results"], dict), "master_quantitative_results should be a dict"
        for master_id in MASTER_ANALYST_CONFIG:
            assert master_id in state["master_reports"], f"Missing master_id in master_reports: {master_id}"
            assert state["master_reports"][master_id] == "", f"Report should be empty: {master_id}"
            assert master_id in state["master_tool_call_counts"], f"Missing master_id in master_tool_call_counts: {master_id}"
            assert state["master_tool_call_counts"][master_id] == 0, f"Counter should be 0: {master_id}"
            assert master_id in state["master_data_quality"], f"Missing master_id in master_data_quality: {master_id}"
            assert master_id in state["master_quantitative_results"], f"Missing master_id in master_quantitative_results: {master_id}"


def test_master_consensus_uses_guarded_quantitative_results():
    from tradingagents.agents.masters.master_consensus import create_master_consensus

    node = create_master_consensus(llm=None)
    state = {
        "master_reports": {
            "warren_buffett": "valid report text",
        },
        "master_quantitative_results": {
            "warren_buffett": {
                "signal": "neutral",
                "score": 6,
                "max_score": 10,
                "quality_guard": {
                    "applied": True,
                    "original_signal": "bullish",
                    "guarded_signal": "neutral",
                    "reasons": ["estimated_required_fields"],
                },
            }
        },
        "prefetched_fundamentals_data": "",
    }

    result = node(state)
    report = result["master_consensus_report"]

    assert "quality_guard:bullish->neutral" in report
    assert "量化信号:neutral" in report

    def test_propagator_initializes_prefetch_fields(self):
        from tradingagents.graph.propagation import Propagator
        mock_graph = MagicMock()
        propagator = Propagator(mock_graph)
        state = propagator.create_initial_state("000001", "2024-01-01")
        assert "prefetched_fundamentals_data" in state
        assert "prefetched_market_data" in state


class TestProgressTrackerMasterMapping:
    def test_tracker_master_step_info(self):
        from tradingagents.agents.masters import MASTER_ANALYST_IDS
        try:
            from app.services.progress.tracker import RedisProgressTracker
            tracker_mock = MagicMock(spec=RedisProgressTracker)
            from app.services.progress.tracker import RedisProgressTracker as TrackerClass
            tracker_mock._get_analyst_step_info = TrackerClass._get_analyst_step_info.__get__(tracker_mock, TrackerClass)
            for master_id in MASTER_ANALYST_IDS:
                info = tracker_mock._get_analyst_step_info(master_id)
                assert "🎩" in info["name"], f"Master {master_id} should have hat emoji in name"
                assert info["description"], f"Master {master_id} should have description"
        except ImportError:
            pytest.skip("Progress tracker not available in test environment")
