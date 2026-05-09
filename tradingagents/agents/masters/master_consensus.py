import re
from tradingagents.utils.logging_init import get_logger
from tradingagents.agents.masters.base_master import MASTER_ANALYST_CONFIG, QUANTITATIVE_ANALYZERS, _init_quantitative_analyzers
from tradingagents.agents.masters import MASTER_ANALYST_INFO

logger = get_logger("default")


def _quality_guard_note(quant_result: dict) -> str:
    guard = quant_result.get("quality_guard") if isinstance(quant_result, dict) else None
    if not isinstance(guard, dict) or not guard.get("applied"):
        return ""
    reasons = ",".join(guard.get("reasons", []))
    return f" [quality_guard:{guard.get('original_signal')}->{guard.get('guarded_signal')}; reasons={reasons}]"

MASTER_CONSENSUS_PROMPT = """你是一位资深投资顾问，负责综合多位投资大师的分析报告，生成一份深度共识摘要。

## 以下是大师的分析报告：

{master_reports_section}

## 量化评分统计：
- 看涨：{bullish_count}位 | 中性：{neutral_count}位 | 看跌：{bearish_count}位
- 量化平均得分：{avg_score:.1f}/{avg_max:.1f}

## 请你完成以下任务：

1. **共识信号**：综合所有大师的观点和量化评分，给出最终共识信号（看涨/看跌/中性）
2. **各大师核心观点**：用1-2句话概括每位大师的核心判断和关键理由，让读者快速了解每位大师的立场
3. **核心共识**：列出所有大师都认同的关键观点（2-3条）
4. **主要分歧**：列出大师之间的重要分歧点（1-2条），说明哪位大师持不同意见，并解释分歧背后的逻辑差异
5. **关键洞察**：选择最有价值的1-2个独特观点，说明来自哪位大师
6. **风险提示**：列出大师们提到的关键风险因素（1-2条）
7. **共识推理**：解释最终共识信号是如何从各大师观点中推导出来的，说明哪些因素权重更大以及为什么
8. **综合建议**：基于以上分析，给出综合投资建议（2-3句话）

## 输出格式（必须严格遵守）：

# 投资大师共识报告

## 共识信号：[看涨/看跌/中性]

## 各大师核心观点
- [大师名]：[1-2句核心判断和理由]
- [大师名]：[1-2句核心判断和理由]

## 核心共识
- [共识点1]
- [共识点2]

## 主要分歧
- [分歧点]：[大师A]认为X，[大师B]认为Y。逻辑差异：[解释为什么两位大师会得出不同结论]

## 关键洞察
- [洞察点]（来源：[大师名]）

## 风险提示
- [风险因素1]
- [风险因素2]

## 共识推理
最终共识为[看涨/看跌/中性]，主要因为：[解释推导过程，说明哪些因素权重更大以及为什么]

## 综合建议
[2-3句综合建议]

---

**结构化数据**（请严格按照以下JSON格式输出，便于程序解析）：
```json
{{
  "consensus_signal": "bullish/neutral/bearish",
  "confidence_level": "high/medium/low",
  "bullish_count": {bullish_count},
  "neutral_count": {neutral_count},
  "bearish_count": {bearish_count},
  "individual_views": [
    {{"master": "大师名", "view": "1-2句核心判断", "signal": "bullish/neutral/bearish"}}
  ],
  "key_consensus": ["共识1", "共识2"],
  "key_disagreements": ["分歧1：大师A认为X，大师B认为Y"],
  "key_insights": ["洞察1"],
  "risk_factors": ["风险1"],
  "consensus_reasoning": "共识推导过程说明",
  "recommendation": "综合建议"
}}
```
"""


