# TradingAgents-CN 免费数据源全面优化设计文档

**日期**: 2026-05-03
**版本**: v2.0
**状态**: 待审核
**范围**: 仅免费数据源，付费数据源暂不涉及

---

## 1. 背景与目标

### 1.1 项目现状

TradingAgents-CN v1.0.1 已完成32轮开发迭代，5轮全面Bug修复（累计50+个Bug），3个Phase优化（稳定性/性能/可维护性）已全部完成。但系统在免费数据源下的端到端可用性仍不稳定，且存在一个P0级Bug（巴菲特大师报告缺失）。

### 1.2 核心问题

| # | 问题 | 严重度 | 影响 |
|---|------|--------|------|
| 1 | LangGraph并行大师节点数据竞争，后完成节点覆盖先完成节点的报告 | 🔴 P0 | 巴菲特等大师报告随机缺失 |
| 2 | AKShare依赖东方财富单一接口，反爬/限流频繁 | 🔴 P0 | A股数据获取不稳定 |
| 3 | BaoStock每次login/logout，login偶发失败 | 🟡 P1 | A股降级数据源不可靠 |
| 4 | 免费数据源财务数据不完整（缺ROE/PE/PB等） | 🟡 P1 | 大师分析质量受限 |
| 5 | 所有数据源失败时无兜底方案 | 🟡 P1 | 分析完全无法进行 |
| 6 | 数据源数量有限，降级路径不足 | 🟡 P1 | 故障时无备选 |
| 7 | 分析时才获取数据，无预取机制 | 🟢 P2 | 分析速度慢 |

### 1.3 优化目标

1. **P0修复**：解决巴菲特大师报告缺失Bug
2. **稳定性**：免费数据源下分析流程端到端可用率>95%
3. **完整性**：基本面数据完整度从~40%提升到~75%
4. **多元性**：引入额外免费数据源，丰富降级路径
5. **性能**：热门股票分析时缓存命中率>80%

### 1.4 约束

- 仅关注免费数据源：AKShare/BaoStock/yfinance + 新增新浪财经/东方财富直接API
- 付费数据源(Tushare/Alpha Vantage/Finnhub等)暂不涉及，但降级链路保留
- 所有改动需Docker镜像构建验证通过
- 每个Phase完成后验证再进入下一个Phase

---

## 2. Phase 0（紧急修复）：巴菲特大师报告缺失Bug

### 2.1 根因分析

LangGraph并行执行大师节点时，`merge_dicts` reducer的`dict.update()`覆盖式合并导致数据竞争：

```
初始: master_reports = {"warren_buffett": "", "peter_lynch": ""}

巴菲特节点返回: {"warren_buffett": "报告...", "peter_lynch": ""}  ← 包含林奇空值
林奇节点返回:   {"warren_buffett": "", "peter_lynch": "报告..."}  ← 包含巴菲特空值

merge_dicts合并:
  left.update(right) → {"warren_buffett": "", "peter_lynch": "报告..."}

结果：巴菲特报告被林奇节点返回的空值覆盖！
```

### 2.2 修复方案

#### 修复1：大师节点只返回自己的key

**文件**: `tradingagents/agents/masters/base_master.py`

**当前代码**（6处返回点）：
```python
updated_reports = dict(master_reports)
updated_reports[master_id] = report
updated_counts = dict(master_tool_counts)
updated_counts[master_id] = tool_call_count
return {"master_reports": updated_reports, "master_tool_call_counts": updated_counts}
```

**修复后**：
```python
return {
    "master_reports": {master_id: report},
    "master_tool_call_counts": {master_id: tool_call_count}
}
```

每个大师节点只返回自己修改的key，不包含其他大师的key。这样`merge_dicts`合并时不会互相覆盖。

#### 修复2：merge_dicts增加空值保护

**文件**: `tradingagents/utils/agent_states.py`

