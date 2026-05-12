import json
from pathlib import Path

import pytest

from tradingagents.graph.report_audit import (
    audit_cn_report,
    reconcile_cn_decision,
    run_role_data_gate,
)


SAMPLE_PATH = Path("results/000002_分析报告_2026-05-11.json")


def _load_sample():
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def test_cn_report_audit_detects_price_conflict():
    sample = _load_sample()

    audit = audit_cn_report(sample)

    issue_codes = {issue["code"] for issue in audit["issues"]}
    assert "PRICE_CONFLICT" in issue_codes
    price_issue = next(issue for issue in audit["issues"] if issue["code"] == "PRICE_CONFLICT")
    assert price_issue["severity"] == "high"


def test_decision_reconciler_uses_weighted_roles_and_data_gate_for_sample():
    sample = _load_sample()

    decision = reconcile_cn_decision(sample, sample.get("decision", {}))

    assert decision["action"] == "持有"
    assert decision["confidence"] <= 0.45
    assert "TARGET_PRICE_INVALID" in {issue["code"] for issue in decision["audit"]["issues"]}
    assert decision["target_price"] is None
    assert len(decision["key_points"]) >= 3
    assert decision["role_contributions"]
    assert "角色加权" in decision["reasoning"] or "数据" in decision["reasoning"]
    risk_role = next(item for item in decision["role_contributions"] if item["role"] == "risk_management")
    assert risk_role["action"] == "持有"


def test_low_quality_caps_confidence():
    result = {
        "reports": {
            "final_trade_decision": "最终建议：买入。目标价 10 元。",
            "fundamentals_report": "数据质量等级: D级。PE/ROE 数据矛盾。",
        },
        "decision": {"action": "买入", "confidence": 0.9, "target_price": 10.0},
        "cn_fact_snapshot": {
            "current_price": 4.0,
            "quality": {
                "grade": "D",
                "missing_fields": [],
                "conflicts": [{"code": "pe_conflict", "field": "pe"}],
            },
        },
    }

    decision = reconcile_cn_decision(result, result["decision"])

    assert decision["confidence"] <= 0.45
    assert decision["action"] == "持有"


def test_key_points_are_backfilled():
    result = {
        "reports": {
            "final_trade_decision": "最终建议：持有。\n- 风险委员会提示现金流风险。\n- 价格数据存在冲突。",
            "master_consensus_report": "大师共识：看跌。ROE 为负，负债较高。",
            "fundamentals_report": "数据质量 D 级，缺少营业收入。",
        },
        "decision": {"action": "持有", "confidence": 0.4, "key_points": []},
    }

    decision = reconcile_cn_decision(result, result["decision"])

    assert len(decision["key_points"]) >= 3


def test_invalid_target_price_blocks_high_confidence_buy():
    result = {
        "reports": {
            "final_trade_decision": "最终建议：买入。",
            "fundamentals_report": "数据质量等级: D级。",
        },
        "decision": {"action": "买入", "confidence": 0.8, "target_price": None},
        "cn_fact_snapshot": {"quality": {"grade": "D", "missing_fields": [], "conflicts": []}},
    }

    decision = reconcile_cn_decision(result, result["decision"])

    assert decision["action"] == "持有"
    assert decision["confidence"] <= 0.45


def test_dialogue_artifacts_flagged():
    result = {
        "reports": {
            "final_trade_decision": "你们觉得这个方案是否有道理？最终建议：持有。"
        }
    }

    audit = audit_cn_report(result)

    assert "DIALOGUE_ARTIFACT" in {issue["code"] for issue in audit["issues"]}


def test_dialogue_artifacts_are_removed_from_final_recommendation():
    result = {
        "reports": {
            "final_trade_decision": "最终建议：持有。"
        },
        "decision": {
            "action": "持有",
            "confidence": 0.5,
            "reasoning": "你们觉得这个方案是否有道理？最终应以风险约束为准。",
        },
    }

    decision = reconcile_cn_decision(result, result["decision"])

    assert "你们觉得" not in decision["reasoning"]
    assert "是否有道理" not in decision["recommendation"]
    assert "风险约束" in decision["recommendation"]


