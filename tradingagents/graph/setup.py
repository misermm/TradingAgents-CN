from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import (
    create_bear_researcher,
    create_bull_researcher,
    create_fundamentals_analyst,
    create_market_analyst,
    create_msg_delete,
    create_news_analyst,
    create_neutral_debator,
    create_research_manager,
    create_risk_manager,
    create_risky_debator,
    create_safe_debator,
    create_social_media_analyst,
    create_trader,
    MASTER_ANALYST_IDS,
    MASTER_CREATE_FUNCS,
    MASTER_ANALYST_INFO,
)
from tradingagents.agents.masters.master_consensus import create_master_consensus
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import Toolkit
from tradingagents.agents.utils.analyst_registry import AnalystRegistry
from tradingagents.graph.data_prefetch import create_data_prefetch_node

from .conditional_logic import ConditionalLogic

from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")

REGULAR_ANALYST_IDS = {"market", "social", "news", "fundamentals"}
MASTER_DISPLAY_NAMES = {
    master_id: AnalystRegistry.get_master_display_name(master_id)
    for master_id in MASTER_ANALYST_IDS
}


class GraphSetup:

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
        config: Dict[str, Any] = None,
        react_llm = None,
    ):
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.config = config or {}
        self.react_llm = react_llm

    def _separate_analysts(self, selected_analysts: List[str]):
        regular = [a for a in selected_analysts if a in REGULAR_ANALYST_IDS]
        masters = [a for a in selected_analysts if a in MASTER_ANALYST_IDS]
        unknown = [a for a in selected_analysts if a not in REGULAR_ANALYST_IDS and a not in MASTER_ANALYST_IDS]
        if unknown:
            logger.warning(f"[GraphSetup] 未知分析师ID将被忽略: {unknown}")
        return regular, masters

    def _create_regular_analyst_nodes(self, regular_analysts: List[str]):
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in regular_analysts:
            analyst_nodes["market"] = create_market_analyst(self.quick_thinking_llm, self.toolkit)
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in regular_analysts:
            analyst_nodes["social"] = create_social_media_analyst(self.quick_thinking_llm, self.toolkit)
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        if "news" in regular_analysts:
            analyst_nodes["news"] = create_news_analyst(self.quick_thinking_llm, self.toolkit)
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in regular_analysts:
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(self.quick_thinking_llm, self.toolkit)
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        return analyst_nodes, delete_nodes, tool_nodes

    def _create_master_analyst_nodes(self, master_analysts: List[str]):
        master_nodes = {}
        master_delete_nodes = {}
        master_tool_nodes = {}

        for master_id in master_analysts:
            create_func = MASTER_CREATE_FUNCS.get(master_id)
            if create_func:
                master_nodes[master_id] = create_func(self.quick_thinking_llm, self.toolkit)
                master_delete_nodes[master_id] = create_msg_delete()
                master_tool_nodes[master_id] = self.tool_nodes.get("fundamentals", self.tool_nodes.get("market"))
                info = MASTER_ANALYST_INFO.get(master_id, {})
                logger.info(f"[GraphSetup] 创建大师分析师: {info.get('name_cn', master_id)}")
            else:
                logger.warning(f"[GraphSetup] 未找到大师分析师创建函数: {master_id}")

        return master_nodes, master_delete_nodes, master_tool_nodes

    def _get_node_name(self, analyst_id: str) -> str:
        return AnalystRegistry.get_master_display_name(analyst_id) if analyst_id in MASTER_ANALYST_IDS else analyst_id.capitalize()

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        regular_analysts, master_analysts = self._separate_analysts(selected_analysts)

        if not regular_analysts and not master_analysts:
            raise ValueError("Trading Agents Graph Setup Error: no valid analysts selected!")

        analyst_nodes, delete_nodes, tool_nodes = self._create_regular_analyst_nodes(regular_analysts)
        master_nodes, master_delete_nodes, master_tool_nodes = self._create_master_analyst_nodes(master_analysts)

        bull_researcher_node = create_bull_researcher(self.quick_thinking_llm, self.bull_memory)
        bear_researcher_node = create_bear_researcher(self.quick_thinking_llm, self.bear_memory)
        research_manager_node = create_research_manager(self.deep_thinking_llm, self.invest_judge_memory)
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)

        risky_analyst = create_risky_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        safe_analyst = create_safe_debator(self.quick_thinking_llm)
        risk_manager_node = create_risk_manager(self.deep_thinking_llm, self.risk_manager_memory)
        master_consensus_node = create_master_consensus(llm=self.deep_thinking_llm)

        workflow = StateGraph(AgentState)

        if master_analysts:
            data_prefetch_node = create_data_prefetch_node(self.toolkit)
            workflow.add_node("Data PreFetch", data_prefetch_node)

        for analyst_type, node in analyst_nodes.items():
            node_name = f"{self._get_node_name(analyst_type)} Analyst"
            workflow.add_node(node_name, node)
            workflow.add_node(f"Msg Clear {self._get_node_name(analyst_type)}", delete_nodes[analyst_type])
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        for master_id, node in master_nodes.items():
            display_name = self._get_node_name(master_id)
            workflow.add_node(f"{display_name} Analyst", node)
            workflow.add_node(f"Msg Clear {display_name}", master_delete_nodes[master_id])
            workflow.add_node(f"tools_{master_id}", master_tool_nodes[master_id])

        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)
        if master_analysts:
            workflow.add_node("Master Consensus", master_consensus_node)

        if master_analysts:
            if regular_analysts:
                first_analyst = regular_analysts[0]
                workflow.add_edge(START, f"{self._get_node_name(first_analyst)} Analyst")
            else:
                workflow.add_edge(START, "Data PreFetch")
                for master_id in master_analysts:
                    display_name = self._get_node_name(master_id)
                    workflow.add_edge("Data PreFetch", f"{display_name} Analyst")
        else:
            if regular_analysts:
                first_analyst = regular_analysts[0]
                workflow.add_edge(START, f"{self._get_node_name(first_analyst)} Analyst")

        for i, analyst_type in enumerate(regular_analysts):
            current_name = self._get_node_name(analyst_type)
            current_analyst = f"{current_name} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {current_name}"

            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

            if i < len(regular_analysts) - 1:
                next_name = self._get_node_name(regular_analysts[i + 1])
                next_analyst = f"{next_name} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                if master_analysts:
                    workflow.add_edge(current_clear, "Data PreFetch")
                else:
                    workflow.add_edge(current_clear, "Bull Researcher")

        if master_analysts and regular_analysts:
            for master_id in master_analysts:
                display_name = self._get_node_name(master_id)
                workflow.add_edge("Data PreFetch", f"{display_name} Analyst")

        for master_id in master_analysts:
            display_name = self._get_node_name(master_id)
            master_analyst_node = f"{display_name} Analyst"
            master_tools = f"tools_{master_id}"
            master_clear = f"Msg Clear {display_name}"

            workflow.add_conditional_edges(
                master_analyst_node,
                getattr(self.conditional_logic, f"should_continue_{master_id}"),
                [master_tools, master_clear],
            )
            workflow.add_edge(master_tools, master_analyst_node)
            workflow.add_edge(master_clear, "Master Consensus")

        if master_analysts:
            workflow.add_edge("Master Consensus", "Bull Researcher")

        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Risky Analyst")
        workflow.add_conditional_edges(
            "Risky Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Safe Analyst": "Safe Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Safe Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Risky Analyst": "Risky Analyst",
                "Risk Judge": "Risk Judge",
            },
        )

        workflow.add_edge("Risk Judge", END)

        # 使用 MemorySaver checkpointer 确保并行节点状态正确持久化
        # 没有 checkpointer 时，graph.get_state() 无法可靠返回最终状态
        # 导致并行大师节点的报告可能在手动累积过程中丢失且无法恢复
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

        return workflow.compile(checkpointer=checkpointer)
