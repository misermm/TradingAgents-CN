# tests/0.1.14/

Parent: ../AGENTS.md
Generated: 2026-05-07
Updated: 2026-05-07

## Purpose

v0.1.14 版本的回归与功能验证测试集。覆盖分析结果持久化、数据源备份与降级、工具选择逻辑、美股数据独立性等关键场景。

## Key Files

| File | Description |
|------|-------------|
| `cleanup_test_data.py` | 清理测试残留数据（文件系统 + MongoDB），删除 TEST123/TEST001 相关记录 |
| `create_sample_reports.py` | 生成示例报告数据，用于前端展示与集成测试 |
| `test_analysis_save.py` | 测试分析结果保存功能：JSON 文件持久化 + MongoDB 存储 |
| `test_backup_datasource.py` | 测试数据源备份与降级机制 |
| `test_comprehensive_backup.py` | 综合备份策略测试 |
| `test_data_structure.py` | 测试数据结构正确性与一致性 |
| `test_fallback_mechanism.py` | 测试数据源回退机制（主数据源不可用时的降级逻辑） |
| `test_google_tool_handler_fix.py` | 测试 Google 工具处理器修复 |
| `test_guide_auto_hide.py` | 测试引导自动隐藏功能 |
| `test_import_fix.py` | 测试导入路径修复 |
| `test_online_tools_config.py` | 测试在线工具配置（online_tools / online_news / realtime_data） |
| `test_real_scenario_fix.py` | 测试真实场景修复验证 |
| `test_tool_selection_logic.py` | 测试工具选择逻辑：离线/实时/在线新闻/完全在线四种场景下的市场/新闻/社交工具选择 |
| `test_tushare_direct.py` | 测试 Tushare 直连数据获取 |
| `test_us_stock_independence.py` | 测试美股数据获取独立性，验证不再依赖 OpenAI 配置 |

## Subdirectories

无

## For AI Agents

### Working In This Directory
- 这些测试属于 v0.1.14 版本的回归测试，用于验证该版本引入的功能改动
- 多数测试为脚本式（`if __name__ == "__main__"`），非 pytest 标准用例
- 部分测试依赖 MongoDB 连接和 Web 模块（`web.utils`、`web.components`），需确保服务可用
- `cleanup_test_data.py` 应在测试完成后运行，清理 TEST123/TEST001 等测试数据
- 工具选择逻辑测试验证了四个配置场景：完全离线、实时数据、在线新闻、完全在线

### Testing
- 运行单个测试：`python tests/0.1.14/test_tool_selection_logic.py`
- 清理测试数据：`python tests/0.1.14/cleanup_test_data.py`
- 不建议通过 pytest 批量运行（多数为脚本式测试）

### Dependencies
- 内部依赖：`tradingagents.graph.trading_graph`、`tradingagents.default_config`、`tradingagents.agents.utils.agent_utils`、`web.utils.mongodb_report_manager`、`web.components.analysis_results`
- 外部依赖：MongoDB（部分测试）、pandas
