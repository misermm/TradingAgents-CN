from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.masters.base_master import MASTER_ANALYST_CONFIG
from tradingagents.agents.utils.analyst_registry import AnalystRegistry
from tradingagents.agents.utils.text_tool_call_parser import TextToolCallParser

from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


def _is_invalid_report(report: str) -> bool:
    if not report or len(report) <= 100:
        return True
    if TextToolCallParser.detect_text_tool_call(report):
        logger.warning(f"🚫 [报告质量守门] 报告包含原始工具调用文本，视为无效")
        return True
    return False


def _make_master_should_continue(master_id: str):
    config = MASTER_ANALYST_CONFIG[master_id]
    name_cn = config["name_cn"]
    max_tool_calls = config["max_tool_calls"]
    display_name = AnalystRegistry.get_master_display_name(master_id)

    def should_continue_master(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]

        master_tool_counts = state.get("master_tool_call_counts", {})
        tool_call_count = master_tool_counts.get(master_id, 0)
        master_reports = state.get("master_reports", {})
        report = master_reports.get(master_id, "")

        logger.info(f"🔀 [条件判断] should_continue_{master_id} ({name_cn})")
        logger.info(f"🔀 [条件判断] - 报告长度: {len(report)}")
        logger.info(f"🔧 [工具调用] - 次数: {tool_call_count}/{max_tool_calls}")

        if tool_call_count >= max_tool_calls:
            logger.info(f"🔀 [条件判断] 达到最大调用次数，结束")
            return f"Msg Clear {display_name}"

        if report and len(report) > 100:
            logger.info(f"🔀 [条件判断] 报告已完成，结束")
            return f"Msg Clear {display_name}"

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"🔀 [条件判断] 检测到tool_calls，执行工具")
            return f"tools_{master_id}"

        logger.info(f"🔀 [条件判断] 无tool_calls，结束")
        return f"Msg Clear {display_name}"

    return should_continue_master


class ConditionalLogic:

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

        for master_id in MASTER_ANALYST_CONFIG:
            method_name = f"should_continue_{master_id}"
            if not hasattr(self, method_name):
                setattr(self, method_name, _make_master_should_continue(master_id))

    def should_continue_market(self, state: AgentState):
        from tradingagents.utils.logging_init import get_logger
        logger = get_logger("agents")

        messages = state["messages"]
        last_message = messages[-1]

        tool_call_count = state.get("market_tool_call_count", 0)
        max_tool_calls = 3

        market_report = state.get("market_report", "")

        logger.info(f"🔀 [条件判断] should_continue_market")
        logger.info(f"🔀 [条件判断] - 消息数量: {len(messages)}")
        logger.info(f"🔀 [条件判断] - 报告长度: {len(market_report)}")
        logger.info(f"🔧 [死循环修复] - 工具调用次数: {tool_call_count}/{max_tool_calls}")

        if tool_call_count >= max_tool_calls:
            logger.warning(f"🔧 [死循环修复] 达到最大工具调用次数，强制结束: Msg Clear Market")
            return "Msg Clear Market"

        if market_report and len(market_report) > 100:
            logger.info(f"🔀 [条件判断] ✅ 报告已完成，返回: Msg Clear Market")
            return "Msg Clear Market"

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"🔀 [条件判断] 🔧 检测到tool_calls，返回: tools_market")
            return "tools_market"

        logger.info(f"🔀 [条件判断] ✅ 无tool_calls，返回: Msg Clear Market")
        return "Msg Clear Market"

    def should_continue_social(self, state: AgentState):
        from tradingagents.utils.logging_init import get_logger
        logger = get_logger("agents")

        messages = state["messages"]
        last_message = messages[-1]

        tool_call_count = state.get("sentiment_tool_call_count", 0)
        max_tool_calls = 3

        sentiment_report = state.get("sentiment_report", "")

        logger.info(f"🔀 [条件判断] should_continue_social")
        logger.info(f"🔀 [条件判断] - 报告长度: {len(sentiment_report)}")
        logger.info(f"🔧 [死循环修复] - 工具调用次数: {tool_call_count}/{max_tool_calls}")

        if tool_call_count >= max_tool_calls:
            return "Msg Clear Social"

        if sentiment_report and len(sentiment_report) > 100 and not _is_invalid_report(sentiment_report):
            return "Msg Clear Social"

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools_social"

        return "Msg Clear Social"

    def should_continue_news(self, state: AgentState):
        from tradingagents.utils.logging_init import get_logger
        logger = get_logger("agents")

        messages = state["messages"]
        last_message = messages[-1]

        tool_call_count = state.get("news_tool_call_count", 0)
        max_tool_calls = 3

        news_report = state.get("news_report", "")

        logger.info(f"🔀 [条件判断] should_continue_news")
        logger.info(f"🔀 [条件判断] - 报告长度: {len(news_report)}")
        logger.info(f"🔧 [死循环修复] - 工具调用次数: {tool_call_count}/{max_tool_calls}")

        if tool_call_count >= max_tool_calls:
            return "Msg Clear News"

        if news_report and len(news_report) > 100:
            return "Msg Clear News"

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools_news"

        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        from tradingagents.utils.logging_init import get_logger
        logger = get_logger("agents")

        messages = state["messages"]
        last_message = messages[-1]

        tool_call_count = state.get("fundamentals_tool_call_count", 0)
        max_tool_calls = 1

        fundamentals_report = state.get("fundamentals_report", "")

        logger.info(f"🔀 [条件判断] should_continue_fundamentals")
        logger.info(f"🔀 [条件判断] - 报告长度: {len(fundamentals_report)}")
        logger.info(f"🔧 [死循环修复] - 工具调用次数: {tool_call_count}/{max_tool_calls}")

        if tool_call_count >= max_tool_calls:
            return "Msg Clear Fundamentals"

        if fundamentals_report and len(fundamentals_report) > 100 and not _is_invalid_report(fundamentals_report):
            return "Msg Clear Fundamentals"

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools_fundamentals"

        return "Msg Clear Fundamentals"

    def should_continue_debate(self, state: AgentState) -> str:
        current_count = state["investment_debate_state"]["count"]
        max_count = 2 * self.max_debate_rounds
        current_speaker = state["investment_debate_state"]["current_response"]

        logger.info(f"🔍 [投资辩论控制] 当前发言次数: {current_count}, 最大次数: {max_count}")

        if current_count >= max_count:
            return "Research Manager"

        next_speaker = "Bear Researcher" if current_speaker.startswith("Bull") else "Bull Researcher"
        return next_speaker

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        current_count = state["risk_debate_state"]["count"]
        max_count = 3 * self.max_risk_discuss_rounds
        latest_speaker = state["risk_debate_state"]["latest_speaker"]

        if current_count >= max_count:
            return "Risk Judge"

        if latest_speaker.startswith("Risky"):
            next_speaker = "Safe Analyst"
        elif latest_speaker.startswith("Safe"):
            next_speaker = "Neutral Analyst"
        else:
            next_speaker = "Risky Analyst"

        return next_speaker
