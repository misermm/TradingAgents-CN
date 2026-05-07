<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# llm_clients

## Purpose
LLM 客户端封装模块，提供统一的 LLM 调用接口。支持 OpenAI、Google、Anthropic 等供应商，通过工厂模式创建客户端，模型目录管理可用模型。

## Key Files

| File | Description |
|------|-------------|
| `factory.py` | create_llm_client() 工厂函数，根据供应商创建 LLM 实例 |
| `model_catalog.py` | ModelCatalog 类，管理可用模型目录、定价和能力 |
| `openai_client.py` | OpenAI 兼容客户端 (支持 DeepSeek 等兼容 API) |
| `google_client.py` | Google Generative AI 客户端 |
| `anthropic_client.py` | Anthropic Claude 客户端 |
| `base_client.py` | LLM 客户端基类，定义统一接口 |
| `provider_keys.py` | 供应商 API Key 管理 |
| `validators.py` | 模型和参数验证器 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 创建客户端：`from tradingagents.llm_clients.factory import create_llm_client`
- 模型查询：`ModelCatalog` 类管理模型信息和能力
- 供应商配置：`provider_keys.py` 管理 API Key 映射
- 新增供应商需实现 BaseClient 接口并在 factory 注册

### Testing Requirements
- LLM 客户端测试：`python -m pytest tests/ -k "llm" -v`
- 模型目录测试：`python -m pytest tests/ -k "model_catalog" -v`

### Common Patterns
- 工厂模式：create_llm_client(provider, model) → 返回对应客户端实例
- 模型选择：ModelCatalog 查询可用模型 → 根据能力筛选 → 创建客户端

## Dependencies

### Internal
- `tradingagents/config/` - 供应商和 API Key 配置

### External
- OpenAI Python SDK - OpenAI API
- Google Generative AI SDK - Gemini API
- Anthropic SDK - Claude API

<!-- MANUAL: Custom project notes can be added below -->
