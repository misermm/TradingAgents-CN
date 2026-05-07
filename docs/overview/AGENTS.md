<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs/overview

## Purpose
项目概览文档，提供安装指南、项目介绍和快速入门指导。

## Key Files

| File | Description |
|------|-------------|
| `installation.md` | 详细安装指南：系统要求、多平台 Python 安装、虚拟环境创建、依赖安装、API 密钥配置、安装验证脚本、常见问题排查、Docker 安装、卸载指南 |
| `project-overview.md` | 项目概述：TradingAgents-CN 中文增强版介绍、多智能体协作机制、核心特性（多维度分析/智能体协作/灵活架构/数据集成/Web界面）、应用场景、技术优势、发展路线图 |
| `quick-start.md` | 快速开始指南：v0.1.7 新特性（Docker 部署/报告导出/DeepSeek V3）、前置要求、快速安装步骤、Web/CLI/Python API 三种运行方式、配置选项、成本控制建议 |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源文档
- 安装指南覆盖 Windows/macOS/Linux 三平台
- 快速开始推荐阿里百炼 + DeepSeek V3 作为高性价比 LLM 方案
- 项目概述强调：仅用于研究和教育目的，不构成投资建议

### Testing Requirements
- 文档无需运行测试
- 可验证安装脚本：`python test_installation.py`

### Common Patterns
- 安装流程：克隆 → 虚拟环境 → 依赖 → .env 配置 → 验证
- API 密钥管理：.env 文件 + python-dotenv
- 成本控制：小模型 + 少辩论轮次 + 选择性分析师 + 缓存数据

## Dependencies

### Internal
- `tradingagents/` - 文档描述的核心库
- `app/` - Web 界面和后端服务

### External
- Python 3.10+ - 运行时
- 各 LLM API 密钥 - 服务接入

<!-- MANUAL: Custom project notes can be added below -->
