<!-- Parent: ../AGENTS.md | Generated: 2026-05-07 | Updated: 2026-05-07 -->

# frontend/src/api/

## Purpose
前端 API 层，封装所有与后端 FastAPI 服务的 HTTP 通信。基于 Axios 实例，提供统一的请求/响应拦截、认证注入、错误处理与重试机制。每个模块对应一个业务域，导出类型安全的 API 函数或对象。

## Key Files

| File | Description |
|------|-------------|
| `request.ts` | Axios 实例与 ApiClient 封装核心，含请求/响应拦截器、JWT 认证注入、401 自动刷新、错误去重、网络重试、业务错误码处理、文件上传/下载工具 |
| `analysis.ts` | 股票分析 API，含单股/批量分析启动、进度查询、结果获取、历史记录、导出、分享、股票搜索与热门股票，以及市场类型/分析类型/数据源/步骤状态等常量与验证函数 |
| `auth.ts` | 认证 API，含登录、注册、登出、Token 刷新、获取/更新用户信息、修改密码、重置密码、验证邮箱 |
| `cache.ts` | 缓存管理 API，含缓存统计、过期清理、全量清空、详情分页列表、后端信息查询（MongoDB/Redis 可用性） |
| `config.ts` | 系统配置管理 API，含大模型厂家 CRUD、模型目录管理、LLM 配置 CRUD、数据源配置 CRUD、市场分类管理、数据源分组管理、数据库配置管理、系统设置读写、配置导入导出/重载/迁移、本地模型扫描（Ollama/LM Studio），以及大量默认配置模板与验证函数 |
| `database.ts` | 数据库管理 API，含 MongoDB/Redis 状态与统计查询、连接测试、备份创建/列表/删除、数据导入（FormData）/导出（Blob）、旧数据清理、分析结果清理、操作日志清理 |
| `favorites.ts` | 自选股收藏 API，含收藏列表、添加/更新/删除收藏、收藏状态检查、标签列表、自选股实时行情同步 |
| `logs.ts` | 系统日志文件 API，含日志文件列表、内容读取（支持级别/关键词/时间过滤）、日志导出（Blob）、统计信息、日志文件删除 |
| `modelCapabilities.ts` | 模型能力管理 API，含默认模型能力配置、分析深度要求、能力等级描述、徽章样式、模型推荐、模型对验证、批量初始化能力、单模型能力查询 |
| `multiMarket.ts` | 多市场股票统一查询 API，支持 A股/港股/美股，含市场列表、股票搜索、基础信息、实时行情、历史 K 线数据 |
| `news.ts` | 新闻数据 API，含最新新闻获取（支持按股票/市场）、股票新闻查询、市场新闻后台同步 |
| `notifications.ts` | 通知消息 API，含未读数查询、通知列表（分页/状态/类型过滤）、单条标记已读、全部标记已读，含后端未就绪时的兜底逻辑 |
| `operationLogs.ts` | 操作日志 API（类风格），含日志列表查询（分页/日期/类型/关键词）、统计信息、详情查看、创建日志、清空日志、CSV 导出，以及操作类型常量/名称/标签颜色映射 |
| `paper.ts` | 模拟交易 API，含账户概览（多币种现金/持仓市值）、下单（买/卖）、持仓列表、委托记录、账户重置 |
| `scheduler.ts` | 定时任务调度 API，含任务列表/详情、暂停/恢复/手动触发、执行历史、调度器统计/健康检查、任务元数据更新、执行记录查询/统计/取消/标记失败/删除 |
| `screening.ts` | 股票筛选 API，含条件筛选执行（支持排序/分页）、筛选字段配置获取、行业列表获取 |
| `stockSync.ts` | 股票数据同步 API，含单股同步（实时/历史/财务/基础）、批量同步、同步状态查询，支持 tushare/akshare 数据源与降级回退 |
| `stocks.ts` | 单股行情数据 API，含行情报价、基本面数据（PE/PB/PS/ROE 等）、K 线数据（多周期/复权）、股票新闻/公告 |
| `sync.ts` | 多数据源同步 API，含数据源状态查询、当前数据源、同步状态、股票基础信息同步触发、数据源连接测试、同步建议、同步历史、缓存清理，以及传统单源同步兼容接口 |
| `tags.ts` | 标签管理 API，含标签列表、创建/更新/删除标签 |
| `templates.ts` | 模板管理 API，含模板列表/详情/创建/更新/删除，以及智能体模板列表查询 |
| `usage.ts` | 使用统计 API，含使用记录查询、统计汇总（按供应商/模型/日期）、按供应商/模型成本统计、每日成本统计、旧记录删除 |