**当前代码**：
```python
def merge_dicts(left: Dict, right: Dict) -> Dict:
    if left is None:
        left = {}
    if right is None:
        right = {}
    merged = dict(left)
    merged.update(right)
    return merged
```

**修复后**：
```python
def merge_dicts(left: Dict, right: Dict) -> Dict:
    if left is None:
        left = {}
    if right is None:
        right = {}
    merged = dict(left)
    for key, value in right.items():
        if key in merged and merged[key] and not value:
            continue
        merged[key] = value
    return merged
```

#### 修复3：手动累积合并增加空值保护

**文件**: `tradingagents/graph/trading_graph.py`

2处手动累积合并逻辑（约L781-784和L825-827）增加空值保护，不允许用空值覆盖已有报告。

### 2.3 验证标准

- 勾选巴菲特+彼得林奇执行分析，两位大师报告都正常显示
- 勾选全部13位大师执行分析，所有报告都正常显示
- 前端报告详情页所有大师Tab都有内容

---

## 3. Phase 1：深度加固免费数据源

### 3.1 AKShare多接口冗余

**问题**：AKShare依赖东方财富单一接口，接口被封或返回异常时无备选。

**设计**：在 `akshare_adapter.py` 中添加 `_try_multiple_apis()` 方法，为关键数据类型注册多个接口。

| 数据类型 | 主接口 | 备选接口 | 说明 |
|---------|--------|---------|------|
| A股实时行情 | `stock_zh_a_spot_em` | `stock_zh_a_hist`（最近1天） | 行情数据冗余 |
| A股历史K线 | `stock_zh_a_hist` | `stock_zh_a_daily` | K线数据冗余 |
| 财务指标 | `stock_financial_analysis_indicator` | `stock_financial_report_sina` | 财务数据冗余 |
| PE/PB/市值 | `stock_zh_a_spot_em` | `stock_a_indicator_lg` | 估值数据冗余 |
| 港股行情 | `stock_hk_spot_em` | `stock_hk_hist` | 港股数据冗余 |

**实现**：

```python
def _try_multiple_apis(self, api_methods: List[Tuple[str, Callable]], symbol: str, **kwargs) -> Optional[pd.DataFrame]:
    """尝试多个API接口，按优先级依次调用"""
    for api_name, api_func in api_methods:
        try:
            result = api_func(symbol, **kwargs)
            if result is not None and not result.empty:
                logger.info(f"✅ AKShare接口 {api_name} 成功")
                return result
        except Exception as e:
            logger.warning(f"⚠️ AKShare接口 {api_name} 失败: {e}")
            continue
    return None
```

### 3.2 BaoStock连接池化

**问题**：BaoStock每次操作都login/logout，login偶发失败导致整个操作失败。

**设计**：