def create_master_consensus(llm=None):
    def master_consensus_node(state) -> dict:
        _init_quantitative_analyzers()

        master_reports_dict = state.get("master_reports", {})
        state_quant_results = state.get("master_quantitative_results", {}) or {}

        reports_data = {}
        for master_id, config in MASTER_ANALYST_CONFIG.items():
            report = master_reports_dict.get(master_id, "")
            if report and report.strip():
                name_cn = config.get("name_cn", master_id)
                name_en = config.get("name_en", master_id)
                info = MASTER_ANALYST_INFO.get(master_id, {})
                style = info.get("style", "")
                reports_data[master_id] = {
                    "name_cn": name_cn,
                    "name_en": name_en,
                    "style": style,
                    "report": report,
                }

        if not reports_data:
            logger.info("[MasterConsensus] No master reports found, skipping consensus")
            return {"master_consensus_report": ""}

        quant_signals = {}
        prefetched_data = state.get("prefetched_fundamentals_data", "")
        for master_id in reports_data:
            existing_quant = state_quant_results.get(master_id) if isinstance(state_quant_results, dict) else None
            if isinstance(existing_quant, dict) and existing_quant:
                quant_signals[master_id] = {
                    "signal": existing_quant.get("signal", "neutral"),
                    "score": existing_quant.get("score", 0),
                    "max_score": existing_quant.get("max_score", 1),
                    "quality_guard": existing_quant.get("quality_guard", {}),
                }
                continue
            quant_func = QUANTITATIVE_ANALYZERS.get(master_id)
            if quant_func:
                try:
                    raw_data = prefetched_data if prefetched_data else reports_data.get(master_id, {}).get("report", "")
                    result = quant_func(raw_data)
                    if not isinstance(result, dict):
                        logger.warning(f"[MasterConsensus] Quant analysis for {master_id} returned non-dict: {type(result).__name__}")
                        quant_signals[master_id] = {"signal": "neutral", "score": 0, "max_score": 1, "quality_guard": {}}
                        continue
                    quant_signals[master_id] = {
                        "signal": result.get("signal", "neutral"),
                        "score": result.get("score", 0),
                        "max_score": result.get("max_score", 1),
                        "quality_guard": result.get("quality_guard", {}),
                    }
                except Exception as e:
                    logger.warning(f"[MasterConsensus] Quant analysis failed for {master_id}: {type(e).__name__}: {e}")
                    quant_signals[master_id] = {"signal": "neutral", "score": 0, "max_score": 1, "quality_guard": {}}

        bullish_count = sum(1 for s in quant_signals.values() if s["signal"] == "bullish")
        bearish_count = sum(1 for s in quant_signals.values() if s["signal"] == "bearish")
        neutral_count = sum(1 for s in quant_signals.values() if s["signal"] == "neutral")
        total_quant = len(quant_signals)

        if total_quant > 0:
            avg_score = sum(s["score"] for s in quant_signals.values()) / total_quant
            avg_max = sum(s["max_score"] for s in quant_signals.values()) / total_quant
        else:
            avg_score = 0
            avg_max = 1

        report_sections = []
        for master_id, data in reports_data.items():
            report = data["report"]
            if len(report) > 1500:
                report = report[:1500] + "\n...(内容已截断)"
            quant_str = ""
            if master_id in quant_signals:
                qs = quant_signals[master_id]
                quant_str = f" [量化信号:{qs['signal']}, 得分:{qs['score']:.1f}/{qs['max_score']:.1f}]{_quality_guard_note(qs)}"
            report_sections.append(f"### {data['name_cn']}({data['name_en']}) - {data['style']}{quant_str}\n{report}")

        master_reports_section = "\n\n".join(report_sections)

        if llm is not None:
            try:
                prompt = MASTER_CONSENSUS_PROMPT.replace("{master_reports_section}", master_reports_section).replace("{bullish_count}", str(bullish_count)).replace("{neutral_count}", str(neutral_count)).replace("{bearish_count}", str(bearish_count)).replace("{avg_score:.1f}", f"{avg_score:.1f}").replace("{avg_max:.1f}", f"{avg_max:.1f}")
                prompt = re.sub(r'\{[^{}]+\}', 'N/A', prompt)
                from langchain_core.messages import HumanMessage
                result = llm.invoke([HumanMessage(content=prompt)])
                consensus_report = result.content if hasattr(result, 'content') else str(result)
                structured_data = _extract_structured_json(consensus_report)
                if structured_data:
                    logger.info(f"[MasterConsensus] 结构化数据: signal={structured_data.get('consensus_signal')}, confidence={structured_data.get('confidence_level')}")
                logger.info(f"[MasterConsensus] LLM-generated consensus report, length={len(consensus_report)}")
            except Exception as e:
                logger.error(f"[MasterConsensus] LLM consensus generation failed, falling back to statistical: {e}")
                consensus_report = _generate_statistical_consensus(
                    reports_data, quant_signals, bullish_count, neutral_count, bearish_count, avg_score, avg_max, total_quant
                )
        else:
            consensus_report = _generate_statistical_consensus(
                reports_data, quant_signals, bullish_count, neutral_count, bearish_count, avg_score, avg_max, total_quant
            )

        return {"master_consensus_report": consensus_report}

    return master_consensus_node


def _extract_structured_json(report_text: str) -> dict:
    import re
    import json
    try:
        json_match = re.search(r'```json\s*(\{.*\})\s*```', report_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        brace_start = report_text.find('{')
        brace_end = report_text.rfind('}')
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            candidate = report_text[brace_start:brace_end + 1]
            return json.loads(candidate)
    except Exception:
        pass
    return {}


def _generate_statistical_consensus(master_reports, quant_signals, bullish_count, neutral_count, bearish_count, avg_score, avg_max, total_quant):
    if bullish_count > bearish_count and bullish_count > neutral_count:
        consensus_signal = "看涨"
    elif bearish_count > bullish_count and bearish_count > neutral_count:
        consensus_signal = "看跌"
    else:
        consensus_signal = "中性"

    report_summaries = []
    for master_id, data in master_reports.items():
        report = data["report"]
        if len(report) > 2000:
            report = report[:2000] + "...[truncated]"
        quant_str = ""
        if master_id in quant_signals:
            qs = quant_signals[master_id]
            quant_str = f" [量化信号:{qs['signal']}, 得分:{qs['score']:.1f}/{qs['max_score']:.1f}]{_quality_guard_note(qs)}"
        report_summaries.append(f"### {data['name_cn']}({data['name_en']}) - {data['style']}{quant_str}\n{report}")

    return f"""# 投资大师共识报告

## 共识信号：{consensus_signal}
- 看涨：{bullish_count}位 | 中性：{neutral_count}位 | 看跌：{bearish_count}位
- 量化平均得分：{avg_score:.1f}/{avg_max:.1f}

## 各大师核心观点

{chr(10).join(report_summaries)}

## 共识要点
- 参与大师：{len(master_reports)}位
- 量化评估覆盖：{total_quant}位
- 共识方向：{consensus_signal}

## 共识推理
共识信号为{consensus_signal}，基于{bullish_count}位看涨、{neutral_count}位中性、{bearish_count}位看跌的量化统计结果得出。
"""