## For AI Agents

### Working In This Directory
- 所有 API 模块依赖 `request.ts` 中的 `ApiClient` 类或 `request` 实例，新增模块必须导入其中之一
- `ApiClient` 是静态方法封装（`get/post/put/delete/patch/upload/download`），返回 `ApiResponse<T>`；`request` 是原始 Axios 实例，用于需要直接调用的场景
- 认证 Token 通过请求拦截器自动注入，无需手动添加 Authorization 头
- 两种导出风格共存：对象字面量风格（如 `analysisApi`、`configApi`）和独立函数风格（如 `getCacheStats`、`getJobs`），新增模块建议统一使用对象风格
- `operationLogs.ts` 使用类静态方法风格（`OperationLogsApi`），为历史遗留风格
- `ApiResponse<T>` 标准格式：`{ success: boolean, data: T, message: string, code?: number }`；部分模块使用 `unwrapResponse` 解包为 `Promise<T>`
- 文件下载/导出接口使用原生 `fetch` + `Blob`，不经过 Axios 拦截器
- 股票代码字段正在从 `stock_code` 迁移到 `symbol`，兼容期内两个字段共存

### API 端点约定
- 后端基础路径：`/api/`
- 认证：`/api/auth/*`
- 分析：`/api/analysis/*`
- 配置：`/api/config/*`
- 系统：`/api/system/*`
- 数据同步：`/api/sync/*`、`/api/stock-sync/*`
- 市场：`/api/markets/*`
- 自选股：`/api/favorites/*`
- 模拟交易：`/api/paper/*`
- 调度器：`/api/scheduler/*`
- 筛选：`/api/screening/*`
- 标签：`/api/tags/*`
- 模板：`/api/templates/*`
- 使用统计：`/api/usage/*`
- 新闻：`/api/news-data/*`
- 通知：`/api/notifications/*`
- 缓存：`/api/cache/*`
- 模型能力：`/api/model-capabilities/*`

### Testing Requirements
- 无独立单元测试；API 调用正确性依赖后端集成测试
- 前端开发时可通过 `testApiConnection()` 验证后端连通性
- 修改 API 模块后需确认 TypeScript 类型检查通过：`npx vue-tsc --noEmit`

### Common Patterns
- 新增 API 模块：`import { ApiClient } from './request'` → 定义接口类型 → 导出 API 对象
- 调用 API：`const res = await analysisApi.startAnalysis(params)` → `res.data` 获取结果
- 需要跳过认证的请求：`ApiClient.post(url, data, { skipAuth: true })`
- 需要跳过错误弹窗的请求：`ApiClient.get(url, { skipErrorHandler: true })`
- 长时间操作设置超时：`ApiClient.post(url, data, { timeout: 120000 })`
- 文件下载：`ApiClient.download(url, filename)` 或原生 `fetch` + `Blob`

### Dependencies

#### Internal
- `request.ts` → 所有模块的基础依赖
- `@/stores/auth` → Token 获取与刷新（`database.ts`、`operationLogs.ts` 的导出接口）
- `@/stores/app` → 加载状态与语言设置（`request.ts` 拦截器）
- `@/types/analysis` → 分析相关类型定义（`analysis.ts`）
- `@/types/auth` → 认证相关类型定义（`auth.ts`）
- `@/utils/datetime` → 时间格式化（`operationLogs.ts`）
- `@/router` → 401 跳转登录页（`request.ts`）

#### External
- `axios` → HTTP 客户端
- `element-plus` → `ElMessage` 错误提示（`request.ts`）
