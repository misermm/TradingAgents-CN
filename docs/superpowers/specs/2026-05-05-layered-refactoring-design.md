# TradingAgents-CN 分层重构优化设计文档

**日期**: 2026-05-05
**版本**: v3.0
**状态**: 待审核
**范围**: 仅免费数据源，付费数据源暂不涉及
**方案**: 方案B — 分层重构（稳定性→架构→性能→可维护性）

---

## 1. 背景与目标

### 1.1 项目现状

TradingAgents-CN v1.0.1 已完成53轮开发迭代，13位投资大师集成，免费数据源增强。但系统在免费数据源下的端到端可用性仍不稳定，且存在架构层面的问题影响长期维护。

### 1.2 核心问题

| # | 问题 | 严重度 | 类别 |
|---|------|--------|------|
| 1 | LangGraph并行大师节点数据竞争，后完成节点覆盖先完成节点的报告 | 🔴 P0 | 稳定性 |
| 2 | AKShare依赖东方财富单一接口，反爬/限流频繁 | 🔴 P0 | 稳定性 |
| 3 | BaoStock每次login/logout，login偶发失败 | 🟡 P1 | 稳定性 |
| 4 | 免费数据源财务数据不完整（缺ROE/PE/PB等） | 🟡 P1 | 准确性 |
| 5 | 所有数据源失败时无兜底方案 | 🟡 P1 | 稳定性 |
| 6 | interface.py约1950行，混合数据获取/降级/缓存/格式化 | 🔴 P0 | 架构 |
| 7 | 降级逻辑分散在interface.py和data_source_manager.py两处 | 🟡 P1 | 架构 |
| 8 | 缓存键生成不统一，不同后端间无法互相查找 | 🟡 P1 | 性能 |
| 9 | 快照与缓存功能重叠，同一数据可能存两份 | 🟡 P1 | 性能 |
| 10 | 两层熔断器阈值不一致（3次 vs 5次） | 🟡 P1 | 架构 |
| 11 | PROVIDER_CAPABILITIES能力矩阵未在降级选择时使用 | 🟡 P1 | 架构 |
| 12 | trading_graph.py中3段重复的手动合并代码 | 🟡 P1 | 可维护性 |
| 13 | 关键指标无交叉验证，分析结果可能基于错误数据 | 🟡 P1 | 准确性 |
| 14 | 估算字段（TTM/动态PE）未标注，与实际值混淆 | 🟡 P1 | 准确性 |

### 1.3 优化目标

1. **P0修复**：解决巴菲特大师报告缺失Bug
2. **稳定性**：免费数据源下分析流程端到端可用率>95%
3. **准确性**：关键指标交叉验证覆盖率>60%，分析报告包含数据溯源信息
4. **完整性**：基本面数据完整度从~40%提升到~75%
5. **架构**：interface.py从~1950行降到~200行，降级逻辑统一入口
6. **性能**：热门股票分析时缓存命中率>80%
7. **可维护性**：核心模块测试覆盖率>60%

### 1.4 约束

- 仅关注免费数据源：AKShare/BaoStock/yfinance + 新浪财经/东方财富直接API（后两者已有Provider文件，需验证加固）
- 付费数据源(Tushare/Alpha Vantage/Finnhub等)暂不涉及，但降级链路保留
- 所有改动需Docker镜像构建验证通过
- 每个Phase完成后验证再进入下一个Phase
- 所有公开函数签名保持向后兼容

---

## 2. Phase 0（紧急修复）：P0 Bug修复

### 2.1 巴菲特大师报告缺失

**根因**：LangGraph并行执行大师节点时，`merge_dicts` reducer的覆盖式合并导致数据竞争。

**修复1：大师节点只返回自己的key**

**文件**: `tradingagents/agents/masters/base_master.py`

当前6处返回点返回整个 `master_reports` 字典（包含其他大师的空值），改为只返回自己修改的key：

```python
return {
    "master_reports": {master_id: report},
    "master_tool_call_counts": {master_id: tool_call_count}
}
```

**修复2：确认merge_dicts空值保护生效**

**文件**: `tradingagents/agents/utils/agent_states.py`

当前已有空值保护逻辑（`if key in merged and merged[key] and not value: continue`），需确认所有返回路径都经过此reducer，特别是 `master_data_quality` 和 `master_quantitative_results` 字段。

