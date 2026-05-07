<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests

## Purpose
测试套件 (Apache 2.0)，包含 200+ 测试文件覆盖核心库、数据流、API、服务层等。默认跳过集成测试，支持按模块和标记筛选运行。

## Key Files

| File | Description |
|------|-------------|
| `conftest.py` | pytest 全局 fixture 与配置 |
| `pytest.ini` | pytest 配置：testpaths=tests, 默认 -m "not integration" |
| `__init__.py` | 包初始化 |
| `README.md` | 测试组织说明 |
| `FILE_ORGANIZATION_SUMMARY.md` | 文件组织摘要 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `config/` | 配置相关测试 |
| `dataflows/` | 数据流测试 |
| `e2e/` | 端到端测试 |
| `integration/` | 集成测试 (需 -m integration 标记) |
| `middleware/` | 中间件测试 |
| `services/` | 服务层测试 |
| `system/` | 系统级测试 |
| `unit/` | 单元测试 |
| `0.1.14/` | 版本 0.1.14 相关测试 |
| `test_tushare_unified/` | Tushare 统一接口测试 |

## For AI Agents

### Working In This Directory
- Apache 2.0 开源模块
- 默认跳过集成测试：`-m "not integration"`
- 运行全部：`python -m pytest tests/ -v`
- 运行集成测试：`python -m pytest tests/ -m integration -v`
- 按关键词：`python -m pytest tests/ -k "akshare" -v`
- 根目录有大量测试文件（200+），子目录按功能分类

### Testing Requirements
- 测试本身即是被测试对象，确保测试可运行
- 新功能需添加对应测试文件

### Common Patterns
- 测试文件命名：`test_<功能>.py`
- 调试脚本命名：`debug_<功能>.py`、`quick_<功能>.py`
- 快速验证脚本：`simple_<功能>_test.py`

## Dependencies

### Internal
- `tradingagents/` - 被测试的核心库
- `app/` - 被测试的后端服务

### External
- pytest - 测试框架
- pytest-asyncio - 异步测试支持
- pytest-mock - Mock 支持

<!-- MANUAL: Custom project notes can be added below -->
