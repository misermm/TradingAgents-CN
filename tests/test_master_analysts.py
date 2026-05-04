import pytest
from unittest.mock import MagicMock, patch
import importlib


EXPECTED_MASTER_IDS = [
    "warren_buffett", "peter_lynch", "ben_graham", "charlie_munger",
    "cathie_wood", "bill_ackman", "phil_fisher", "stanley_druckenmiller",
    "aswath_damodaran", "michael_burry", "mohnish_pabrai", "nassim_taleb",
    "rakesh_jhunjhunwala",
]


class TestMasterAnalystImports:
    def test_master_analyst_ids(self):
        from tradingagents.agents.masters import MASTER_ANALYST_IDS
        assert MASTER_ANALYST_IDS == EXPECTED_MASTER_IDS

    def test_master_analyst_info(self):
        from tradingagents.agents.masters import MASTER_ANALYST_INFO
        assert "warren_buffett" in MASTER_ANALYST_INFO
        assert MASTER_ANALYST_INFO["warren_buffett"]["name_cn"] == "巴菲特"
        assert MASTER_ANALYST_INFO["peter_lynch"]["name_cn"] == "彼得·林奇"
        assert MASTER_ANALYST_INFO["aswath_damodaran"]["name_cn"] == "达莫达兰"
        assert len(MASTER_ANALYST_INFO) == 13

    def test_master_create_funcs(self):
        from tradingagents.agents.masters import MASTER_CREATE_FUNCS
        assert len(MASTER_CREATE_FUNCS) == 13
        for master_id in EXPECTED_MASTER_IDS:
            assert master_id in MASTER_CREATE_FUNCS
            assert callable(MASTER_CREATE_FUNCS[master_id])


class TestMasterAnalystConfig:
    def test_master_analyst_config(self):
        from tradingagents.agents.masters.base_master import MASTER_ANALYST_CONFIG
        assert len(MASTER_ANALYST_CONFIG) == 13
        for master_id, config in MASTER_ANALYST_CONFIG.items():
            assert "name_cn" in config
            assert "report_key" in config
            assert "counter_key" in config
            assert "max_tool_calls" in config
            assert config["report_key"].endswith("_report")
            assert config["counter_key"].endswith("_tool_call_count")


class TestMasterAnalystCreation:
    @pytest.mark.parametrize("master_id", EXPECTED_MASTER_IDS)
    def test_master_creation_delegates_to_base_factory(self, master_id):
        module = importlib.import_module(f"tradingagents.agents.masters.{master_id}")
        create_func = getattr(module, f"create_{master_id}_analyst")
        mock_llm = MagicMock()
        mock_toolkit = MagicMock()

        with patch(f"{module.__name__}.create_master_analyst") as mock_create:
            create_func(mock_llm, mock_toolkit)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["master_id"] == master_id


class TestMasterAnalystPhilosophy:
    def test_warren_buffett_philosophy(self):
        from tradingagents.agents.masters.warren_buffett import WARREN_BUFFETT_PHILOSOPHY
        assert "护城河" in WARREN_BUFFETT_PHILOSOPHY
        assert "安全边际" in WARREN_BUFFETT_PHILOSOPHY
        assert "能力圈" in WARREN_BUFFETT_PHILOSOPHY

    def test_peter_lynch_philosophy(self):
        from tradingagents.agents.masters.peter_lynch import PETER_LYNCH_PHILOSOPHY
        assert "PEG" in PETER_LYNCH_PHILOSOPHY
        assert "翻番" in PETER_LYNCH_PHILOSOPHY or "Tenbagger" in PETER_LYNCH_PHILOSOPHY

    def test_ben_graham_philosophy(self):
        from tradingagents.agents.masters.ben_graham import BEN_GRAHAM_PHILOSOPHY
        assert "安全边际" in BEN_GRAHAM_PHILOSOPHY
        assert "防御型" in BEN_GRAHAM_PHILOSOPHY

    def test_charlie_munger_philosophy(self):
        from tradingagents.agents.masters.charlie_munger import CHARLIE_MUNGER_PHILOSOPHY
        assert "反向思考" in CHARLIE_MUNGER_PHILOSOPHY
        assert "多元思维" in CHARLIE_MUNGER_PHILOSOPHY

    def test_cathie_wood_philosophy(self):
        from tradingagents.agents.masters.cathie_wood import CATHIE_WOOD_PHILOSOPHY
        assert "颠覆式创新" in CATHIE_WOOD_PHILOSOPHY
        assert "5年" in CATHIE_WOOD_PHILOSOPHY

    def test_bill_ackman_philosophy(self):
        from tradingagents.agents.masters.bill_ackman import BILL_ACKMAN_PHILOSOPHY
        assert "集中投资" in BILL_ACKMAN_PHILOSOPHY
        assert "维权" in BILL_ACKMAN_PHILOSOPHY

    def test_phil_fisher_philosophy(self):
        from tradingagents.agents.masters.phil_fisher import PHIL_FISHER_PHILOSOPHY
        assert "十五要点" in PHIL_FISHER_PHILOSOPHY
        assert "闲聊法" in PHIL_FISHER_PHILOSOPHY

    def test_stanley_druckenmiller_philosophy(self):
        from tradingagents.agents.masters.stanley_druckenmiller import STANLEY_DRUCKENMILLER_PHILOSOPHY
        assert "宏观" in STANLEY_DRUCKENMILLER_PHILOSOPHY
        assert "不对称" in STANLEY_DRUCKENMILLER_PHILOSOPHY


class TestAgentStateMasterFields:
    def test_agent_state_has_master_dict_fields(self):
        from tradingagents.agents.utils.agent_states import AgentState
        annotations = AgentState.__annotations__
        assert "master_reports" in annotations, "Missing master_reports dict field"
        assert "master_tool_call_counts" in annotations, "Missing master_tool_call_counts dict field"
        assert "master_data_quality" in annotations, "Missing master_data_quality dict field"

    def test_agent_state_has_prefetch_fields(self):
        from tradingagents.agents.utils.agent_states import AgentState
        annotations = AgentState.__annotations__
        assert "prefetched_fundamentals_data" in annotations, "Missing prefetched_fundamentals_data field"
        assert "prefetched_market_data" in annotations, "Missing prefetched_market_data field"

    def test_agent_state_has_consensus_field(self):
        from tradingagents.agents.utils.agent_states import AgentState
        annotations = AgentState.__annotations__
        assert "master_consensus_report" in annotations, "Missing master_consensus_report field"


class TestAgentsInitMasterExports:
    def test_master_exports_in_agents_init(self):
        from tradingagents.agents import (
            create_warren_buffett_analyst,
            create_peter_lynch_analyst,
            create_ben_graham_analyst,
            create_charlie_munger_analyst,
            create_cathie_wood_analyst,
            create_bill_ackman_analyst,
            create_phil_fisher_analyst,
            create_stanley_druckenmiller_analyst,
            MASTER_ANALYST_IDS,
            MASTER_ANALYST_INFO,
            MASTER_CREATE_FUNCS,
        )
        assert len(MASTER_ANALYST_IDS) == 13
        assert len(MASTER_CREATE_FUNCS) == 13