**修复3：提取手动合并代码为复用函数**

**文件**: `tradingagents/graph/trading_graph.py`

3段重复的手动合并代码（L714-739、L784-804、L829-853）提取为 `_merge_master_state()` 函数：

```python
def _merge_master_state(final_state: dict, node_update: dict) -> dict:
    """合并大师节点状态，复用merge_dicts逻辑"""
    for field in ("master_reports", "master_tool_call_counts",
                   "master_data_quality", "master_quantitative_results"):
        if field in node_update and field in final_state:
            existing = final_state.get(field, {})
            if isinstance(existing, dict):
                merged = dict(existing)
                for k, v in node_update[field].items():
                    if k in merged and merged[k] and not v:
                        continue
                    merged[k] = v
                node_update = dict(node_update)
                node_update[field] = merged
    return node_update
```

### 2.2 AKShare基本面数据获取问题

**根因**：AKShare依赖东方财富单一接口，反爬/限流频繁导致数据获取失败。

**修复**：在 `akshare.py` 中为关键数据类型注册多个备选API接口，实现自动切换。

### 2.3 验证标准

- 勾选巴菲特+彼得林奇执行分析，两位大师报告都正常显示
- 勾选全部13位大师执行分析，所有报告都正常显示
- AKShare接口失败时自动切换备选，不阻塞分析
- Docker镜像构建成功

---

## 3. Phase 1：免费数据源深度加固 + 分析准确性提升

### 3.1 AKShare多接口冗余

在 `akshare.py` 中添加 `_try_multiple_apis()` 方法，为关键数据类型注册多个接口：

| 数据类型 | 主接口 | 备选接口 | 说明 |
|---------|--------|---------|------|
| A股实时行情 | `stock_zh_a_spot_em` | `stock_zh_a_hist`（最近1天） | 行情数据冗余 |
| A股历史K线 | `stock_zh_a_hist` | `stock_zh_a_daily` | K线数据冗余 |
| 财务指标 | `stock_financial_analysis_indicator` | `stock_financial_report_sina` | 财务数据冗余 |
| PE/PB/市值 | `stock_zh_a_spot_em` | `stock_a_indicator_lg` | 估值数据冗余 |
| 港股行情 | `stock_hk_spot_em` | `stock_hk_hist` | 港股数据冗余 |

```python
def _try_multiple_apis(self, api_methods: List[Tuple[str, Callable]], symbol: str, **kwargs) -> Optional[pd.DataFrame]:
    for api_name, api_func in api_methods:
        try:
            result = api_func(symbol, **kwargs)
            if result is not None and not result.empty:
                logger.info(f"AKShare接口 {api_name} 成功")
                return result
        except Exception as e:
            logger.warning(f"AKShare接口 {api_name} 失败: {e}")
            continue
    return None
```

### 3.2 BaoStock连接池化

当前每次操作都login/logout，改为维持长连接+心跳检测+自动重连：

```python
class BaoStockConnectionPool:
    def __init__(self):
        self._connected = False
        self._last_ping = 0
        self._lock = asyncio.Lock()
        self._max_reconnects = 3

    async def ensure_connected(self) -> bool:
        async with self._lock:
            if self._connected and self._is_connection_alive():
                return True
            return await self._reconnect()

    async def _reconnect(self) -> bool:
        for attempt in range(self._max_reconnects):
            try:
                lg = await asyncio.to_thread(self.bs.login)
                if lg.error_code == '0':
                    self._connected = True
                    return True
            except Exception:
                pass
            await asyncio.sleep(2 ** attempt)
        return False

    async def _is_connection_alive(self) -> bool:
        now = time.time()
        if now - self._last_ping < 300:
            return True
        try:
            rs = await asyncio.to_thread(self.bs.query_trade_dates, start_date="2024-01-01", end_date="2024-01-02")
            self._last_ping = now
            return rs.error_code == '0'
        except Exception:
            self._connected = False
            return False
```

### 3.3 数据补全引擎

在 `data_source_manager.py` 中添加数据补全流程：

```
获取数据 → 质量评分(0-5) → 缺失字段识别 → 从备选接口补全 → 返回完整数据
```

**质量评分规则**：