```python
class BaoStockConnectionPool:
    """BaoStock连接池，维持长连接"""

    def __init__(self):
        self._connected = False
        self._last_ping = 0
        self._lock = asyncio.Lock()
        self._reconnect_count = 0
        self._max_reconnects = 3

    async def ensure_connected(self) -> bool:
        """确保连接可用，必要时重连"""
        async with self._lock:
            if self._connected and self._is_connection_alive():
                return True
            return await self._reconnect()

    async def _reconnect(self) -> bool:
        """重连逻辑：3次重试，指数退避"""
        for attempt in range(self._max_reconnects):
            try:
                lg = await asyncio.to_thread(self.bs.login)
                if lg.error_code == '0':
                    self._connected = True
                    self._reconnect_count = 0
                    return True
            except Exception:
                pass
            await asyncio.sleep(2 ** attempt)
        return False

    async def _is_connection_alive(self) -> bool:
        """心跳检测：每5分钟ping一次"""
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

**问题**：单个数据源获取的数据经常不完整。

**设计**：在 `data_source_manager.py` 中添加数据补全流程：

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
| 三大报表 | 东方财富报表接口 | AKShare |
| 营收/净利润TTM | 本地TTM计算器 | BaoStock季度数据 |

### 3.4 本地数据快照

**问题**：所有数据源都失败时，分析完全无法进行。

**设计**：

- 存储路径：`data_cache/snapshots/{market}/{symbol}/`
- 快照格式：JSON，包含 `data`/`fetched_at`/`completeness_score`/`source`
- 读取优先级：实时数据 > 未过期快照 > 过期快照(标注时效)
- 快照有效期：

| 数据类型 | 有效期 | 说明 |
|---------|--------|------|
| 实时行情 | 1天 | 交易时段数据 |
| 历史K线 | 7天 | 日频数据 |
| 基本面数据 | 30天 | 季报更新 |
| 财务报表 | 90天 | 年报/季报 |
| 证券基本信息 | 180天 | 极少变化 |

**使用场景**：快照仅在所有实时数据源失败时使用，并在报告中标注"数据截止时间: YYYY-MM-DD"。

### 3.5 请求频率自适应

**问题**：AKShare请求频率固定，响应慢时仍高频请求容易触发反爬。

**设计**：

```python
class AdaptiveRateLimiter:
    """自适应请求频率控制器"""

    def __init__(self, min_interval=0.5, max_interval=5.0):
        self._min_interval = min_interval
        self._max_interval = max_interval
        self._current_interval = min_interval
        self._response_times = []  # 最近10次响应时间
        self._last_request_time = 0
        self._cooldown_until = 0

    async def acquire(self):
        """获取请求许可，自动等待"""
        now = time.time()

        # 冷却期检查
        if now < self._cooldown_until:
            await asyncio.sleep(self._cooldown_until - now)

        # 频率控制
        elapsed = now - self._last_request_time
        if elapsed < self._current_interval:
            await asyncio.sleep(self._current_interval - elapsed)

        self._last_request_time = time.time()

    def record_response(self, response_time: float, status_code: int = 200):
        """记录响应，自适应调整频率"""
        self._response_times.append(response_time)
        if len(self._response_times) > 10:
            self._response_times.pop(0)

        avg_time = sum(self._response_times) / len(self._response_times)

        # 响应慢时增加间隔
        if avg_time > 2.0:
            self._current_interval = min(self._current_interval * 1.5, self._max_interval)
        elif avg_time < 1.0 and self._current_interval > self._min_interval:
            self._current_interval = max(self._current_interval * 0.8, self._min_interval)

        # 429/403立即进入冷却
        if status_code in (429, 403):
            self._cooldown_until = time.time() + 60
            self._current_interval = min(self._current_interval * 2, self._max_interval)
