# views/

Parent: ../AGENTS.md | Generated: 2026-05-07

Vue 3 页面视图层，每个子目录对应一个功能模块的路由页面。所有页面使用 Element Plus 组件库 + Composition API (`<script setup lang="ts">`) 编写。

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `About/` | 关于页面，展示项目介绍、核心功能、技术架构、版本信息和联系方式 |
| `Analysis/` | 股票分析模块，包含单股分析 (`SingleAnalysis.vue`)、批量分析 (`BatchAnalysis.vue`) 和分析历史 (`AnalysisHistory.vue`) |
| `Auth/` | 用户认证页面，提供登录表单 (`Login.vue`)，调用 authStore 进行身份验证 |
| `Dashboard/` | 仪表板首页，展示欢迎区域、快速操作、最近分析、自选股、模拟交易账户概览和市场快讯 |
| `Error/` | 错误页面，目前包含 404 页面 (`404.vue`)，提供返回首页和推荐链接 |
| `Favorites/` | 自选股管理页面，支持添加/编辑/移除自选股、标签管理、实时行情同步和批量数据同步 |
| `Learning/` | 学习中心，包含首页 (`index.vue`)、分类浏览 (`Category.vue`) 和文章阅读 (`Article.vue`)，涵盖 AI 基础、提示词工程、模型选择等主题 |
| `PaperTrading/` | 模拟交易页面，支持 A股/港股/美股虚拟账户的买卖操作、持仓管理和订单记录，可关联分析报告 |
| `Queue/` | 任务队列管理页面，实时监控分析任务状态，支持查看结果、重试失败任务和清理已完成任务 |
| `Reports/` | 分析报告模块，包含报告列表 (`index.vue`)、报告详情 (`ReportDetail.vue`) 和 Token 使用统计 (`TokenStatistics.vue`)，支持多格式导出 |
| `Screening/` | 股票筛选页面，提供多维度筛选条件（行业、市值、PE/PB/ROE、涨跌幅等），支持批量分析和加入自选 |
| `Settings/` | 设置模块，包含个人设置 (`index.vue`)、配置管理 (`ConfigManagement.vue`)、使用统计 (`UsageStatistics.vue`) 和缓存管理 (`CacheManagement.vue`)，以及 LLM/数据源/市场分类等子组件 |
| `Stocks/` | 股票详情页面 (`Detail.vue`)，展示实时报价、K线图、基本面快照、新闻公告、分析结果，支持数据同步和模拟交易 |
| `System/` | 系统管理模块，包含数据库管理 (`DatabaseManagement.vue`)、日志管理 (`LogManagement.vue`)、多数据源同步 (`MultiSourceSync.vue`)、操作日志 (`OperationLogs.vue`) 和定时任务管理 (`SchedulerManagement.vue`) |
| `Tasks/` | 任务中心页面 (`TaskCenter.vue`)，统一管理分析任务，支持进行中/已完成/失败/全部标签页切换、WebSocket 实时进度更新和批量操作 |

## Key Files

| File | Description |
|------|-------------|
| `Dashboard/index.vue` | 应用首页入口，聚合自选股、最近分析、模拟账户和市场快讯 |
| `Analysis/SingleAnalysis.vue` | 单股分析核心页面，配置分析参数后提交 AI 分析任务 |
| `Analysis/BatchAnalysis.vue` | 批量分析页面，支持同时分析多只股票 |
| `Stocks/Detail.vue` | 股票详情页，集成报价、K线、基本面、新闻、分析报告 |
| `PaperTrading/index.vue` | 模拟交易页面，支持多市场虚拟交易 |
| `Settings/index.vue` | 设置入口页面，按 personal/config/admin 三组展示菜单 |
| `Tasks/TaskCenter.vue` | 任务中心，WebSocket 驱动的实时任务管理 |

## Common Patterns

- 所有页面使用 `<script setup lang="ts">` + Element Plus 组件
- API 调用统一通过 `@/api/` 模块（如 `analysisApi`, `favoritesApi`, `paperApi`）
- 路由跳转使用 `useRouter()` 的命名路由（如 `{ name: 'ReportDetail', params: { id } }`）
- 用户认证状态通过 `useAuthStore()` 管理
- 应用全局状态（主题、侧边栏等）通过 `useAppStore()` 管理
- 时间格式化统一使用 `@/utils/datetime` 工具函数
- 市场类型转换使用 `@/utils/market` 工具函数

## Dependencies

### Internal
- `@/api/` — 后端 API 调用层
- `@/stores/` — Pinia 状态管理（auth, app）
- `@/types/` — TypeScript 类型定义
- `@/utils/` — 工具函数（datetime, market）
- `@/components/` — 可复用组件
- `@/constants/` — 常量定义（如报告名称映射）

### External
- Vue 3 + Vue Router
- Element Plus（UI 组件库）
- ECharts + vue-echarts（K线图表，仅 `Stocks/Detail.vue` 使用）
- marked（Markdown 渲染，用于分析报告展示）