| 评分 | 条件 |
|------|------|
| 5分 | 所有核心字段都有值，数据完整 |
| 4分 | 核心字段完整，1-2个次要字段缺失 |
| 3分 | 核心字段缺失1个 |
| 2分 | 核心字段缺失2-3个 |
| 1分 | 大量字段缺失 |
| 0分 | 完全无数据 |

**补全规则**：

| 缺失字段 | 补全接口 | 数据源 |
|---------|---------|--------|
| ROE/ROA | `stock_financial_analysis_indicator` | AKShare |
| PE/PB | `stock_zh_a_spot_em` | AKShare |
| 总市值/流通市值 | `stock_zh_a_spot_em` | AKShare |
| 换手率/量比 | `stock_zh_a_spot_em` | AKShare |
| 营收/净利润TTM | 本地TTM计算器 | BaoStock季度数据 |

### 3.4 分析结果准确性保障

#### a) 数据溯源标记

每个数据字段标注来源、获取时间、完整度评分。分析报告中展示数据可信度：

```python
@dataclass
class FieldProvenance:
    source: str           # "akshare" / "baostock" / "yfinance" / "sina" / "eastmoney"
    fetched_at: datetime  # 获取时间
    completeness: float   # 0.0-1.0
    is_estimated: bool    # 是否为估算值
    cross_validated: bool # 是否经过交叉验证
```

#### b) 数据交叉验证

关键指标从至少2个独立数据源获取，不一致时取中值并标注偏差：

| 指标 | 主数据源 | 验证数据源 | 偏差阈值 |
|------|---------|-----------|---------|
| PE | AKShare | BaoStock | 10% |
| PB | AKShare | BaoStock | 10% |
| ROE | AKShare | BaoStock | 15% |
| 营收 | AKShare | BaoStock | 5% |
| 净利润 | AKShare | BaoStock | 5% |

超过偏差阈值时，在报告中标注"⚠️ 数据源偏差较大，请谨慎参考"。

#### c) 过期数据保护

所有数据源失败时使用本地快照，报告中必须标注：
- "数据截止时间: YYYY-MM-DD"
- "⚠️ 数据可能过时，建议等待数据源恢复后重新分析"

#### d) 估算字段透明化

TTM计算、动态PE等估算值明确标注"估算值"，与实际报告值区分：

```python
# 报告中展示格式
"PE(TTM, 估算)": "25.3"  # 标注为估算值
"PE(静态, 实际)": "22.1"  # 标注为实际值
```

#### e) 结论降权机制

已有基础（`apply_quantitative_quality_guard`），继续增强：
- 数据完整度<0.9时，bullish/bearish信号降温为neutral
- 估算字段占比>50%时，整体结论降一级
- 交叉验证偏差>15%时，相关指标结论降权

### 3.5 新浪财经/东方财富直接API验证加固

已有Provider文件需验证和加固：

| Provider | 文件 | 状态 | 需要的加固 |
|---------|------|------|-----------|
| 新浪财经 | `providers/china/sina_finance.py` | 已有 | 验证API可用性，添加ResilientHttpClient集成 |
| 东方财富直接API | `providers/china/eastmoney_direct.py` | 已有 | 验证API可用性，添加curl_cffi浏览器指纹 |

**优先级排序**：
- A股实时行情：AKShare → 新浪财经 → 东方财富直接API → BaoStock
- A股基本面：AKShare → 东方财富直接API → BaoStock
- 港股行情：AKShare → yfinance → 新浪财经

### 3.6 本地数据快照兜底

- 存储路径：`data_cache/snapshots/{market}/{symbol}/`
- 快照格式：JSON，包含 `data`/`fetched_at`/`completeness_score`/`source`/`provenance`
- 读取优先级：实时数据 > 未过期快照 > 过期快照(标注时效)
- 快照有效期：

| 数据类型 | 有效期 | 说明 |
|---------|--------|------|
| 实时行情 | 1天 | 交易时段数据 |
| 历史K线 | 7天 | 日频数据 |
| 基本面数据 | 30天 | 季报更新 |
| 财务报表 | 90天 | 年报/季报 |
| 证券基本信息 | 180天 | 极少变化 |

### 3.7 验证标准