```

---

## 4. Phase 1.5：引入额外免费数据源

### 4.1 新增新浪财经Provider

**能力矩阵**：

| 数据类型 | 支持 | 接口 |
|---------|------|------|
| A股实时行情 | ✅ | `hq.sinajs.cn` |
| A股历史K线 | ✅ | `finance.sina.com.cn/realstock` |
| 财务摘要 | ✅ | `money.finance.sina.com.cn` |
| 大单交易 | ✅ | `vip.stock.finance.sina.com.cn` |

**新增文件**：`tradingagents/dataflows/providers/china/sina_finance.py`

**优先级**：A股实时行情第2优先级（AKShare之后，BaoStock之前）

**特点**：
- 新浪财经API稳定运行10+年，反爬策略宽松
- 实时行情数据延迟<3秒
- 无需API Key

### 4.2 新增东方财富直接API Provider

**能力矩阵**：

| 数据类型 | 支持 | 接口 |
|---------|------|------|
| A股实时行情 | ✅ | `push2.eastmoney.com` |
| 财务数据 | ✅ | `datacenter.eastmoney.com` |
| 行业数据 | ✅ | `push2.eastmoney.com` |
| 龙虎榜 | ✅ | `datacenter.eastmoney.com` |

**新增文件**：`tradingagents/dataflows/providers/china/eastmoney_direct.py`

**优先级**：AKShare的底层接口备选（AKShare也是调用东方财富，直接调用减少中间层）

**特点**：
- 绕过AKShare中间层，直接调用东方财富API
- 减少AKShare版本更新导致的接口失效风险
- 需要模拟浏览器请求头（使用curl_cffi）

### 4.3 数据源能力矩阵

**设计**：为每个数据源建立能力矩阵，按需选择最佳数据源。

```python
PROVIDER_CAPABILITIES = {
    "akshare": {
        "cn_realtime_quotes": True,
        "cn_historical_kline": True,
        "cn_financial_indicators": True,
        "cn_financial_statements": True,
        "cn_pe_pb": True,
        "cn_news": True,
        "hk_realtime_quotes": True,
        "hk_historical_kline": True,
    },
    "baostock": {
        "cn_realtime_quotes": False,
        "cn_historical_kline": True,
        "cn_financial_indicators": True,
        "cn_financial_statements": False,
        "cn_pe_pb": False,
        "cn_news": False,
        "hk_realtime_quotes": False,
        "hk_historical_kline": False,
    },
    "sina_finance": {
        "cn_realtime_quotes": True,
        "cn_historical_kline": True,
        "cn_financial_indicators": False,
        "cn_financial_statements": False,
        "cn_pe_pb": False,
        "cn_news": False,
        "hk_realtime_quotes": True,
        "hk_historical_kline": True,
    },
    "eastmoney_direct": {
        "cn_realtime_quotes": True,
        "cn_historical_kline": True,
        "cn_financial_indicators": True,
        "cn_financial_statements": True,
        "cn_pe_pb": True,
        "cn_news": True,
        "hk_realtime_quotes": True,
        "hk_historical_kline": True,
    },
    "yfinance": {
        "us_realtime_quotes": True,
        "us_historical_kline": True,
        "us_financial_indicators": True,
        "us_financial_statements": True,
        "hk_realtime_quotes": True,
        "hk_historical_kline": True,
    },
}
```

**优先级排序逻辑**：根据请求数据类型，从能力矩阵中筛选支持的数据源，再按健康状态和优先级排序。

### 4.4 数据源注册机制扩展

**修改文件**：

| 文件 | 修改 |
|------|------|
| `data_source_manager.py` | `ChinaDataSource`枚举添加SINA/EASTMONEY，优先级排序逻辑支持新数据源 |
| `base_provider.py` | 添加`capabilities`属性，声明数据源能力 |
| `__init__.py` | 注册新Provider |

---

## 5. Phase 2：数据预取+缓存优先策略

### 5.1 热门股票定时预取

**设计**：在 `scheduler_service.py` 中添加定时预取任务。

| 任务ID | 频率 | 数据 | 目标 |
|--------|------|------|------|
| `prefetch_cn_quotes` | 交易时段每5分钟 | 沪深300实时行情+PE/PB | 热门A股分析时缓存命中 |
| `prefetch_cn_fundamentals` | 每日一次(收盘后20:00) | 财务指标+三大报表 | 基本面分析数据就绪 |
| `prefetch_us_quotes` | 美股交易时段每5分钟 | yfinance行情 | 热门美股分析时缓存命中 |
| `prefetch_hk_quotes` | 港股交易时段每5分钟 | 港股行情 | 热门港股分析时缓存命中 |

**预取列表**：

| 市场 | 股票 | 数量 |
|------|------|------|
| A股 | 沪深300成分股 | 300只 |
| 美股 | MAG7 + SPY/QQQ | 9只 |
| 港股 | 恒生指数成分股 | 80只 |

**实现**：

```python
async def prefetch_cn_quotes(self):
    """预取A股热门股票行情数据"""
    symbols = self._get_hs300_symbols()
    for symbol in symbols:
        try:
            data = await self.data_source_manager.get_stock_data(symbol)
            if data:
                self.cache_manager.set(
                    generate_cache_key("cn", "realtime_quotes", symbol),
                    data,
                    ttl=DEFAULT_TTL.cn_realtime_quotes
                )
        except Exception as e:
            logger.warning(f"预取 {symbol} 行情失败: {e}")
            continue
