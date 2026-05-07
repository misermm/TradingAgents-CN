<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# utils

## Purpose
后端通用工具函数集合，为 `app/` 各模块提供 API Key 管理、错误信息格式化、报告导出、时区处理和交易时间判断等基础能力，是整个后端服务的共享工具层。

## Key Files

| File | Description |
|------|-------------|
| `api_key_utils.py` | API Key 处理工具：验证 Key 有效性（长度、占位符、截断检测）、缩略显示（前6后6）、按厂家/数据源从环境变量读取 Key、判断是否应跳过更新 |
| `error_formatter.py` | 错误信息格式化器：将技术性错误转换为用户友好提示，支持 LLM（API Key/网络/配额/内容审核）、数据源（API Key/网络/无数据）、股票代码、网络、系统等 12 种错误类别的自动分类与中文提示生成 |
| `report_exporter.py` | 报告导出器：支持 Markdown、Word（pypandoc）、PDF（pdfkit+wkhtmltopdf）三种格式导出，内置中文竖排修复、表格分页优化、A4 页面样式等处理逻辑 |
| `timezone.py` | 时区工具：获取配置时区（优先数据库缓存 > 环境变量 > 默认 Asia/Shanghai）、当前时区时间、时区转换、确保 datetime 含时区信息 |
| `trading_time.py` | 交易时间判断：判断当前是否处于 A 股交易时段（含收盘后 30 分钟缓冲期）、严格交易时段、盘前（9:00-9:30）、盘后（15:00-15:30），以及获取完整交易状态字符串 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 这些工具函数被 `app/` 多处引用，修改时需确保向后兼容
- `error_formatter.py` 的 `ErrorCategory` 枚举和关键词列表需与实际 LLM/数据源错误信息保持同步
- `report_exporter.py` 的 PDF 导出依赖外部工具（wkhtmltopdf），Word 导出依赖 pandoc，运行时需检查 `EXPORT_AVAILABLE` / `PANDOC_AVAILABLE` / `PDFKIT_AVAILABLE` 标志
- `timezone.py` 通过懒加载引用 `app.services.config_provider` 避免循环导入
- `trading_time.py` 当前仅支持 A 股交易时间，港股/美股需扩展

### Testing Requirements
- 单元测试应覆盖各工具函数的边界条件（空值、占位符 Key、非交易日等）
- `error_formatter.py` 应测试各类错误关键词的匹配准确性
- `report_exporter.py` 应测试无 pandoc/pdfkit 时的降级行为

### Common Patterns
- API Key 读取：`get_env_api_key_for_provider("deepseek")` / `get_env_api_key_for_datasource("tushare")`
- 错误格式化：`ErrorFormatter.format_error(error_msg, context={"llm_provider": "deepseek"})`
- 报告导出：`report_exporter.generate_markdown_report(doc)` / `generate_docx_report(doc)` / `generate_pdf_report(doc)`
- 时区时间：`now_tz()` / `to_config_tz(dt)` / `ensure_timezone(dt)`
- 交易状态：`is_trading_time()` / `get_trading_status()`

## Dependencies

### Internal
- `app.core.config.settings` — 时区和全局配置（timezone.py、trading_time.py）
- `app.services.config_provider` — 数据库配置缓存（timezone.py 懒加载）

### External
- `pypandoc` — Word 文档生成（report_exporter.py，可选）
- `markdown` — Markdown 转 HTML（report_exporter.py，可选）
- `pdfkit` + `wkhtmltopdf` — PDF 生成（report_exporter.py，可选）
- `python-docx` — Word 文档后处理修复文本方向（report_exporter.py，可选）
- `zoneinfo` (标准库) — 时区处理

<!-- MANUAL: Custom project notes can be added below -->
