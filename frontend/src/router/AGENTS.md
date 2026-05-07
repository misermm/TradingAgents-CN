<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# router

## Purpose
Vue Router 路由配置，定义所有页面路由、导航守卫和页面切换动画。使用 HTML5 History 模式，NProgress 进度条指示路由切换。

## Key Files

| File | Description |
|------|-------------|
| `index.ts` | 路由定义、全局前置/后置守卫、NProgress 配置、认证拦截 |

## For AI Agents

### Working In This Directory
- 新增页面：在 `routes` 数组中添加路由配置，使用 `BasicLayout` 作为布局组件
- 认证保护：设置 `meta.requiresAuth: true` 标记需要登录的页面
- 菜单控制：`meta.hideInMenu: true` 隐藏菜单项，`meta.icon` 设置 Element Plus 图标
- 页面动画：`meta.transition` 设置过渡动画名（fade / slide-up / slide-left）
- 重定向：`/queue` → `/tasks`，`/analysis/history` → `/tasks?tab=completed`，`/paper/:name.md` → 学习中心文章

### Testing Requirements
- 路由守卫测试：mock `useAuthStore` 验证认证拦截逻辑
- 路由配置测试：验证所有路由的 `meta` 属性和组件懒加载

### Common Patterns
- 页面路由模式：`{ path, name, component: () => import('@/views/X/index.vue'), meta: { title, requiresAuth, icon } }`
- 嵌套路由：父路由使用 `BasicLayout`，子路由为实际页面组件
- 守卫流程：`beforeEach` → NProgress.start → 认证检查 → 设置页面标题 → `afterEach` → NProgress.done

## Dependencies

### Internal
- `@/stores/auth` - 认证状态（路由守卫）
- `@/stores/app` - 应用状态（当前路由、页面标题）
- `@/layouts/BasicLayout.vue` - 基础布局组件

### External
- Vue Router - 路由管理
- NProgress - 路由切换进度条
- Element Plus - `ElMessage` 错误提示

<!-- MANUAL: Custom project notes can be added below -->
