# TradingAgents-CN 渐进式优化设计文档

**日期**: 2026-05-02
**版本**: v1.0
**状态**: 待审核
**范围**: 仅免费数据源（AKShare + BaoStock + yfinance），付费数据源暂不涉及

---

## 1. 背景与目标

### 1.1 项目现状

TradingAgents-CN v1.0.1 已完成32轮开发迭代，5轮全面Bug修复（累计50+个Bug），13位投资大师集成，AKShare免费数据源增强。但系统在免费数据源下的端到端可用性仍不稳定，存在以下核心问题：

- **数据可靠性**：AKShare/BaoStock网络波动导致分析失败，无健壮重试/熔断机制
- **LLM工具调用**：DeepSeek适配器invoke()绕过LangChain工具调用编排，可能导致工具不执行
- **缓存策略**：三个缓存系统键格式/TTL/失效策略不统一
- **数据标准化**：各Provider返回DataFrame格式不一致，缺少统一标准化层
- **测试覆盖**：LLM客户端层、图执行引擎、数据源统一接口等核心模块零测试覆盖

### 1.2 优化目标

按稳定性→性能→可维护性三步走，使免费数据源下分析流程端到端稳定可用，并逐步提升系统性能和可维护性。

### 1.3 约束

- 仅关注免费数据源：AKShare(A股/港股)、BaoStock(A股)、yfinance(美股/港股)
- 付费数据源(Tushare/Alpha Vantage/Finnhub等)暂不涉及，但降级链路保留
- 所有改动需Docker镜像构建验证通过
- 每个Phase完成后验证再进入下一个Phase

---

## 2. Phase 1：稳定性 — 免费数据源下分析流程端到端可用

### 2.1 统一HTTP客户端封装（ResilientHttpClient）

**问题**：8个数据源Provider各自实现HTTP调用，重试/超时/限速逻辑不一致，4个Provider完全没有重试和超时。

**新增文件**：`tradingagents/dataflows/providers/resilient_http_client.py`

**ResilientHttpClient** 核心能力：

| 能力 | 实现 | 默认值 |
|------|------|--------|
| 重试 | tenacity `@retry` 装饰器 | 3次，指数退避(1s/2s/4s) |
| 超时 | httpx `timeout` 参数 | 连接10s，读取30s |
| 限速 | `asyncio.Semaphore` + 间隔控制 | 可配置，默认1 req/s |
| 熔断 | 简易CircuitBreaker类 | 单次请求5次失败→熔断30s→半开探测 |
| 降级判断 | 返回Result对象(success/data/error) | 替代字符串匹配`"❌"` |

**CircuitBreaker状态机**：

```
CLOSED ──(失败达阈值)──→ OPEN ──(冷却期后)──→ HALF_OPEN
   ↑                                              │
   └────────────(探测成功)─────────────────────────┘
   └────────────(探测失败)──→ OPEN
```

**Result对象**：

```python
@dataclass
class DataSourceResult:
    success: bool
    data: Optional[Any] = None  # str(文本数据) 或 DataFrame(结构化数据)
    error: Optional[str] = None
    source: str = ""
    latency_ms: float = 0
    from_cache: bool = False
```

**集成方式**：
- `akshare.py`：monkey-patch requests.get改为使用ResilientHttpClient
- `baostock.py`：login/query操作包装超时和重试
- `yfinance.py`：ticker.history()包装超时
- `data_source_manager.py`：`_get_*_data()`方法添加整体超时

**依赖**：`tenacity`（项目已使用，google_news.py中有引用）、`httpx`（项目已安装）

### 2.2 数据源健康状态跟踪与熔断冷却

**问题**：DataSourceManager无数据源健康状态跟踪，故障数据源每次请求仍先尝试，浪费时间和资源。

**新增类**：在`data_source_manager.py`中添加`SourceHealthTracker`

```python
@dataclass
class SourceHealth:
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    circuit_state: str = "closed"  # closed/open/half_open
    cooldown_until: float = 0
    total_calls: int = 0
    total_failures: int = 0

class SourceHealthTracker:
    _health_status: Dict[str, SourceHealth]
    
    def is_available(self, source_name: str) -> bool
    def record_success(self, source_name: str) -> None
    def record_failure(self, source_name: str) -> None
    def get_available_sources(self, market: str) -> List[str]
```

