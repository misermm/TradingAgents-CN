import re
from typing import Any, Dict, List, Mapping, Optional, Tuple


ACTION_BUY = "买入"
ACTION_HOLD = "持有"
ACTION_SELL = "卖出"

DIALOGUE_ARTIFACT_MARKERS = ("你们觉得", "我要问激进派", "我要问保守派", "是否有道理？")
TARGET_PRICE_DEVIATION_LIMIT = 1.0


FIELD_METADATA: Dict[str, Dict[str, Any]] = {
    "revenue": {
        "label": "营业收入",
        "impact": "无法判断业务规模和增长趋势",
        "blocks_roles": ["fundamentals", "peter_lynch", "master_consensus"],
        "suggested_fix": "检查利润表字段映射；若现有免费源不可得，可评估接入新的免费外部财报数据源",
    },
    "total_liabilities": {
        "label": "总负债",
        "impact": "无法计算资产负债率和偿债风险",
        "blocks_roles": ["fundamentals", "warren_buffett", "risk_management"],
        "suggested_fix": "检查资产负债表字段映射；若现有免费源不可得，可评估接入新的免费财报数据源",
    },
    "operating_cash_flow": {
        "label": "经营现金流",
        "impact": "无法判断经营造血能力和盈利质量",
        "blocks_roles": ["fundamentals", "warren_buffett", "risk_management"],
        "suggested_fix": "检查现金流量表字段映射；若现有免费源不可得，可评估接入新的免费现金流数据源",
    },
    "net_profit": {
        "label": "净利润",
        "impact": "无法判断盈利能力和估值基础",
        "blocks_roles": ["fundamentals", "master_quant"],
        "suggested_fix": "检查利润表净利润字段映射和报告期选择",
    },
    "total_assets": {
        "label": "总资产",
        "impact": "无法计算资产结构和资产负债率",
        "blocks_roles": ["fundamentals", "risk_management"],
        "suggested_fix": "检查资产负债表总资产字段映射",
    },
    "roe": {
        "label": "ROE",
        "impact": "无法判断股东回报质量",
        "blocks_roles": ["fundamentals", "master_quant"],
        "suggested_fix": "检查 ROE 字段映射或由净利润/净资产推导",
    },
    "pe": {
        "label": "市盈率",
        "impact": "无法判断盈利估值水平",
        "blocks_roles": ["fundamentals", "master_quant"],
        "suggested_fix": "检查实时行情和每股收益字段映射",
    },
    "pb": {
        "label": "市净率",
        "impact": "无法判断资产估值水平",
        "blocks_roles": ["fundamentals", "master_quant"],
        "suggested_fix": "检查实时行情和每股净资产字段映射",
    },
    "current_price": {
        "label": "当前价",
        "impact": "无法计算目标价偏离和交易价格依据",
        "blocks_roles": ["market", "trader", "risk_management"],
        "suggested_fix": "检查实时行情源和价格字段映射",
    },
    "historical_kline": {
        "label": "历史K线",
        "impact": "无法计算技术指标、支撑阻力和趋势",
        "blocks_roles": ["market"],
        "suggested_fix": "检查历史行情接口和日期区间",
    },
    "volume": {
        "label": "成交量",
        "impact": "无法判断量价配合和流动性",
        "blocks_roles": ["market"],
        "suggested_fix": "检查行情源成交量字段",
    },
}


