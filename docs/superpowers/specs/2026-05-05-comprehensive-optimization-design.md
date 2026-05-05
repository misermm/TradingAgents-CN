# TradingAgents-CN 全面均衡优化设计文档

**日期**: 2026-05-05
**版本**: v1.0
**范围**: tradingagents/ 核心模块（数据源稳定性 + 性能优化 + 架构治理）
**约束**: 仅免费数据源，付费数据源暂搁置

---

## 一、背景与目标

### 1.1 当前状态

项目已完成分层重构 Phase 0-4 + 14个Bug修复，核心数据流架构基本成型。但仍存在以下关键问题：

| 问题类别 | 具体问题 | 严重度 |
|---------|---------|--------|
| 数据源稳定性 | AKShare全局monkey-patch `requests.get`，线程安全隐患 | Critical |
| 数据源稳定性 | BaoStock无实时行情，盘中分析不可用 | Critical |
| 数据源稳定性 | 港股名称硬编码仅40只，覆盖面极小 | High |
| 性能 | 行情数据全量获取，无增量更新 | Medium |
| 性能 | 交叉验证重复获取数据 | Medium |
| 性能 | 缓存key无统一规范，TTL策略粗糙 | Medium |
| 架构 | interface.py约1280行未拆分 | High |
| 架构 | DataOrchestrator能力矩阵硬编码 | Medium |
| 架构 | LLM创建逻辑在trading_graph.py和factory.py重复 | Medium |
| 架构 | 配置来源双轨制 | High |

### 1.2 优化目标

1. **数据源稳定性**：消除全局monkey-patch，补全BaoStock实时行情，新增免费数据源填补能力空白
2. **性能优化**：统一缓存架构，实现增量更新，消除重复数据获取
3. **架构治理**：拆分interface.py，动态化能力矩阵，统一LLM工厂，配置收口

### 1.3 约束

- 仅使用免费数据源（AKShare/BaoStock/新浪/东方财富/yfinance + 新增腾讯财经/同花顺）
- 付费数据源（Tushare高级权限、Finnhub API等）暂不涉及
- 优化范围聚焦 `tradingagents/` 核心模块，不动 `app/` 和 `frontend/`
- 所有现有函数签名保持不变（向后兼容）

---

## 二、数据源适配层重构

### 2.1 统一适配器基类 BaseDataProvider

**文件**: `tradingagents/dataflows/providers/base_provider.py`（新增）

```python
from abc import ABC, abstractmethod
from typing import Any, Optional
import pandas as pd

class BaseDataProvider(ABC):
    provider_name: str
    supported_markets: list[str]
    capabilities: dict[str, bool]

    async def _resilient_call(self, fn, *args, **kwargs) -> Any:
        """统一弹性调用：内置重试/超时/熔断/限流"""
        ...

    @abstractmethod
    async def get_realtime_quotes(self, symbol: str) -> Optional[dict]:
        ...

    @abstractmethod
    async def get_historical_kline(self, symbol: str, period: str, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        ...

    @abstractmethod
    async def get_fundamentals(self, symbol: str) -> Optional[dict]:
        ...

    @abstractmethod
    async def get_stock_info(self, symbol: str) -> Optional[dict]:
        ...

    async def health_check(self) -> dict:
        """返回 {"healthy": bool, "latency_ms": int, "last_error": str}"""
        ...
```

**能力声明示例**：

```python
class AKShareProvider(BaseDataProvider):
    provider_name = "akshare"
    supported_markets = ["cn", "hk"]
    capabilities = {
        "realtime_quotes": True,
        "historical_kline": True,
        "fundamentals": True,
        "stock_info": True,
        "news": True,
        "valuation": True,
    }
```

**弹性调用机制**：
- 重试：3次，指数退避（1s/2s/4s）
- 超时：连接5s，读取30s
- 熔断：5次失败后进入30s冷却期
- 限流：自适应间隔（默认0.5s，429/403时进入60s冷却）

### 2.2 AKShare monkey-patch 修复

**文件**: `tradingagents/dataflows/providers/china/akshare.py`（修改）

**当前问题**：全局修改 `requests.get`，影响所有HTTP请求模块

**修复方案**：改为 session 级别拦截

