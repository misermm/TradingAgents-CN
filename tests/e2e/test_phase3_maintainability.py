"""
Phase 3 可维护性测试
LLM适配器统一、核心模块mock单元测试
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import pandas as pd
import numpy as np


class TestLLMAdapterUnification:
    """测试LLM适配器统一"""

    def test_deepseek_alias(self):
        try:
            from tradingagents.llm_adapters import ChatDeepSeek, ChatDeepSeekOpenAI
            assert ChatDeepSeek is ChatDeepSeekOpenAI
        except ImportError:
            pytest.skip("LLM适配器依赖未安装")

    def test_dashscope_alias(self):
        try:
            from tradingagents.llm_adapters import ChatDashScopeOpenAI, ChatDashScopeOpenAIUnified
            assert ChatDashScopeOpenAI is ChatDashScopeOpenAIUnified
        except ImportError:
            pytest.skip("LLM适配器依赖未安装")

    def test_deepseek_adapter_backward_compat(self):
        try:
            from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek
            from tradingagents.llm_adapters.openai_compatible_base import ChatDeepSeekOpenAI
            assert ChatDeepSeek is ChatDeepSeekOpenAI
        except ImportError:
            pytest.skip("LLM适配器依赖未安装")

    def test_dashscope_adapter_backward_compat(self):
        try:
            from tradingagents.llm_adapters.dashscope_openai_adapter import ChatDashScopeOpenAI
            from tradingagents.llm_adapters.openai_compatible_base import ChatDashScopeOpenAIUnified
            assert ChatDashScopeOpenAI is ChatDashScopeOpenAIUnified
        except ImportError:
            pytest.skip("LLM适配器依赖未安装")

    def test_deepseek_has_token_estimation(self):
        try:
            from tradingagents.llm_adapters.openai_compatible_base import ChatDeepSeekOpenAI
            assert hasattr(ChatDeepSeekOpenAI, '_estimate_input_tokens')
            assert hasattr(ChatDeepSeekOpenAI, '_estimate_output_tokens')
        except ImportError:
            pytest.skip("LLM适配器依赖未安装")

    def test_all_exports_available(self):
        try:
            from tradingagents.llm_adapters import (
                OpenAICompatibleBase,
                ChatDeepSeekOpenAI,
                ChatDashScopeOpenAIUnified,
                ChatQianfanOpenAI,
                ChatZhipuOpenAI,
                ChatCustomOpenAI,
            )
            assert OpenAICompatibleBase is not None
            assert ChatDeepSeekOpenAI is not None
            assert ChatDashScopeOpenAIUnified is not None
        except ImportError:
            pytest.skip("LLM适配器依赖未安装")


class TestProviderKeys:
    """测试Provider密钥管理"""

    def test_provider_keys_module_import(self):
        from tradingagents.llm_clients import provider_keys
        assert provider_keys is not None

    def test_provider_keys_has_aliases(self):
        from tradingagents.llm_clients.provider_keys import _ALIASES
        assert isinstance(_ALIASES, dict)

    def test_provider_keys_has_deepseek_alias(self):
        from tradingagents.llm_clients.provider_keys import _ALIASES
        assert "deepseek" in _ALIASES or any("deepseek" in str(v) for v in _ALIASES.values())


class TestCacheConfigIntegration:
    """测试缓存配置与DataSourceManager集成"""

    def test_cache_text_methods_exist(self):
        from tradingagents.dataflows.data_source_manager import DataSourceManager
        assert hasattr(DataSourceManager, '_get_cached_text')
        assert hasattr(DataSourceManager, '_save_cached_text')

    def test_health_tracker_on_manager(self):
        from tradingagents.dataflows.data_source_manager import DataSourceManager
        manager = DataSourceManager()
        assert hasattr(manager, '_health_tracker')
        status = manager._health_tracker.get_status()
        assert isinstance(status, dict)


class TestUnifiedDataFrameIntegration:
    """测试数据标准化与DataSourceManager集成"""

    def test_standardize_delegates(self):
        from tradingagents.dataflows.data_source_manager import DataSourceManager
        manager = DataSourceManager()
        df = pd.DataFrame({
            "日期": ["2024-01-01", "2024-01-02"],
            "开盘": [10.0, 11.0],
            "收盘": [10.5, 11.5],
            "成交量": [1000, 1100],
        })
        result = manager._standardize_dataframe(df)
        assert "date" in result.columns
        assert "open" in result.columns
        assert "close" in result.columns
        assert "vol" in result.columns


class TestResilientHttpClientIntegration:
    """测试弹性HTTP客户端集成"""

    def test_baostock_has_http_client(self):
        from tradingagents.dataflows.providers.china.baostock import BaoStockProvider
        provider = BaoStockProvider()
        assert hasattr(provider, '_http_client')

    def test_yfinance_has_http_client(self):
        from tradingagents.dataflows.providers.us.yfinance import _yfinance_client
        assert _yfinance_client is not None
        assert _yfinance_client._name == "yfinance"


class TestSourceHealthTrackerIntegration:
    """测试健康跟踪器与降级链路集成"""

    def test_fallback_skips_circuited_sources(self):
        from tradingagents.dataflows.data_source_manager import DataSourceManager, SourceHealthTracker
        manager = DataSourceManager()

        manager._health_tracker.record_failure("akshare")
        manager._health_tracker.record_failure("akshare")
        manager._health_tracker.record_failure("akshare")

        assert not manager._health_tracker.is_available("akshare")
        assert manager._health_tracker.is_available("baostock")

    def test_health_tracker_status_report(self):
        from tradingagents.dataflows.data_source_manager import DataSourceManager
        manager = DataSourceManager()
        manager._health_tracker.record_success("akshare")
        manager._health_tracker.record_failure("baostock")

        status = manager._health_tracker.get_status()
        assert "akshare" in status
        assert status["akshare"]["consecutive_failures"] == 0
        assert "baostock" in status
        assert status["baostock"]["consecutive_failures"] == 1
