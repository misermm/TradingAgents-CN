<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs/learning

## Purpose
TradingAgents-CN 学习中心，提供从 AI 基础到实战应用的系统化教学路径，涵盖 LLM 原理、提示词工程、模型选择、分析原理、风险认知和实战教程。

## Key Files

| File | Description |
|------|-------------|
| `README.md` | 学习中心导航首页：目录结构、内容规范、学习路径（初学者/进阶/高级）、贡献指南、已完成文档清单 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `01-ai-basics/` | AI 基础知识：LLM 概念、Transformer 架构、训练过程、能力边界 |
| `02-prompt-engineering/` | 提示词工程：基础概念、常用模式、最佳实践、Few-shot、思维链、优化技巧 |
| `03-model-selection/` | 模型选择指南：主流模型对比、OpenAI 系列、国产模型、成本分析 |
| `04-analysis-principles/` | AI 分析股票原理：多智能体系统、辩论机制、分析流程、数据处理、技术/基本面/情感分析 |
| `05-risks-limitations/` | 风险与局限性：幻觉问题、数据时效性、市场波动性、风险警示、正确使用方式 |
| `06-resources/` | 源项目与论文：TradingAgents 介绍、论文中文/英文版、相关资源 |
| `07-tutorials/` | 实战教程：快速开始、单股/批量分析、筛选、模拟交易、自定义提示词、LLM 配置、高级功能 |
| `08-faq/` | 常见问题：安装、配置、数据同步、分析问题、LLM 问题、故障排除 |

## For AI Agents

### Working In This Directory
- 已完成 8 篇核心文档，覆盖入门到进阶主要内容
- 文档格式规范：标题+元信息（分类/难度/阅读时间/更新日期）→ 引言 → 正文 → 示例代码 → 总结 → 延伸阅读
- 学习路径设计：初学者（AI基础→快速开始→风险警示）、进阶（提示词→多智能体→自定义）、高级（Transformer→模型对比→论文研读）
- 核心概念文档：`what-is-llm.md`（LLM 定义、Transformer、预训练微调、上下文学习、涌现能力）
- 论文解读：`paper-guide.md`（多智能体架构、辩论机制、实验验证、创新点、未来方向）
- FAQ：`general-questions.md`（23 个问答，覆盖功能、模型选择、使用技巧、问题排查、费用）

### Testing Requirements
- 文档无需运行测试
- 检查内部链接有效性

### Common Patterns
- 文档元信息格式：`**分类**: xxx | **难度**: 入门/进阶/高级 | **阅读时间**: X分钟 | **更新日期**: YYYY-MM-DD`
- 交叉引用：文档间通过相对路径链接
- 模型推荐策略：DeepSeek V3.1（日常/性价比）→ Qwen3-Plus（长文本/中文）→ Qwen-Max（深度裁决）
- 数据源降级链：A股 MongoDB→Tushare→AKShare→BaoStock；港股 AKShare→yfinance→Finnhub

## Dependencies

### Internal
- `docs/paper/` - 论文原文与中文版
- `docs/examples/` - 实战示例代码
- `tradingagents/` - 学习内容描述的核心库

### External
- 无外部依赖（纯文档模块）

<!-- MANUAL: Custom project notes can be added below -->