```python
class AKShareProvider(BaseDataProvider):
    def __init__(self):
        self._session = self._create_resilient_session()

    def _create_resilient_session(self) -> requests.Session:
        session = requests.Session()
        if curl_cffi_available:
            from curl_cffi import requests as cf_requests
            session.mount('https://', CurlCffiAdapter(browser='chrome120'))
        return session
```

**迁移策略**：
1. 创建隔离session
2. 将所有 `akshare.xxx()` 调用改为通过session发起
3. 移除全局 `requests.get` monkey-patch
4. 对AKShare SDK内部调用，使用 `akshare.set_http_session()` 注入（如支持）或通过环境变量控制

### 2.3 BaoStock 实时行情补全

**文件**: `tradingagents/dataflows/providers/china/baostock.py`（修改）

**方案**：BaoStock + 新浪财经组合策略

```python
class BaoStockProvider(BaseDataProvider):
    capabilities = {
        "realtime_quotes": True,   # 通过新浪财经补充
        "historical_kline": True,  # BaoStock自身
        "fundamentals": True,      # BaoStock自身（五大能力）
        "valuation": True,         # BaoStock自身（PE_TTM/PB_MRQ等）
    }

    async def get_realtime_quotes(self, symbol: str):
        sina_quotes = await self._sina_provider.get_realtime_quotes(symbol)
        baostock_valuation = await self._get_latest_valuation(symbol)
        return self._merge_quotes_and_valuation(sina_quotes, baostock_valuation)
```

**合并策略**：
- 新浪提供：价格/成交量/涨跌幅/换手率（实时）
- BaoStock提供：PE_TTM/PB_MRQ/PS_TTM/PCF_TTM（最新日频）
- 冲突字段以新浪为准（实时性更高）

### 2.4 新增腾讯财经 Provider

**文件**: `tradingagents/dataflows/providers/hk/tencent_finance.py`（新增）

**填补能力**：港股实时行情 + 港股名称映射

**关键接口**：

| 接口 | URL | 用途 | 返回格式 |
|------|-----|------|---------|
| 港股实时行情 | `https://qt.gtimg.cn/q=r_hk0{code}` (5位代码，如r_hk00700) | 实时价格/成交量/涨跌幅 | 分号分隔文本 |
| 港股名称映射 | `https://qt.gtimg.cn/q=s_hk` | 全量港股代码-名称列表 | 分号分隔文本 |
| A股实时行情 | `https://qt.gtimg.cn/q=sz{6位代码},sh{6位代码}` | A股补充源 | 分号分隔文本 |
| 港股K线 | `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=hk{code},day,,,320,qfq` | 港股历史K线 | JSON |

**能力声明**：

```python
class TencentFinanceProvider(BaseDataProvider):
    provider_name = "tencent_finance"
    supported_markets = ["cn", "hk"]
    capabilities = {
        "realtime_quotes": True,
        "stock_info": True,       # 名称映射
        "historical_kline": False,
        "fundamentals": False,
        "news": False,
    }
```

### 2.5 新增同花顺 Provider

**文件**: `tradingagents/dataflows/providers/china/ths_direct.py`（新增）

**填补能力**：A股行业分类 + 基本面补充

**关键接口**：

| 接口 | URL | 用途 | 返回格式 |
|------|-----|------|---------|
| 行业分类 | `https://basic.10jqka.com.cn/api/stockph/industrylist` | 申万行业分类 | JSON |
| 财务摘要 | `https://basic.10jqka.com.cn/stock/finance/{code}.html` (解析HTML) | 补充AKShare缺失字段 | HTML |
| 个股信息 | `https://basic.10jqka.com.cn/{code}/` (解析HTML) | 股票基础信息+行业 | HTML |

**能力声明**：

```python
class THSDirectProvider(BaseDataProvider):
    provider_name = "ths_direct"
    supported_markets = ["cn"]
    capabilities = {
        "realtime_quotes": False,
        "stock_info": True,        # 行业分类
        "fundamentals": True,      # 财务摘要补充
        "historical_kline": False,
        "news": False,
    }
```

### 2.6 数据源降级链路总览（优化后）

