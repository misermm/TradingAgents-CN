from __future__ import annotations

from typing import Any, Dict, Optional

from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def build_blocked_master_update(
    state: Dict[str, Any],
    *,
    master_id: str,
    tool_call_count: int = 0,
) -> Optional[Dict[str, Any]]:
    gate = _run_cn_master_gate(state, master_id)
    if not gate:
        return None

    diagnostic = str(gate.get("diagnostic_report") or "")
    return {
        "master_reports": {master_id: diagnostic},
        "master_tool_call_counts": {master_id: tool_call_count},
        "master_data_quality": {master_id: gate},
        "messages": [],
    }


def build_blocked_master_consensus_update(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    gate = _run_cn_master_gate(state, "master_consensus")
    if not gate:
        return None

    diagnostic = str(gate.get("diagnostic_report") or "")
    return {
        "master_consensus_report": diagnostic,
        "master_data_quality": {"master_consensus": gate},
        "messages": [],
    }


def _run_cn_master_gate(state: Dict[str, Any], role_id: str) -> Optional[Dict[str, Any]]:
    try:
        ticker = state.get("company_of_interest", "")
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)
        if not market_info.get("is_china"):
            return None

        from tradingagents.graph.report_audit import run_role_data_gate

        gate = run_role_data_gate(role_id, state.get("cn_fact_snapshot") or {})
        return gate if gate.get("role_blocked") else None
    except Exception as exc:
        logger.warning(f"[Master Data Gate] skipped for {role_id}: {type(exc).__name__}: {str(exc)[:120]}")
        return None