- AKShare接口失败时自动切换备选，不阻塞分析
- BaoStock长连接稳定，login失败自动重连
- 数据补全后完整度从~40%提升到~75%
- 关键指标交叉验证覆盖率>60%
- 所有分析报告包含数据溯源信息
- 估算字段明确标注
- 新浪财经/东方财富直接API可用，降级路径从3条增加到5条
- Docker镜像构建成功

---

## 4. Phase 2：架构解耦

### 4.1 interface.py 拆分

当前 `interface.py` 约1950行，拆分为：

| 新模块 | 职责 | 预估行数 |
|--------|------|---------|
| `interface.py` | 统一入口，委托调用 | ~200 |
| `cn_data_service.py` | A股数据获取+降级 | ~400 |
| `us_data_service.py` | 美股数据获取+降级 | ~300 |
| `hk_data_service.py` | 港股数据获取+降级 | ~300 |
| `data_orchestrator.py` | 统一降级框架+数据补全+交叉验证 | ~400 |

**迁移策略**：
- `interface.py` 保留所有公开函数签名，内部委托到新模块
- 外部调用无需修改，零破坏性
- 逐步迁移，每迁移一个市场验证一次

**迁移示例**：

```python
# interface.py (迁移后)
from tradingagents.dataflows.cn_data_service import CNDataService
from tradingagents.dataflows.us_data_service import USDataService
from tradingagents.dataflows.hk_data_service import HKDataService

_cn_service = CNDataService()
_us_service = USDataService()
_hk_service = HKDataService()

def get_stock_data(symbol, **kwargs):
    market = _detect_market(symbol)
    if market == "cn":
        return _cn_service.get_stock_data(symbol, **kwargs)
    elif market == "us":
        return _us_service.get_stock_data(symbol, **kwargs)
    elif market == "hk":
        return _hk_service.get_stock_data(symbol, **kwargs)
```

### 4.2 统一降级框架

当前降级逻辑分散在 `interface.py` 和 `data_source_manager.py`，统一到 `DataOrchestrator`：

```python
class DataOrchestrator:
    """统一数据获取+降级+补全+验证框架"""

    def __init__(self, health_tracker: SourceHealthTracker, cache_manager, snapshot_manager):
        self._health_tracker = health_tracker
        self._cache_manager = cache_manager
        self._snapshot_manager = snapshot_manager

    async def get_data(self, market: str, data_type: str, symbol: str, **kwargs) -> DataResult:
        # 1. 查缓存
        cached = self._cache_manager.get(cache_key)
        if cached and not cached.expired:
            return DataResult(data=cached.data, from_cache=True, provenance=cached.provenance)

        # 2. 按能力矩阵筛选可用数据源
        capable_sources = self._filter_by_capability(market, data_type)

        # 3. 按优先级+健康状态排序（使用SourceHealthTracker.get_available_sources过滤后按优先级排序）
        available_sources = self._sort_by_priority_and_health(capable_sources)

        # 4. 逐个尝试，收集结果
        results = []
        for source in available_sources:
            try:
                result = await self._fetch_from_source(source, symbol, data_type, **kwargs)
                if result:
                    results.append(result)
                    if self._is_sufficient(result):
                        break
            except Exception as e:
                self._health_tracker.record_failure(source)
                continue

        # 5. 数据补全（缺失字段从备选源补）
        if results and self._quality_score(results[0]) < 4:
            results = await self._complement_data(results, symbol, data_type)

        # 6. 交叉验证（关键指标多源对比）
        if len(results) >= 2:
            validated = self._cross_validate(results)
        else:
            validated = results[0] if results else None

        # 7. 质量评分+溯源标记
        if validated:
            validated.provenance = self._build_provenance(validated)

        # 8. 写缓存+快照
        if validated:
            self._cache_manager.set(cache_key, validated)
            self._snapshot_manager.save(symbol, validated)

        # 9. 返回 DataResult
        return validated or self._fallback_to_snapshot(symbol, data_type)
```

### 4.3 熔断器统一

当前两层熔断器阈值不一致，统一为：

| 级别 | 类 | 失败阈值 | 冷却期 | 半开探测 |
|------|-----|---------|--------|---------|
| HTTP请求 | CircuitBreaker | 3次重试失败 | 30s | 1次请求 |
| 数据源 | SourceHealthTracker | 连续3次失败 | 30s | 1次请求 |

