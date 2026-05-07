<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# masters

## Purpose
主控智能体，模拟不同投资大师的风格进行投资决策。包含定性大师（价值投资、成长投资等）和量化大师（基于量化指标的评分系统）。

## Key Files

| File | Description |
|------|-------------|
| `base_master.py` | 定性主控基类，定义投资哲学和分析框架 |
| `quantitative_base.py` | 量化主控基类，定义量化评分框架 |
| `master_consensus.py` | 主控共识机制，综合多位大师意见 |
| `warren_buffett.py` | 沃伦·巴菲特：价值投资、护城河分析 |
| `charlie_munger.py` | 查理·芒格：理性投资、多元思维 |
| `ben_graham.py` | 本杰明·格雷厄姆：安全边际、价值投资 |
| `phil_fisher.py` | 菲利普·费舍尔：成长股投资 |
| `peter_lynch.py` | 彼得·林奇：PEG 估值、生活投资 |
| `bill_ackman.py` | 比尔·阿克曼：激进投资 |
| `cathie_wood.py` | 凯瑟琳·伍德：创新科技投资 |
| `nassim_taleb.py` | 纳西姆·塔勒布：反脆弱、黑天鹅 |
| `michael_burry.py` | 迈克尔·布瑞：深度价值、逆向投资 |
| `aswath_damodaran.py` | 阿斯瓦斯·达莫达兰：估值大师 |
| `mohnish_pabrai.py` | 莫尼什·帕布莱：价值套利 |
| `rakesh_jhunjhunwala.py` | 拉凯什·琼俊瓦拉：印度价值投资 |
| `stanley_druckenmiller.py` | 斯坦利·德鲁肯米勒：宏观交易 |
| `quant_buffett.py` | 量化巴菲特 |
| `quant_graham.py` | 量化格雷厄姆 |
| `quant_lynch.py` | 量化林奇 |
| `quant_fisher.py` | 量化费舍尔 |
| `quant_ackman.py` | 量化阿克曼 |
| `quant_wood.py` | 量化伍德 |
| `quant_taleb.py` | 量化塔勒布 |
| `quant_burry.py` | 量化布瑞 |
| `quant_munger.py` | 量化芒格 |
| `quant_pabrai.py` | 量化帕布莱 |
| `quant_damodaran.py` | 量化达莫达兰 |
| `quant_druckenmiller.py` | 量化德鲁肯米勒 |
| `quant_jhunjhunwala.py` | 量化琼俊瓦拉 |
| `__init__.py` | 包初始化，导出所有主控类 |

## Subdirectories
无

## For AI Agents

### Working In This Directory
- 定性主控继承 `base_master.py` 的 BaseMaster
- 量化主控继承 `quantitative_base.py` 的 QuantitativeBase
- 新增主控需创建文件并在 `__init__.py` 导出
- `master_consensus.py` 实现多主控意见综合

### Testing Requirements
- 主控测试：`python -m pytest tests/ -k "master" -v`

### Common Patterns
- 定性主控：继承 BaseMaster → 定义投资哲学 prompt → 实现 create_agent()
- 量化主控：继承 QuantitativeBase → 定义评分指标 → 实现评分逻辑

## Dependencies

### Internal
- `tradingagents/agents/analysts/` - 使用分析师结果
- `tradingagents/llm_clients/` - LLM 调用

### External
- LangChain - Agent 框架

<!-- MANUAL: Custom project notes can be added below -->
