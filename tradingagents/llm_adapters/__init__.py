# LLM Adapters for TradingAgents
# 统一导出，所有适配器来自 openai_compatible_base

from .openai_compatible_base import (
    OpenAICompatibleBase,
    ChatDeepSeekOpenAI,
    ChatDashScopeOpenAIUnified,
    ChatQianfanOpenAI,
    ChatZhipuOpenAI,
    ChatCustomOpenAI,
)

# 向后兼容别名
ChatDashScopeOpenAI = ChatDashScopeOpenAIUnified
ChatDeepSeek = ChatDeepSeekOpenAI

try:
    from .google_openai_adapter import ChatGoogleOpenAI
except ImportError:
    ChatGoogleOpenAI = None

__all__ = [
    "OpenAICompatibleBase",
    "ChatDeepSeekOpenAI",
    "ChatDashScopeOpenAIUnified",
    "ChatDashScopeOpenAI",
    "ChatDeepSeek",
    "ChatQianfanOpenAI",
    "ChatZhipuOpenAI",
    "ChatCustomOpenAI",
    "ChatGoogleOpenAI",
]
