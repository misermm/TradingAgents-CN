<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# constants

## Purpose
常量定义模块，统一管理系统中使用的常量。当前主要包含数据源编码、数据源信息及注册表，为整个 tradingagents 系统提供数据源的标准化定义和查询接口。添加新数据源时只需在此模块注册即可，无需修改各业务模块。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 模块入口，从 `data_sources` 导出核心类型和函数（`DataSourceCode`、`DataSourceInfo`、`DATA_SOURCE_REGISTRY`、`get_data_source_info`、`list_all_data_sources`、`is_data_source_supported`），供外部统一引用 |
| `data_sources.py` | 数据源编码与注册表定义。包含 `DataSourceCode` 枚举（15+ 数据源编码，覆盖 A股/美股/港股/专业/自定义）、`DataSourceInfo` 数据类（名称、提供商、支持市场、是否免费等）、`DATA_SOURCE_REGISTRY` 全局注册表，以及按市场/免费筛选等辅助函数 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 添加新数据源时，先在 `DataSourceCode` 枚举中添加编码，再在 `DATA_SOURCE_REGISTRY` 中注册 `DataSourceInfo`，最后在 `__init__.py` 的导出中确认是否需要新增导出
- 数据源编码命名规范：枚举名用大写字母+下划线，值用小写字母+下划线
- `supported_markets` 字段使用标准市场标识：`a_shares`、`us_stocks`、`hk_stocks`、`crypto`、`futures`
- 修改此模块后需确认下游 `tradingagents/data_provider/` 和 `app/` 中的引用是否兼容

### Testing Requirements
- 运行测试：`python -m pytest tests/ -v -k "data_source or constants"`
- 验证注册表完整性：确保每个 `DataSourceCode` 枚举值在 `DATA_SOURCE_REGISTRY` 中都有对应条目
- 验证辅助函数：`get_data_source_info`、`list_all_data_sources`、`is_data_source_supported` 的返回值正确性

### Common Patterns
- 获取数据源信息：`from tradingagents.constants import get_data_source_info; info = get_data_source_info("akshare")`
- 列出所有数据源：`from tradingagents.constants import list_all_data_sources; sources = list_all_data_sources()`
- 检查数据源是否支持：`from tradingagents.constants import is_data_source_supported; is_data_source_supported("tushare")`
- 引用数据源编码常量：`from tradingagents.constants import DataSourceCode; code = DataSourceCode.AKSHARE`

## Dependencies

### Internal
- 被 `tradingagents/data_provider/` 数据提供层引用，用于数据源路由和选择
- 被 `app/` 后端 API 引用，用于向前端暴露可用数据源列表
- 被 `scripts/` 数据同步脚本引用，用于指定数据源

### External
- Python 标准库 `enum`、`dataclasses`、`typing`

<!-- MANUAL: Custom project notes can be added below -->
