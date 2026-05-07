<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# llm_adapters

## Purpose
LLM 适配器模块，为不同 LLM 供应商提供 OpenAI 兼容的适配层。处理工具调用格式差异、消息格式转换和特殊行为兼容。

## Key Files

| File | Description |
|------|-------------|
| `dashscope_adapter.py` | 阿里百炼 DashScope 适配器，处理工具调用格式 |
| `dashscope_openai_adapter.py` | DashScope OpenAI 兼容模式适配器 |
| `deepseek_adapter.py` | DeepSeek 适配器，处理推理模型特殊行为 |
| `google_openai_adapter.py` | Google Gemini OpenAI 兼容适配器 |
| `openai_compatible_base.py` | OpenAI 兼容基类，提供通用适配逻辑 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 所有适配器继承 `openai_compatible_base.py` 基类
- 适配器主要处理：工具调用格式转换、消息格式兼容、特殊模型行为
- 新增供应商适配器需继承 OpenAICompatibleBase

### Testing Requirements
- 适配器测试：`python -m pytest tests/ -k "adapter" -v`
- DashScope 测试：`python -m pytest tests/ -k "dashscope" -v`

### Common Patterns
- 适配器模式：继承基类 → 重写格式转换方法 → 注册到工厂

## Dependencies

### Internal
- `tradingagents/llm_clients/` - 被客户端模块调用

### External
- OpenAI Python SDK - 兼容接口基础

<!-- MANUAL: Custom project notes can be added below -->
