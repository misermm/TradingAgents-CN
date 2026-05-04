"""
阿里百炼 OpenAI兼容适配器

已统一到 openai_compatible_base.ChatDashScopeOpenAIUnified
本文件保留用于向后兼容
"""

from tradingagents.llm_adapters.openai_compatible_base import ChatDashScopeOpenAIUnified as ChatDashScopeOpenAI
from tradingagents.llm_adapters.openai_compatible_base import ChatDashScopeOpenAIUnified

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

try:
    from tradingagents.config.config_manager import token_tracker
except ImportError:
    token_tracker = None


DASHSCOPE_OPENAI_MODELS = {
    "qwen-turbo": {"description": "通义千问 Turbo", "context_length": 8192, "supports_function_calling": True},
    "qwen-plus": {"description": "通义千问 Plus", "context_length": 32768, "supports_function_calling": True},
    "qwen-plus-latest": {"description": "通义千问 Plus 最新版", "context_length": 32768, "supports_function_calling": True},
    "qwen-max": {"description": "通义千问 Max", "context_length": 32768, "supports_function_calling": True},
    "qwen-max-latest": {"description": "通义千问 Max 最新版", "context_length": 32768, "supports_function_calling": True},
    "qwen-long": {"description": "通义千问 Long", "context_length": 1000000, "supports_function_calling": True},
}


def get_available_openai_models():
    return DASHSCOPE_OPENAI_MODELS


def create_dashscope_openai_llm(
    model: str = "qwen-plus-latest",
    api_key: str = None,
    temperature: float = 0.1,
    max_tokens: int = 2000,
    **kwargs
) -> ChatDashScopeOpenAI:
    return ChatDashScopeOpenAI(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )


def test_dashscope_openai_connection(model: str = "qwen-turbo", api_key: str = None) -> bool:
    try:
        llm = create_dashscope_openai_llm(model=model, api_key=api_key, max_tokens=50)
        response = llm.invoke("你好")
        return bool(response and hasattr(response, 'content') and response.content)
    except Exception as e:
        logger.error(f"❌ DashScope连接失败: {e}")
        return False


def test_dashscope_openai_function_calling(model: str = "qwen-plus-latest", api_key: str = None) -> bool:
    try:
        llm = create_dashscope_openai_llm(model=model, api_key=api_key, max_tokens=200)
        from langchain_core.tools import tool

        @tool
        def test_tool(query: str) -> str:
            return f"收到查询: {query}"

        llm_with_tools = llm.bind_tools([test_tool])
        response = llm_with_tools.invoke("请使用test_tool查询hello")
        return True
    except Exception as e:
        logger.error(f"❌ Function Calling测试失败: {e}")
        return False