```
A股行情: 东方财富直接(实时+指标) → AKShare(stock_bid_ask_em) → 新浪财经(实时) → 腾讯财经(实时) → AKShare(stock_zh_a_hist) → BaoStock(最新日K)
A股基本面: Tushare(需Token) → AKShare(三大报表) → BaoStock(五大能力) → 东方财富(8期摘要) → 同花顺(补充)
A股新闻: AKShare(stock_news_em) → 东方财富直接(curl_cffi)
A股行业: 同花顺(申万分类) → AKShare(行业接口)

港股行情: 腾讯财经(实时) → AKShare(港股接口) → 新浪财经(港股) → yfinance(延迟15min)
港股名称: 腾讯财经(动态映射) → 硬编码(40只兜底)
港股基本面: yfinance → AKShare(有限)

美股行情: yfinance(延迟15min) → 腾讯财经(美股接口)
美股基本面: yfinance(三大报表)
```

---

## 三、智能缓存与性能优化

### 3.1 统一缓存管理器

**文件**: `tradingagents/dataflows/cache/unified_cache_manager.py`（新增）

**替代**: `integrated_cache.py` 和 `adaptive_cache.py`（保留但标记为deprecated）

```python
class UnifiedCacheManager:
    TTL_POLICIES = {
        "realtime_quotes": 30,
        "daily_quotes": 3600,
        "historical_kline": 86400,
        "fundamentals": 43200,
        "stock_info": 604800,
        "industry_info": 604800,
        "news": 1800,
        "valuation": 3600,
    }

    def make_key(self, category: str, symbol: str, **params) -> str:
        param_hash = hashlib.md5(str(sorted(params.items())).encode()).hexdigest()[:8]
        return f"cache:{category}:{symbol}:{param_hash}"

    async def get_or_fetch(self, key: str, fetch_fn, ttl: int = None) -> Any:
        """带穿透防护的获取：并发请求同一key时只执行一次fetch"""
        ...

    async def prefetch(self, symbols: list, categories: list) -> None:
        """批量预取"""
        ...

    def get_stats(self) -> dict:
        """缓存统计：{"hit_rate": float, "total_requests": int, ...}"""
        ...
```

**缓存穿透防护**：
- 使用 `asyncio.Lock` 保证同一key的并发请求只执行一次fetch
- fetch失败时设置短TTL（60s）防止缓存击穿

**迁移策略**：
- 新代码使用 `UnifiedCacheManager`
- 旧代码的 `integrated_cache` / `adaptive_cache` 调用逐步迁移
- 迁移完成前两套并存，不破坏现有功能

### 3.2 行情增量更新

**文件**: `tradingagents/dataflows/cn_data_service.py`（修改）

```python
class IncrementalQuoteUpdater:
    async def update_quotes(self, symbol: str):
        last_timestamp = await self._get_last_timestamp(symbol)
        if last_timestamp:
            incremental_data = await self._fetch_since(symbol, last_timestamp)
        else:
            incremental_data = await self._fetch_full(symbol)
        await self._merge_and_save(symbol, incremental_data)
```

**增量判断逻辑**：
- 查询本地最新记录的 `trade_date`
- 仅获取 `trade_date > last_timestamp` 的数据
- 首次同步仍全量获取
- 增量数据追加到已有数据，不覆盖

### 3.3 交叉验证去重

**文件**: `tradingagents/dataflows/data_quality_engine.py`（修改）

```python
class DataQualityEngine:
    def __init__(self):
        self._request_cache = {}

    async def cross_validate(self, symbol: str, field: str):
        cache_key = f"{symbol}:{field}"
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]
        result = await self._do_cross_validate(symbol, field)
        self._request_cache[cache_key] = result
        return result

    def clear_request_cache(self):
        self._request_cache.clear()
```

**生命周期**：
- 每次分析开始时调用 `clear_request_cache()`
- 同一分析周期内相同(symbol, field)只获取一次
- 分析结束后自动释放

---

## 四、代码架构治理

### 4.1 interface.py 拆分

**当前**: `interface.py` 约1280行，混合所有市场/功能函数

**目标**: 拆分为4个门面模块 + 1个统一入口

```
tradingagents/dataflows/
├── interface.py              # 统一入口（<100行，仅做转发）
├── cn_market_facade.py       # A股门面（~250行）
├── hk_market_facade.py       # 港股门面（~200行）
├── us_market_facade.py       # 美股门面（~200行）
└── market_common_facade.py   # 公共门面（~150行）
```