**行为规则**（数据源级别，与HTTP级别CircuitBreaker不同）：
- 连续3次失败 → 熔断(circuit_state=open)，跳过该数据源
- 熔断后30s进入半开状态(half_open)，允许1次探测
- 探测成功 → 恢复(closed)；探测失败 → 继续熔断(再等30s)
- 成功调用 → 重置consecutive_failures为0

注：ResilientHttpClient的CircuitBreaker是HTTP请求级别的（单次请求5次重试失败后熔断），SourceHealthTracker是数据源级别的（跨请求3次连续失败后熔断），两者互补。

**集成点**：`_get_data_source_priority_order()`返回数据源列表时，通过`SourceHealthTracker.get_available_sources()`过滤掉熔断状态的数据源。

### 2.3 DeepSeek invoke() 工具调用修复

**问题**：`deepseek_adapter.py`的`invoke()`方法重写了LangChain标准流程，直接调用`_generate()`返回AIMessage，绕过了工具调用编排，导致工具调用可能不执行。

**修复方案**：

1. 删除`deepseek_adapter.py` L231-L262的`invoke()`方法重写
2. 保留`_estimate_input_tokens()`和`_estimate_output_tokens()`作为内部方法
3. Token追踪改为在`_generate()`中处理（已有逻辑）
4. 添加工具调用验证：在`_generate()`返回后检查`tool_calls`字段是否存在且格式正确

**风险缓解**：
- DeepSeek已通过OpenAI兼容接口(`https://api.deepseek.com`)调用，理论上应兼容LangChain标准工具调用流程
- 修复前添加mock单元测试验证工具调用行为
- 修复后运行完整分析流程验证

### 2.4 端到端验证

**问题**：真实股票代码完整分析流程未验证，无法确认免费数据源下系统是否可用。

**新增文件**：`tests/e2e/test_free_source_analysis.py`

**测试场景**：

| 测试场景 | 数据源 | 股票 | 验证内容 |
|---------|--------|------|---------|
| A股完整分析 | AKShare+BaoStock | 600519(茅台) | 数据获取→大师分析→报告生成 |
| A股降级测试 | BaoStock only | 000001(平安) | AKShare失败→BaoStock降级 |
| 美股完整分析 | yfinance | AAPL | 数据获取→大师分析→报告生成 |
| 港股完整分析 | AKShare+yfinance | 00700(腾讯) | 数据获取→报告生成 |

**验证标准**：
- 所有数据获取方法返回非空结果
- 降级链路正确触发
- 报告包含预期字段（decision/risk_level/key_points）
- 无未捕获异常

**Phase 1 交付物**：
1. `resilient_http_client.py` — 统一HTTP客户端
2. `SourceHealthTracker` — 数据源健康跟踪
3. `deepseek_adapter.py` 修复 — 删除invoke()重写
4. `test_free_source_analysis.py` — 端到端验证测试
5. 更新DEV_PROGRESS.md

**Phase 1 验证标准**：
- Docker镜像构建成功
- 免费数据源下(AKShare+BaoStock+yfinance)分析流程端到端可用
- 数据源故障时自动降级，不阻塞分析流程
- DeepSeek模型工具调用正常执行

---

## 3. Phase 2：性能优化 — 提升分析速度和资源利用率

### 3.1 统一缓存键/TTL策略

**问题**：三个缓存系统使用完全不同的键格式，同一份数据在不同缓存中无法互相查找；TTL策略不一致。

**统一缓存键格式**：`{market}:{data_type}:{symbol}:{params_hash}`

| 字段 | 说明 | 示例 |
|------|------|------|
| market | 市场 | `cn`, `us`, `hk` |
| data_type | 数据类型 | `stock_data`, `fundamentals`, `news`, `financial` |
| symbol | 股票代码 | `600519`, `AAPL`, `00700` |
| params_hash | 参数指纹(12位) | `a1cc6e9ff077` |

**统一TTL策略**：

| 数据类型 | A股TTL | 美股TTL | 理由 |
|---------|--------|---------|------|
| 实时行情 | 5分钟 | 5分钟 | 交易时段需频繁更新 |
| 历史K线 | 4小时 | 4小时 | 日频更新，非交易时段可长缓存 |
| 基本面数据 | 12小时 | 24小时 | 季报更新，A股财报更频繁 |
| 新闻数据 | 2小时 | 4小时 | 新闻时效性 |
| 财务报表 | 24小时 | 48小时 | 季报更新，变化慢 |
| 证券基本信息 | 7天 | 7天 | 极少变化 |

