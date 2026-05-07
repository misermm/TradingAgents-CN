<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs/faq

## Purpose
TradingAgents 框架常见问题解答，覆盖安装配置、成本控制、技术问题、数据获取、开发扩展和错误处理等主题。

## Key Files

| File | Description |
|------|-------------|
| `faq.md` | 完整 FAQ 文档，16 个问答，涵盖安装依赖冲突、API 密钥、Python 版本、成本估算、性能优化、内存管理、网络问题、数据源、自定义智能体、调试模式等 |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- FAQ 按 6 大类组织：安装配置、成本使用、技术问题、数据分析、开发扩展、错误处理
- Python 版本支持：3.10 / 3.11 / 3.12，推荐 3.11
- 单次分析成本：经济模式 $0.01-0.05，标准模式 $0.05-0.15，高精度模式 $0.10-0.30
- 常见错误类型：API_KEY_INVALID、RATE_LIMIT_EXCEEDED、NETWORK_TIMEOUT、DATA_NOT_FOUND、INSUFFICIENT_MEMORY
- 调试模式：`TradingAgentsGraph(debug=True)` + `logging.basicConfig(level=logging.DEBUG)`

### Testing Requirements
- 文档无需运行测试
- FAQ 中的代码片段可独立验证

### Common Patterns
- 依赖冲突解决：新建虚拟环境 → pip-tools → 逐个安装
- 成本控制：经济模型 + 减少辩论轮次 + 缓存 + 选择性分析师
- 性能优化：并行处理 + 快速模型 + 减少辩论轮次 + 启用缓存
- 网络重试：指数退避装饰器 + 超时设置 + 代理配置
- 自定义扩展：继承 `BaseAnalyst` → 实现 `perform_analysis` → 注册到 config

## Dependencies

### Internal
- `tradingagents/graph/trading_graph.py` - FAQ 示例代码的核心入口
- `tradingagents/default_config.py` - 配置参考
- `tradingagents/agents/analysts/base_analyst.py` - 自定义智能体基类

### External
- `openai` / `finnhub` - API 连接测试
- `langchain-openai` / `langgraph` - 框架依赖

<!-- MANUAL: Custom project notes can be added below -->
