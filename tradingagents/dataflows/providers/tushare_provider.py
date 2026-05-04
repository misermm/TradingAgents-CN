"""Backward-compatible alias to the unified Tushare provider module."""

import sys

from tradingagents.dataflows.providers.china import tushare as _impl

sys.modules[__name__] = _impl
