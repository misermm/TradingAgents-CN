"""Backward-compatible DashScope adapter exports."""

from tradingagents.llm_adapters.dashscope_openai_adapter import (
    ChatDashScopeOpenAI,
    ChatDashScopeOpenAIUnified,
    create_dashscope_openai_llm,
    get_available_openai_models,
    test_dashscope_openai_connection,
    test_dashscope_openai_function_calling,
)

ChatDashScope = ChatDashScopeOpenAIUnified

__all__ = [
    "ChatDashScope",
    "ChatDashScopeOpenAI",
    "ChatDashScopeOpenAIUnified",
    "create_dashscope_openai_llm",
    "get_available_openai_models",
    "test_dashscope_openai_connection",
    "test_dashscope_openai_function_calling",
]