FREE_DATA_SOURCE_CANDIDATES: Dict[str, List[Dict[str, str]]] = {
    "financial_statement": [
        {
            "name": "新浪财经 A股财报接口",
            "coverage": "利润表、资产负债表、现金流量表常用字段",
            "risk": "非正式接口，字段名和反爬策略可能变化",
        },
        {
            "name": "东方财富财务分析接口",
            "coverage": "主要财务指标、报告期数据、部分估值字段",
            "risk": "需校验接口稳定性、频率限制和页面字段变更",
        },
        {
            "name": "巨潮资讯公开披露文件",
            "coverage": "上市公司公告和定期报告原文",
            "risk": "需要解析 PDF/HTML，字段抽取成本较高",
        },
    ],
    "market_quote": [
        {
            "name": "腾讯财经行情接口",
            "coverage": "实时价格、成交量、涨跌幅等行情字段",
            "risk": "非正式接口，需控制请求频率并保留源更新时间",
        },
        {
            "name": "新浪财经行情接口",
            "coverage": "实时价格、成交量、昨收、开高低等行情字段",
            "risk": "字段格式偏文本化，需要稳定解析和异常兜底",
        },
    ],
}


ROLE_REQUIRED_FIELDS: Dict[str, List[str]] = {
    "fundamentals": [
        "revenue",
        "net_profit",
        "operating_cash_flow",
        "total_assets",
        "total_liabilities",
        "roe",
        "pe",
        "pb",
    ],
    "market": ["current_price", "historical_kline", "volume"],
    "risk_management": ["total_liabilities", "operating_cash_flow"],
    "trader": ["current_price"],
    "warren_buffett": ["net_profit", "operating_cash_flow", "total_liabilities", "roe"],
    "peter_lynch": ["revenue", "net_profit", "operating_cash_flow", "pe"],
    "master_consensus": ["revenue", "net_profit", "total_liabilities", "roe"],
}


ROLE_WEIGHTS: Dict[str, float] = {
    "risk_management": 0.25,
    "trader": 0.18,
    "master_quant": 0.18,
    "master_consensus": 0.14,
    "fundamentals": 0.10,
    "market": 0.06,
    "research_manager": 0.05,
    "sentiment": 0.04,
}