def test_missing_data_details_are_reported():
    result = {
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "revenue"},
                    {"field": "total_liabilities"},
                    {"field": "operating_cash_flow"},
                ],
                "conflicts": [],
            }
        }
    }

    audit = audit_cn_report(result)

    assert len(audit["missing_data"]) == 3
    for item in audit["missing_data"]:
        assert item["field"]
        assert item["label"]
        assert item["required_by"]
        assert item["missing_reason"]
        assert item["impact"]
        assert "affects_result" in item
        assert "blocks_roles" in item
        assert item["suggested_fix"]
        assert "candidate_free_sources" in item


def test_price_conflict_flags_any_deviation():
    result = {
        "cn_fact_snapshot": {
            "current_price": 4.09,
            "quality": {"missing_fields": [], "conflicts": []},
        },
        "reports": {
            "market_report": "当前价：4.10 元，成交量稳定。"
        },
    }

    audit = audit_cn_report(result)

    issue_codes = {issue["code"] for issue in audit["issues"]}
    assert "PRICE_CONFLICT" in issue_codes
    issue = next(issue for issue in audit["issues"] if issue["code"] == "PRICE_CONFLICT")
    assert issue["severity"] in {"low", "medium", "high"}


def test_weighted_role_decision_uses_professional_weights():
    result = {
        "reports": {
            "risk_management_decision": "最终建议：持有。",
            "trader_investment_plan": "最终交易建议：买入。",
            "master_consensus_report": "共识信号：看跌。",
            "fundamentals_report": "最终投资建议：回避。",
            "market_report": "技术面建议：观望。",
        },
        "master_quantitative_results": {
            "warren_buffett": {"signal": "bearish"},
            "peter_lynch": {"signal": "bearish"},
        },
        "cn_fact_snapshot": {
            "quality": {"grade": "B", "missing_fields": [], "conflicts": []}
        },
    }

    decision = reconcile_cn_decision(result, {})

    assert decision["role_contributions"]
    assert decision["weighted_score"] < 0
    assert decision["action"] in {"持有", "卖出"}


def test_role_using_conflicting_price_gets_evidence_quality_discount():
    result = {
        "reports": {
            "risk_management_decision": "最终建议：持有。",
            "trader_investment_plan": "最终交易建议：买入。当前价 20.00 元。",
            "market_report": "当前价：4.00 元，趋势中性。",
        },
        "cn_fact_snapshot": {
            "current_price": 4.0,
            "quality": {"grade": "B", "missing_fields": [], "conflicts": []},
        },
    }

    decision = reconcile_cn_decision(result, {})

    trader = next(item for item in decision["role_contributions"] if item["role"] == "trader")
    market = next(item for item in decision["role_contributions"] if item["role"] == "market")
    assert trader["conflicts_with_snapshot"] is True
    assert trader["evidence_quality"] < market["evidence_quality"]


def test_missing_data_can_recommend_new_free_source():
    result = {
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {
                        "field": "revenue",
                        "missing_reason": "现有免费数据源未返回该字段",
                    }
                ],
                "conflicts": [],
            }
        }
    }

    audit = audit_cn_report(result)

    assert "免费" in audit["missing_data"][0]["suggested_fix"]
    assert audit["missing_data"][0]["candidate_free_sources"]


def test_invalid_target_price_deviation_is_audit_issue():
    result = {
        "reports": {
            "final_trade_decision": "最终建议：买入。"
        },
        "decision": {"action": "买入", "confidence": 0.8, "target_price": 20.0},
        "cn_fact_snapshot": {
            "current_price": 4.0,
            "quality": {"grade": "B", "missing_fields": [], "conflicts": []},
        },
    }

    decision = reconcile_cn_decision(result, result["decision"])

    assert "TARGET_PRICE_INVALID" in {issue["code"] for issue in decision["audit"]["issues"]}
    assert decision["action"] == "持有"
    assert decision["confidence"] <= 0.45


def test_role_data_gate_blocks_analysis_when_required_fields_missing():
    snapshot = {
        "quality": {
            "missing_fields": [
                {"field": "revenue"},
                {"field": "total_liabilities"},
                {"field": "operating_cash_flow"},
            ]
        }
    }

    gate = run_role_data_gate("fundamentals", snapshot)

    assert gate["role_blocked"] is True
    report = gate["diagnostic_report"]
    assert "数据缺失诊断" in report
    assert "营业收入" in report
    assert "总负债" in report
    assert "经营现金流" in report
    for forbidden in ["目标价", "仓位", "置信度"]:
        assert forbidden not in report


