<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs/releases

## Purpose
项目更新日志，记录 TradingAgents-CN 各版本的重要更改、功能增删和修复内容。

## Key Files

| File | Description |
|------|-------------|
| `CHANGELOG.md` | 完整更新日志，按版本记录所有重要更改（Docker 部署整合、一键部署脚本优化、前端代理修复等） |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- 日志格式：`[Unreleased]` 或 `[版本号] - 日期 - 简要描述`，下方按分类列出改动
- 最新未发布版本聚焦 Docker 部署整合：删除本地启动脚本、统一环境配置文件、优化 docker-compose.local.yml、重写 redeploy.bat、修复前端 Vite proxy
- 关键修复：Vite proxy 在 Docker 中无法连接后端（localhost → backend 服务名）
- 部署优化：移除 apt-get 步骤（8-15 分钟 → 0 秒）、健康检查改用 Python、启动等待时间 120s → 300s

### Testing Requirements
- 文档无需运行测试

### Common Patterns
- 日志分类：删除文件、统一配置、优化 compose、重写脚本、修复 bug
- 版本标记：`[Unreleased]` 表示尚未发布的改动
- 部署模式：`--dev`（4 服务，前端 5173）vs `--prod`（6 服务，前端 80）

## Dependencies

### Internal
- `docker-compose.local.yml` - 开发环境 Docker 编排
- `docker-compose.yml` - 生产环境 Docker 编排
- `scripts/redeploy.bat` - 一键部署脚本
- `frontend/vite.config.ts` - 前端代理配置

### External
- Docker / Docker Compose - 部署依赖

<!-- MANUAL: Custom project notes can be added below -->
