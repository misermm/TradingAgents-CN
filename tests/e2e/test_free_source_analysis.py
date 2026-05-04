"""
Phase 1 端到端验证测试
验证免费数据源下分析流程的稳定性改进

测试内容:
1. ResilientHttpClient 重试/超时/熔断
2. SourceHealthTracker 健康跟踪
3. DeepSeek invoke() 修复后工具调用正常
4. 免费数据源数据获取
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta


class TestResilientHttpClient:
    """测试弹性HTTP客户端"""

    def test_call_success(self):
        from tradingagents.dataflows.providers.resilient_http_client import ResilientHttpClient

        client = ResilientHttpClient(name="test")
        result = client.call(lambda: "ok")
        assert result.success is True
        assert result.data == "ok"
        assert result.error is None

    def test_call_retry_on_failure(self):
        from tradingagents.dataflows.providers.resilient_http_client import ResilientHttpClient

        call_count = {"n": 0}

        def flaky_func():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("connection lost")
            return "ok"

        client = ResilientHttpClient(
            max_retries=3, retry_delay=0.01, name="test_retry"
        )
        result = client.call(flaky_func)
        assert result.success is True
        assert result.data == "ok"
        assert call_count["n"] == 3

    def test_call_all_retries_fail(self):
        from tradingagents.dataflows.providers.resilient_http_client import ResilientHttpClient

        def always_fail():
            raise ConnectionError("always down")

        client = ResilientHttpClient(
            max_retries=2, retry_delay=0.01, name="test_fail"
        )
        result = client.call(always_fail)
        assert result.success is False
        assert "重试2次后仍失败" in result.error

    def test_circuit_breaker_opens(self):
        from tradingagents.dataflows.providers.resilient_http_client import (
            ResilientHttpClient, CircuitBreaker,
        )

        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        client = ResilientHttpClient(
            max_retries=1, retry_delay=0.01,
            circuit_breaker=cb, name="test_cb"
        )

        def always_fail():
            raise ConnectionError("down")

        client.call(always_fail)
        client.call(always_fail)

        result = client.call(lambda: "should_be_blocked")
        assert result.success is False
        assert "熔断器打开" in result.error

    def test_circuit_breaker_half_open(self):
        from tradingagents.dataflows.providers.resilient_http_client import (
            CircuitBreaker,
        )

        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.06)
        assert cb.state == "half_open"
        assert cb.allow_request() is True

        cb.record_success()
        assert cb.state == "closed"

    def test_circuit_breaker_half_open_failure_reopens(self):
        from tradingagents.dataflows.providers.resilient_http_client import (
            CircuitBreaker,
        )

        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.06)
        assert cb.state == "half_open"

        cb.record_failure()
        assert cb.state == "open"

    def test_call_sync_with_timeout_success(self):
        from tradingagents.dataflows.providers.resilient_http_client import ResilientHttpClient

        client = ResilientHttpClient(name="test_timeout")
        result = client.call_sync_with_timeout(lambda: "fast", timeout=5.0)
        assert result.success is True
        assert result.data == "fast"

    def test_call_sync_with_timeout_exceeds(self):
        from tradingagents.dataflows.providers.resilient_http_client import ResilientHttpClient

        def slow_func():
            time.sleep(10)
            return "too_late"

        client = ResilientHttpClient(
            max_retries=1, retry_delay=0.01, name="test_slow"
        )
        result = client.call_sync_with_timeout(slow_func, timeout=1.0)
        assert result.success is False
        assert "超时" in result.error

    def test_non_retryable_exception(self):
        from tradingagents.dataflows.providers.resilient_http_client import ResilientHttpClient

        def value_error_func():
            raise ValueError("bad input")

        client = ResilientHttpClient(name="test_value_error")
        result = client.call(value_error_func)
        assert result.success is False
        assert "不可重试异常" in result.error


class TestSourceHealthTracker:
    """测试数据源健康跟踪器"""

    def test_initial_state_is_closed(self):
        from tradingagents.dataflows.data_source_manager import SourceHealthTracker

        tracker = SourceHealthTracker()
        assert tracker.is_available("akshare") is True

    def test_record_failure_trips_circuit(self):
        from tradingagents.dataflows.data_source_manager import SourceHealthTracker

        tracker = SourceHealthTracker()
        tracker.record_failure("akshare")
        tracker.record_failure("akshare")
        tracker.record_failure("akshare")

        assert tracker.is_available("akshare") is False

    def test_record_success_resets_failures(self):
        from tradingagents.dataflows.data_source_manager import SourceHealthTracker

        tracker = SourceHealthTracker()
        tracker.record_failure("akshare")
        tracker.record_failure("akshare")
        tracker.record_success("akshare")

        assert tracker.is_available("akshare") is True

        tracker.record_failure("akshare")
        assert tracker.is_available("akshare") is True

    def test_cooldown_then_half_open(self):
        from tradingagents.dataflows.data_source_manager import SourceHealthTracker

        tracker = SourceHealthTracker()
        tracker.COOLDOWN_SECONDS = 0.2

        tracker.record_failure("akshare")
        tracker.record_failure("akshare")
        tracker.record_failure("akshare")

        assert tracker.is_available("akshare") is False

        time.sleep(0.3)
        assert tracker.is_available("akshare") is True

    def test_get_available_sources_filters(self):
        from tradingagents.dataflows.data_source_manager import SourceHealthTracker

        tracker = SourceHealthTracker()
        tracker.record_failure("akshare")
        tracker.record_failure("akshare")
        tracker.record_failure("akshare")

        sources = ["akshare", "baostock", "tushare"]
        available = tracker.get_available_sources(sources)
        assert "akshare" not in available
        assert "baostock" in available
        assert "tushare" in available

    def test_get_status(self):
        from tradingagents.dataflows.data_source_manager import SourceHealthTracker

        tracker = SourceHealthTracker()
        tracker.record_failure("akshare")
        tracker.record_success("baostock")

        status = tracker.get_status()
        assert "akshare" in status
        assert status["akshare"]["consecutive_failures"] == 1
        assert "baostock" in status
        assert status["baostock"]["total_calls"] == 1


class TestDataSourceResult:
    """测试数据源结果对象"""

    def test_success_result(self):
        from tradingagents.dataflows.providers.resilient_http_client import DataSourceResult

        result = DataSourceResult(
            success=True, data="test_data", source="akshare", latency_ms=100.0
        )
        assert result.success is True
        assert result.data == "test_data"
        assert result.from_cache is False

    def test_failure_result(self):
        from tradingagents.dataflows.providers.resilient_http_client import DataSourceResult

        result = DataSourceResult(
            success=False, error="timeout", source="baostock"
        )
        assert result.success is False
        assert result.data is None
        assert result.error == "timeout"


class TestDeepSeekInvokeFix:
    """测试DeepSeek invoke()修复"""

    def test_no_invoke_override(self):
        try:
            from tradingagents.llm_adapters.openai_compatible_base import ChatDeepSeekOpenAI
            from langchain_openai import ChatOpenAI
            assert ChatDeepSeekOpenAI.invoke is ChatOpenAI.invoke
        except ImportError:
            pytest.skip("LLM适配器依赖未安装")

    def test_estimate_tokens_methods_exist(self):
        try:
            from tradingagents.llm_adapters.openai_compatible_base import ChatDeepSeekOpenAI
            assert hasattr(ChatDeepSeekOpenAI, '_estimate_input_tokens')
            assert hasattr(ChatDeepSeekOpenAI, '_estimate_output_tokens')
        except ImportError:
            pytest.skip("LLM适配器依赖未安装")


class TestFreeDataSourceBasic:
    """测试免费数据源基本可用性（需要网络）"""

    @pytest.mark.integration
    def test_akshare_provider_import(self):
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider
        provider = AKShareProvider()
        assert provider.connected is True

    @pytest.mark.integration
    def test_baostock_provider_import(self):
        from tradingagents.dataflows.providers.china.baostock import BaoStockProvider
        provider = BaoStockProvider()
        assert provider.connected is True

    @pytest.mark.integration
    def test_yfinance_utils_import(self):
        from tradingagents.dataflows.providers.us.yfinance import YFinanceUtils
        utils = YFinanceUtils()
        assert utils is not None

    @pytest.mark.integration
    def test_data_source_manager_health_tracker(self):
        from tradingagents.dataflows.data_source_manager import DataSourceManager
        manager = DataSourceManager()
        assert hasattr(manager, '_health_tracker')
        assert manager._health_tracker is not None

    @pytest.mark.integration
    def test_akshare_get_stock_data(self):
        from tradingagents.dataflows.providers.china.akshare import get_akshare_provider
        import asyncio

        provider = get_akshare_provider()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        loop = asyncio.new_event_loop()
        try:
            data = loop.run_until_complete(
                provider.get_historical_data("600519", start_date, end_date)
            )
            assert data is not None
            assert not data.empty
        finally:
            loop.close()

    @pytest.mark.integration
    def test_baostock_get_stock_data(self):
        from tradingagents.dataflows.providers.china.baostock import get_baostock_provider
        import asyncio

        provider = get_baostock_provider()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        loop = asyncio.new_event_loop()
        try:
            data = loop.run_until_complete(
                provider.get_historical_data("000001", start_date, end_date)
            )
            assert data is not None
            assert not data.empty
        finally:
            loop.close()

    @pytest.mark.integration
    def test_yfinance_get_stock_data(self):
        from tradingagents.dataflows.providers.us.yfinance import YFinanceUtils

        utils = YFinanceUtils()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        data = utils.get_stock_data("AAPL", start_date, end_date)
        assert data is not None
        assert not data.empty