def test_analysis_result_model_preserves_cn_audit_fields():
    from app.models.analysis import AnalysisResult

    result = AnalysisResult(
        recommendation="投资建议：持有。",
        report_audit={"audit_passed": False, "issues": [{"code": "PRICE_CONFLICT"}]},
        weighted_decision={"action": "持有", "weighted_score": 0.0},
        cn_fact_snapshot={"symbol": "000002", "market": "CN"},
    )

    dumped = result.model_dump()

    assert dumped["report_audit"]["issues"][0]["code"] == "PRICE_CONFLICT"
    assert dumped["weighted_decision"]["action"] == "持有"
    assert dumped["cn_fact_snapshot"]["symbol"] == "000002"


def test_fundamentals_analyst_stops_when_role_data_gate_blocks():
    from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst

    class _FailingToolkit:
        config = {"online_tools": True}

        @property
        def get_stock_fundamentals_unified(self):
            raise AssertionError("blocked role must not access data tools")

    node = create_fundamentals_analyst(llm=object(), toolkit=_FailingToolkit())
    state = {
        "messages": [],
        "trade_date": "2026-05-11",
        "company_of_interest": "000002",
        "fundamentals_tool_call_count": 0,
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "revenue"},
                    {"field": "operating_cash_flow"},
                ]
            }
        },
    }

    update = node(state)

    assert update["fundamentals_tool_call_count"] == 0
    assert "数据缺失诊断" in update["fundamentals_report"]
    assert "营业收入" in update["fundamentals_report"]
    assert "买入" not in update["fundamentals_report"]


def test_market_analyst_stops_when_role_data_gate_blocks():
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    class _FailingToolkit:
        config = {"online_tools": True}

        @property
        def get_stock_market_data_unified(self):
            raise AssertionError("blocked role must not access data tools")

    node = create_market_analyst(llm=object(), toolkit=_FailingToolkit())
    state = {
        "messages": [],
        "trade_date": "2026-05-11",
        "company_of_interest": "000002",
        "market_tool_call_count": 0,
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "current_price"},
                    {"field": "historical_kline"},
                ]
            }
        },
    }

    update = node(state)

    assert update["market_tool_call_count"] == 0
    assert "数据缺失诊断" in update["market_report"]
    assert "当前价" in update["market_report"]
    assert "卖出" not in update["market_report"]


def test_trader_stops_when_role_data_gate_blocks():
    from tradingagents.agents.trader.trader import create_trader

    class _FailingLLM:
        def invoke(self, *_args, **_kwargs):
            raise AssertionError("blocked trader must not call LLM")

    node = create_trader(llm=_FailingLLM(), memory=None)
    state = {
        "messages": [],
        "company_of_interest": "000002",
        "investment_plan": "上游计划建议买入。",
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "current_price"},
                ]
            }
        },
    }

    update = node(state)

    assert update["messages"] == []
    assert "数据缺失诊断" in update["trader_investment_plan"]
    assert "当前价" in update["trader_investment_plan"]
    assert "买入" not in update["trader_investment_plan"]


def test_risk_manager_stops_when_role_data_gate_blocks():
    from tradingagents.agents.managers.risk_manager import create_risk_manager

    class _FailingLLM:
        def invoke(self, *_args, **_kwargs):
            raise AssertionError("blocked risk manager must not call LLM")

    node = create_risk_manager(llm=_FailingLLM(), memory=None)
    state = {
        "company_of_interest": "000002",
        "risk_debate_state": {
            "history": "风险辩论历史",
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
        "market_report": "市场报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "sentiment_report": "情绪报告",
        "investment_plan": "交易计划建议买入。",
        "master_consensus_report": "",
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "total_liabilities"},
                    {"field": "operating_cash_flow"},
                ]
            }
        },
    }

    update = node(state)

    assert update["messages"] == []
    assert "数据缺失诊断" in update["final_trade_decision"]
    assert "总负债" in update["final_trade_decision"]
    assert "买入" not in update["final_trade_decision"]


