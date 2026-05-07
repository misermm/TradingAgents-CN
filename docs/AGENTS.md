<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs

## Purpose
项目文档与学习资源 (Apache 2.0)，包含安装指南、LLM 集成文档、API 安全说明、学习材料和更新日志。

## Key Files

| File | Description |
|------|-------------|
| `README.md` | 文档导航首页 |
| `STRUCTURE.md` | 项目结构说明 |
| `QUICK_START.md` | 快速开始指南 |
| `BUILD_GUIDE.md` | 构建指南 |
| `database_setup.md` | 数据库部署指南 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `overview/` | 项目概览：安装、快速开始、开源声明 |
| `llm/` | LLM 集成文档：模型目录、供应商选择、定价指南 |
| `examples/` | 使用示例：基础和高级用法 |
| `learning/` | 学习资源：AI 基础、资源推荐、FAQ |
| `paper/` | 论文：TradingAgents 原始论文及中文版 |
| `releases/` | 更新日志 |
| `security/` | 安全文档：API Key 安全、认证系统 |
| `faq/` | 常见问题 |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源模块
- 文档使用 Markdown 格式
- LLM 相关文档最为详细（10+ 文件）

### Testing Requirements
- 文档无需运行测试
- 检查链接有效性

### Common Patterns
- 文档文件命名：大写加下划线 (如 MODEL_CATALOG_MANAGEMENT.md)
- 指南类文档：`*_GUIDE.md`
- 快速入门：`*_QUICKSTART.md`

## Dependencies

### Internal
- `tradingagents/` - 文档描述的核心库
- `app/` - 部署和配置文档涉及后端

### External
- 无外部依赖

<!-- MANUAL: Custom project notes can be added below -->
