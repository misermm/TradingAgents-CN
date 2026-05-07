<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# cli

## Purpose
命令行界面工具，提供股票分析的 CLI 入口，支持数据源初始化（AkShare/BaoStock/Tushare）和交互式分析。

## Key Files

| File | Description |
|------|-------------|
| `main.py` | CLI 主入口，定义命令和交互流程 |
| `models.py` | CLI 数据模型定义 |
| `utils.py` | CLI 工具函数 |
| `akshare_init.py` | AkShare 数据源初始化 |
| `baostock_init.py` | BaoStock 数据源初始化 |
| `tushare_init.py` | Tushare 数据源初始化 |
| `__init__.py` | 包初始化 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `static/` | 静态资源：欢迎文本 |

## For AI Agents

### Working In This Directory
- CLI 入口通过 `python main.py` 或 `python -m cli` 启动
- 数据源初始化需在分析前完成
- 使用 Typer/Click 风格的命令定义

### Testing Requirements
- CLI 测试：`python -m pytest tests/ -k "cli" -v`

### Common Patterns
- 初始化流程：选择数据源 → 初始化 → 同步数据 → 执行分析

## Dependencies

### Internal
- `tradingagents/` - 调用核心分析引擎

### External
- Typer/Click - CLI 框架
- Rich - 终端美化输出

<!-- MANUAL: Custom project notes can be added below -->
