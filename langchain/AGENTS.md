<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# langchain

## Purpose
LangChain 扩展模块，提供自定义的 LangChain Schema 和工具定义，被核心库的智能体和工具模块引用。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化 |
| `schema.py` | 自定义 LangChain Schema 定义，扩展工具和消息结构 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 此模块定义了核心库使用的 LangChain 扩展类型
- 修改 Schema 可能影响所有智能体的工具调用

### Testing Requirements
- 通过核心库的测试间接验证

### Common Patterns
- Schema 扩展模式：继承 LangChain 基类 → 添加自定义字段

## Dependencies

### Internal
- `tradingagents/` - 核心库引用此模块

### External
- LangChain - AI 编排框架

<!-- MANUAL: Custom project notes can be added below -->
