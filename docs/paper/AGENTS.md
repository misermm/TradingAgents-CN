<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# docs/paper

## Purpose
TradingAgents 学术论文存档，包含原始英文论文和完整中文翻译版，是理解项目理论基础的权威参考。

## Key Files

| File | Description |
|------|-------------|
| `TradingAgents_论文中文版.md` | 论文完整中文翻译：摘要、引言、相关工作、核心架构（分析师/研究员/交易员/风险管理）、辩论机制、工具系统、实验验证、结论 |
| `TradingAgents_paper.pdf` | 论文英文原版 PDF |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- 论文核心贡献：提出受交易公司启发的多智能体 LLM 股票交易框架
- 智能体角色：基本面分析师、情绪分析师、技术分析师、新闻分析师 → 看涨/看跌研究员 → 交易员 → 风险管理团队
- 关键创新：角色专业化 + 辩论机制 + 工具生态
- 实验结论：多智能体辩论准确率 ~90%，显著优于单智能体 ~70%
- 作者：Yijia Xiao, Edward Sun, Di Luo, Wei Wang（UCLA / MIT / Tauric Research）
- 中文版为完整翻译，可直接替代英文版阅读

### Testing Requirements
- 文档无需运行测试

### Common Patterns
- 论文结构：摘要 → 引言 → 相关工作 → 方法 → 实验 → 结论
- 框架架构：Analysts → Researchers (Bull/Bear) → Trader → Risk Management
- 实验指标：累积收益、年化收益、夏普比率、最大回撤

## Dependencies

### Internal
- `docs/learning/06-resources/paper-guide.md` - 论文解读与学习指南
- `docs/learning/04-analysis-principles/multi-agent-system.md` - 多智能体系统详解

### External
- 原始项目：https://github.com/TauricResearch/TradingAgents

<!-- MANUAL: Custom project notes can be added below -->
