<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# TradingAgents-CN

## Purpose
多智能体 AI 股票分析学习平台，基于 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)。支持 A股/港股/美股分析，LLM 供应商聚合（OpenAI、Google、DeepSeek、阿里百炼等）。定位为学习与研究用途，不提供实盘交易指令。

## Key Files

| File | Description |
|------|-------------|
| `main.py` | 核心分析入口，启动 TradingAgentsGraph 执行股票分析 |
| `pyproject.toml` | Python 项目配置与依赖声明 |
| `requirements.txt` | Python 依赖列表 |
| `docker-compose.yml` | 生产环境 Docker 编排 |
| `docker-compose.local.yml` | 本地开发 Docker 编排 |
| `Dockerfile.backend` | 后端 Docker 镜像构建 |
| `Dockerfile.frontend` | 前端 Docker 镜像构建 |
| `conftest.py` | pytest 全局配置与 fixture |
| `VERSION` | 项目版本号 |
| `.env.docker` | Docker 环境变量模板 |
| `AGENTS.md` | AI 代理开发指南（本文件） |
| `DEV_PROGRESS.md` | 开发进度追踪文档 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `tradingagents/` | 核心库 (Apache 2.0)，多智能体分析引擎 (see `tradingagents/AGENTS.md`) |
| `app/` | FastAPI 后端 (专有，商用需授权) (see `app/AGENTS.md`) |
| `frontend/` | Vue 3 前端 (专有，商用需授权) (see `frontend/AGENTS.md`) |
| `tests/` | 测试套件 (Apache 2.0) (see `tests/AGENTS.md`) |
| `scripts/` | 运维脚本与数据库初始化 (see `scripts/AGENTS.md`) |
| `docs/` | 项目文档与学习资源 (see `docs/AGENTS.md`) |
| `cli/` | CLI 命令行工具 (see `cli/AGENTS.md`) |
| `examples/` | 使用示例与演示代码 (see `examples/AGENTS.md`) |
| `config/` | 配置文件 (日志等) (see `config/AGENTS.md`) |
| `langchain/` | LangChain 扩展模块 (see `langchain/AGENTS.md`) |
| `install/` | 安装配置文件 |
| `nginx/` | Nginx 反向代理配置 |
| `docker/` | Docker 辅助配置 |
| `assets/` | 静态资源 (图片等) |
| `images/` | README 用图片资源 |
| `reports/` | 修复报告存档 |

## For AI Agents

### Working In This Directory
- 许可证区分：`tradingagents/`、`tests/`、`scripts/`、`docs/` 为 Apache 2.0；`app/`、`frontend/` 为专有
- 商业使用 `app/` 或 `frontend/` 需联系 hsliup@163.com 获取授权
- 分析股票前**必须**先同步数据，否则结果会出现数据错误
- 国内数据源需直连 (NO_PROXY)，国外 LLM 需走 HTTP_PROXY
- Windows 环境下 NO_PROXY 使用完整域名，不支持通配符

### Testing Requirements
- 运行测试：`python -m pytest tests/ -v`
- 默认跳过集成测试：`-m "not integration"`
- 跑集成测试：`python -m pytest tests/ -m integration -v`
- 运行特定测试：`python -m pytest tests/test_analysis.py -v`

### Common Patterns
- 核心用法：`from tradingagents.graph.trading_graph import TradingAgentsGraph`
- Docker 开发：`docker-compose -f docker-compose.local.yml up -d`
- 数据同步：`python scripts/akshare_sync_optimized.py --codes 000001,600519 --limit 365`

## Dependencies

### Internal
- `tradingagents/` → 核心分析引擎，被 `app/` 和 `cli/` 调用
- `app/` → 后端 API，调用 `tradingagents/` 执行分析
- `frontend/` → 前端界面，通过 API 调用 `app/`
- `langchain/` → LangChain 扩展，被 `tradingagents/` 引用

### External
- Python 3.10+ - 运行时
- MongoDB - 主数据库
- Redis - 缓存与队列
- FastAPI + Uvicorn - 后端框架
- Vue 3 + Vite + Element Plus - 前端框架
- LangChain, LangGraph - AI 编排
- AkShare, Tushare, BaoStock - A股数据源
- Finnhub, yfinance - 美股数据源
- ChromaDB - 向量数据库

## Configuration

### 环境变量 (.env)
必需配置见 `.env.example`，关键项：

```env
MONGODB_HOST=localhost; MONGODB_PORT=27017; MONGODB_USERNAME=admin; MONGODB_PASSWORD=tradingagents123
REDIS_HOST=localhost; REDIS_PORT=6379; REDIS_PASSWORD=tradingagents123
JWT_SECRET=your-super-secret-jwt-key-change-in-production
DEEPSEEK_API_KEY=sk-xxx; DASHSCOPE_API_KEY=sk-xxx; GOOGLE_API_KEY=xxx
HTTP_PROXY=http://127.0.0.1:7890; HTTPS_PROXY=http://127.0.0.1:7890
NO_PROXY=localhost,127.0.0.1,eastmoney.com,api.tushare.pro,baostock.com
```

### 常见问题
1. **数据缺失**: 同步数据后再分析
2. **LLM 连接失败**: 配置 HTTP_PROXY / 检查 API Key
3. **数据库连接**: 检查 MongoDB/Redis 服务是否运行

### 调试技巧
- 查看日志: `logs/` 目录或 Docker 日志
- 快速测试数据源: `python tests/simple_akshare_test.py`
- 检查配置: `python scripts/check_api_config.py`

<!-- MANUAL: Custom project notes can be added below -->
