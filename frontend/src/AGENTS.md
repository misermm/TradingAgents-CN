<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# src

## Purpose
Vue 3 前端源代码目录，包含所有页面视图、组件、API 接口、状态管理、路由和样式定义。

## Key Files

| File | Description |
|------|-------------|
| `main.ts` | 应用入口，初始化 Vue 实例、插件和全局配置 |
| `App.vue` | 根组件，定义页面基本结构和网络状态指示 |
| `test-import.js` | 导入测试脚本 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `api/` | API 接口层：封装所有后端 API 调用 |
| `views/` | 页面视图：仪表盘、报告、设置、筛选等 |
| `components/` | 共享组件：配置向导、模型配置、网络状态等 |
| `stores/` | Pinia 状态管理：应用状态、认证、通知 |
| `router/` | Vue Router 路由配置 |
| `layouts/` | 布局组件：BasicLayout 基础布局 |
| `styles/` | 全局样式：SCSS 变量、暗色主题 |
| `types/` | TypeScript 类型定义 |
| `utils/` | 工具函数：认证、日期、市场判断、股票校验 |
| `constants/` | 常量定义：分析师、报告 |

## For AI Agents

### Working In This Directory
- 页面开发：在 `views/` 创建组件 → 在 `router/` 注册路由
- API 调用：在 `api/` 定义接口 → 在组件中调用
- 状态管理：在 `stores/` 定义 Pinia store
- 样式：使用 SCSS，暗色主题在 `styles/dark-theme.scss`

### Testing Requirements
- 组件测试：使用 Vue Test Utils
- 类型检查：`vue-tsc --noEmit`

### Common Patterns
- 页面模式：views/X/index.vue → router 注册 → API 调用 → Pinia 状态
- 组件模式：components/X.vue → props/emits → Element Plus 组件
- API 模式：api/x.ts → request.ts 封装 → 组件调用

## Dependencies

### Internal
- `app/` - 后端 API

### External
- Vue 3 - 前端框架
- Element Plus - UI 组件库
- Vue Router - 路由
- Pinia - 状态管理
- Axios - HTTP 请求
- TypeScript - 类型安全
- SCSS - 样式

<!-- MANUAL: Custom project notes can be added below -->
