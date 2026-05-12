import time
import json

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.llm_retry import retry_llm_invoke
from tradingagents.agents.utils.instrument_utils import build_instrument_context
from tradingagents.agents.utils.text_tool_call_parser import TextToolCallParser
logger = get_logger("default")


def _sanitize_report(report: str, report_name: str) -> str:
    if not report:
        return f"⚠️ {report_name}数据未获取"
    if TextToolCallParser.detect_text_tool_call(report):
        logger.warning(f"⚠️ [风控输入验证] {report_name}包含原始工具调用文本，替换为警告")
        return f"⚠️ {report_name}数据获取异常，无法提供有效分析内容。请基于其他可用报告进行决策。"
    return report


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:
        try:
            company_name = state["company_of_interest"]
            instrument_context = build_instrument_context(company_name)

            history = state["risk_debate_state"]["history"]
            risk_debate_state = state["risk_debate_state"]
            market_research_report = _sanitize_report(state["market_report"], "市场分析")
            news_report = _sanitize_report(state["news_report"], "新闻分析")
            fundamentals_report = _sanitize_report(state["fundamentals_report"], "基本面分析")
            sentiment_report = _sanitize_report(state["sentiment_report"], "情绪分析")
            trader_plan = state["investment_plan"]
            master_consensus = state.get("master_consensus_report", "")

            try:
                from tradingagents.utils.stock_utils import StockUtils
                market_info = StockUtils.get_market_info(company_name)
                if market_info.get("is_china"):
                    from tradingagents.graph.report_audit import run_role_data_gate
                    gate = run_role_data_gate("risk_management", state.get("cn_fact_snapshot") or {})
                    if gate.get("role_blocked"):
                        logger.warning("⚠️ [风控管理器] A股风控核心字段缺失，停止正式决策并返回诊断报告")
                        new_risk_debate_state = {
                            "judge_decision": gate.get("diagnostic_report", ""),
                            "history": risk_debate_state.get("history", ""),
                            "risky_history": risk_debate_state.get("risky_history", ""),
                            "safe_history": risk_debate_state.get("safe_history", ""),
                            "neutral_history": risk_debate_state.get("neutral_history", ""),
                            "latest_speaker": "Judge",
                            "current_risky_response": risk_debate_state.get("current_risky_response", ""),
                            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
                            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
                            "count": risk_debate_state.get("count", 0),
                        }
                        return {
                            "risk_debate_state": new_risk_debate_state,
                            "final_trade_decision": gate.get("diagnostic_report", ""),
                            "messages": [],
                        }
            except Exception as e:
                logger.warning(f"⚠️ [风控管理器] 角色数据准入检查失败，继续原风控流程: {e}")

            curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"

            if master_consensus and master_consensus.strip():
                master_consensus_section = f"""
**投资大师共识意见：**
{master_consensus}

**重要提示**：以上是投资大师团队（巴菲特、林奇、格雷厄姆等）的共识分析。请将大师共识作为重要参考，但不是唯一依据。当大师共识与常规分析结论冲突时，需在决策中明确说明并给出理由。
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
                past_memory_str += rec["recommendation"] + "\n\n"

            prompt = f"""作为风险管理委员会主席和辩论主持人，您的目标是评估三位风险分析师——激进、中性和安全/保守——之间的辩论，并确定交易员的最佳行动方案。您的决策必须产生明确的建议：买入、卖出或持有。只有在有具体论据强烈支持时才选择持有，而不是在所有方面都似乎有效时作为后备选择。力求清晰和果断。

决策指导原则：
1. **总结关键论点**：提取每位分析师的最强观点，重点关注与背景的相关性。
2. **提供理由**：用辩论中的直接引用和反驳论点支持您的建议。
3. **完善交易员计划**：从交易员的原始计划**{trader_plan}**开始，根据分析师的见解进行调整。
4. **从过去的错误中学习**：使用**{past_memory_str}**中的经验教训来解决先前的误判，改进您现在做出的决策，确保您不会做出错误的买入/卖出/持有决定而亏损。

交付成果：
- 明确且可操作的建议：买入、卖出或持有。
- 基于辩论和过去反思的详细推理。

标的约束：
{instrument_context}

---

**分析师辩论历史：**
{history}
{master_consensus_section}

---