**实施方式**：
1. 在`CacheConfig`类中统一定义TTL映射表
2. 三个缓存系统共享同一个键生成函数`generate_cache_key()`
3. 迁移期间保持旧键兼容（读取时同时查旧键和新键）

### 3.2 AKShare/BaoStock启用缓存

**问题**：当前只有Tushare数据源使用了`_get_cached_data()`，AKShare和BaoStock每次都重新获取数据。

**设计**：在DataSourceManager中为所有数据源启用缓存

```python
async def _get_akshare_data(self, ...):
    cached = self._get_cached_data(cache_key)
    if cached and not cached.startswith("❌"):
        return cached
    result = await self._fetch_akshare_data(...)
    if result and "❌" not in result:
        self._save_to_cache(cache_key, result)
    return result
```

**关键点**：
- 缓存键使用Phase 2.1的统一格式
- 缓存读取时检查数据质量（非空、非错误标记）
- MongoDB缓存适配器优先（已有数据时直接返回）

### 3.3 数据标准化层（unified_dataframe.py）

**问题**：各Provider返回DataFrame列名/类型/单位不一致，测试文件已引用该模块但文件不存在。

**新增文件**：`tradingagents/dataflows/unified_dataframe.py`

**核心功能**：

| 功能 | 说明 |
|------|------|
| 列名标准化 | `Volume→vol`, `日期→date`, `开盘→open` 等统一映射 |
| 数据类型标准化 | `date`列统一为datetime，数值列统一为float |
| 单位标准化 | 市值统一为亿元，金额统一为万元 |
| 数据验证 | 非空检查、范围检查、类型检查 |
| 缺失值处理 | 前向填充/默认值/NaN标记 |

**统一列名映射**（标准化后统一使用英文列名，便于代码处理；显示层可按需转为中文）：

```python
STANDARD_COLUMNS = {
    "date": "日期", "open": "开盘价", "high": "最高价",
    "low": "最低价", "close": "收盘价", "vol": "成交量",
    "amount": "成交额", "pct_change": "涨跌幅",
    "turnover": "换手率", "pe": "市盈率", "pb": "市净率",
    "market_cap": "总市值(亿)", "circulating_market_cap": "流通市值(亿)",
}
# 标准化后DataFrame列名为英文key（date/open/high/low/close/vol/...）
# 中文value仅用于显示映射
```

**集成方式**：
1. 各Provider返回原始DataFrame
2. DataSourceManager的`_standardize_dataframe()`调用UnifiedDataFrame标准化
3. 标准化后的数据写入缓存和MongoDB
4. 下游代码只需处理标准格式

### 3.4 MongoDB TTL索引

**问题**：MongoDB缓存集合的`expires_at`字段只是文档属性，不会自动删除过期数据。

**设计**：为MongoDB缓存集合添加TTL索引

```javascript
db.stock_data_cache.createIndex(
    { "expires_at": 1 },
    { expireAfterSeconds: 0 }
)
```

**影响集合**：`stock_data_cache`、`fundamentals_cache`、`news_cache`

**注意事项**：
- TTL索引在MongoDB后台线程每60秒清理一次
- 需确保`expires_at`字段为UTC时间的BSON Date类型
- 已有文档如果`expires_at`格式不正确需要迁移

**Phase 2 交付物**：
1. `CacheConfig` + `generate_cache_key()` — 统一缓存键/TTL
2. DataSourceManager缓存启用 — AKShare/BaoStock缓存支持
3. `unified_dataframe.py` — 数据标准化层
4. MongoDB TTL索引脚本
5. 更新DEV_PROGRESS.md

**Phase 2 验证标准**：
- 同一股票二次分析时缓存命中率>80%
- 数据标准化后各Provider输出格式一致
- MongoDB过期数据自动清理
- 分析速度提升（缓存命中时减少50%+数据获取时间）

---

## 4. Phase 3：可维护性 — 降低后续开发成本

### 4.1 LLM适配器统一到OpenAICompatibleBase

**问题**：两套并行适配器体系——独立文件和统一基类功能重复，行为不一致。

