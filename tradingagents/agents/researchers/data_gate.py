from __future__ import annotations

from typing import Any, Dict, List, Optional

from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

RESEARCH_REQUIRED_ROLES = ("fundamentals", "market")


def build_blocked_research_debate_update(
    state: Dict[str, Any],
    *,
    history_key: str,
    speaker_label: str,
) -> Optional[Dict[str, Any]]:
    """Return a non-directional research debate update when A-share core data is missing."""
    gates = _collect_blocking_research_gates(state)
    if not gates:
        return None

    debate_state = state.get("investment_debate_state", {})
    diagnostic = f"{speaker_label}: {_format_research_gate_diagnostic(gates)}"
    history = debate_state.get("history", "")
    new_history = f"{history}\n{diagnostic}" if history else diagnostic
    new_count = debate_state.get("count", 0) + 1

    return {
        "investment_debate_state": {
            "history": new_history,
            "bull_history": _append_if_key(debate_state, "bull_history", history_key, diagnostic),
            "bear_history": _append_if_key(debate_state, "bear_history", history_key, diagnostic),
            "current_response": diagnostic,
            "count": new_count,
        },
        "messages": [],
    }


def build_blocked_research_manager_update(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a non-directional manager decision when A-share core research data is missing."""
    gates = _collect_blocking_research_gates(state)
    if not gates:
        return None

    debate_state = state.get("investment_debate_state", {})
    diagnostic = _format_research_gate_diagnostic(gates)
    return {
        "investment_debate_state": {
            "judge_decision": diagnostic,
            "history": debate_state.get("history", ""),
            "bear_history": debate_state.get("bear_history", ""),
            "bull_history": debate_state.get("bull_history", ""),
            "current_response": diagnostic,
            "count": debate_state.get("count", 0),
        },
        "investment_plan": diagnostic,
        "messages": [],
    }


def _collect_blocking_research_gates(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        ticker = state.get("company_of_interest", "")
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)
        if not market_info.get("is_china"):
            return []

        from tradingagents.graph.report_audit import run_role_data_gate

        snapshot = state.get("cn_fact_snapshot") or {}
        gates: List[Dict[str, Any]] = []
        for role in RESEARCH_REQUIRED_ROLES:
            gate = run_role_data_gate(role, snapshot)
            if gate.get("role_blocked"):
                gates.append(gate)
        return gates
    except Exception as exc:
        logger.warning(f"[Research Data Gate] skipped: {type(exc).__name__}: {str(exc)[:120]}")
        return []


def _format_research_gate_diagnostic(gates: List[Dict[str, Any]]) -> str:
    sections = [
        "## 数据缺失诊断",
        "",
        "当前角色：研究辩论/研究经理",
        "结论：核心行情或基本面数据不足，停止生成投资方向，先补齐下列数据。",
    ]
    for gate in gates:
        report = str(gate.get("diagnostic_report") or "").strip()
        if report:
            sections.extend(["", report])
    return "\n".join(sections)


def _append_if_key(
    debate_state: Dict[str, Any],
    target_key: str,
    active_key: str,
    diagnostic: str,
) -> str:
    current = debate_state.get(target_key, "")
    if target_key != active_key:
        return current
    return f"{current}\n{diagnostic}" if current else diagnostic
