from typing import Any, Dict, Optional

from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def build_blocked_risk_debate_update(
    state: Dict[str, Any],
    latest_speaker: str,
    current_response_key: str,
    history_key: str,
    speaker_label: str,
) -> Optional[Dict[str, Any]]:
    """Return a diagnostic risk debate update when A-share risk data is missing."""
    try:
        from tradingagents.utils.stock_utils import StockUtils

        company_name = state.get("company_of_interest")
        if not StockUtils.get_market_info(company_name).get("is_china"):
            return None

        from tradingagents.graph.report_audit import run_role_data_gate

        gate = run_role_data_gate("risk_management", state.get("cn_fact_snapshot") or {})
        if not gate.get("role_blocked"):
            return None

        risk_debate_state = state.get("risk_debate_state") or {}
        diagnostic = f"{speaker_label}: {gate.get('diagnostic_report', '')}"
        new_count = risk_debate_state.get("count", 0) + 1
        logger.warning(f"⚠️ [{speaker_label}] A股风控核心字段缺失，停止风险辩论并返回诊断报告")

        return {
            "risk_debate_state": {
                "history": risk_debate_state.get("history", "") + "\n" + diagnostic,
                "risky_history": _append_if_target(risk_debate_state, history_key, "risky_history", diagnostic),
                "safe_history": _append_if_target(risk_debate_state, history_key, "safe_history", diagnostic),
                "neutral_history": _append_if_target(risk_debate_state, history_key, "neutral_history", diagnostic),
                "latest_speaker": latest_speaker,
                "current_risky_response": diagnostic if current_response_key == "current_risky_response" else risk_debate_state.get("current_risky_response", ""),
                "current_safe_response": diagnostic if current_response_key == "current_safe_response" else risk_debate_state.get("current_safe_response", ""),
                "current_neutral_response": diagnostic if current_response_key == "current_neutral_response" else risk_debate_state.get("current_neutral_response", ""),
                "count": new_count,
            },
            "messages": [],
        }
    except Exception as e:
        logger.warning(f"⚠️ [{speaker_label}] 风险辩论数据准入检查失败，继续原辩论流程: {e}")
        return None


def _append_if_target(state: Dict[str, Any], target_key: str, key: str, diagnostic: str) -> str:
    value = state.get(key, "")
    if key != target_key:
        return value
    return value + "\n" + diagnostic
