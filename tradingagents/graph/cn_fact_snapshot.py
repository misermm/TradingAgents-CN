import re
from typing import Any, Dict, List, Mapping, Optional

from tradingagents.graph.report_audit import FIELD_METADATA, candidate_sources_for_field


def build_cn_fact_snapshot(
    ticker: str,
    market_info: Mapping[str, Any],
    fundamental_snapshot: Optional[Mapping[str, Any]] = None,
    trade_date: Optional[str] = None,
    market_report: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a normalized A-share fact snapshot from the existing free-data snapshot."""
    if not market_info.get("is_china"):
        return {}

    fundamental_snapshot = fundamental_snapshot or {}
    fields = fundamental_snapshot.get("fields", {}) if isinstance(fundamental_snapshot, Mapping) else {}
    quality = fundamental_snapshot.get("quality", {}) if isinstance(fundamental_snapshot, Mapping) else {}

    missing_fields = []
    for field_name in quality.get("missing_required_fields", []) or []:
        missing_fields.append(_missing_field_detail(field_name))

    conflicts = []
    for field_name in quality.get("conflict_fields", []) or []:
        field = fields.get(field_name, {}) if isinstance(fields, Mapping) else {}
        conflicts.append({
            "code": f"{field_name}_conflict",
            "field": field_name,
            "values": [
                {"source": source, "value": value}
                for source, value in (field.get("conflict_values") or {}).items()
            ],
            "impact": FIELD_METADATA.get(field_name, {}).get("impact", "不同数据源返回冲突值，可能影响分析结果"),
        })

    current_price = _field_value(fields, "price") or _field_value(fields, "current_price")
    current_price_source = _field_source(fields, "price") or _field_source(fields, "current_price")
    market_report_price = _extract_market_report_current_price_strict(market_report or "")
    if market_report_price is not None:
        current_price = market_report_price
        current_price_source = "market_report"
    return {
        "symbol": ticker,
        "stock_name": market_info.get("stock_name") or ticker,
        "market": "CN",
        "currency": "CNY",
        "current_price": current_price,
        "price_source": current_price_source,
        "price_as_of": trade_date,
        "valuation": {
            "pe": _field_value(fields, "pe") or _field_value(fields, "pe_ttm"),
            "pb": _field_value(fields, "pb"),
            "roe": _field_value(fields, "roe"),
            "debt_ratio": _field_value(fields, "debt_ratio"),
        },
        "quality": {
            "grade": quality.get("quality_grade") or quality.get("grade"),
            "score": quality.get("required_score", quality.get("score")),
            "missing_fields": missing_fields,
            "conflicts": conflicts,
            "raw_quality": dict(quality),
        },
        "sources_used": list(fundamental_snapshot.get("sources_used", []) or []),
    }


def _extract_market_report_current_price(market_report: str) -> Optional[float]:
    if not market_report:
        return None
    patterns = [
        r"(?:当前价格|当前价|现价|最新价|股价)\s*[：:]\s*[¥￥]?\s*(\d+(?:\.\d+)?)",
        r"(?:当前价格|当前价|现价|最新价|股价)[^0-9¥￥]{0,16}[¥￥]?\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, market_report, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return float(match.group(1))
        except Exception:
            continue
    return None


def _field_value(fields: Mapping[str, Any], field_name: str):
    if not isinstance(fields, Mapping):
        return None
    field = fields.get(field_name)
    if isinstance(field, Mapping):
        return field.get("value")
    return None


def _field_source(fields: Mapping[str, Any], field_name: str):
    if not isinstance(fields, Mapping):
        return None
    field = fields.get(field_name)
    if isinstance(field, Mapping):
        return field.get("source")
    return None


def _missing_field_detail(field_name: str) -> Dict[str, Any]:
    meta = FIELD_METADATA.get(field_name, {})
    return {
        "field": field_name,
        "label": meta.get("label") or field_name,
        "required_by": list(meta.get("required_by") or meta.get("blocks_roles", [])),
        "missing_reason": "现有免费数据源未返回该字段，或字段映射未命中",
        "blocks_roles": list(meta.get("blocks_roles", [])),
        "impact": meta.get("impact") or "可能影响相关分析结论",
        "affects_result": True,
        "suggested_fix": meta.get("suggested_fix") or "检查字段映射；若现有免费源不可得，可评估接入新的免费外部数据源",
        "candidate_free_sources": candidate_sources_for_field(field_name),
    }


def _extract_market_report_current_price_strict(market_report: str) -> Optional[float]:
    if not market_report:
        return None
    normalized = market_report.replace("：", ":").replace("¥", "￥").replace("元", "")
    patterns = [
        r"(?:当前价|当前价格|当前股价|现价|最新价|Current Price)\s*(?:[:：]|为|是|在)\s*[￥]?\s*(\d+(?:\.\d+)?)",
        r"(?:当前价|当前价格|当前股价|现价|最新价|Current Price)\s*[￥]?\s*(\d+(?:\.\d+)?)",
    ]
    candidates: List[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
            suffix = normalized[match.end(): match.end() + 2]
            if "%" in suffix:
                continue
            try:
                candidates.append(float(match.group(1)))
            except Exception:
                continue
    if candidates:
        return candidates[0]
    return None
