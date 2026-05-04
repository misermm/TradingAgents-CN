import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from .base_client import BaseLLMClient, normalize_content
from .validators import validate_model


class NormalizedChatOpenAI(ChatOpenAI):
    """ChatOpenAI wrapper that normalizes typed content blocks to text."""

    def invoke(self, input, config=None, **kwargs):
        return normalize_content(super().invoke(input, config, **kwargs))


_PASSTHROUGH_KWARGS = (
    "temperature",
    "max_tokens",
    "timeout",
    "max_retries",
    "callbacks",
    "http_client",
    "http_async_client",
)

_PROVIDER_CONFIG = {
    "deepseek": ("https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_API_KEY"),
    "glm": ("https://open.bigmodel.cn/api/paas/v4/", "ZHIPU_API_KEY"),
    "qianfan": ("https://qianfan.baidubce.com/v2", "QIANFAN_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "aihubmix": ("https://aihubmix.com/v1", "AIHUBMIX_API_KEY"),
    "ollama": ("http://localhost:11434/v1", None),
    "lmstudio": ("http://localhost:1234/v1", None),
    "custom_openai": (None, "CUSTOM_OPENAI_API_KEY"),
}

_ADAPTER_PROVIDER_MAP = {
    "deepseek": "ChatDeepSeekOpenAI",
    "qwen": "ChatDashScopeOpenAIUnified",
    "glm": "ChatZhipuOpenAI",
    "qianfan": "ChatQianfanOpenAI",
    "custom_openai": "ChatCustomOpenAI",
}


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI and OpenAI-compatible providers."""

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        provider: str = "openai",
        **kwargs,
    ):
        super().__init__(model, base_url, **kwargs)
        self.provider = provider.lower()

    def get_llm(self) -> Any:
        self.warn_if_unknown_model()

        if self.provider in _ADAPTER_PROVIDER_MAP:
            return self._get_adapter_llm()

        return self._get_basic_llm()

    def _get_adapter_llm(self) -> Any:
        try:
            from tradingagents.llm_adapters.openai_compatible_base import (
                ChatDeepSeekOpenAI,
                ChatDashScopeOpenAIUnified,
                ChatZhipuOpenAI,
                ChatQianfanOpenAI,
                ChatCustomOpenAI,
            )

            adapter_classes = {
                "deepseek": ChatDeepSeekOpenAI,
                "qwen": ChatDashScopeOpenAIUnified,
                "glm": ChatZhipuOpenAI,
                "qianfan": ChatQianfanOpenAI,
                "custom_openai": ChatCustomOpenAI,
            }

            adapter_class = adapter_classes.get(self.provider)
            if adapter_class:
                llm_kwargs = {"model": self.model}
                if self.base_url:
                    llm_kwargs["base_url"] = self.base_url
                api_key = self.kwargs.get("api_key")
                if api_key:
                    llm_kwargs["api_key"] = api_key
                for key in _PASSTHROUGH_KWARGS:
                    if key in self.kwargs:
                        llm_kwargs[key] = self.kwargs[key]
                return adapter_class(**llm_kwargs)
        except ImportError:
            pass

        return self._get_basic_llm()

    def _get_basic_llm(self) -> Any:
        llm_kwargs = {"model": self.model}

        if self.provider in _PROVIDER_CONFIG:
            default_base_url, api_key_env = _PROVIDER_CONFIG[self.provider]
            if self.base_url:
                llm_kwargs["base_url"] = self.base_url
            elif self.provider in ("ollama", "lmstudio"):
                from .provider_keys import default_backend_url
                llm_kwargs["base_url"] = default_backend_url(self.provider)
            else:
                llm_kwargs["base_url"] = default_base_url
            if api_key_env:
                api_key = self.kwargs.get("api_key") or os.environ.get(api_key_env)
                if api_key:
                    llm_kwargs["api_key"] = api_key
            else:
                llm_kwargs["api_key"] = self.provider if self.provider in ("ollama", "lmstudio") else "ollama"
        elif self.base_url:
            llm_kwargs["base_url"] = self.base_url
            api_key = self.kwargs.get("api_key") or os.environ.get("OPENAI_API_KEY")
            if api_key:
                llm_kwargs["api_key"] = api_key

        for key in _PASSTHROUGH_KWARGS:
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        return NormalizedChatOpenAI(**llm_kwargs)

    def validate_model(self) -> bool:
        return validate_model(self.provider, self.model)
