<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# models

## Purpose
数据模型定义模块，使用 Pydantic 定义所有业务数据的结构化模型，包括分析、用户、股票、筛选、通知等。

## Key Files

| File | Description |
|------|-------------|
| `analysis.py` | 分析模型：AnalysisParameters, AnalysisResult, AnalysisTask |
| `stock_models.py` | 股票模型：StockBasicInfoExtended, MarketQuotesExtended |
| `user.py` | 用户模型：User, UserCreate, UserUpdate |
| `config.py` | 配置模型 |
| `notification.py` | 通知模型 |
| `operation_log.py` | 操作日志模型 |
| `screening.py` | 筛选模型 |
| `__init__.py` | 包初始化 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 所有数据模型使用 Pydantic V2 定义
- MongoDB 文档模型使用 `model_config = ConfigDict(...)` 配置
- 新增业务实体需在此添加对应模型

### Testing Requirements
- 模型测试：`python -m pytest tests/ -k "model" -v`

### Common Patterns
- 模型模式：BaseModel → 定义字段 → ConfigDict 配置 → 在 Service 中使用

## Dependencies

### Internal
- `app/core/` - 配置引用

### External
- Pydantic V2 - 数据验证

<!-- MANUAL: Custom project notes can be added below -->
