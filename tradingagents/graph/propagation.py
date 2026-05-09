from typing import Dict, Any
import uuid

from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.agents.utils.analyst_registry import AnalystRegistry


class Propagator:

    def __init__(self, max_recur_limit=100):
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self, company_name: str, trade_date: str
    ) -> Dict[str, Any]:
        from langchain_core.messages import HumanMessage

        analysis_request = f"请对股票 {company_name} 进行全面分析，交易日期为 {trade_date}。"

        resolved_name = self._resolve_company_name(company_name)

        state = {
            "messages": [HumanMessage(content=analysis_request)],
            "company_of_interest": company_name,
            "trade_date": str(trade_date),
            "company_name_resolved": resolved_name,
            "investment_debate_state": InvestDebateState(
                {"history": "", "bull_history": "", "bear_history": "", "current_response": "", "judge_decision": "", "count": 0}
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "history": "",
                    "risky_history": "",
                    "safe_history": "",
                    "neutral_history": "",
                    "latest_speaker": "",
                    "current_risky_response": "",
                    "current_safe_response": "",
                    "current_neutral_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
            "market_tool_call_count": 0,
            "news_tool_call_count": 0,
            "sentiment_tool_call_count": 0,
            "fundamentals_tool_call_count": 0,
            "master_reports": {},
            "master_tool_call_counts": {},
            "master_data_quality": {},
            "master_quantitative_results": {},
            "master_consensus_report": "",
            "china_market_report": "",
            "china_market_tool_call_count": 0,
            "prefetched_fundamentals_data": "",
            "prefetched_market_data": "",
            "prefetched_news_data": "",
            "prefetched_social_media_data": "",
            "prefetched_quant_data": "",
            "fundamental_snapshot": {},
        }

        AnalystRegistry.ensure_initialized()

        for master_id in AnalystRegistry.get_master_ids():
            state["master_reports"][master_id] = ""
            state["master_tool_call_counts"][master_id] = 0
            state["master_data_quality"][master_id] = {}
            state["master_quantitative_results"][master_id] = {}

        return state

    def get_graph_args(self, use_progress_callback: bool = False) -> Dict[str, Any]:
        stream_mode = "updates" if use_progress_callback else "values"
        # 为每次分析生成唯一的 thread_id，确保 checkpointer 能正确追踪状态
        # 这对于并行大师节点的状态持久化至关重要
        thread_id = str(uuid.uuid4())
        return {
            "stream_mode": stream_mode,
            "config": {
                "recursion_limit": self.max_recur_limit,
                "configurable": {"thread_id": thread_id},
            },
        }

    def _resolve_company_name(self, ticker: str) -> str:
        try:
            from tradingagents.utils.company_utils import get_company_name
            return get_company_name(ticker)
        except Exception as e:
            logger.warning(f"Company name resolution failed for {ticker}: {e}")
            return ticker