统一冷却期和半开探测逻辑，消除行为不一致。

### 4.4 手动合并代码提取

`trading_graph.py` 中3段重复的手动合并代码提取为 `_merge_master_state()` 函数（Phase 0已定义），3处调用点统一使用。

### 4.5 验证标准

- `interface.py` 行数从~1950降到~200
- 降级逻辑统一入口，不再分散
- 所有公开函数签名不变，外部零改动
- 熔断器行为一致
- Docker镜像构建成功

---

## 5. Phase 3：缓存整合 + 性能优化

### 5.1 缓存系统整合

#### 统一缓存键格式

`{market}:{data_type}:{symbol}:{params_hash}`

| 字段 | 说明 | 示例 |
|------|------|------|
| market | 市场 | `cn`, `us`, `hk` |
| data_type | 数据类型 | `stock_data`, `fundamentals`, `news`, `financial` |
| symbol | 股票代码 | `600519`, `AAPL`, `00700` |
| params_hash | 参数指纹(12位) | `a1cc6e9ff077` |

#### 统一TTL策略

| 数据类型 | A股TTL | 美股TTL | 理由 |
|---------|--------|---------|------|
| 实时行情 | 5分钟 | 5分钟 | 交易时段需频繁更新 |
| 历史K线 | 4小时 | 4小时 | 日频更新，非交易时段可长缓存 |
| 基本面数据 | 12小时 | 24小时 | 季报更新，A股财报更频繁 |
| 新闻数据 | 2小时 | 4小时 | 新闻时效性 |
| 财务报表 | 24小时 | 48小时 | 季报更新，变化慢 |
| 证券基本信息 | 7天 | 7天 | 极少变化 |

#### 快照并入缓存

`DataSnapshotManager` 功能合并到 `IntegratedCacheManager`（Phase 1创建的DataSnapshotManager在Phase 3中迁移）：
- 快照作为带质量评分的缓存条目
- 消除同一数据存储两份的冗余
- 快照的 `completeness_score` 和 `provenance` 作为缓存元数据保存
- 迁移策略：DataSnapshotManager.save() → IntegratedCacheManager.set() with metadata；DataSnapshotManager.load() → IntegratedCacheManager.get() with metadata

#### 消除缓存查找断裂

`find_cached_fundamentals_data` 改为先查自适应缓存（MongoDB/Redis），再降级文件缓存。

#### MongoDB TTL索引

为缓存集合添加自动过期索引：

```javascript
db.stock_data_cache.createIndex(
    { "expires_at": 1 },
    { expireAfterSeconds: 0 }
)
```

影响集合：`stock_data_cache`、`fundamentals_cache`、`news_cache`

### 5.2 数据预取

| 任务ID | 频率 | 数据 | 目标 |
|--------|------|------|------|
| `prefetch_cn_quotes` | 交易时段每5分钟 | 沪深300实时行情+PE/PB | 热门A股分析时缓存命中 |
| `prefetch_cn_fundamentals` | 每日一次(收盘后20:00) | 财务指标+三大报表 | 基本面分析数据就绪 |
| `prefetch_us_quotes` | 美股交易时段每5分钟 | MAG7 + SPY/QQQ | 热门美股分析时缓存命中 |
| `prefetch_hk_quotes` | 港股交易时段每5分钟 | 恒生指数成分股 | 热门港股分析时缓存命中 |

### 5.3 增量更新

行情数据只更新最新一天，而非全量重新获取：

```python
def _get_incremental_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
    cached = self._get_cached_data(cache_key)
    if cached and not cached.empty:
        last_date = cached['date'].max()
        if last_date >= end_date:
            return cached
        incremental_start = (pd.Timestamp(last_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        new_data = self._fetch_stock_data(symbol, incremental_start, end_date)
        if new_data is not None and not new_data.empty:
            merged = pd.concat([cached, new_data]).drop_duplicates(subset=['date'])
            self._save_to_cache(cache_key, merged)
            return merged
    return self._fetch_stock_data(symbol, start_date, end_date)
```

### 5.4 自适应请求频率

