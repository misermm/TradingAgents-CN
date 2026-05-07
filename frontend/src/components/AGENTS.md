<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# components

## Purpose
前端共享组件目录，包含配置向导、模型选择、网络状态、布局、全局交互、数据同步、仪表盘及开发调试等可复用 Vue 3 组件。

## Key Files

| File | Description |
|------|-------------|
| `index.ts` | 全局组件注册入口，将 MarketSelector 和 MultiMarketStockSearch 注册为全局组件 |
| `ConfigWizard.vue` | 配置向导对话框，分步引导用户完成数据库、大模型、数据源等初始配置（5步流程） |
| `ConfigValidator.vue` | 配置验证组件，检查环境变量必需/推荐配置项及 MongoDB 中大模型和数据源配置的有效性 |
| `ModelConfig.vue` | AI 模型配置组件，支持快速分析模型和深度决策模型的切换，含能力等级徽章和智能推荐 |
| `DeepModelSelector.vue` | 深度模型选择器，通用下拉选择组件，支持快速/深度模式切换，显示能力等级和角色标签 |
| `NetworkStatus.vue` | 网络状态指示器，固定定位在右上角，检测网络断开和后端 API 连接失败，支持重试和定时检查 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `Dashboard/` | 仪表盘专用组件：多数据源同步卡片等 |
| `Dev/` | 开发环境调试组件 |
| `Global/` | 全局交互组件：市场选择器、股票搜索、确认对话框、通知、任务报告/结果对话框 |
| `Layout/` | 布局组件：侧边栏菜单、面包屑、头部操作栏、用户资料、页脚 |
| `Sync/` | 数据同步组件：数据源状态、同步控制、同步历史、同步建议 |

## For AI Agents

### Working In This Directory
- 组件风格：使用 Vue 3 `<script setup lang="ts">` + Element Plus 组件库 + SCSS scoped 样式
- 全局组件：需在 `index.ts` 的 `setupGlobalComponents` 中注册
- 模型选择：`ModelConfig.vue` 用于分析页面内嵌，`DeepModelSelector.vue` 是更通用的独立选择器
- 配置验证：`ConfigValidator.vue` 调用 `/api/system/config/validate` 接口，同时验证 .env 和 MongoDB 配置
- 网络检测：`NetworkStatus.vue` 依赖 `@/stores/app` 的 `isOnline` 和 `apiConnected` 状态

### Testing Requirements
- 组件测试：使用 Vue Test Utils
- 类型检查：`vue-tsc --noEmit`

### Common Patterns
- 双向绑定：`v-model` + `computed get/set` + `emit('update:modelValue')`
- API 调用：组件内直接调用 `@/api/` 模块，或通过 Pinia store 间接调用
- 状态轮询：`setInterval` + `onUnmounted` 清理，用于同步状态等实时更新场景
- 图标使用：从 `@element-plus/icons-vue` 按需导入

## Dependencies

### Internal
- `@/stores/app` - 应用全局状态（主题、网络、侧边栏）
- `@/stores/auth` - 认证状态（用户信息、登录/登出）
- `@/stores/notifications` - 通知状态（WebSocket/SSE 连接、未读计数）
- `@/api/sync` - 数据同步 API（状态查询、同步执行、数据源管理）
- `@/api/multiMarket` - 多市场股票搜索 API
- `@/api/modelCapabilities` - 模型能力与推荐 API
- `@/api/request` - HTTP 请求封装

### External
- Vue 3 - 响应式框架
- Element Plus - UI 组件库（el-dialog, el-select, el-card, el-timeline 等）
- @element-plus/icons-vue - 图标库
- marked - Markdown 渲染（TaskReportDialog, TaskResultDialog）
- vue-router - 路由（SidebarMenu, Breadcrumb, UserProfile）
- pinia - 状态管理（storeToRefs）
- axios - HTTP 请求（ConfigValidator）

<!-- MANUAL: Custom project notes can be added below -->