```

### 5.2 缓存优先读取

**设计**：分析时数据获取流程改为：

```
查本地缓存 → 命中且未过期 → 直接使用
                ↓ 未命中或过期
        实时获取 → 成功 → 更新缓存 → 使用
                    ↓ 失败
                使用本地快照(标注时效)
```

**修改文件**：`data_source_manager.py` 的所有 `_get_*_data()` 方法

### 5.3 增量更新

**设计**：行情数据只更新最新一天，而非全量重新获取。

```python
def _get_incremental_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
    """增量更新行情数据"""
    cached = self._get_cached_data(cache_key)
    if cached and not cached.empty:
        last_date = cached['date'].max()
        if last_date >= end_date:
            return cached  # 缓存已覆盖请求范围

        # 只请求缺失部分
        incremental_start = (pd.Timestamp(last_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        new_data = self._fetch_stock_data(symbol, incremental_start, end_date)

        if new_data is not None and not new_data.empty:
            merged = pd.concat([cached, new_data]).drop_duplicates(subset=['date'])
            self._save_to_cache(cache_key, merged)
            return merged

    # 无缓存，全量获取
    return self._fetch_stock_data(symbol, start_date, end_date)
```

---

## 6. 实施计划

### 6.1 实施顺序

```
Phase 0 (紧急, 1天) → Phase 1 (加固, 3-5天) → Phase 1.5 (新数据源, 3-5天) → Phase 2 (预取, 2-3天)
```

### 6.2 每个Phase的验证标准

| Phase | 验证标准 |
|-------|---------|
| Phase 0 | 巴菲特+林奇报告都正常显示；13位大师全选报告都正常 |
| Phase 1 | AKShare接口失败时自动切换备选；BaoStock长连接稳定；数据补全后完整度>70% |
| Phase 1.5 | 新浪财经/东方财富直接API可用；数据源降级路径从3条增加到5条 |
| Phase 2 | 热门股票缓存命中率>80%；分析速度提升50%+ |

### 6.3 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| merge_dicts修复影响其他reducer | 低 | 高 | 添加空值保护而非改变合并逻辑 |
| 新浪财经API变更 | 中 | 中 | 作为备选数据源，不影响主路径 |
| 东方财富直接API反爬加强 | 中 | 中 | 使用curl_cffi模拟浏览器指纹 |
| 预取任务影响数据源稳定性 | 低 | 中 | 控制预取频率，使用自适应限速 |
| BaoStock长连接意外断开 | 低 | 低 | 心跳检测+自动重连 |

---

## 7. 不在范围内

- 付费数据源(Tushare/Alpha Vantage/Finnhub)的优化
- 前端UI改进
- 新功能开发
- CI/CD流水线搭建
- 国际化/多语言支持

---

## 8. 关键文件入口

| 功能 | 文件路径 |
|------|---------|
| 大师节点基类 | `tradingagents/agents/masters/base_master.py` |
| AgentState定义 | `tradingagents/utils/agent_states.py` |
| 交易图主逻辑 | `tradingagents/graph/trading_graph.py` |
| 数据源管理器 | `tradingagents/dataflows/data_source_manager.py` |
| AKShare适配器 | `tradingagents/dataflows/providers/china/akshare.py` |
| BaoStock适配器 | `tradingagents/dataflows/providers/china/baostock.py` |
| yfinance适配器 | `tradingagents/dataflows/providers/us/yfinance.py` |
| 弹性HTTP客户端 | `tradingagents/dataflows/providers/resilient_http_client.py` |
| 缓存配置 | `tradingagents/dataflows/cache/cache_config.py` |
| 调度服务 | `app/services/scheduler_service.py` |
| 新增：新浪财经Provider | `tradingagents/dataflows/providers/china/sina_finance.py` |
| 新增：东方财富直接API | `tradingagents/dataflows/providers/china/eastmoney_direct.py` |