专注于可操作的见解和持续改进。建立在过去经验教训的基础上，批判性地评估所有观点，确保每个决策都能带来更好的结果。请用中文撰写所有分析内容和建议。"""

            prompt_length = len(prompt)
            estimated_tokens = int(prompt_length / 1.8)

            logger.info(f"📊 [Risk Manager] Prompt 统计:")
            logger.info(f"   - 辩论历史长度: {len(history)} 字符")
            logger.info(f"   - 交易员计划长度: {len(trader_plan)} 字符")
            logger.info(f"   - 历史记忆长度: {len(past_memory_str)} 字符")
            logger.info(f"   - 总 Prompt 长度: {prompt_length} 字符")
            logger.info(f"   - 估算输入 Token: ~{estimated_tokens} tokens")

            start_time = time.time()

            logger.info(f"🔄 [Risk Manager] 调用LLM生成交易决策")
            response = retry_llm_invoke(llm.invoke, prompt, max_retries=3, base_delay=2.0)

            elapsed_time = time.time() - start_time

            response_content = ""
            if response and hasattr(response, 'content') and response.content:
                response_content = response.content.strip()

                response_length = len(response_content)
                estimated_output_tokens = int(response_length / 1.8)

                usage_info = ""
                if hasattr(response, 'response_metadata') and response.response_metadata:
                    metadata = response.response_metadata
                    if 'token_usage' in metadata:
                        token_usage = metadata['token_usage']
                        usage_info = f", 实际Token: 输入={token_usage.get('prompt_tokens', 'N/A')} 输出={token_usage.get('completion_tokens', 'N/A')} 总计={token_usage.get('total_tokens', 'N/A')}"

                logger.info(f"⏱️ [Risk Manager] LLM调用耗时: {elapsed_time:.2f}秒")
                logger.info(f"📊 [Risk Manager] 响应统计: {response_length} 字符, 估算~{estimated_output_tokens} tokens{usage_info}")

            if not response_content:
                logger.warning(f"⚠️ [Risk Manager] LLM响应为空，使用默认决策")
                response_content = f"""**默认建议：持有**

由于技术原因无法生成详细分析，基于当前市场状况和风险控制原则，建议对{company_name}采取持有策略。

**理由：**
1. 市场信息不足，避免盲目操作
2. 保持现有仓位，等待更明确的市场信号
3. 控制风险，避免在不确定性高的情况下做出激进决策

**建议：**
- 密切关注市场动态和公司基本面变化
- 设置合理的止损和止盈位
- 等待更好的入场或出场时机

注意：此为系统默认建议，建议结合人工分析做出最终决策。"""

            new_risk_debate_state = {
                "judge_decision": response_content,
                "history": risk_debate_state.get("history", ""),
                "risky_history": risk_debate_state.get("risky_history", ""),
                "safe_history": risk_debate_state.get("safe_history", ""),
                "neutral_history": risk_debate_state.get("neutral_history", ""),
                "latest_speaker": "Judge",
                "current_risky_response": risk_debate_state.get("current_risky_response", ""),
                "current_safe_response": risk_debate_state.get("current_safe_response", ""),
                "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
                "count": risk_debate_state.get("count", 0),
            }

            logger.info(f"📋 [Risk Manager] 最终决策生成完成，内容长度: {len(response_content)} 字符")

            return {
                "risk_debate_state": new_risk_debate_state,
                "final_trade_decision": response_content,
            }
        except Exception as e:
            logger.error(f"❌ [风控管理器] 节点执行异常: {type(e).__name__}: {str(e)[:200]}")
            risk_debate_state = state.get("risk_debate_state", {})
            return {
                "risk_debate_state": {
                    "judge_decision": "风控分析异常",
                    "history": risk_debate_state.get("history", ""),
                    "risky_history": risk_debate_state.get("risky_history", ""),
                    "safe_history": risk_debate_state.get("safe_history", ""),
                    "neutral_history": risk_debate_state.get("neutral_history", ""),
                    "latest_speaker": "Judge",
                    "current_risky_response": risk_debate_state.get("current_risky_response", ""),
                    "current_safe_response": risk_debate_state.get("current_safe_response", ""),
                    "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
                    "count": risk_debate_state.get("count", 0),
                },
                "final_trade_decision": "风控分析异常，无法生成最终交易决策",
                "messages": [],
            }

    return risk_manager_node
