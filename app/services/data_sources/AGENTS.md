<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# data_sources

## Purpose
数据源适配子包。提供统一的数据源适配器基类、多数据源管理器及各数据源具体实现，支持优先级排序与自动降级（fallback）。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，导出 `DataSourceAdapter`、`TushareAdapter`、`AKShareAdapter`、`BaoStockAdapter`、`DataSourceManager` |
| `base.py` | 数据源适配器抽象基类 `DataSourceAdapter`，定义统一接口：股票列表、日度基础数据、最新交易日、实时行情、K线、新闻 |
| `manager.py` | 数据源管理器 `DataSourceManager`：管理多适配器、优先级排序、fallback 获取、一致性检查 |

## For AI Agents

### Working In This Directory
- 新增数据源适配器需继承 `DataSourceAdapter` 并实现所有抽象方法
- 适配器优先级从数据库 `datasource_groupings` 集合动态加载（A 股市场），无配置时使用默认优先级
- `DataSourceManager` 的所有 `*_with_fallback` 方法按优先级依次尝试，返回首个成功结果
- 一致性检查为可选功能，依赖 `data_consistency_checker` 模块，不可用时自动降级
- `close()` 方法负责清理适配器 Provider 和同步数据库连接

### Common Patterns
- 获取股票列表：`manager.get_stock_list_with_fallback()` → `(DataFrame, source_name)`
- 获取日度基础数据：`manager.get_daily_basic_with_fallback(trade_date)` → `(DataFrame, source_name)`
- 带一致性检查获取：`manager.get_daily_basic_with_consistency_check(trade_date)` → `(DataFrame, source_name, report)`
- 获取实时行情：`manager.get_realtime_quotes_with_fallback()` → `(dict, source_name)`
- 获取 K 线：`manager.get_kline_with_fallback(code, period, limit, adj)` → `(items, source_name)`
- 获取新闻：`manager.get_news_with_fallback(code, days, limit)` → `(items, source_name)`

### Dependencies

#### Internal
- `app/core/database` - MongoDB 连接（加载优先级配置）
- `app/core/config` - 配置
- `data_consistency_checker` - 数据一致性检查（可选）

#### External
- Tushare Pro API - A股数据源
- AkShare - A股数据源
- BaoStock - A股数据源

<!-- MANUAL: Custom project notes can be added below -->