def audit_cn_report(result: Mapping[str, Any], cn_fact_snapshot: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Audit an A-share analysis result for data and decision trust issues."""
    snapshot = dict(cn_fact_snapshot or result.get("cn_fact_snapshot") or {})
    reports = _get_reports(result)
    issues: List[Dict[str, Any]] = []

    missing_data = _complete_missing_fields(_snapshot_quality(snapshot).get("missing_fields", []))
    if missing_data:
        issues.append({
            "code": "MISSING_DATA",
            "severity": "high" if any(item.get("affects_result") for item in missing_data) else "medium",
            "message": "存在缺失字段，已列出字段、原因、影响和修复入口",
            "affected_fields": [item["field"] for item in missing_data],
            "missing_or_conflicting_data": missing_data,
        })

    price_issue = _detect_price_conflict(reports, snapshot)
    if price_issue:
        issues.append(price_issue)

    if _has_low_data_quality(result, snapshot, reports):
        issues.append({
            "code": "LOW_DATA_QUALITY",
            "severity": "high",
            "message": "A股核心数据质量较低或存在核心指标冲突",
            "affected_fields": _quality_conflict_fields(snapshot),
            "missing_or_conflicting_data": missing_data,
        })

    if _has_dialogue_artifact(reports):
        issues.append({
            "code": "DIALOGUE_ARTIFACT",
            "severity": "medium",
            "message": "最终报告包含 agent 内部对话残留",
            "affected_fields": ["reports"],
            "missing_or_conflicting_data": [],
        })

    target_issue = _detect_target_price_issue(result, snapshot)
    if target_issue:
        issues.append(target_issue)

    role_result = compute_weighted_role_decision(result, reports=reports)
    raw_decision = result.get("decision") or {}
    if isinstance(raw_decision, Mapping):
        raw_action = raw_decision.get("action")
        if raw_action and raw_action != role_result["action"]:
            issues.append({
                "code": "DECISION_CONFLICT",
                "severity": "high",
                "message": f"顶层决策 {raw_action} 与角色加权结果 {role_result['action']} 不一致",
                "affected_fields": ["decision.action"],
                "missing_or_conflicting_data": [],
            })

    severity = _max_severity(issues)
    key_points = _build_key_points(result, issues, role_result)
    return {
        "audit_passed": not issues,
        "severity": severity,
        "issues": issues,
        "missing_data": missing_data,
        "recommended_action": role_result["action"],
        "confidence_cap": _confidence_cap(issues, snapshot),
        "key_points": key_points,
        "role_contributions": role_result["role_contributions"],
        "weighted_score": role_result["weighted_score"],
    }


def reconcile_cn_decision(result: Mapping[str, Any], raw_decision: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Create a final structured decision from audit gates and weighted role outputs."""
    raw_decision = dict(raw_decision if raw_decision is not None else (result.get("decision") or {}))
    audit_input = dict(result)
    audit_input["decision"] = raw_decision
    audit = audit_cn_report(audit_input)
    role_result = compute_weighted_role_decision(audit_input)

    action = role_result["action"]
    confidence = _safe_float(raw_decision.get("confidence"), 0.7)
    confidence = min(confidence, audit["confidence_cap"])

    has_high_gate = any(issue.get("severity") == "high" for issue in audit["issues"])
    target_price = raw_decision.get("target_price")
    if target_price in ("", "null", "None", 0):
        target_price = None

    if has_high_gate and action == ACTION_BUY:
        action = ACTION_HOLD
    if _target_price_invalid_for_buy(raw_decision, target_price, result.get("cn_fact_snapshot") or {}) and confidence > 0.45:
        action = ACTION_HOLD
        confidence = min(confidence, 0.45)

    risk_score = _safe_float(raw_decision.get("risk_score"), 0.5)
    if has_high_gate:
        risk_score = max(risk_score, 0.7)

    key_points = list(raw_decision.get("key_points") or [])
    if len(key_points) < 3:
        for point in audit["key_points"]:
            if point not in key_points:
                key_points.append(point)
            if len(key_points) >= 3:
                break

    reasoning = _build_reasoning(audit, role_result, raw_decision)
    decision = {
        "action": action,
        "confidence": round(confidence, 4),
        "risk_score": round(risk_score, 4),
        "target_price": target_price,
        "reasoning": reasoning,
        "key_points": key_points[:5],
        "audit": audit,
        "role_contributions": role_result["role_contributions"],
        "weighted_score": role_result["weighted_score"],
    }
    decision["recommendation"] = _format_recommendation(decision)
    decision["confidence_score"] = decision["confidence"]
    decision["risk_level"] = "高" if decision["risk_score"] >= 0.7 else ("低" if decision["risk_score"] < 0.3 else "中等")
    return decision


def run_role_data_gate(role_id: str, cn_fact_snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    role_key = _normalize_role(role_id)
    required_fields = ROLE_REQUIRED_FIELDS.get(role_key, [])
    quality = _snapshot_quality(cn_fact_snapshot)
    missing_data = _complete_missing_fields(quality.get("missing_fields", []))
    missing_required = [item for item in missing_data if item["field"] in required_fields]
    blocked = any(item.get("affects_result", True) for item in missing_required)
    return {
        "role": role_key,
        "required_fields": required_fields,
        "missing_data": missing_required,
        "role_blocked": blocked,
        "diagnostic_report": _format_role_diagnostic(role_key, missing_required, blocked),
    }


def compute_weighted_role_decision(result: Mapping[str, Any], reports: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    reports = reports or _get_reports(result)
    role_actions: List[Tuple[str, Optional[str], str, float, str]] = []

    risk_text = _first_report(reports, ["risk_management_decision", "final_trade_decision"])
    trader_text = reports.get("trader_investment_plan", "")
    master_text = reports.get("master_consensus_report", "")
    fundamentals_text = reports.get("fundamentals_report", "")
    market_text = reports.get("market_report", "")
    research_text = _first_report(reports, ["research_team_decision", "investment_plan"])
    sentiment_text = _first_report(reports, ["sentiment_report", "social_report", "news_report"])

    role_actions.append(("risk_management", _extract_action(risk_text), "风险委员会", 1.0, risk_text))
    role_actions.append(("trader", _extract_action(trader_text), "交易员", 1.0, trader_text))
    role_actions.append(("master_consensus", _extract_action(master_text), "大师共识", 1.0, master_text))
    role_actions.append(("fundamentals", _extract_action(fundamentals_text), "基本面分析师", 1.0, fundamentals_text))
    role_actions.append(("market", _extract_action(market_text), "技术面/市场分析师", 1.0, market_text))
    role_actions.append(("research_manager", _extract_action(research_text), "研究团队经理", 1.0, research_text))
    role_actions.append(("sentiment", _extract_action(sentiment_text), "新闻/社交情绪", 0.8, sentiment_text))

    quant_action = _extract_quant_action(result.get("master_quantitative_results") or {})
    role_actions.append(("master_quant", quant_action, "大师量化评分", 1.0, ""))

    snapshot = result.get("cn_fact_snapshot") or {}
    audit_penalty = _evidence_quality_penalty(snapshot)
    weighted_score = 0.0
    total_weight = 0.0
    contributions: List[Dict[str, Any]] = []

    for role, action, label, evidence_quality, evidence_text in role_actions:
        if not action:
            continue
        weight = ROLE_WEIGHTS.get(role, 0.0)
        conflicts_with_snapshot = _role_price_conflicts_with_snapshot(evidence_text, snapshot)
        role_quality = evidence_quality * audit_penalty
        if conflicts_with_snapshot:
            role_quality *= 0.3
        value = _action_value(action)
        contribution = weight * role_quality * value
        weighted_score += contribution
        total_weight += weight * role_quality
        contributions.append({
            "role": role,
            "label": label,
            "action": action,
            "weight": weight,
            "evidence_quality": round(role_quality, 4),
            "conflicts_with_snapshot": conflicts_with_snapshot,
            "contribution": round(contribution, 4),
        })

    if weighted_score >= 0.25:
        action = ACTION_BUY
    elif weighted_score <= -0.25:
        action = ACTION_SELL
    else:
        action = ACTION_HOLD

    return {
        "action": action,
        "weighted_score": round(weighted_score, 4),
        "total_effective_weight": round(total_weight, 4),
        "role_contributions": contributions,
    }


def _get_reports(result: Mapping[str, Any]) -> Dict[str, str]:
    raw_reports = result.get("reports", result)
    reports: Dict[str, str] = {}
    if isinstance(raw_reports, Mapping):
        for key, value in raw_reports.items():
            if isinstance(value, str):
                reports[key] = value
    for key in [
        "market_report",
        "fundamentals_report",
        "sentiment_report",
        "news_report",
        "investment_plan",
        "trader_investment_plan",
        "final_trade_decision",
        "master_consensus_report",
        "risk_management_decision",
    ]:
        value = result.get(key)
        if isinstance(value, str) and key not in reports:
            reports[key] = value
    return reports


def _snapshot_quality(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    quality = snapshot.get("quality") if isinstance(snapshot, Mapping) else {}
    return dict(quality or {})


def _complete_missing_fields(raw_missing: Any) -> List[Dict[str, Any]]:
    if not raw_missing:
        return []
    completed = []
    for item in raw_missing:
        if isinstance(item, str):
            field = item
            source = {}
        elif isinstance(item, Mapping):
            field = str(item.get("field", "")).strip()
            source = dict(item)
        else:
            continue
        if not field:
            continue
        meta = FIELD_METADATA.get(field, {})
        missing_reason = source.get("missing_reason") or "现有数据源未返回该字段，或字段映射未命中"
        blocks_roles = source.get("blocks_roles") or meta.get("blocks_roles", [])
        required_by = source.get("required_by") or meta.get("required_by") or blocks_roles
        affects_result = bool(source.get("affects_result", True))
        completed.append({
            "field": field,
            "label": source.get("label") or meta.get("label") or field,
            "required_by": list(required_by),
            "missing_reason": missing_reason,
            "blocks_roles": list(blocks_roles),
            "impact": source.get("impact") or meta.get("impact") or "可能影响相关分析结论",
            "affects_result": affects_result,
            "suggested_fix": source.get("suggested_fix") or meta.get("suggested_fix") or "检查字段映射；若现有免费源不可得，可评估接入新的免费外部数据源",
            "candidate_free_sources": source.get("candidate_free_sources") or _candidate_sources_for_field(field),
        })
    return completed


def _detect_price_conflict(reports: Mapping[str, str], snapshot: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    snapshot_price = _safe_float(snapshot.get("current_price"), None)
    explicit_prices: List[Tuple[str, float]] = []
    price_report_keys = {
        "market_report",
        "fundamentals_report",
        "trader_investment_plan",
        "final_trade_decision",
        "risk_management_decision",
    }

    for name, text in reports.items():
        if name not in price_report_keys:
            continue
        for price in _extract_explicit_current_prices(text):
            explicit_prices.append((name, price))

    conflict_values: List[Dict[str, Any]] = []
    severity = "low"
    if snapshot_price is not None and explicit_prices:
        for name, price in explicit_prices:
            if abs(price - snapshot_price) > 1e-9:
                conflict_values.append({"source": "cn_fact_snapshot", "value": snapshot_price})
                conflict_values.append({"source": name, "value": price})
                ratio = abs(price - snapshot_price) / max(abs(snapshot_price), 1e-9)
                severity = _price_severity(ratio)
                break

    if not conflict_values:
        return None

    return {
        "code": "PRICE_CONFLICT",
        "severity": severity,
        "message": "A股报告中当前价或核心价格事实与事实快照/其他报告不一致",
        "affected_fields": ["current_price"],
        "missing_or_conflicting_data": conflict_values,
    }


def _extract_explicit_current_prices(text: str) -> List[float]:
    if not text:
        return []
    normalized = (
        text.replace("：", ":")
        .replace("￥", "¥")
        .replace("元", "")
    )
    prices: List[float] = []
    patterns = [
        r"(?:当前价|当前价格|当前股价|现价|最新价|Current Price)\s*[:：]?\s*[¥]?\s*(\d+(?:\.\d+)?)",
        r"(?:当前价|当前价格|当前股价|现价|最新价|Current Price)[^0-9¥]{0,16}[¥]?\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            price = _safe_float(match.group(1), None)
            if price is not None:
                prices.append(price)
    return prices


def _extract_currency_prices(text: str) -> List[float]:
    if not text:
        return []
    prices: List[float] = []
    for pattern in [r"[¥￥]\s*(\d+(?:\.\d+)?)", r"(\d+(?:\.\d+)?)\s*元"]:
        for match in re.finditer(pattern, text):
            price = _safe_float(match.group(1), None)
            if price is not None and 0 < price < 10000:
                prices.append(price)
    return prices


def _price_severity(ratio: float) -> str:
    if ratio >= 0.2:
        return "high"
    if ratio >= 0.02:
        return "medium"
    return "low"


def _role_price_conflicts_with_snapshot(text: str, snapshot: Mapping[str, Any]) -> bool:
    snapshot_price = _safe_float(snapshot.get("current_price"), None)
    if snapshot_price is None or not text:
        return False
    for price in _extract_explicit_current_prices(text):
        if abs(price - snapshot_price) > 1e-9:
            return True
    return False


def _has_low_data_quality(result: Mapping[str, Any], snapshot: Mapping[str, Any], reports: Mapping[str, str]) -> bool:
    quality = _snapshot_quality(snapshot)
    if str(quality.get("grade", "")).upper() == "D":
        return True
    if quality.get("conflicts"):
        return True
    joined = "\n".join(reports.values())
    low_markers = ["数据质量等级: D", "数据质量等级：D", "D级", "PE/ROE", "数据矛盾"]
    return any(marker in joined for marker in low_markers)


def _quality_conflict_fields(snapshot: Mapping[str, Any]) -> List[str]:
    fields = []
    for conflict in _snapshot_quality(snapshot).get("conflicts", []) or []:
        if isinstance(conflict, Mapping) and conflict.get("field"):
            fields.append(str(conflict["field"]))
    return fields


def _has_dialogue_artifact(reports: Mapping[str, str]) -> bool:
    joined = "\n".join(reports.values())
    return any(marker in joined for marker in DIALOGUE_ARTIFACT_MARKERS)


def _detect_target_price_issue(result: Mapping[str, Any], snapshot: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    raw_decision = result.get("decision") or {}
    if not isinstance(raw_decision, Mapping):
        return None
    target_price = raw_decision.get("target_price")
    if target_price in ("", "null", "None", 0):
        target_price = None
    confidence = _safe_float(raw_decision.get("confidence"), 0.0) or 0.0
    raw_action = raw_decision.get("action")
    invalid_reason = None

    if target_price is None and raw_action == ACTION_BUY:
        invalid_reason = "目标价缺失时不允许保持高置信买入"
    elif target_price is not None:
        current_price = _safe_float(snapshot.get("current_price"), None)
        target_value = _safe_float(target_price, None)
        if target_value is None or target_value <= 0:
            invalid_reason = "目标价不是有效正数"
        elif current_price and current_price > 0:
            deviation = abs(target_value - current_price) / current_price
            if deviation > TARGET_PRICE_DEVIATION_LIMIT and raw_action == ACTION_BUY:
                invalid_reason = "目标价与当前价偏离过大，需人工复核"

    if not invalid_reason:
        return None

    return {
        "code": "TARGET_PRICE_INVALID",
        "severity": "high" if confidence > 0.45 else "medium",
        "message": invalid_reason,
        "affected_fields": ["decision.target_price", "decision.action", "decision.confidence"],
        "missing_or_conflicting_data": [
            {
                "target_price": target_price,
                "current_price": snapshot.get("current_price"),
                "action": raw_action,
                "confidence": confidence,
            }
        ],
    }


def _target_price_invalid_for_buy(raw_decision: Mapping[str, Any], target_price: Any, snapshot: Mapping[str, Any]) -> bool:
    if raw_decision.get("action") != ACTION_BUY:
        return False
    if target_price is None:
        return True
    current_price = _safe_float(snapshot.get("current_price"), None)
    target_value = _safe_float(target_price, None)
    if target_value is None or target_value <= 0:
        return True
    if current_price and current_price > 0:
        return abs(target_value - current_price) / current_price > TARGET_PRICE_DEVIATION_LIMIT
    return False


def _extract_action(text: str) -> Optional[str]:
    if not text:
        return None
    windows = []
    for marker in ["最终建议", "明确建议", "最终决策", "核心决策", "共识信号", "综合评分", "建议"]:
        idx = text.find(marker)
        if idx >= 0:
            windows.append(text[idx: idx + 120])
    windows.append(text[:500])
    joined = "\n".join(windows)

    token_map = {
        "买入": ACTION_BUY,
        "看涨": ACTION_BUY,
        "增持": ACTION_BUY,
        "建仓": ACTION_BUY,
        "卖出": ACTION_SELL,
        "看跌": ACTION_SELL,
        "回避": ACTION_SELL,
        "减仓": ACTION_SELL,
        "清仓": ACTION_SELL,
        "持有": ACTION_HOLD,
        "观望": ACTION_HOLD,
        "中性": ACTION_HOLD,
        "等待": ACTION_HOLD,
    }
    earliest = None
    for token, action in token_map.items():
        idx = joined.find(token)
        if idx >= 0 and (earliest is None or idx < earliest[0]):
            earliest = (idx, action)
    return earliest[1] if earliest else None


def _extract_quant_action(quant_results: Mapping[str, Any]) -> Optional[str]:
    if not isinstance(quant_results, Mapping) or not quant_results:
        return None
    score = 0
    count = 0
    for result in quant_results.values():
        if not isinstance(result, Mapping):
            continue
        signal = str(result.get("signal", "")).lower()
        if signal in {"bullish", "buy", "买入", "看涨"}:
            score += 1
            count += 1
        elif signal in {"bearish", "sell", "卖出", "看跌"}:
            score -= 1
            count += 1
        elif signal in {"neutral", "hold", "持有", "中性"}:
            count += 1
    if count == 0:
        return None
    if score > 0:
        return ACTION_BUY
    if score < 0:
        return ACTION_SELL
    return ACTION_HOLD


def _action_value(action: Optional[str]) -> int:
    if action == ACTION_BUY:
        return 1
    if action == ACTION_SELL:
        return -1
    return 0


def _evidence_quality_penalty(snapshot: Mapping[str, Any]) -> float:
    quality = _snapshot_quality(snapshot)
    if str(quality.get("grade", "")).upper() == "D":
        return 0.5
    if quality.get("missing_fields") or quality.get("conflicts"):
        return 0.7
    return 1.0


def _confidence_cap(issues: List[Mapping[str, Any]], snapshot: Mapping[str, Any]) -> float:
    if any(issue.get("severity") == "high" for issue in issues):
        return 0.45
    if any(issue.get("severity") == "medium" for issue in issues):
        return 0.65
    return 0.9


def _max_severity(issues: List[Mapping[str, Any]]) -> str:
    order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    severity = "none"
    for issue in issues:
        cur = str(issue.get("severity", "low"))
        if order.get(cur, 0) > order.get(severity, 0):
            severity = cur
    return severity


def _build_key_points(result: Mapping[str, Any], issues: List[Mapping[str, Any]], role_result: Mapping[str, Any]) -> List[str]:
    points: List[str] = []
    reports = _get_reports(result)
    for issue in issues:
        message = issue.get("message")
        if message:
            points.append(str(message))
    if role_result.get("role_contributions"):
        top = sorted(role_result["role_contributions"], key=lambda x: abs(x.get("contribution", 0)), reverse=True)[:2]
        for item in top:
            points.append(f"{item['label']}权重{item['weight']:.0%}，方向为{item['action']}")
    if len(points) < 3:
        points.extend(_extract_report_key_points(reports, limit=3 - len(points)))
    if not points:
        points.append("未发现高优先级审计问题")
    return _dedupe(points)[:5]


def _extract_report_key_points(reports: Mapping[str, str], limit: int = 3) -> List[str]:
    points: List[str] = []
    keywords = ["风险", "数据质量", "缺失", "矛盾", "共识", "现金流", "负债", "ROE", "PE"]
    preferred_keys = [
        "final_trade_decision",
        "risk_management_decision",
        "fundamentals_report",
        "master_consensus_report",
        "trader_investment_plan",
    ]
    for key in preferred_keys:
        text = reports.get(key, "")
        if not text:
            continue
        for raw_line in re.split(r"[\n。；]", text):
            line = raw_line.strip().lstrip("-*•0123456789. ").strip()
            if len(line) < 6:
                continue
            if any(keyword in line for keyword in keywords):
                points.append(line[:120])
                if len(points) >= limit:
                    return points
    return points


def _build_reasoning(audit: Mapping[str, Any], role_result: Mapping[str, Any], raw_decision: Mapping[str, Any]) -> str:
    pieces = []
    if audit.get("issues"):
        pieces.append("数据审计发现：" + "；".join(str(issue.get("message")) for issue in audit["issues"][:3]))
    pieces.append(f"角色加权结果为{role_result['action']}，加权分数 {role_result['weighted_score']:.4f}")
    if raw_decision.get("reasoning"):
        cleaned_reasoning = _sanitize_dialogue_artifacts(str(raw_decision["reasoning"]))[:160]
        if cleaned_reasoning:
            pieces.append(f"原始理由参考：{cleaned_reasoning}")
    return _sanitize_dialogue_artifacts("；".join(pieces))


def _format_recommendation(decision: Mapping[str, Any]) -> str:
    rec = f"投资建议：{decision.get('action', ACTION_HOLD)}。"
    if decision.get("target_price"):
        rec += f"目标价格：{decision['target_price']}元。"
    if decision.get("reasoning"):
        rec += f"决策依据：{decision['reasoning']}"
    return _sanitize_dialogue_artifacts(rec)


def _format_role_diagnostic(role: str, missing_data: List[Mapping[str, Any]], blocked: bool) -> str:
    role_name = {
        "fundamentals": "基本面分析师",
        "market": "市场分析师",
        "risk_management": "风险管理",
        "trader": "交易员",
        "warren_buffett": "巴菲特大师分析师",
        "peter_lynch": "彼得林奇大师分析师",
        "master_consensus": "投资大师共识",
    }.get(role, role)
    conclusion = "停止分析，原因是核心数据缺失会影响分析结果。" if blocked else "可继续分析，但必须标注数据缺失影响。"
    lines = [
        "## 数据缺失诊断",
        "",
        f"当前角色：{role_name}",
        f"结论：{conclusion}",
        "",
        "| 字段 | 中文名 | 缺失原因 | 是否影响结果 | 影响说明 | 建议修复 |",
        "|------|--------|----------|--------------|----------|----------|",
    ]
    for item in missing_data:
        affects = "是" if item.get("affects_result") else "否"
        lines.append(
            f"| {item.get('field')} | {item.get('label')} | {item.get('missing_reason')} | {affects} | {item.get('impact')} | {item.get('suggested_fix')} |"
        )
    return "\n".join(lines)


def _normalize_role(role_id: str) -> str:
    mapping = {
        "fundamental": "fundamentals",
        "fundamentals_analyst": "fundamentals",
        "risk": "risk_management",
        "risk_manager": "risk_management",
        "market_analyst": "market",
    }
    return mapping.get(str(role_id), str(role_id))


def _first_report(reports: Mapping[str, str], keys: List[str]) -> str:
    for key in keys:
        value = reports.get(key)
        if value:
            return value
    return ""


def _safe_float(value: Any, default: Optional[float]) -> Optional[float]:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            cleaned = value.replace("¥", "").replace("￥", "").replace("元", "").strip()
            if not cleaned or cleaned.lower() in {"none", "null", "n/a", "nan"}:
                return default
            return float(cleaned)
        return float(value)
    except Exception:
        return default


def _candidate_sources_for_field(field: str) -> List[Dict[str, str]]:
    if field in {"current_price", "historical_kline", "volume"}:
        return FREE_DATA_SOURCE_CANDIDATES["market_quote"]
    if field in {
        "revenue",
        "net_profit",
        "operating_cash_flow",
        "total_assets",
        "total_liabilities",
        "roe",
        "pe",
        "pb",
    }:
        return FREE_DATA_SOURCE_CANDIDATES["financial_statement"]
    return []


def candidate_sources_for_field(field: str) -> List[Dict[str, str]]:
    """Return free-source candidates for a missing audit field."""
    return _candidate_sources_for_field(field)


def _sanitize_dialogue_artifacts(text: str) -> str:
    if not text:
        return ""
    kept = []
    for part in re.split(r"([。！？!?；;\n])", text):
        if any(marker in part for marker in DIALOGUE_ARTIFACT_MARKERS):
            continue
        kept.append(part)
    cleaned = "".join(kept)
    for marker in DIALOGUE_ARTIFACT_MARKERS:
        cleaned = cleaned.replace(marker, "")
    cleaned = re.sub(r"^[。！？!?；;\s]+", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