**迁移计划**：

| 现有适配器 | 迁移目标 | 关键差异处理 |
|-----------|---------|-------------|
| `ChatDeepSeek` (deepseek_adapter.py) | `ChatDeepSeekOpenAI` (openai_compatible_base.py) | 保留`_estimate_*_tokens()`方法，invoke()已在Phase 1删除 |
| `ChatDashScopeOpenAI` (dashscope_openai_adapter.py) | `ChatDashScopeOpenAIUnified` (openai_compatible_base.py) | 保留Token追踪逻辑，补充估算降级 |

**工厂方法更新**：
- `factory.py`中的`create_llm_client()`统一使用`OpenAICompatibleBase`子类
- 删除对独立适配器文件的导入

**风险控制**：
- 迁移前为现有适配器添加mock单元测试，确保行为不变
- 迁移后运行完整测试套件验证
- 保留独立文件1个版本周期作为回退

### 4.2 核心模块Mock单元测试

**问题**：LLM客户端层、图执行引擎、数据源统一接口等核心模块零测试覆盖。

**第一批：LLM客户端层**

| 模块 | 测试文件 | 测试内容 |
|------|---------|---------|
| `factory.py` | `test_llm_factory.py` | 各Provider客户端创建、参数传递、降级 |
| `openai_compatible_base.py` | `test_openai_compatible_base.py` | Token追踪、消息格式、工具调用 |
| `provider_keys.py` | `test_provider_keys.py` | API Key读取优先级、Docker环境检测 |
| `validators.py` | `test_validators.py` | 模型名验证、Provider验证 |

**第二批：数据源层**

| 模块 | 测试文件 | 测试内容 |
|------|---------|---------|
| `interface.py` | `test_data_interface.py` | 统一接口函数、降级逻辑、错误处理 |
| `data_source_manager.py` | `test_data_source_manager.py` | 优先级排序、降级链路、健康跟踪 |
| `resilient_http_client.py` | `test_resilient_http.py` | 重试、超时、熔断、限速 |
| `unified_dataframe.py` | `test_unified_dataframe.py` | 列名映射、类型转换、单位标准化 |

**第三批：图执行层**

| 模块 | 测试文件 | 测试内容 |
|------|---------|---------|
| `setup.py` | `test_graph_setup.py` | 节点注册、边构建、条件路由 |
| `propagation.py` | `test_propagation.py` | 状态初始化、动态字段 |
| `conditional_logic.py` | `test_conditional_logic.py` | should_continue逻辑、大师路由 |

### 4.3 conftest.py公共Fixture

**问题**：测试文件各自mock，大量重复代码；无公共测试基础设施。

**新增fixture**：

```python
# LLM Mock
@pytest.fixture
def mock_llm_client(): ...

@pytest.fixture
def mock_tool_call_response(): ...

# 数据源 Mock
@pytest.fixture
def mock_akshare_provider(): ...

@pytest.fixture
def mock_baostock_provider(): ...

@pytest.fixture
def mock_yfinance_provider(): ...

# 数据库 Mock
@pytest.fixture
def mock_mongo_db(): ...

@pytest.fixture
def mock_redis_client(): ...

# 测试数据工厂
@pytest.fixture
def sample_stock_data(): ...

@pytest.fixture
def sample_analysis_state(): ...
```

### 4.4 配置读取路径统一

**问题**：tradingagents层绕过ConfigService直接读取MongoDB，配置读取路径不统一。

**统一配置读取优先级**：`数据库配置 > 环境变量 > 默认值`

**统一入口**：通过`ConfigManager`（已有）统一读取，tradingagents层不再直接访问MongoDB。

**具体改动**：

| 现有路径 | 统一后 |
|---------|--------|
| `DataSourceManager._get_datasource_configs_from_db()` 直接读MongoDB | → 调用`ConfigManager.get_datasource_configs()` |
| `MongoDBCacheAdapter._get_data_source_priority_order()` 直接读MongoDB | → 调用`ConfigManager.get_datasource_priority()` |
| `runtime_settings.use_app_cache_enabled()` 读环境变量 | → 调用`ConfigManager.get_cache_config()` |

**ConfigManager扩展**：
- 添加缓存层（内存缓存+TTL），避免每次请求都查数据库
- 添加配置变更通知机制（可选，后续扩展）

