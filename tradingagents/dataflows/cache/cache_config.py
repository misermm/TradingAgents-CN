"""
统一缓存配置
提供统一的缓存键生成和TTL策略，替代各缓存系统各自独立的实现
"""

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CacheTTLConfig:
    """缓存TTL配置（秒）"""
    cn_realtime_quotes: int = 300
    us_realtime_quotes: int = 300
    hk_realtime_quotes: int = 300
    cn_stock_data: int = 14400
    us_stock_data: int = 14400
    hk_stock_data: int = 14400
    cn_fundamentals: int = 43200
    us_fundamentals: int = 86400
    hk_fundamentals: int = 86400
    cn_news: int = 7200
    us_news: int = 14400
    hk_news: int = 14400
    cn_financial: int = 86400
    us_financial: int = 172800
    hk_financial: int = 172800
    cn_stock_info: int = 604800
    us_stock_info: int = 604800
    hk_stock_info: int = 604800


DEFAULT_TTL = CacheTTLConfig()


def detect_market(symbol: str) -> str:
    """
    根据股票代码判断市场

    规则:
    - 6位纯数字 → cn (A股)
    - 5位数字开头 → hk (港股，如00700)
    - 纯字母 → us (美股，如AAPL)
    - 其他 → us (默认)
    """
    if not symbol:
        return "us"
    clean = symbol.strip().lstrip("0")
    if len(symbol) == 6 and symbol.isdigit():
        return "cn"
    if len(symbol) == 5 and symbol.isdigit():
        return "hk"
    if symbol.isalpha():
        return "us"
    return "us"


def generate_cache_key(
    market: str,
    data_type: str,
    symbol: str,
    **params,
) -> str:
    """
    统一缓存键生成

    格式: {market}:{data_type}:{symbol}:{params_hash}

    Args:
        market: 市场 (cn/us/hk)
        data_type: 数据类型 (stock_data/fundamentals/news/financial/stock_info/realtime_quotes)
        symbol: 股票代码
        **params: 额外参数 (start_date, end_date, data_source, period 等)

    Returns:
        统一格式的缓存键
    """
    params_str = ""
    for key in sorted(params.keys()):
        val = params[key]
        if val is not None:
            params_str += f"_{key}_{val}"

    raw = f"{market}_{data_type}_{symbol}{params_str}"
    params_hash = hashlib.md5(raw.encode()).hexdigest()[:12]

    return f"{market}:{data_type}:{symbol}:{params_hash}"


def get_ttl_seconds(
    market: str,
    data_type: str,
    ttl_config: Optional[CacheTTLConfig] = None,
) -> int:
    """
    获取统一TTL（秒）

    Args:
        market: 市场 (cn/us/hk)
        data_type: 数据类型
        ttl_config: TTL配置，默认使用DEFAULT_TTL

    Returns:
        TTL秒数
    """
    config = ttl_config or DEFAULT_TTL
    key = f"{market}_{data_type}"
    return getattr(config, key, 7200)


def generate_legacy_compatible_key(
    data_type: str,
    symbol: str,
    **kwargs,
) -> str:
    """
    生成与旧版file_cache兼容的缓存键
    用于迁移期间的兼容读取

    格式: {symbol}_{data_type}_{md5[:12]}
    """
    params_str = f"{data_type}_{symbol}"
    for key, value in sorted(kwargs.items()):
        params_str += f"_{key}_{value}"
    cache_key = hashlib.md5(params_str.encode()).hexdigest()[:12]
    return f"{symbol}_{data_type}_{cache_key}"


def generate_db_compatible_key(
    data_type: str,
    symbol: str,
    **kwargs,
) -> str:
    """
    生成与旧版db_cache兼容的缓存键
    用于迁移期间的兼容读取

    格式: {data_type}:{symbol}:{md5[:16]}
    """
    params_str = f"{data_type}_{symbol}"
    for key, value in sorted(kwargs.items()):
        params_str += f"_{key}_{value}"
    cache_key = hashlib.md5(params_str.encode()).hexdigest()[:16]
    return f"{data_type}:{symbol}:{cache_key}"
