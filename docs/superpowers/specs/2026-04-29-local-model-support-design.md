# LM Studio/Ollama 本地模型支持 + 大师分析模块改进 设计文档

**日期**: 2026-04-29
**状态**: 已批准

## 概述

为项目添加 LM Studio 一级提供商支持，优化 Ollama 的 Docker 环境适配，实现本地模型自动发现功能，同时修复大师分析模块的 Bug 并改进其量化评分体系。

## 第一部分：LM Studio 一级提供商支持

### 1.1 现状分析

- **Ollama**: 已有完整一级提供商支持（`_OPENAI_COMPATIBLE`、`_PROVIDER_CONFIG`、`MODEL_OPTIONS` 等）
- **LM Studio**: 仅在 `provider_keys.py` 中有默认 URL，需通过 `custom_openai` 间接使用

### 1.2 后端注册（6个文件）

| 文件 | 改动内容 |
|------|---------|
| `tradingagents/llm_clients/provider_keys.py` | 添加 `lmstudio` 别名、env_key、默认URL |
| `tradingagents/llm_clients/factory.py` | 将 `lmstudio` 加入 `_OPENAI_COMPATIBLE` |
| `tradingagents/llm_clients/openai_client.py` | 在 `_PROVIDER_CONFIG` 添加 LM Studio 配置 |
| `tradingagents/llm_clients/model_catalog.py` | 在 `MODEL_OPTIONS` 添加 LM Studio 模型选项 |
| `app/models/config.py` | `ModelProvider` 枚举添加 `LMSTUDIO` |
| `app/constants/model_capabilities.py` | 添加 LM Studio 的模型能力定义 |

### 1.3 LM Studio 默认配置

- Base URL: `http://localhost:1234/v1`（本地）/ `http://host.docker.internal:1234/v1`（Docker）
- API Key: 无需（硬编码 `"lmstudio"`）
- 模型列表: 通过 `/v1/models` API 动态获取

### 1.4 本地模型自动发现 API

新增后端 API 端点：`GET /api/local-models/scan`

扫描逻辑：
1. 检测是否在 Docker 容器内（检查 `/.dockerenv` 文件或环境变量）
2. 根据环境选择 base URL（localhost vs host.docker.internal）
3. 并行请求 Ollama `GET /v1/models` 和 LM Studio `GET /v1/models`
4. 返回发现的模型列表

返回格式：
```json
{
  "ollama": {
    "available": true,
    "base_url": "http://localhost:11434/v1",
    "models": [{"id": "llama3.1", "object": "model"}]
  },
  "lmstudio": {
    "available": true,
    "base_url": "http://localhost:1234/v1",
    "models": [{"id": "qwen2.5-7b", "object": "model"}]
  }
}
```

### 1.5 Docker 环境自动适配

在 `provider_keys.py` 的 `default_backend_url()` 中添加环境检测：

```python
def _is_docker():
    return os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER") == "1"
```

Ollama 和 LM Studio 的默认 URL 根据环境自动切换。

### 1.6 前端集成

在配置页面添加"检测本地模型"按钮，点击后调用扫描 API，展示发现的模型，一键选择并自动填充配置。

## 第二部分：大师分析模块改进

### 2.1 Bug 修复

#### Bug 1：条件逻辑节点名称不匹配

**位置**: `tradingagents/graph/conditional_logic.py` 第30行
**问题**: `master_id.replace('_', ' ').title().replace(' ', '')` 生成 `WarrenBuffett`，但 `setup.py` 注册的节点名是 `Warren Buffett`（有空格）
**修复**: 使用与 `setup.py` 相同的 `_get_node_name()` 方法生成节点名

#### Bug 2：`_log_state` 缺少大师报告记录

**位置**: `tradingagents/graph/trading_graph.py` 第1143-1183行
**问题**: 只记录4个常规报告，缺少8个大师报告
**修复**: 在 `_log_state` 中添加大师报告的日志记录

### 2.2 量化评分改进

借鉴 ai-hedge-fund 项目的实现，为每个大师分析师添加专属量化分析函数：

| 大师 | 量化子分析 |
|------|-----------|
| 巴菲特 | 基本面分析 + 一致性分析 + 护城河分析 + 定价权分析 + 内在价值计算 |
| 林奇 | 增长分析 + 基本面分析 + GARP估值（PEG比率） |
| 格雷厄姆 | 盈利稳定性 + 财务实力 + 格雷厄姆估值（Graham Number/Net-Net） |
| 芒格 | 护城河强度 + 管理质量 + 可预测性 |
| 伍德 | 颠覆性潜力 + 创新增长 + 高增长估值 |
| 阿克曼 | 业务质量 + 财务纪律 + 激进主义潜力 |
| 费舍尔 | 增长质量 + 利润率稳定性 + 管理效率 |
| 德鲁肯米勒 | 增长动量 + 情绪分析 + 风险回报 + 内幕活动 |

每个大师的量化分析结果将作为 LLM 推理的输入数据，提升分析质量和稳定性。

## 第三部分：Nginx 启动问题修复

### 3.1 根因

主 `docker-compose.yml` 不包含 Nginx 服务，需要使用 `docker-compose.hub.nginx.yml`。

### 3.2 修复方案

在 `docker-compose.yml` 中添加 Nginx 服务定义，从 `docker-compose.hub.nginx.yml` 迁移关键配置。

## 实施优先级

1. **P0**: LM Studio 一级提供商注册（后端6文件）
2. **P0**: 修复大师分析模块 Bug（节点名称 + 日志）
3. **P1**: 本地模型自动发现 API
4. **P1**: Docker 环境自动适配
5. **P1**: 前端本地模型扫描集成
6. **P2**: 大师分析模块量化评分改进
7. **P2**: Nginx 启动问题修复
