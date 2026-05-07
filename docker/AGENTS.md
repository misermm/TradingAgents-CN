<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docker

## Purpose
Docker 辅助配置目录，存放前端容器内使用的 Nginx 配置文件，用于 SPA 静态资源服务与 API 反向代理。

## Key Files

| File | Description |
|------|-------------|
| `nginx.conf` | 前端容器 Nginx 配置：SPA 路由回退、API 代理、静态资源缓存策略 |

## For AI Agents

### Working In This Directory
- 此配置用于前端 Docker 镜像（`Dockerfile.frontend`）内的 Nginx
- 与 `nginx/nginx.conf`（生产网关）不同，本配置专注于前端容器内的 SPA 服务
- 上游服务：`backend:8000`

### Configuration Highlights
- **SPA 回退**：`try_files $uri $uri/ /index.html`，支持 Vue Router history 模式
- **API 代理**：`/api/` → `http://backend:8000/api/`，支持 WebSocket
- **静态资源缓存**：JS/CSS 缓存 1 年（immutable），图片/字体缓存 1 年
- **index.html 不缓存**：确保用户始终获取最新版本
- **安全头**：与生产网关配置一致
- **Gzip 压缩**：启用，最小 1024 字节
- **健康检查**：`/health` → `http://backend:8000/api/health`

### Common Patterns
- 修改缓存策略：调整 `expires` 和 `Cache-Control` 指令
- 添加新路由：在 `location /` 之前添加新的 location 块

## Dependencies

### Internal
- `Dockerfile.frontend` - 将此配置复制到前端镜像
- `app/` - 后端 API 服务（代理目标）

<!-- MANUAL: Custom project notes can be added below -->
