<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# tests/e2e

## Purpose
端到端测试，验证免费数据源下分析流程的稳定性、性能优化和可维护性改进。

## Key Files

| File | Description |
|------|-------------|
| `test_free_source_analysis.py` | Phase 1 端到端验证：ResilientHttpClient 重试/超时/熔断、SourceHealthTracker 健康跟踪、DeepSeek invoke() 修复、免费数据源基本可用性 |
| `test_phase2_performance.py` | Phase 2 性能优化：统一缓存键/TTL 生成、市场检测（CN/HK/US）、DataFrame 标准化（列名/类型/派生列/缺失值/单位） |
| `test_phase3_maintainability.py` | Phase 3 可维护性：LLM 适配器统一（别名/向后兼容/Token 估算）、Provider 密钥管理、缓存配置与 DataSourceManager 集成、健康跟踪器降级链路 |

## For AI Agents

### Working In This Directory
- Phase 1 测试分两类：单元级（Mock）和集成级（@pytest.mark.integration，需网络）
- Phase 2 测试覆盖 `cache_config` 和 `unified_dataframe` 两个核心模块
- Phase 3 测试验证适配器别名关系（ChatDeepSeek = ChatDeepSeekOpenAI）和跨模块集成
- 集成测试默认跳过，需 `-m integration` 标记运行

### Testing Requirements
- 运行单元测试：`python -m pytest tests/e2e/ -v -m "not integration"`
- 运行集成测试：`python -m pytest tests/e2e/ -m integration -v`
- 集成测试需要网络连接和真实数据源

### Common Patterns
- `ResilientHttpClient` + `CircuitBreaker`：重试/熔断/半开状态机
- `SourceHealthTracker`：连续失败计数 → 熔断 → 冷却恢复
- `DataSourceResult`：统一成功/失败结果对象
- 缓存键格式：`{market}:{type}:{symbol}:{hash}`
- DataFrame 标准化管线：列名映射 → 类型转换 → 派生列 → 缺失值填充 → 单位标准化

## Dependencies

### Internal
- `tradingagents.dataflows.providers.resilient_http_client` - 弹性 HTTP 客户端
- `tradingagents.dataflows.data_source_manager` - 数据源管理器
- `tradingagents.dataflows.cache.cache_config` - 缓存配置
- `tradingagents.dataflows.unified_dataframe` - 统一 DataFrame
- `tradingagents.llm_adapters` - LLM 适配器
- `tradingagents.llm_clients.provider_keys` - Provider 密钥管理

### External
- pytest - 测试框架
- pandas / numpy - 数据处理
- LLM 适配器依赖（langchain-openai 等，可选）

<!-- MANUAL: Custom project notes can be added below -->
