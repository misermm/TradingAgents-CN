#!/usr/bin/env python3
"""
TradingAgents-CN 核心模块

这是一个基于多智能体的股票分析系统，支持A股、港股和美股的综合分析。
"""

__version__ = "1.0.0-preview"
__author__ = "TradingAgents-CN Team"
__description__ = "Multi-agent stock analysis system for Chinese markets"

# Avoid eager side-effect imports here. Legacy config initialization may open
# sync MongoDB connections during import, which is undesirable for lightweight
# package imports and test collection.

__all__ = [
    "__version__",
    "__author__", 
    "__description__"
]