```python
class AdaptiveRateLimiter:
    def __init__(self, min_interval=0.5, max_interval=5.0):
        self._min_interval = min_interval
        self._max_interval = max_interval
        self._current_interval = min_interval
        self._response_times = []
        self._cooldown_until = 0

    async def acquire(self):
        now = time.time()
        if now < self._cooldown_until:
            await asyncio.sleep(self._cooldown_until - now)
        elapsed = now - self._last_request_time
        if elapsed < self._current_interval:
            await asyncio.sleep(self._current_interval - elapsed)
        self._last_request_time = time.time()

    def record_response(self, response_time: float, status_code: int = 200):
        self._response_times.append(response_time)
        if len(self._response_times) > 10:
            self._response_times.pop(0)
        avg_time = sum(self._response_times) / len(self._response_times)
        if avg_time > 2.0:
            self._current_interval = min(self._current_interval * 1.5, self._max_interval)
        elif avg_time < 1.0 and self._current_interval > self._min_interval:
            self._current_interval = max(self._current_interval * 0.8, self._min_interval)
        if status_code in (429, 403):
            self._cooldown_until = time.time() + 60
            self._current_interval = min(self._current_interval * 2, self._max_interval)
```

### 5.5 验证标准

- 同一股票二次分析时缓存命中率>80%
- 分析速度提升50%+（缓存命中场景）
- MongoDB过期数据自动清理
- 快照与缓存不再冗余存储
- Docker镜像构建成功

---

## 6. Phase 4：可维护性 + 测试覆盖

### 6.1 LLM适配器统一

当前两套并行适配器体系，统一到 `OpenAICompatibleBase` 子类：

| 现有适配器 | 迁移目标 | 关键差异处理 |
|-----------|---------|-------------|
| `ChatDeepSeek` | `ChatDeepSeekOpenAI` | 保留 `_estimate_*_tokens()` 方法 |
| `ChatDashScopeOpenAI` | `ChatDashScopeOpenAIUnified` | 保留Token追踪逻辑，补充估算降级 |

工厂方法 `create_llm_client()` 统一使用 `OpenAICompatibleBase` 子类。保留独立文件1个版本周期作为回退。

### 6.2 配置读取路径统一

当前 tradingagents 层绕过 ConfigService 直接读 MongoDB，统一为：

| 现有路径 | 统一后 |
|---------|--------|
| `DataSourceManager._get_datasource_configs_from_db()` 直接读MongoDB | → 调用 `ConfigManager.get_datasource_configs()` |
| `MongoDBCacheAdapter._get_data_source_priority_order()` 直接读MongoDB | → 调用 `ConfigManager.get_datasource_priority()` |
| `runtime_settings.use_app_cache_enabled()` 读环境变量 | → 调用 `ConfigManager.get_cache_config()` |

`ConfigManager` 扩展：
- 添加内存缓存层（TTL 60秒），避免每次请求都查数据库
- 统一优先级：数据库配置 > 环境变量 > 默认值

### 6.3 核心模块Mock单元测试

| 批次 | 模块 | 测试文件 | 测试内容 |
|------|------|---------|---------|
| 第一批 | `factory.py` | `test_llm_factory.py` | 各Provider客户端创建、参数传递、降级 |
| 第一批 | `openai_compatible_base.py` | `test_openai_compatible_base.py` | Token追踪、消息格式、工具调用 |
| 第一批 | `provider_keys.py` | `test_provider_keys.py` | API Key读取优先级、Docker环境检测 |
| 第二批 | `data_orchestrator.py` | `test_data_orchestrator.py` | 降级逻辑、数据补全、交叉验证 |
| 第二批 | `data_source_manager.py` | `test_data_source_manager.py` | 优先级排序、降级链路、健康跟踪 |
| 第二批 | `resilient_http_client.py` | `test_resilient_http.py` | 重试、超时、熔断、限速 |
| 第三批 | `setup.py` | `test_graph_setup.py` | 节点注册、边构建、条件路由 |
| 第三批 | `trading_graph.py` | `test_trading_graph.py` | 状态合并、大师路由、报告生成 |

### 6.4 conftest.py 公共Fixture

