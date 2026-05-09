import time
import functools
import threading
import json
import re
from typing import Any, Callable, Tuple, Type

from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

_RETRYABLE_ERRORS = (
    "InternalServerError",
    "ServiceUnavailable",
    "BadGateway",
    "GatewayTimeout",
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "429",
    "500",
    "502",
    "503",
    "504",
)


def _extract_openrouter_error(exc: Exception) -> dict:
    exc_str = str(exc)
    error_info = {
        "type": type(exc).__name__,
        "message": exc_str,
        "http_code": None,
        "error_code": None,
        "raw_details": None,
        "provider_hint": None,
    }

    # 尝试从异常消息中提取 HTTP 状态码
    http_match = re.search(r'HTTP[_\s]?(\d{3})', exc_str, re.IGNORECASE)
    if http_match:
        try:
            error_info["http_code"] = int(http_match.group(1))
        except (ValueError, IndexError):
            pass

    # 尝试提取 JSON 格式的错误详情（通用模式）
    json_patterns = [
        r'\{.*"error".*\}',
        r'\{.*"message".*\}',
        r'\{.*"error_message".*\}',
        r'\{.*"error_code".*\}',
    ]
    for pattern in json_patterns:
        json_match = re.search(pattern, exc_str, re.DOTALL)
        if json_match:
            try:
                error_data = json.loads(json_match.group())
                if isinstance(error_data, dict):
                    if "error" in error_data:
                        err = error_data["error"]
                        if isinstance(err, dict):
                            error_info["message"] = err.get("message") or err.get("Message") or str(err)
                            error_info["error_code"] = err.get("code") or err.get("error_code") or err.get("type")
                            error_info["raw_details"] = err
                        elif isinstance(err, str):
                            error_info["message"] = err
                    elif "message" in error_data:
                        error_info["message"] = error_data["message"]
                        error_info["error_code"] = error_data.get("code") or error_data.get("error_code")
                        error_info["raw_details"] = error_data
                    elif "error_message" in error_data:
                        error_info["message"] = error_data["error_message"]
                        error_info["error_code"] = error_data.get("error_code")
                        error_info["raw_details"] = error_data
                    break
            except (json.JSONDecodeError, KeyError):
                pass

    # 从消息中直接提取常见错误代码
    if not error_info["error_code"]:
        code_patterns = [
            r'\[([A-Z_]+)\]$',
            r'"code":\s*"([^"]+)"',
            r'error_code[=:\s]+([A-Z_0-9]+)',
            r'code[=:\s]+([A-Z_0-9]+)',
        ]
        for pattern in code_patterns:
            match = re.search(pattern, exc_str, re.IGNORECASE)
            if match:
                error_info["error_code"] = match.group(1)
                break

    # 尝试识别提供商
    provider_hints = {
        "openrouter": ["openrouter", "sk-or-v1"],
        "deepseek": ["deepseek", "deepseek-api"],
        "dashscope": ["dashscope", "aliyun", "qwen"],
        "anthropic": ["anthropic", "claude"],
        "google": ["google", "gemini", "aiplatform"],
        "openai": ["openai", "gpt"],
        "azure": ["azure", "api.azure"],
    }
    for provider, hints in provider_hints.items():
        for hint in hints:
            if hint in exc_str.lower():
                error_info["provider_hint"] = provider
                break
        if error_info["provider_hint"]:
            break

    return error_info


def _format_error_for_display(error_info: dict) -> str:
    parts = []

    if error_info["provider_hint"]:
        parts.append(f"[{error_info['provider_hint'].upper()}]")

    if error_info["http_code"] and str(error_info["http_code"]) not in error_info["message"]:
        parts.append(f"HTTP {error_info['http_code']}")

    if error_info["error_code"]:
        parts.append(f"[{error_info['error_code']}]")

    # 使用原始消息，但清理可能重复的信息
    msg = error_info["message"]
    if error_info["http_code"]:
        msg = re.sub(r'HTTP[_\s]?\d{3}\s*', '', msg, flags=re.IGNORECASE)
    parts.append(msg.strip())

    return " ".join(parts).strip()


class TokenCounter:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._total_tokens = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._call_count = 0

    @classmethod
    def get(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def add(self, response):
        try:
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                meta = response.usage_metadata
                pt = getattr(meta, 'input_tokens', None) or meta.get('input_tokens', 0) or 0
                ct = getattr(meta, 'output_tokens', None) or meta.get('output_tokens', 0) or 0
                self._prompt_tokens += pt
                self._completion_tokens += ct
                self._total_tokens += pt + ct
                self._call_count += 1
                return
            if hasattr(response, 'response_metadata') and response.response_metadata:
                meta = response.response_metadata
                token_usage = meta.get('token_usage', meta.get('usage', {}))
                if isinstance(token_usage, dict):
                    pt = token_usage.get('prompt_tokens', token_usage.get('input_tokens', 0))
                    ct = token_usage.get('completion_tokens', token_usage.get('output_tokens', 0))
                    self._prompt_tokens += pt or 0
                    self._completion_tokens += ct or 0
                    self._total_tokens += (pt or 0) + (ct or 0)
                    self._call_count += 1
        except Exception:
            pass

    @property
    def total_tokens(self):
        return self._total_tokens

    @property
    def prompt_tokens(self):
        return self._prompt_tokens

    @property
    def completion_tokens(self):
        return self._completion_tokens

    @property
    def call_count(self):
        return self._call_count

    def reset(self):
        self._total_tokens = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._call_count = 0

    def to_dict(self):
        return {
            "total_tokens": self._total_tokens,
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "call_count": self._call_count,
        }


def _is_retryable_error(exc: Exception) -> bool:
    exc_name = type(exc).__name__
    exc_str = str(exc)
    for pattern in _RETRYABLE_ERRORS:
        if pattern in exc_name or pattern in exc_str:
            return True
    return False


def retry_llm_invoke(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    **kwargs,
) -> Any:
    last_error = None
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            try:
                TokenCounter.get().add(result)
            except Exception:
                pass
            return result
        except Exception as exc:
            last_error = exc
            if not _is_retryable_error(exc):
                raise

            error_info = _extract_openrouter_error(exc)
            error_display = _format_error_for_display(error_info)

            if attempt < max_retries - 1:
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                jitter = delay * 0.1
                actual_delay = delay + (time.time() % jitter if jitter > 0 else 0)
                logger.warning(
                    f"⚠️ [LLM重试] {error_display} "
                    f"(第{attempt + 1}/{max_retries}次重试，{actual_delay:.1f}s后重试)"
                )
                if error_info.get("raw_details"):
                    raw = error_info["raw_details"]
                    if isinstance(raw, dict):
                        for key in ["message", "code", "type", "param", "internal_error"]:
                            if key in raw and raw[key]:
                                logger.warning(f"   {key}: {raw[key]}")
                time.sleep(actual_delay)
            else:
                logger.error(f"❌ [LLM重试] 重试{max_retries}次后仍失败:")
                logger.error(f"   原始错误: {error_display}")
                if error_info.get("raw_details"):
                    raw = error_info["raw_details"]
                    if isinstance(raw, dict):
                        logger.error("   详细信息:")
                        for key, value in raw.items():
                            if value:
                                logger.error(f"      {key}: {value}")
                raise
    raise last_error


def with_llm_retry(max_retries: int = 3, base_delay: float = 2.0):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_llm_invoke(
                func, *args,
                max_retries=max_retries,
                base_delay=base_delay,
                **kwargs,
            )
        return wrapper
    return decorator
