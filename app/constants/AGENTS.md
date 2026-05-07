<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# constants

## Purpose
定义应用级别的常量与配置数据，目前包含模型能力分级系统。该模块为 LLM 供应商的各类模型提供统一的能力等级（1-5级）、适用角色、特性标签等元数据，用于智能匹配分析深度和模型选择；同时定义聚合渠道（302.AI、OpenRouter、AIHubMix、One API、New API）及本地模型（Ollama、LM Studio）的默认配置。

## Key Files

| File | Description |
|------|-------------|
| `model_capabilities.py` | 模型能力分级系统核心定义，包含 `ModelCapabilityLevel`（能力等级枚举）、`ModelRole`（角色枚举）、`ModelFeature`（特性标签枚举）、`DEFAULT_MODEL_CAPABILITIES`（常见模型默认配置字典）、`ANALYSIS_DEPTH_REQUIREMENTS`（分析深度与最低能力要求映射）、`AGGREGATOR_PROVIDERS`（聚合渠道配置）、`LOCAL_MODEL_PROVIDERS`（本地模型配置），以及徽章样式和聚合渠道模型名解析等辅助函数 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 修改模型能力配置时，务必同时更新 `DEFAULT_MODEL_CAPABILITIES` 字典和对应的枚举定义
- 新增模型时需填写 `capability_level`、`suitable_roles`、`features`、`recommended_depths`、`performance_metrics`、`description` 六个字段
- 新增聚合渠道时需在 `AGGREGATOR_PROVIDERS` 中添加配置，并确保 `model_name_format` 与实际 API 格式一致
- 能力等级 1-5 对应：基础→标准→高级→专业→旗舰，修改等级定义需同步更新 `CAPABILITY_DESCRIPTIONS`
- `performance_metrics` 中 speed/cost/quality 取值 1-5，5 为最优

### Testing Requirements
- 运行测试：`python -m pytest tests/ -v -k "model_capabilities"`
- 验证枚举值和字典键的一致性
- 验证 `is_aggregator_model` 和 `parse_aggregator_model` 函数对边界情况的处理

### Common Patterns
- 获取模型能力等级：`DEFAULT_MODEL_CAPABILITIES[model_name]["capability_level"]`
- 判断聚合渠道模型：`is_aggregator_model(model_name)` → `parse_aggregator_model(model_name)` 返回 `(provider, model)`
- 获取徽章样式：`get_model_capability_badge(level)` / `get_role_badge(role)` / `get_feature_badge(feature)`
- 分析深度匹配：`ANALYSIS_DEPTH_REQUIREMENTS[depth]["min_capability"]`

## Dependencies

### Internal
- 被 `app/` 中的模型选择、分析配置等模块引用

### External
- Python 标准库 `enum`、`typing`

<!-- MANUAL: Custom project notes can be added below -->
