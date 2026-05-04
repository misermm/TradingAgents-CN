"""Compatibility exports backed by ``langchain_core.messages``."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

__all__ = [
    "AIMessage",
    "BaseMessage",
    "HumanMessage",
    "SystemMessage",
    "ToolMessage",
]
