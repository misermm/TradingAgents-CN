<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# types

## Purpose
TypeScript 类型定义层，为前端所有模块提供统一的接口和枚举类型声明，确保与后端 API 的类型安全对接。

## Key Files

| File | Description |
|------|-------------|
| `analysis.ts` | 分析相关类型：状态枚举、请求/响应接口、任务/批次/报告/队列/统计类型 |
| `auth.ts` | 认证相关类型：用户信息、登录/注册表单、Token 响应、权限、偏好设置、活动日志 |
| `config.ts` | 配置管理类型：LLM 厂家/模型配置、数据源配置、数据库配置、系统配置、测试请求/响应 |
| `router.d.ts` | Vue Router 路由元信息扩展：title / requiresAuth / icon / hideInMenu / transition |

## For AI Agents

### Working In This Directory
- 新增类型：按领域分文件定义，导出 `interface` 或 `enum`
- 字段兼容：`symbol` 为主字段，`stock_code` / `code` 为兼容字段（已废弃但保留）
- 枚举使用：`AnalysisStatus` / `BatchStatus` 为字符串枚举，与后端状态值一一对应
- 路由元信息：通过 `declare module 'vue-router'` 扩展 `RouteMeta` 接口

### Testing Requirements
- 类型检查：`vue-tsc --noEmit` 确保类型正确
- 字段兼容性：验证 `symbol` / `stock_code` / `code` 的兼容逻辑

### Common Patterns
- 分析状态：`AnalysisStatus.PENDING → 'pending'` 字符串枚举，与后端 API 状态值对齐
- 股票代码字段：`symbol`（主）+ `stock_code`（兼容）+ `code`（兼容），新代码统一使用 `symbol`
- 用户偏好：`UserPreferences` 包含分析偏好、外观设置、语言地区、通知设置四个维度
- LLM 配置：`LLMProvider`（厂家）→ `LLMConfig`（模型实例），支持聚合渠道

## Dependencies

### Internal
- 无内部依赖（纯类型定义层）

### External
- TypeScript - 类型系统
- Vue Router - `router.d.ts` 扩展 RouteMeta

<!-- MANUAL: Custom project notes can be added below -->
