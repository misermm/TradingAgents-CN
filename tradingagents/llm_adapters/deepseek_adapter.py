"""
DeepSeek LLM适配器

已统一到 openai_compatible_base.ChatDeepSeekOpenAI
本文件保留用于向后兼容
"""

from tradingagents.llm_adapters.openai_compatible_base import ChatDeepSeekOpenAI as ChatDeepSeek
from tradingagents.llm_adapters.openai_compatible_base import ChatDeepSeekOpenAI

try:
    from tradingagents.config.config_manager import token_tracker
    TOKEN_TRACKING_ENABLED = True
except ImportError:
    TOKEN_TRACKING_ENABLED = False


def create_deepseek_llm(
    model: str = "deepseek-chat",
    temperature: float = 0.1,
    max_tokens: int = None,
    **kwargs
) -> ChatDeepSeek:
    return ChatDeepSeek(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )


DeepSeekLLM = ChatDeepSeek
