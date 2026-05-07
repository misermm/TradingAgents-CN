<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# analysis

## Purpose
分析服务子包。从单体 `analysis_service.py` 拆分出的工具模块，保持 `AnalysisService` 公共 API 不变。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，声明子包用途并保持公共导入 |

## For AI Agents

### Working In This Directory
- 本子包为过渡性拆分产物，公共 API 仍由上层 `analysis_service.py` 暴露
- 新增分析相关工具函数应放在此子包，再由 `__init__.py` 导出

### Dependencies

#### Internal
- `app/services/analysis_service.py` - 上层分析服务主类

<!-- MANUAL: Custom project notes can be added below -->
