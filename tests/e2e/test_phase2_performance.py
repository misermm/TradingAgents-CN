"""
Phase 2 性能优化测试
验证统一缓存键/TTL、数据标准化、缓存启用
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestCacheConfig:
    """测试统一缓存配置"""

    def test_detect_market_cn(self):
        from tradingagents.dataflows.cache.cache_config import detect_market
        assert detect_market("600519") == "cn"
        assert detect_market("000001") == "cn"
        assert detect_market("300750") == "cn"

    def test_detect_market_hk(self):
        from tradingagents.dataflows.cache.cache_config import detect_market
        assert detect_market("00700") == "hk"
        assert detect_market("09988") == "hk"

    def test_detect_market_us(self):
        from tradingagents.dataflows.cache.cache_config import detect_market
        assert detect_market("AAPL") == "us"
        assert detect_market("GOOGL") == "us"
        assert detect_market("TSLA") == "us"

    def test_detect_market_edge(self):
        from tradingagents.dataflows.cache.cache_config import detect_market
        assert detect_market("") == "us"
        assert detect_market("1234") == "us"

    def test_generate_cache_key_format(self):
        from tradingagents.dataflows.cache.cache_config import generate_cache_key
        key = generate_cache_key("cn", "stock_data", "600519", start_date="2024-01-01", end_date="2024-12-31")
        assert key.startswith("cn:stock_data:600519:")
        parts = key.split(":")
        assert len(parts) == 4
        assert len(parts[3]) == 12

    def test_generate_cache_key_deterministic(self):
        from tradingagents.dataflows.cache.cache_config import generate_cache_key
        key1 = generate_cache_key("cn", "stock_data", "600519", start_date="2024-01-01")
        key2 = generate_cache_key("cn", "stock_data", "600519", start_date="2024-01-01")
        assert key1 == key2

    def test_generate_cache_key_different_params(self):
        from tradingagents.dataflows.cache.cache_config import generate_cache_key
        key1 = generate_cache_key("cn", "stock_data", "600519", start_date="2024-01-01")
        key2 = generate_cache_key("cn", "stock_data", "600519", start_date="2024-06-01")
        assert key1 != key2

    def test_generate_cache_key_different_market(self):
        from tradingagents.dataflows.cache.cache_config import generate_cache_key
        key_cn = generate_cache_key("cn", "stock_data", "600519")
        key_us = generate_cache_key("us", "stock_data", "600519")
        assert key_cn != key_us

    def test_get_ttl_seconds_cn_stock(self):
        from tradingagents.dataflows.cache.cache_config import get_ttl_seconds
        ttl = get_ttl_seconds("cn", "stock_data")
        assert ttl == 14400  # 4小时

    def test_get_ttl_seconds_us_fundamentals(self):
        from tradingagents.dataflows.cache.cache_config import get_ttl_seconds
        ttl = get_ttl_seconds("us", "fundamentals")
        assert ttl == 86400  # 24小时

    def test_get_ttl_seconds_cn_news(self):
        from tradingagents.dataflows.cache.cache_config import get_ttl_seconds
        ttl = get_ttl_seconds("cn", "news")
        assert ttl == 7200  # 2小时

    def test_get_ttl_seconds_default(self):
        from tradingagents.dataflows.cache.cache_config import get_ttl_seconds
        ttl = get_ttl_seconds("cn", "unknown_type")
        assert ttl == 7200  # 默认2小时

    def test_legacy_compatible_key(self):
        from tradingagents.dataflows.cache.cache_config import generate_legacy_compatible_key
        key = generate_legacy_compatible_key("stock_data", "600519")
        assert key.startswith("600519_stock_data_")
        assert len(key.split("_")[-1]) == 12

    def test_db_compatible_key(self):
        from tradingagents.dataflows.cache.cache_config import generate_db_compatible_key
        key = generate_db_compatible_key("stock_data", "AAPL")
        assert key.startswith("stock_data:AAPL:")
        assert len(key.split(":")[-1]) == 16


class TestUnifiedDataFrame:
    """测试统一DataFrame标准化"""

    def _make_sample_df(self, market="cn"):
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        data = {
            "日期": dates,
            "开盘": [10.0, 11.0, 12.0, 13.0, 14.0],
            "最高": [10.5, 11.5, 12.5, 13.5, 14.5],
            "最低": [9.5, 10.5, 11.5, 12.5, 13.5],
            "收盘": [10.2, 11.2, 12.2, 13.2, 14.2],
            "成交量": [1000, 1100, 1200, 1300, 1400],
            "成交额": [10000, 11000, 12000, 13000, 14000],
        }
        return pd.DataFrame(data)

    def test_standardize_columns_chinese(self):
        from tradingagents.dataflows.unified_dataframe import standardize_columns
        df = self._make_sample_df()
        result = standardize_columns(df)
        assert "date" in result.columns
        assert "open" in result.columns
        assert "close" in result.columns
        assert "vol" in result.columns
        assert "日期" not in result.columns
        assert "开盘" not in result.columns

    def test_standardize_columns_english(self):
        from tradingagents.dataflows.unified_dataframe import standardize_columns
        df = pd.DataFrame({
            "Date": ["2024-01-01"],
            "Open": [100.0],
            "High": [105.0],
            "Low": [95.0],
            "Close": [102.0],
            "Volume": [5000],
        })
        result = standardize_columns(df)
        assert "date" in result.columns
        assert "open" in result.columns
        assert "vol" in result.columns

    def test_standardize_types(self):
        from tradingagents.dataflows.unified_dataframe import standardize_types
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02"],
            "close": ["10.5", "11.5"],
        })
        result = standardize_types(df)
        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert pd.api.types.is_float_dtype(result["close"])

    def test_compute_derived_pct_change(self):
        from tradingagents.dataflows.unified_dataframe import compute_derived_columns
        df = pd.DataFrame({
            "close": [10.0, 11.0, 12.1],
        })
        result = compute_derived_columns(df)
        assert "pct_change" in result.columns
        assert np.isclose(result["pct_change"].iloc[1], 10.0)
        assert np.isclose(result["pct_change"].iloc[2], 10.0, atol=0.1)

    def test_validate_empty_dataframe(self):
        from tradingagents.dataflows.unified_dataframe import validate_dataframe
        is_valid, issues = validate_dataframe(None)
        assert is_valid is False
        is_valid, issues = validate_dataframe(pd.DataFrame())
        assert is_valid is False

    def test_validate_good_dataframe(self):
        from tradingagents.dataflows.unified_dataframe import validate_dataframe
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "close": [100.0],
        })
        is_valid, issues = validate_dataframe(df)
        assert is_valid is True
        assert len(issues) == 0

    def test_full_standardize_pipeline(self):
        from tradingagents.dataflows.unified_dataframe import standardize_dataframe
        df = self._make_sample_df()
        result = standardize_dataframe(df, market="cn")
        assert "date" in result.columns
        assert "open" in result.columns
        assert "close" in result.columns
        assert "pct_change" in result.columns
        assert result["close"].dtype == np.float64

    def test_standardize_empty_df(self):
        from tradingagents.dataflows.unified_dataframe import standardize_dataframe
        result = standardize_dataframe(None)
        assert result.empty
        result = standardize_dataframe(pd.DataFrame())
        assert result.empty

    def test_fill_missing_values(self):
        from tradingagents.dataflows.unified_dataframe import fill_missing_values
        df = pd.DataFrame({
            "close": [10.0, np.nan, 12.0],
            "vol": [100, np.nan, 300],
        })
        result = fill_missing_values(df)
        assert result["close"].iloc[1] == 10.0
        assert result["vol"].iloc[1] == 100.0

    def test_standardize_units_cn_market_cap(self):
        from tradingagents.dataflows.unified_dataframe import standardize_units
        df = pd.DataFrame({
            "market_cap": [5000.0, 6000.0],
            "circulating_market_cap": [3000.0, 4000.0],
        })
        result = standardize_units(df, market="cn")
        assert result["market_cap"].max() > 0
