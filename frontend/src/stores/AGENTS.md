<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# stores

## Purpose
Pinia 状态管理层，管理应用全局状态、用户认证和实时通知。基于 Pinia + `@vueuse/core` 的 `useStorage` 实现状态持久化到 localStorage。

## Key Files

| File | Description |
|------|-------------|
| `app.ts` | 应用全局状态：主题/语言/侧边栏/用户偏好/API 连接检测/加载进度 |
| `auth.ts` | 认证状态：登录/注册/登出/Token 刷新/权限管理/用户信息同步 |
| `notifications.ts` | 通知状态：WebSocket 实时推送/通知列表/未读计数/自动重连 |

## For AI Agents

### Working In This Directory
- 新增 store：使用 `defineStore` 创建，Options API 或 Composition API 均可
- 持久化：使用 `@vueuse/core` 的 `useStorage` 包装需要持久化的字段
- 循环依赖：store 之间使用动态 `import()` 避免循环引用（如 auth → notifications、auth → app）
- Token 验证：auth store 初始化时自动校验 JWT 格式（3段式）并清除无效/mock token

### Testing Requirements
- 使用 Pinia 的 `createTestingPinia` 进行单元测试
- mock API 调用：`authApi`、`notificationsApi` 等

### Common Patterns
- 应用状态持久化：`useStorage('key', defaultValue)` → localStorage 自动同步
- 认证流程：`login()` → `setAuthInfo()` → `syncUserPreferencesToAppStore()` → `setupTokenRefreshTimer()`
- WebSocket 通知：`connect()` → `connectWebSocket()` → 指数退避重连（最大 10 次）
- Token 自动刷新：`setupTokenRefreshTimer()` 每分钟检查 → `autoRefreshToken()` → `refreshAccessToken()`

## Dependencies

### Internal
- `@/api/auth` - 认证 API 接口
- `@/api/notifications` - 通知 API 接口
- `@/types/auth` - 认证相关类型定义
- `@/utils/auth` - Token 工具函数

### External
- Pinia - 状态管理
- @vueuse/core - `useStorage` 响应式持久化
- Element Plus - `ElMessage` 消息提示

<!-- MANUAL: Custom project notes can be added below -->
