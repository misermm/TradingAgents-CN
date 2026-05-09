import functools
import time
import json

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.llm_retry import retry_llm_invoke
from tradingagents.agents.utils.instrument_utils import build_instrument_context
logger = get_logger("default")


def create_trader(llm, memory):
    def trader_node(state, name):
        try:
            company_name = state["company_of_interest"]
            instrument_context = build_instrument_context(company_name)
            investment_plan = state["investment_plan"]
            market_research_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]

            from tradingagents.utils.stock_utils import StockUtils
            market_info = StockUtils.get_market_info(company_name)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            currency = market_info['currency_name']
            currency_symbol = market_info['currency_symbol']

            logger.debug(f"💰 [DEBUG] ===== 交易员节点开始 =====")
            logger.debug(f"💰 [DEBUG] 交易员检测股票类型: {company_name} -> {market_info['market_name']}, 货币: {currency}")
            logger.debug(f"💰 [DEBUG] 货币符号: {currency_symbol}")
            logger.debug(f"💰 [DEBUG] 市场详情: 中国A股={is_china}, 港股={is_hk}, 美股={is_us}")
            logger.debug(f"💰 [DEBUG] 基本面报告长度: {len(fundamentals_report)}")
            logger.debug(f"💰 [DEBUG] 基本面报告前200字符: {fundamentals_report[:200]}...")

            curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"

            if memory is not None:
                logger.warning(f"⚠️ [DEBUG] memory可用，获取历史记忆")
                past_memories = memory.get_memories(curr_situation, n_matches=2)
                past_memory_str = ""
                for i, rec in enumerate(past_memories, 1):
                    past_memory_str += rec["recommendation"] + "\n\n"
            else:
                logger.warning(f"⚠️ [DEBUG] memory为None，跳过历史记忆检索")
                past_memories = []
                past_memory_str = "暂无历史记忆数据可参考。"

            context = {
                "role": "user",
                "content": f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision.",
            }

            messages = [
                {
                    "role": "system",
                    "content": f"""您是一位专业的交易员，负责分析市场数据并做出投资决策。基于您的分析，请提供具体的买入、卖出或持有建议。

⚠️ 重要提醒：当前分析的股票代码是 {company_name}，请使用正确的货币单位：{currency}（{currency_symbol}）
{instrument_context}

🔴 严格要求：
- 股票代码 {company_name} 的公司名称必须严格按照基本面报告中的真实数据
- 绝对禁止使用错误的公司名称或混淆不同的股票
- 所有分析必须基于提供的真实数据，不允许假设或编造
- **必须提供具体的目标价位，不允许设置为null或空值**

请在您的分析中包含以下关键信息：
1. **投资建议**: 明确的买入/持有/卖出决策
2. **目标价位**: 基于分析的合理目标价格({currency}) - 🚨 强制要求提供具体数值
   - 买入建议：提供目标价位和预期涨幅
   - 持有建议：提供合理价格区间（如：{currency_symbol}XX-XX）
   - 卖出建议：提供止损价位和目标卖出价
3. **置信度**: 对决策的信心程度(0-1之间)
4. **风险评分**: 投资风险等级(0-1之间，0为低风险，1为高风险)
5. **详细推理**: 支持决策的具体理由

🎯 目标价位计算指导：
- 基于基本面分析中的估值数据（P/E、P/B、DCF等）
- 参考技术分析的支撑位和阻力位
- 考虑行业平均估值水平
- 结合市场情绪和新闻影响
- 即使市场情绪过热，也要基于合理估值给出目标价

特别注意：
- 当前股票的货币单位为{currency}（{currency_symbol}），所有价格必须使用此货币单位
- 目标价位必须与当前股价的货币单位保持一致
- 必须使用基本面报告中提供的正确公司名称
- **绝对不允许说"无法确定目标价"或"需要更多信息"**

请用中文撰写分析内容，并始终以'最终交易建议: **买入/持有/卖出**'结束您的回应以确认您的建议。

请不要忘记利用过去决策的经验教训来避免重复错误。以下是类似情况下的交易反思和经验教训: {past_memory_str}""",
                },
                context,
            ]

            logger.debug(f"💰 [DEBUG] 准备调用LLM，系统提示包含货币: {currency}")
            logger.debug(f"💰 [DEBUG] 系统提示中的关键部分: 目标价格({currency})")

            result = retry_llm_invoke(llm.invoke, messages, max_retries=2, base_delay=2.0)

            logger.debug(f"💰 [DEBUG] LLM调用完成")
            logger.debug(f"💰 [DEBUG] 交易员回复长度: {len(result.content)}")
            logger.debug(f"💰 [DEBUG] 交易员回复前500字符: {result.content[:500]}...")
            logger.debug(f"💰 [DEBUG] ===== 交易员节点结束 =====")

            content = result.content
            missing_fields = []
            if '目标价' not in content and '目标价位' not in content and 'target' not in content.lower():
                missing_fields.append('目标价位')
            if '置信度' not in content and 'confidence' not in content.lower():
                missing_fields.append('置信度')
            if '风险评分' not in content and '风险等级' not in content and 'risk' not in content.lower():
                missing_fields.append('风险评分')

            if missing_fields:
                warning = f"\n\n⚠️ **注意：LLM输出中缺少以下关键字段: {', '.join(missing_fields)}。请谨慎参考此分析结果。**"
                logger.warning(f"💰 [WARNING] 交易员输出缺少关键字段: {missing_fields}")
                content = content + warning

            return {
                "messages": [result],
                "trader_investment_plan": content,
                "sender": name,
            }
        except Exception as e:
            logger.error(f"❌ [交易员] 节点执行异常: {type(e).__name__}: {str(e)[:200]}")
            return {
                "trader_investment_plan": "交易员分析异常，无法生成投资计划",
                "messages": [],
            }

    return functools.partial(trader_node, name="Trader")