@pytest.mark.parametrize(
    ("factory_path", "factory_name", "current_key", "latest_speaker"),
    [
        ("tradingagents.agents.risk_mgmt.aggresive_debator", "create_risky_debator", "current_risky_response", "Risky"),
        ("tradingagents.agents.risk_mgmt.conservative_debator", "create_safe_debator", "current_safe_response", "Safe"),
        ("tradingagents.agents.risk_mgmt.neutral_debator", "create_neutral_debator", "current_neutral_response", "Neutral"),
    ],
)
def test_risk_debators_stop_when_role_data_gate_blocks(factory_path, factory_name, current_key, latest_speaker):
    import importlib

    class _FailingLLM:
        def invoke(self, *_args, **_kwargs):
            raise AssertionError("blocked risk debator must not call LLM")

    module = importlib.import_module(factory_path)
    node = getattr(module, factory_name)(_FailingLLM())
    state = {
        "company_of_interest": "000002",
        "risk_debate_state": {
            "history": "",
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "total_liabilities"},
                    {"field": "operating_cash_flow"},
                ]
            }
        },
    }

    update = node(state)
    debate_state = update["risk_debate_state"]

    assert update["messages"] == []
    assert debate_state["latest_speaker"] == latest_speaker
    assert debate_state["count"] == 1
    assert "数据缺失诊断" in debate_state[current_key]
    assert "经营现金流" in debate_state[current_key]
    assert "买入" not in debate_state[current_key]


@pytest.mark.parametrize(
    ("factory_path", "factory_name", "history_key"),
    [
        ("tradingagents.agents.researchers.bull_researcher", "create_bull_researcher", "bull_history"),
        ("tradingagents.agents.researchers.bear_researcher", "create_bear_researcher", "bear_history"),
    ],
)
def test_research_debators_stop_when_core_data_gate_blocks(factory_path, factory_name, history_key):
    import importlib

    class _FailingLLM:
        def invoke(self, *_args, **_kwargs):
            raise AssertionError("blocked research debator must not call LLM")

    module = importlib.import_module(factory_path)
    node = getattr(module, factory_name)(_FailingLLM(), memory=None)
    state = {
        "company_of_interest": "000002",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "master_consensus_report": "",
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "current_price"},
                    {"field": "revenue"},
                ]
            }
        },
    }

    update = node(state)
    debate_state = update["investment_debate_state"]

    assert update["messages"] == []
    assert debate_state["count"] == 1
    assert "数据缺失诊断" in debate_state["current_response"]
    assert "当前价" in debate_state["current_response"]
    assert "营业收入" in debate_state["current_response"]
    assert debate_state[history_key]
    assert "买入" not in debate_state["current_response"]
    assert "卖出" not in debate_state["current_response"]
    assert "持有" not in debate_state["current_response"]


def test_research_manager_stops_when_core_data_gate_blocks():
    from tradingagents.agents.managers.research_manager import create_research_manager

    class _FailingLLM:
        def invoke(self, *_args, **_kwargs):
            raise AssertionError("blocked research manager must not call LLM")

    node = create_research_manager(_FailingLLM(), memory=None)
    state = {
        "company_of_interest": "000002",
        "investment_debate_state": {
            "history": "上游辩论历史",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 2,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "master_consensus_report": "",
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "current_price"},
                    {"field": "revenue"},
                ]
            }
        },
    }

    update = node(state)

    assert update["messages"] == []
    assert "数据缺失诊断" in update["investment_plan"]
    assert "当前价" in update["investment_plan"]
    assert "营业收入" in update["investment_plan"]
    assert update["investment_debate_state"]["judge_decision"] == update["investment_plan"]
    assert "买入" not in update["investment_plan"]
    assert "卖出" not in update["investment_plan"]
    assert "持有" not in update["investment_plan"]


@pytest.mark.parametrize(
    ("factory_path", "factory_name", "missing_field", "expected_label"),
    [
        ("tradingagents.agents.masters.warren_buffett", "create_warren_buffett_analyst", "operating_cash_flow", "经营现金流"),
        ("tradingagents.agents.masters.peter_lynch", "create_peter_lynch_analyst", "revenue", "营业收入"),
    ],
)
def test_master_analysts_stop_when_core_data_gate_blocks(factory_path, factory_name, missing_field, expected_label):
    import importlib

    class _FailingLLM:
        def invoke(self, *_args, **_kwargs):
            raise AssertionError("blocked master analyst must not call LLM")

    class _FailingTool:
        def invoke(self, *_args, **_kwargs):
            raise AssertionError("blocked master analyst must not call data tools")

    class _Toolkit:
        get_stock_fundamentals_unified = _FailingTool()

    module = importlib.import_module(factory_path)
    node = getattr(module, factory_name)(_FailingLLM(), _Toolkit())
    state = {
        "messages": [],
        "trade_date": "2026-05-11",
        "company_of_interest": "000002",
        "master_reports": {},
        "master_tool_call_counts": {},
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": missing_field},
                ]
            }
        },
    }

    update = node(state)
    report = next(iter(update["master_reports"].values()))

    assert update["messages"] == []
    assert "数据缺失诊断" in report
    assert expected_label in report
    assert "买入" not in report
    assert "卖出" not in report
    assert "持有" not in report