**Phase 3 交付物**：
1. 统一LLM适配器 — 删除独立适配器文件，统一到OpenAICompatibleBase
2. 核心模块mock单元测试 — 第一批(LLM层)+第二批(数据源层)
3. `conftest.py`公共fixture
4. 配置读取路径统一
5. 更新DEV_PROGRESS.md

**Phase 3 验证标准**：
- LLM适配器统一后所有Provider行为不变
- 核心模块测试覆盖率>60%（LLM层+数据源层）
- 所有测试通过`pytest -m "not integration"`
- 配置读取路径统一，无直接MongoDB访问

---

## 5. 已知Bug清单（免费数据源相关）

### 5.1 P0 严重Bug

| # | Bug | 文件 | 说明 |
|---|-----|------|------|
| 1 | 数据源无重试机制 | akshare.py/baostock.py/yfinance.py | 一次失败直接返回错误，无重试 |
| 2 | 数据源无超时控制 | baostock.py/yfinance.py | bs.login()/ticker.history()可能无限阻塞 |
| 3 | DeepSeek invoke()绕过工具调用 | deepseek_adapter.py | 工具调用可能不执行 |
| 4 | 无数据源健康跟踪 | data_source_manager.py | 故障数据源每次仍先尝试 |

### 5.2 P1 中等Bug

| # | Bug | 文件 | 说明 |
|---|-----|------|------|
| 5 | 缓存键格式不统一 | file_cache/db_cache/adaptive.py | 三个系统三种格式 |
| 6 | TTL策略不一致 | 各缓存实现 | 文件缓存区分市场，Redis不区分 |
| 7 | AKShare/BaoStock不使用缓存 | data_source_manager.py | 每次重新获取数据 |
| 8 | unified_dataframe.py缺失 | tradingagents/dataflows/ | 测试引用但文件不存在 |
| 9 | MongoDB缓存无自动过期 | mongodb_cache_adapter.py | expires_at字段不触发自动删除 |
| 10 | 降级判断条件脆弱 | data_source_manager.py | 用"❌"字符串匹配判断成功 |
| 11 | 两套并行适配器体系 | llm_adapters/ | 维护成本高，行为不一致 |
| 12 | 配置读取路径不统一 | data_source_manager.py/runtime_settings.py | 绕过ConfigService直接读MongoDB |

### 5.3 P2 低优先级

| # | Bug | 文件 | 说明 |
|---|-----|------|------|
| 13 | DashScope无Token估算降级 | dashscope_openai_adapter.py | Token追踪可能丢失 |
| 14 | 前端设置不持久化 | SingleAnalysis.vue | 只保存到Pinia store |
| 15 | 测试目录混入调试脚本 | tests/ | 200+文件中仅~30个是真正测试 |
| 16 | conftest.py无公共fixture | tests/conftest.py | 每个测试文件自行mock |

---

## 6. 免费数据源能力矩阵

| 数据源 | 市场 | 核心能力 | 已知限制 |
|--------|------|---------|---------|
| AKShare | A股/港股 | K线/行情/财务/新闻/基本面 | 依赖东方财富接口，反爬风险 |
| BaoStock | A股 | 历史K线/基本面 | 无实时行情，login偶尔失败 |
| yfinance | 美股/港股 | K线/行情/基本面 | 非官方API，可能被封 |
| Google News | 全球 | 新闻 | 无结构化数据 |
| 中国财经聚合 | A股 | 新闻 | 覆盖有限 |

---

## 7. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| ResilientHttpClient引入新Bug | 中 | 高 | 逐个Provider迁移，每步验证 |
| DeepSeek删除invoke()后工具调用异常 | 低 | 高 | 修复前添加mock测试，修复后端到端验证 |
| 缓存键迁移导致旧缓存失效 | 中 | 低 | 迁移期兼容旧键，逐步切换 |
| LLM适配器统一后行为变化 | 中 | 高 | 迁移前添加mock测试，保留回退1个版本 |
| MongoDB TTL索引影响性能 | 低 | 低 | 监控索引大小，必要时调整 |

---

## 8. 不在范围内

- 付费数据源(Tushare/Alpha Vantage/Finnhub)的优化
- 前端UI改进
- 新功能开发
- CI/CD流水线搭建
- 国际化/多语言支持
