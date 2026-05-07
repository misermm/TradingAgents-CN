<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# utils

## Purpose
智能体辅助工具模块，提供状态管理、注册表、内存管理、ChromaDB 配置和工具处理等基础功能。

## Key Files

| File | Description |
|------|-------------|
| `analyst_registry.py` | AnalystRegistry 类，注册和管理所有分析师和主控 |
| `agent_utils.py` | 智能体工具函数，支持状态和通信 |
| `agent_states.py` | 智能体状态管理 |
| `memory.py` | 智能体内存管理 |
| `chromadb_config.py` | ChromaDB 向量数据库配置 |
| `google_tool_handler.py` | Google LLM 工具调用处理器 |
| `instrument_utils.py` | 金融工具工具函数 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 注册表：新增智能体需在 `analyst_registry.py` 注册
- 内存：`memory.py` 管理智能体的对话历史
- ChromaDB：`chromadb_config.py` 配置向量存储

### Testing Requirements
- 工具测试：`python -m pytest tests/ -k "agent_utils" -v`

### Common Patterns
- 注册模式：AnalystRegistry.register(name, class) → 按名称获取
- 内存模式：Memory 类 → 存储对话 → 检索相关上下文

## Dependencies

### Internal
- `tradingagents/llm_clients/` - LLM 调用

### External
- ChromaDB - 向量存储
- LangChain - 内存管理

<!-- MANUAL: Custom project notes can be added below -->