def test_master_consensus_stops_when_core_data_gate_blocks():
    from tradingagents.agents.masters.master_consensus import create_master_consensus

    class _FailingLLM:
        def invoke(self, *_args, **_kwargs):
            raise AssertionError("blocked master consensus must not call LLM")

    node = create_master_consensus(llm=_FailingLLM())
    state = {
        "company_of_interest": "000002",
        "master_reports": {
            "warren_buffett": "巴菲特报告",
            "peter_lynch": "林奇报告",
        },
        "cn_fact_snapshot": {
            "quality": {
                "missing_fields": [
                    {"field": "revenue"},
                ]
            }
        },
    }

    update = node(state)

    assert update["messages"] == []
    assert "数据缺失诊断" in update["master_consensus_report"]
    assert "营业收入" in update["master_consensus_report"]
    assert "买入" not in update["master_consensus_report"]
    assert "卖出" not in update["master_consensus_report"]
    assert "持有" not in update["master_consensus_report"]


@pytest.mark.integration
def test_lmstudio_near_e2e_cn_audit_output_contains_trust_fields():
    from tradingagents.graph.trading_graph import create_llm_by_provider

    base_url = "http://192.168.3.39:1234/v1"
    model = "qwen3.5-9b-claude-4.6-highiq-instruct"
    max_iterations = 40

    llm = create_llm_by_provider(
        provider="lmstudio",
        model=model,
        backend_url=base_url,
        temperature=0,
        max_tokens=32,
        timeout=30,
        api_key="lmstudio",
        max_retries=0,
    )
    lm_response = llm.invoke("请只回复 OK，用于验证本地 LM Studio 模型可用。")
    assert getattr(lm_response, "content", "")

    near_e2e_result = {
        "reports": {
            "risk_management_decision": "最终建议：持有。现金流和负债风险需要复核。",
            "trader_investment_plan": "最终交易建议：买入。当前价 8.80 元。",
            "master_consensus_report": "共识信号：看跌。ROE 为负，负债较高。",
            "fundamentals_report": "数据质量等级: D级。缺少营业收入和经营现金流。",
            "market_report": "当前价：4.09 元，量价信号偏弱。",
        },
        "decision": {"action": "买入", "confidence": 0.88, "target_price": None, "key_points": []},
        "master_quantitative_results": {
            "warren_buffett": {"signal": "bearish"},
            "peter_lynch": {"signal": "bearish"},
        },
        "cn_fact_snapshot": {
            "symbol": "000002",
            "stock_name": "万科A",
            "market": "CN",
            "currency": "CNY",
            "current_price": 4.09,
            "quality": {
                "grade": "D",
                "missing_fields": [
                    {"field": "revenue"},
                    {"field": "operating_cash_flow"},
                ],
                "conflicts": [{"code": "pe_conflict", "field": "pe"}],
            },
        },
        "lmstudio_validation": {
            "base_url": base_url,
            "model": model,
            "max_iterations": max_iterations,
        },
    }

    decision = reconcile_cn_decision(near_e2e_result, near_e2e_result["decision"])
    output = {
        "report_audit": decision["audit"],
        "weighted_decision": {
            "action": decision["action"],
            "weighted_score": decision["weighted_score"],
            "role_contributions": decision["role_contributions"],
        },
        "cn_fact_snapshot": near_e2e_result["cn_fact_snapshot"],
        "lmstudio_validation": near_e2e_result["lmstudio_validation"],
    }

    assert output["lmstudio_validation"]["base_url"] == base_url
    assert output["lmstudio_validation"]["model"] == model
    assert output["lmstudio_validation"]["max_iterations"] == 40
    assert output["report_audit"]["issues"]
    assert output["weighted_decision"]["role_contributions"]
    assert output["weighted_decision"]["action"] == "持有"
    assert output["cn_fact_snapshot"]["symbol"] == "000002"