```python
@pytest.fixture
def mock_llm_client(): ...

@pytest.fixture
def mock_tool_call_response(): ...

@pytest.fixture
def mock_akshare_provider(): ...

@pytest.fixture
def mock_baostock_provider(): ...

@pytest.fixture
def mock_yfinance_provider(): ...

@pytest.fixture
def mock_mongo_db(): ...

@pytest.fixture
def mock_redis_client(): ...

@pytest.fixture
def sample_stock_data(): ...

@pytest.fixture
def sample_analysis_state(): ...
```

### 6.5 验证标准

- LLM适配器统一后所有Provider行为不变
- 核心模块测试覆盖率>60%（LLM层+数据源层）
- 所有测试通过 `pytest -m "not integration"`
- 配置读取路径统一，无直接MongoDB访问
- Docker镜像构建成功

---

## 7. 实施计划

### 7.1 实施顺序

```
Phase 0 (紧急, 1-2天) → Phase 1 (加固+准确性, 3-5天) → Phase 2 (架构解耦, 3-5天) → Phase 3 (缓存+性能, 2-3天) → Phase 4 (可维护性, 3-5天)
```

### 7.2 每个Phase的验证标准

| Phase | 验证标准 |
|-------|---------|
| Phase 0 | 巴菲特+林奇报告都正常；13位大师全选报告都正常；AKShare备选接口可用 |
| Phase 1 | 数据补全后完整度>75%；交叉验证覆盖率>60%；报告含数据溯源；估算字段标注 |
| Phase 2 | interface.py降到~200行；降级逻辑统一入口；熔断器行为一致 |
| Phase 3 | 缓存命中率>80%；分析速度提升50%+；快照缓存无冗余 |
| Phase 4 | 测试覆盖率>60%；配置路径统一；LLM适配器统一 |

### 7.3 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| merge_dicts修复影响其他reducer | 低 | 高 | 只修改返回结构，不改变合并逻辑 |
| interface.py拆分引入新Bug | 中 | 高 | 保留公开函数签名，逐步迁移，每步验证 |
| 缓存键迁移导致旧缓存失效 | 中 | 低 | 迁移期兼容旧键，逐步切换 |
| LLM适配器统一后行为变化 | 中 | 高 | 迁移前添加mock测试，保留回退1个版本 |
| BaoStock长连接意外断开 | 低 | 低 | 心跳检测+自动重连 |
| 交叉验证增加延迟 | 低 | 中 | 仅对关键指标做交叉验证，非关键指标跳过 |

---

## 8. 不在范围内

- 付费数据源(Tushare/Alpha Vantage/Finnhub)的优化
- 前端UI改进
- 新功能开发
- CI/CD流水线搭建
- 国际化/多语言支持

---

## 9. 关键文件入口

| 功能 | 文件路径 |
|------|---------|
| 大师节点基类 | `tradingagents/agents/masters/base_master.py` |
| AgentState定义 | `tradingagents/agents/utils/agent_states.py` |
| 交易图主逻辑 | `tradingagents/graph/trading_graph.py` |
| 统一数据接口 | `tradingagents/dataflows/interface.py` |
| 数据源管理器 | `tradingagents/dataflows/data_source_manager.py` |
| AKShare适配器 | `tradingagents/dataflows/providers/china/akshare.py` |
| BaoStock适配器 | `tradingagents/dataflows/providers/china/baostock.py` |
| 新浪财经Provider | `tradingagents/dataflows/providers/china/sina_finance.py` |
| 东方财富直接API | `tradingagents/dataflows/providers/china/eastmoney_direct.py` |
| yfinance适配器 | `tradingagents/dataflows/providers/us/yfinance.py` |
| 弹性HTTP客户端 | `tradingagents/dataflows/providers/resilient_http_client.py` |
| 缓存配置 | `tradingagents/dataflows/cache/cache_config.py` |
| 基本面快照 | `tradingagents/dataflows/china_fundamental_snapshot.py` |
| 数据完整度检查 | `tradingagents/dataflows/data_completeness_checker.py` |
| 统一DataFrame | `tradingagents/dataflows/unified_dataframe.py` |
| 新增：A股数据服务 | `tradingagents/dataflows/cn_data_service.py` |
| 新增：美股数据服务 | `tradingagents/dataflows/us_data_service.py` |
| 新增：港股数据服务 | `tradingagents/dataflows/hk_data_service.py` |
| 新增：数据编排器 | `tradingagents/dataflows/data_orchestrator.py` |
