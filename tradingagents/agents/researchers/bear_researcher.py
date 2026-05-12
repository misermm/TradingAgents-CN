from langchain_core.messages import AIMessage
import time
import json

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.llm_retry import retry_llm_invoke
from tradingagents.agents.researchers.data_gate import build_blocked_research_debate_update
logger = get_logger("default")


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        try:
            investment_debate_state = state["investment_debate_state"]
            history = investment_debate_state.get("history", "")
            bear_history = investment_debate_state.get("bear_history", "")

            current_response = investment_debate_state.get("current_response", "")
            market_research_report = state.get("market_report", "")
            sentiment_report = state.get("sentiment_report", "")
            news_report = state.get("news_report", "")
            fundamentals_report = state.get("fundamentals_report", "")
            master_consensus = state.get("master_consensus_report", "") or ""

            blocked_update = build_blocked_research_debate_update(
                state,
                history_key="bear_history",
                speaker_label="Bear Analyst",
            )
            if blocked_update:
                return blocked_update

            ticker = state.get('company_of_interest', 'Unknown')
            from tradingagents.utils.stock_utils import StockUtils
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']

            company_name = state.get("company_name_resolved", "") or ticker
            if not state.get("company_name_resolved"):
                try:
                    from tradingagents.utils.company_utils import get_company_name
                    company_name = get_company_name(ticker)
                except Exception:
                    company_name = ticker
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            currency = market_info['currency_name']
            currency_symbol = market_info['currency_symbol']

            curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
            if master_consensus and str(master_consensus).strip():
                curr_situation += f"\n\n{master_consensus}"

            if master_consensus and str(master_consensus).strip():
                master_consensus_section = f"""
**投资大师共识意见：**
{master_consensus}

**重要提示**：以上是投资大师团队的共识分析。在看跌论证中，你可以引用大师共识中支持看跌或提示风险的观点来加强你的论据，同时也需要回应大师共识中可能存在的看涨观点。
"""
            else:
                master_consensus_section = ""

            if memory is not None:
                past_memories = memory.get_memories(curr_situation, n_matches=2)
            else:
                logger.warning(f"⚠️ [DEBUG] memory为None，跳过历史记忆检索")
                past_memories = []

            past_memory_str = ""
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec.get("recommendation", str(rec)) + "\n\n"

            prompt = f"""你是一位看跌分析师，负责论证不投资股票 {company_name}（股票代码：{ticker}）的理由。

⚠️ 重要提醒：当前分析的是 {market_info['market_name']}，所有价格和估值请使用 {currency}（{currency_symbol}）作为单位。
⚠️ 在你的分析中，请始终使用公司名称"{company_name}"而不是股票代码"{ticker}"来称呼这家公司。

你的目标是提出合理的论证，强调风险、挑战和负面指标。利用提供的研究和数据来突出潜在的不利因素并有效反驳看涨论点。

请用中文回答，重点关注以下几个方面：

- 风险和挑战：突出市场饱和、财务不稳定或宏观经济威胁等可能阻碍股票表现的因素
- 竞争劣势：强调市场地位较弱、创新下降或来自竞争对手威胁等脆弱性
- 负面指标：使用财务数据、市场趋势或最近不利消息的证据来支持你的立场
- 反驳看涨观点：用具体数据和合理推理批判性分析看涨论点，揭露弱点或过度乐观的假设
- 参与讨论：以对话风格呈现你的论点，直接回应看涨分析师的观点并进行有效辩论，而不仅仅是列举事实
- **回应乐观预期**：如果大师共识或看涨方提出了具体的利好因素（如业绩增长、行业景气、政策利好等），你必须逐一承认这些积极因素的存在，然后用数据或逻辑解释为什么这些利好已被市场充分反映（过度定价），或者为什么潜在风险足以抵消这些利好。不要回避或忽视利好，而是要展示你对利好有充分认知后的审慎判断

可用资源：

市场研究报告：{market_research_report}
社交媒体情绪报告：{sentiment_report}
最新世界事务新闻：{news_report}
公司基本面报告：{fundamentals_report}
{master_consensus_section}
辩论对话历史：{history}
最后的看涨论点：{current_response}
类似情况的反思和经验教训：{past_memory_str}

请使用这些信息提供令人信服的看跌论点，反驳看涨声明，并参与动态辩论，展示投资该股票的风险和弱点。你还必须处理反思并从过去的经验教训和错误中学习。

请确保所有回答都使用中文。
"""

            response = retry_llm_invoke(llm.invoke, prompt, max_retries=2, base_delay=2.0)

            argument = f"Bear Analyst: {response.content}"

            new_count = investment_debate_state.get("count", 0) + 1
            logger.info(f"🐻 [空头研究员] 发言完成，计数: {investment_debate_state.get('count', 0)} -> {new_count}")

            new_investment_debate_state = {
                "history": history + "\n" + argument,
                "bear_history": bear_history + "\n" + argument,
                "bull_history": investment_debate_state.get("bull_history", ""),
                "current_response": argument,
                "count": new_count,
            }

            return {"investment_debate_state": new_investment_debate_state}
        except Exception as e:
            logger.error(f"❌ [空头研究员] 节点执行异常: {type(e).__name__}: {str(e)[:200]}")
            investment_debate_state = state.get("investment_debate_state", {})
            return {
                "investment_debate_state": {
                    "history": investment_debate_state.get("history", ""),
                    "bear_history": investment_debate_state.get("bear_history", ""),
                    "bull_history": investment_debate_state.get("bull_history", ""),
                    "current_response": "",
                    "count": investment_debate_state.get("count", 0),
                },
                "messages": [],
            }

    return bear_node
