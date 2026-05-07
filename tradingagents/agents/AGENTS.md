<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# agents

## Purpose
多智能体定义模块，包含分析师、主控智能体、研究员、风控辩论者、交易员和辅助工具。实现不同投资风格和分析视角的智能体协作。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，导出核心智能体类 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `analysts/` | 分析师智能体：基本面、市场、新闻、社交媒体、A股市场 (see `analysts/AGENTS.md`) |
| `masters/` | 主控智能体：投资大师风格 (Graham/Lynch/Buffett/Ackman 等) (see `masters/AGENTS.md`) |
| `managers/` | 管理器：研究管理、风险管理 (see `managers/AGENTS.md`) |
| `researchers/` | 研究员：看多/看空辩论 (see `researchers/AGENTS.md`) |
| `risk_mgmt/` | 风控辩论：激进/保守/中立 (see `risk_mgmt/AGENTS.md`) |
| `trader/` | 交易员：最终交易决策 (see `trader/AGENTS.md`) |
| `utils/` | 智能体工具：状态管理、注册表、内存、ChromaDB (see `utils/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- 智能体通过 `utils/analyst_registry.py` 注册和管理
- 新增智能体需在对应子目录创建文件并在注册表注册
- 主控智能体继承 `masters/base_master.py` 或 `masters/quantitative_base.py`
- 分析师智能体使用 LangChain Agent 模式

### Testing Requirements
- 智能体测试：`python -m pytest tests/ -k "analyst" -v`
- 主控测试：`python -m pytest tests/ -k "master" -v`

### Common Patterns
- 主控智能体模式：继承 BaseMaster → 定义投资哲学 → 实现 create_agent()
- 量化主控模式：继承 QuantitativeBase → 定义量化指标 → 实现评分逻辑
- 分析师模式：定义工具列表 → 创建 LangChain Agent → 返回分析结果

## Dependencies

### Internal
- `tradingagents/dataflows/` - 获取股票数据
- `tradingagents/llm_clients/` - LLM 调用
- `tradingagents/graph/` - 图编排调度

### External
- LangChain - Agent 框架
- ChromaDB - 向量存储 (记忆)

<!-- MANUAL: Custom project notes can be added below -->