**向后兼容**：所有现有函数签名保持不变

```python
# interface.py（重构后）
from .cn_market_facade import CNMarketFacade
from .hk_market_facade import HKMarketFacade
from .us_market_facade import USMarketFacade
from .market_common_facade import MarketCommonFacade

_interface = DataInterface()

def get_china_stock_info_unified(symbol, **kwargs):
    return _interface.cn.get_stock_info(symbol, **kwargs)
# ... 所有现有函数保持签名不变
```

### 4.2 DataOrchestrator 能力矩阵动态化

**文件**: `tradingagents/dataflows/data_orchestrator.py`（修改）

```python
class DataOrchestrator:
    def __init__(self):
        self._providers: dict[str, BaseDataProvider] = {}
        self._capability_matrix: dict[str, list[str]] = {}

    def register_provider(self, provider: BaseDataProvider):
        self._providers[provider.provider_name] = provider
        for cap, supported in provider.capabilities.items():
            if supported:
                self._capability_matrix.setdefault(cap, []).append(provider.provider_name)

    def get_providers_for(self, capability: str, market: str) -> list[BaseDataProvider]:
        provider_names = self._capability_matrix.get(capability, [])
        return [self._providers[name] for name in provider_names
                if market in self._providers[name].supported_markets]
```

### 4.3 LLM 创建逻辑统一

**文件**: `tradingagents/llm_clients/factory.py`（增强）+ `tradingagents/graph/trading_graph.py`（简化）

```python
# factory.py
class LLMFactory:
    _PROVIDER_ALIASES = {
        "deepseek": "openai_compatible",
        "siliconflow": "openai_compatible",
        "openrouter": "openai_compatible",
        "aihubmix": "openai_compatible",
        "dashscope": "dashscope",
        "google": "google",
        "anthropic": "anthropic",
        "openai": "openai",
    }

    @classmethod
    def create(cls, provider: str, model: str, api_key: str = None,
               base_url: str = None, **kwargs) -> BaseChatModel:
        canonical = cls._PROVIDER_ALIASES.get(provider, "openai_compatible")
        creator = cls._CREATORS[canonical]
        return creator(model=model, api_key=api_key, base_url=base_url, **kwargs)
```

```python
# trading_graph.py（简化后）
from tradingagents.llm_clients.factory import LLMFactory

class TradingGraph:
    def _create_llm(self, role: str) -> BaseChatModel:
        provider = self._get_provider_for_role(role)
        return LLMFactory.create(
            provider=provider,
            model=self._get_model_for_role(role),
            api_key=self._get_api_key_for_role(role),
            base_url=self._get_base_url_for_role(role),
        )
```

### 4.4 ConfigManager 收口（tradingagents内部）

**文件**: `tradingagents/config/config_manager.py`（增强）

**范围**：仅收口 `tradingagents/` 内部的配置读取，`app/` 的迁移作为后续任务

```python
class ConfigManager:
    def get(self, key: str, default=None):
        """统一读取：数据库配置 → 环境变量 → .env文件 → 默认值"""
        ...
```

### 4.5 私有方法公开化

**文件**: `cn_data_service.py`, `data_source_manager.py` 等（修改）

| 当前私有方法/属性 | 公开接口 | 说明 |
|-----------------|---------|------|
| `cn_data_service._get_tushare_stock_info()` | `cn_data_service.get_tushare_stock_info()` | 去掉下划线前缀 |
| `data_source_manager._health_tracker` | `data_source_manager.get_health_tracker()` | 添加getter方法 |
| `data_source_manager._snapshot_manager` | `data_source_manager.get_snapshot_manager()` | 添加getter方法 |

---

## 五、实施路线图

### Phase 1：数据源稳定性（最高优先级）

