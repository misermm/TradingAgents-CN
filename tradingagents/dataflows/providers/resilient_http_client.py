"""
弹性HTTP客户端
提供统一的HTTP请求能力：重试、超时、限速、熔断
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class DataSourceResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    source: str = ""
    latency_ms: float = 0.0
    from_cache: bool = False


class CircuitBreaker:
    """
    HTTP请求级别熔断器
    单次请求连续失败达阈值后熔断，冷却期后进入半开状态探测
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._half_open_max_calls = half_open_max_calls

        self._state = self.CLOSED
        self._consecutive_failures = 0
        self._opened_at: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            if self._opened_at and time.monotonic() - self._opened_at >= self._cooldown_seconds:
                self._state = self.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def allow_request(self) -> bool:
        current = self.state
        if current == self.CLOSED:
            return True
        if current == self.HALF_OPEN:
            if self._half_open_calls < self._half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        return False

    def record_success(self):
        self._consecutive_failures = 0
        self._state = self.CLOSED
        self._half_open_calls = 0

    def record_failure(self):
        self._consecutive_failures += 1
        if self._state == self.HALF_OPEN:
            self._trip_open()
        elif self._consecutive_failures >= self._failure_threshold:
            self._trip_open()

    def _trip_open(self):
        self._state = self.OPEN
        self._opened_at = time.monotonic()
        logger.warning(
            f"🔴 熔断器打开，连续失败 {self._consecutive_failures} 次，"
            f"冷却 {self._cooldown_seconds}s"
        )

    def reset(self):
        self._consecutive_failures = 0
        self._state = self.CLOSED
        self._opened_at = None
        self._half_open_calls = 0


