<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs/llm

## Purpose
LLM 集成文档，提供大语言模型接入的完整指导、测试验证和专项指南。

## Key Files

| File | Description |
|------|-------------|
| `README.md` | LLM 文档导航首页：文档结构、快速开始路径、已集成/计划中 LLM 提供商、技术架构、测试策略、常见问题类型、性能优化、贡献指南 |
| `LLM_INTEGRATION_GUIDE.md` | 大模型接入完整指导手册：系统架构、OpenAI 兼容适配器开发、前端集成、千帆接入案例 |
| `LLM_TESTING_VALIDATION_GUIDE.md` | LLM 测试验证指南：测试脚本模板、千帆专项测试、工具调用测试、Web 集成测试、验证清单 |
| `QIANFAN_INTEGRATION_GUIDE.md` | 百度千帆模型专项接入指南：千帆特点、详细步骤、特殊问题解决、性能优化、FAQ |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源文档
- 已集成 LLM：阿里百炼(DashScope)、DeepSeek、Google AI、OpenRouter、百度千帆
- 计划中：智谱AI、腾讯混元、月之暗面(Kimi)、MiniMax
- 核心设计原则：统一接口(OpenAI兼容)、插件化、配置化、可扩展

### Testing Requirements
- 文档无需运行测试
- LLM 测试策略：单元测试 → 集成测试 → 端到端测试 → 性能测试

### Common Patterns
- 适配器继承：`OpenAICompatibleBase`
- 新提供商接入流程：创建适配器 → 实现认证/格式转换 → 更新前端 → 编写测试 → 更新文档
- 配置方式：环境变量管理 API 密钥
- 阅读顺序：LLM_INTEGRATION_GUIDE → QIANFAN_INTEGRATION_GUIDE → LLM_TESTING_VALIDATION_GUIDE

## Dependencies

### Internal
- `tradingagents/llm_adapters/` - LLM 适配器实现
- `tradingagents/web/` - 前端模型选择

### External
- 各 LLM 提供商 API - 服务接入

<!-- MANUAL: Custom project notes can be added below -->