| # | 任务 | 改动文件 | 风险 |
|---|------|---------|------|
| 1.1 | 提取 BaseDataProvider 基类 | 新增 `base_provider.py` | 低 |
| 1.2 | AKShare monkey-patch 修复 | `akshare.py` | 中 |
| 1.3 | BaoStock + 新浪实时行情组合 | `baostock.py` | 低 |
| 1.4 | 新增腾讯财经 Provider | 新增 `tencent_finance.py` | 低 |
| 1.5 | 新增同花顺 Provider | 新增 `ths_direct.py` | 低 |
| 1.6 | DataOrchestrator 动态能力矩阵 | `data_orchestrator.py` | 低 |

**验收标准**：
- 所有现有单元测试通过
- 新增Provider的单元测试覆盖核心接口
- AKShare不再全局修改requests.get
- BaoStock可返回实时行情数据
- 港股名称映射覆盖>200只

### Phase 2：缓存与性能优化

| # | 任务 | 改动文件 | 风险 |
|---|------|---------|------|
| 2.1 | 统一缓存管理器 | 新增 `unified_cache_manager.py` | 中 |
| 2.2 | 行情增量更新 | `cn_data_service.py` 等 | 中 |
| 2.3 | 交叉验证去重 | `data_quality_engine.py` | 低 |
| 2.4 | 缓存穿透防护 | `unified_cache_manager.py` | 低 |

**验收标准**：
- 缓存命中率 > 60%（重复分析场景）
- 行情同步时间减少 > 30%
- 交叉验证零重复获取
- 并发场景无缓存穿透

### Phase 3：代码架构治理

| # | 任务 | 改动文件 | 风险 |
|---|------|---------|------|
| 3.1 | interface.py 拆分 | `interface.py` → 4个门面 | 中 |
| 3.2 | LLM工厂统一 | `factory.py` + `trading_graph.py` | 中 |
| 3.3 | ConfigManager收口 | `config_manager.py` | 低 |
| 3.4 | 私有方法公开化 | `cn_data_service.py` 等 | 低 |

**验收标准**：
- 所有现有函数签名保持不变
- interface.py < 100行
- trading_graph.py LLM创建逻辑 < 20行
- 无访问私有方法/属性

---

## 六、风险控制

| 风险 | 缓解措施 |
|------|---------|
| AKShare monkey-patch 修改影响现有调用 | 修改前跑全量测试，修改后对比行为 |
| interface.py 拆分破坏外部调用 | 保持所有函数签名不变，仅内部重构 |
| 新数据源API变更 | Provider基类统一异常处理，降级到其他源 |
| 缓存策略变更影响数据时效性 | 分级TTL + 可配置 + 热更新 |
| BaoStock+新浪组合数据冲突 | 明确优先级：实时数据以新浪为准，估值以BaoStock为准 |

---

## 七、不在本次范围的内容

- 付费数据源集成（Tushare高级权限、Finnhub API等）
- 前端优化（Vue组件/样式/交互）
- 后端Router/Service精简
- 全链路异步化（httpx.AsyncClient）
- Graph节点插件化
- Prometheus监控指标
- app/ 目录配置双轨制迁移

---

## 八、免费数据源能力矩阵（优化后）

| 数据源 | A股行情 | A股基本面 | A股新闻 | 港股行情 | 港股名称 | 美股行情 | 稳定性 |
|--------|---------|----------|---------|---------|---------|---------|--------|
| AKShare | ✅实时 | ✅完整 | ✅中等 | ⚠️有限 | ❌ | ❌ | ⚠️反爬 |
| BaoStock | ✅实时(新浪) | ✅五大能力 | ❌ | ❌ | ❌ | ❌ | ✅稳定 |
| 新浪财经 | ✅实时 | ❌ | ❌ | ✅实时 | ❌ | ❌ | ✅极稳 |
| 东方财富直接 | ✅实时+指标 | ⚠️8期摘要 | ❌ | ❌ | ❌ | ❌ | ✅稳定 |
| 腾讯财经(新) | ✅实时 | ❌ | ❌ | ✅实时 | ✅动态 | ✅实时 | ✅稳定 |
| 同花顺(新) | ❌ | ✅补充 | ❌ | ❌ | ❌ | ❌ | ✅稳定 |
| Tushare | ⚠️需Token | ✅最完整 | ❌需付费 | ❌ | ❌ | ❌ | ✅稳定 |
| yfinance | ❌ | ❌ | ❌ | ⚠️延迟 | ❌ | ⚠️延迟15min | ⚠️限流 |