class ResilientHttpClient:
    """
    弹性HTTP客户端
    统一提供重试、超时、限速、熔断能力

    用法:
        client = ResilientHttpClient(max_retries=3, timeout_seconds=30)
        result = client.call(func, *args, **kwargs)
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff_factor: float = 2.0,
        timeout_seconds: float = 30.0,
        connect_timeout: float = 10.0,
        rate_limit_per_second: float = 1.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        name: str = "default",
    ):
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._retry_backoff_factor = retry_backoff_factor
        self._timeout_seconds = timeout_seconds
        self._connect_timeout = connect_timeout
        self._name = name

        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._retryable_exceptions = tuple(retryable_exceptions or [
            ConnectionError, TimeoutError, OSError,
        ])

        self._rate_semaphore: Optional[asyncio.Semaphore] = None
        self._rate_limit = rate_limit_per_second
        self._last_request_time: float = 0.0
        self._min_interval = 1.0 / rate_limit_per_second if rate_limit_per_second > 0 else 0

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._rate_semaphore is None:
            self._rate_semaphore = asyncio.Semaphore(5)
        return self._rate_semaphore

    def call(self, func: Callable, *args, **kwargs) -> DataSourceResult:
        """
        同步调用，带重试/超时/熔断

        Args:
            func: 要调用的同步函数
            *args, **kwargs: 函数参数

        Returns:
            DataSourceResult
        """
        if not self._circuit_breaker.allow_request():
            return DataSourceResult(
                success=False,
                error=f"熔断器打开，跳过请求 [{self._name}]",
                source=self._name,
            )

        start_time = time.monotonic()
        last_error = None

        for attempt in range(self._max_retries):
            try:
                self._rate_limit_sync()

                result_data = func(*args, **kwargs)

                latency_ms = (time.monotonic() - start_time) * 1000
                self._circuit_breaker.record_success()

                return DataSourceResult(
                    success=True,
                    data=result_data,
                    source=self._name,
                    latency_ms=latency_ms,
                )

            except self._retryable_exceptions as e:
                last_error = e
                latency_so_far = (time.monotonic() - start_time) * 1000

                if latency_so_far / 1000 > self._timeout_seconds:
                    self._circuit_breaker.record_failure()
                    return DataSourceResult(
                        success=False,
                        error=f"总超时 {self._timeout_seconds}s [{self._name}]: {e}",
                        source=self._name,
                        latency_ms=latency_so_far,
                    )

                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (self._retry_backoff_factor ** attempt)
                    logger.warning(
                        f"⚠️ [{self._name}] 请求失败(第{attempt + 1}次)，"
                        f"{delay:.1f}s后重试: {e}"
                    )
                    time.sleep(delay)
                else:
                    self._circuit_breaker.record_failure()

            except Exception as e:
                latency_ms = (time.monotonic() - start_time) * 1000
                self._circuit_breaker.record_failure()
                return DataSourceResult(
                    success=False,
                    error=f"不可重试异常 [{self._name}]: {e}",
                    source=self._name,
                    latency_ms=latency_ms,
                )

        latency_ms = (time.monotonic() - start_time) * 1000
        return DataSourceResult(
            success=False,
            error=f"重试{self._max_retries}次后仍失败 [{self._name}]: {last_error}",
            source=self._name,
            latency_ms=latency_ms,
        )

    async def acall(self, func: Callable, *args, **kwargs) -> DataSourceResult:
        """
        异步调用，带重试/超时/熔断

        Args:
            func: 要调用的异步函数
            *args, **kwargs: 函数参数

        Returns:
            DataSourceResult
        """
        if not self._circuit_breaker.allow_request():
            return DataSourceResult(
                success=False,
                error=f"熔断器打开，跳过请求 [{self._name}]",
                source=self._name,
            )

        start_time = time.monotonic()
        last_error = None

        for attempt in range(self._max_retries):
            try:
                await self._rate_limit_async()

                result_data = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self._timeout_seconds,
                )

                latency_ms = (time.monotonic() - start_time) * 1000
                self._circuit_breaker.record_success()

                return DataSourceResult(
                    success=True,
                    data=result_data,
                    source=self._name,
                    latency_ms=latency_ms,
                )

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"请求超时 {self._timeout_seconds}s")
                self._circuit_breaker.record_failure()
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (self._retry_backoff_factor ** attempt)
                    logger.warning(
                        f"⚠️ [{self._name}] 请求超时(第{attempt + 1}次)，"
                        f"{delay:.1f}s后重试"
                    )
                    await asyncio.sleep(delay)
                else:
                    latency_ms = (time.monotonic() - start_time) * 1000
                    return DataSourceResult(
                        success=False,
                        error=f"超时重试{self._max_retries}次后仍失败 [{self._name}]",
                        source=self._name,
                        latency_ms=latency_ms,
                    )

            except self._retryable_exceptions as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (self._retry_backoff_factor ** attempt)
                    logger.warning(
                        f"⚠️ [{self._name}] 请求失败(第{attempt + 1}次)，"
                        f"{delay:.1f}s后重试: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self._circuit_breaker.record_failure()

            except Exception as e:
                latency_ms = (time.monotonic() - start_time) * 1000
                self._circuit_breaker.record_failure()
                return DataSourceResult(
                    success=False,
                    error=f"不可重试异常 [{self._name}]: {e}",
                    source=self._name,
                    latency_ms=latency_ms,
                )

        latency_ms = (time.monotonic() - start_time) * 1000
        return DataSourceResult(
            success=False,
            error=f"重试{self._max_retries}次后仍失败 [{self._name}]: {last_error}",
            source=self._name,
            latency_ms=latency_ms,
        )

    def call_sync_with_timeout(self, func: Callable, *args, timeout: Optional[float] = None, **kwargs) -> DataSourceResult:
        """
        在线程中执行同步函数，带超时控制

        适用于 baostock.login()、yfinance.Ticker.history() 等可能阻塞的同步调用
        """
        effective_timeout = timeout or self._timeout_seconds

        if not self._circuit_breaker.allow_request():
            return DataSourceResult(
                success=False,
                error=f"熔断器打开，跳过请求 [{self._name}]",
                source=self._name,
            )

        start_time = time.monotonic()
        last_error = None

        for attempt in range(self._max_retries):
            try:
                self._rate_limit_sync()

                result_container = [None]
                error_container = [None]

                def _target():
                    try:
                        result_container[0] = func(*args, **kwargs)
                    except Exception as e:
                        error_container[0] = e

                thread = threading.Thread(target=_target, daemon=True)
                thread.start()
                thread.join(timeout=effective_timeout)

                if thread.is_alive():
                    last_error = TimeoutError(
                        f"同步调用超时 {effective_timeout}s [{self._name}]"
                    )
                    self._circuit_breaker.record_failure()
                    if attempt < self._max_retries - 1:
                        delay = self._retry_delay * (self._retry_backoff_factor ** attempt)
                        logger.warning(
                            f"⚠️ [{self._name}] 同步调用超时(第{attempt + 1}次)，"
                            f"{delay:.1f}s后重试"
                        )
                        time.sleep(delay)
                        continue
                    latency_ms = (time.monotonic() - start_time) * 1000
                    return DataSourceResult(
                        success=False,
                        error=f"同步调用超时重试{self._max_retries}次后仍失败 [{self._name}]",
                        source=self._name,
                        latency_ms=latency_ms,
                    )

                if error_container[0] is not None:
                    raise error_container[0]

                latency_ms = (time.monotonic() - start_time) * 1000
                self._circuit_breaker.record_success()

                return DataSourceResult(
                    success=True,
                    data=result_container[0],
                    source=self._name,
                    latency_ms=latency_ms,
                )

            except self._retryable_exceptions as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (self._retry_backoff_factor ** attempt)
                    logger.warning(
                        f"⚠️ [{self._name}] 请求失败(第{attempt + 1}次)，"
                        f"{delay:.1f}s后重试: {e}"
                    )
                    time.sleep(delay)
                else:
                    self._circuit_breaker.record_failure()

            except Exception as e:
                latency_ms = (time.monotonic() - start_time) * 1000
                self._circuit_breaker.record_failure()
                return DataSourceResult(
                    success=False,
                    error=f"不可重试异常 [{self._name}]: {e}",
                    source=self._name,
                    latency_ms=latency_ms,
                )

        latency_ms = (time.monotonic() - start_time) * 1000
        return DataSourceResult(
            success=False,
            error=f"重试{self._max_retries}次后仍失败 [{self._name}]: {last_error}",
            source=self._name,
            latency_ms=latency_ms,
        )

    def _rate_limit_sync(self):
        if self._min_interval > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

    async def _rate_limit_async(self):
        if self._min_interval > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()


import threading
