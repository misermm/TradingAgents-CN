import time
import functools
import threading
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
            if attempt < max_retries - 1:
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                jitter = delay * 0.1
                actual_delay = delay + (time.time() % jitter if jitter > 0 else 0)
                logger.warning(
                    f"⚠️ [LLM重试] {type(exc).__name__}: {str(exc)[:150]} "
                    f"(第{attempt + 1}/{max_retries}次重试，{actual_delay:.1f}s后重试)"
                )
                time.sleep(actual_delay)
            else:
                logger.error(
                    f"❌ [LLM重试] 重试{max_retries}次后仍失败: "
                    f"{type(exc).__name__}: {str(exc)[:200]}"
                )
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
