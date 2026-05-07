<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# nginx

## Purpose
生产环境 Nginx 反向代理配置，作为 Docker Compose 部署的统一入口网关，负责前端静态资源代理、后端 API 转发、WebSocket 支持与安全头设置。

## Key Files

| File | Description |
|------|-------------|
| `nginx.conf` | 生产环境 Nginx 主配置文件 |

## For AI Agents

### Working In This Directory
- 此配置用于 `docker-compose.yml` 生产部署
- 上游服务：`backend:8000`（后端 API）、`frontend:80`（前端静态）
- 监听端口：80

### Configuration Highlights
- **安全头**：X-Content-Type-Options、X-Frame-Options、X-XSS-Protection、CSP
- **API 代理**：`/api/` → `http://backend:8000/api/`，禁用缓存，支持 WebSocket
- **WebSocket 超时**：`proxy_send_timeout` / `proxy_read_timeout` 设为 3600s（1 小时）
- **健康检查**：`/health` → `http://backend/api/health`
- **前端代理**：`/` → `http://frontend:80`
- **Gzip 压缩**：启用，最小 1024 字节
- **上传限制**：`client_max_body_size 100M`
- **缓冲区**：`proxy_buffer_size 128k`、`proxy_buffers 4 256k`

### Common Patterns
- 修改代理目标：调整 `upstream backend` 和 `proxy_pass` 指令
- 添加 SSL：在 server 块中增加 listen 443 ssl 配置

## Dependencies

### Internal
- `docker-compose.yml` - 引用此配置启动 Nginx 容器
- `app/` - 后端 API 服务
- `frontend/` - 前端静态资源服务

<!-- MANUAL: Custom project notes can be added below -->
