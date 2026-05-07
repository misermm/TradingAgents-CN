<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# frontend

## Purpose
Vue 3 前端应用 (专有许可证，商用需授权)。基于 Vite + Element Plus 构建，提供股票分析仪表盘、报告查看、股票筛选、数据同步、系统设置等功能界面。

## Key Files

| File | Description |
|------|-------------|
| `package.json` | 前端依赖与脚本配置 |
| `vite.config.ts` | Vite 构建配置 |
| `tsconfig.json` | TypeScript 配置 |
| `index.html` | HTML 入口模板 |
| `env.d.ts` | 环境变量类型声明 |
| `.eslintrc.cjs` | ESLint 规则 |
| `.prettierrc.json` | Prettier 格式化配置 |
| `LICENSE` | 专有许可证文件 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/` | 源代码目录 (see `src/AGENTS.md`) |
| `public/` | 静态资源：图片、SVG、manifest |

## For AI Agents

### Working In This Directory
- 专有许可证模块，商用需联系 hsliup@163.com
- 包管理器：yarn (存在 .yarnrc)
- 开发服务器：`yarn dev` 或 `npm run dev`
- 构建：`yarn build` 或 `npm run build`
- 代码风格：ESLint + Prettier
- API 请求通过 `src/api/request.ts` 统一封装

### Testing Requirements
- 运行测试：`yarn test` 或 `npm run test`
- 类型检查：`vue-tsc --noEmit`

### Common Patterns
- 页面开发：在 `src/views/` 创建 Vue 组件 → 在 `src/router/` 注册路由
- API 调用：在 `src/api/` 定义接口 → 在组件中调用
- 状态管理：Pinia store 在 `src/stores/` 定义
- 组件复用：在 `src/components/` 创建共享组件

## Dependencies

### Internal
- `app/` - 后端 API，前端通过 HTTP 请求调用

### External
- Vue 3 - 前端框架
- Vite - 构建工具
- Element Plus - UI 组件库
- Vue Router - 路由管理
- Pinia - 状态管理
- Axios - HTTP 请求
- TypeScript - 类型安全
- SCSS - 样式预处理

<!-- MANUAL: Custom project notes can be added below -->
