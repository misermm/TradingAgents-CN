"""
Configuration package exports.

Keep this module lightweight. Legacy ``config_manager`` initialization can open
sync MongoDB connections as an import side effect, so these exports are loaded
on demand instead of at package import time.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "config_manager",
    "token_tracker",
    "ModelConfig",
    "PricingConfig",
    "UsageRecord",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        module = import_module("tradingagents.config.config_manager")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
