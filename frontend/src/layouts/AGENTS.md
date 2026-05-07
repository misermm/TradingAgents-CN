<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# layouts

## Purpose
页面布局组件，定义应用的侧边栏 + 顶栏 + 主内容区 + 页脚的经典后台布局结构，支持响应式移动端适配。

## Key Files

| File | Description |
|------|-------------|
| `BasicLayout.vue` | 基础布局：侧边栏（可折叠）+ 顶部导航栏 + 主内容区 + 页脚，含路由过渡动画和 keep-alive 缓存 |

## For AI Agents

### Working In This Directory
- 布局结构：固定侧边栏（z-index: 1000）+ 粘性顶栏（z-index: 999）+ 弹性主内容区
- 移动端适配：`width < 768px` 时侧边栏自动折叠，点击蒙层收起，路由切换自动收起
- 组件缓存：`keep-alive` 缓存 Dashboard / StockScreening / AnalysisHistory / QueueManagement
- 路由动画：`<transition>` 根据 `route.meta.transition` 切换动画（fade / slide-left / slide-up）
- 侧边栏宽度：展开 240px（可调 200-400），折叠 64px

### Testing Requirements
- 响应式测试：验证不同屏幕宽度下侧边栏行为
- 组件交互：测试侧边栏折叠/展开、移动端蒙层点击

### Common Patterns
- 布局组件导入：`SidebarMenu` / `UserProfile` / `Breadcrumb` / `HeaderActions` / `AppFooter` 均来自 `@/components/Layout/`
- 状态驱动：侧边栏状态由 `appStore.sidebarCollapsed` 和 `appStore.actualSidebarWidth` 控制
- 移动端判断：`useWindowSize()` 的 `width < 768`

## Dependencies

### Internal
- `@/stores/app` - 应用状态（侧边栏、主题）
- `@/components/Layout/SidebarMenu.vue` - 侧边栏菜单
- `@/components/Layout/UserProfile.vue` - 用户信息
- `@/components/Layout/Breadcrumb.vue` - 面包屑导航
- `@/components/Layout/HeaderActions.vue` - 顶栏操作区
- `@/components/Layout/AppFooter.vue` - 页脚

### External
- Vue 3 - Composition API
- Element Plus - `el-backtop` 回到顶部、`Expand`/`Fold` 图标
- @vueuse/core - `useWindowSize` / `useRoute`

<!-- MANUAL: Custom project notes can be added below -->
