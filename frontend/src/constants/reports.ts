export interface ReportMapping {
  key: string
  title: string
  category: string
}

export const REPORT_MAPPINGS: ReportMapping[] = [
  { key: 'market_report', title: '📈 市场技术分析', category: '分析师团队' },
  { key: 'china_market_report', title: '📈 A股市场分析', category: '分析师团队' },
  { key: 'sentiment_report', title: '💭 市场情绪分析', category: '分析师团队' },
  { key: 'news_report', title: '📰 新闻事件分析', category: '分析师团队' },
  { key: 'fundamentals_report', title: '💰 基本面分析', category: '分析师团队' },

  { key: 'warren_buffett_report', title: '🎩 巴菲特', category: '投资大师' },
  { key: 'peter_lynch_report', title: '🎩 彼得·林奇', category: '投资大师' },
  { key: 'ben_graham_report', title: '🎩 格雷厄姆', category: '投资大师' },
  { key: 'charlie_munger_report', title: '🎩 芒格', category: '投资大师' },
  { key: 'cathie_wood_report', title: '🎩 凯瑟琳·伍德', category: '投资大师' },
  { key: 'bill_ackman_report', title: '🎩 阿克曼', category: '投资大师' },
  { key: 'phil_fisher_report', title: '🎩 费舍尔', category: '投资大师' },
  { key: 'stanley_druckenmiller_report', title: '🎩 德鲁肯米勒', category: '投资大师' },
  { key: 'aswath_damodaran_report', title: '🎩 达莫达兰', category: '投资大师' },
  { key: 'michael_burry_report', title: '🎩 布瑞', category: '投资大师' },
  { key: 'mohnish_pabrai_report', title: '🎩 帕伯莱', category: '投资大师' },
  { key: 'nassim_taleb_report', title: '🎩 塔勒布', category: '投资大师' },
  { key: 'rakesh_jhunjhunwala_report', title: '🎩 朱朱瓦拉', category: '投资大师' },
  { key: 'master_consensus_report', title: '📊 大师共识', category: '投资大师' },

  { key: 'bull_researcher', title: '🐂 多头研究员', category: '研究团队' },
  { key: 'bear_researcher', title: '🐻 空头研究员', category: '研究团队' },
  { key: 'research_team_decision', title: '🔬 研究经理决策', category: '研究团队' },

  { key: 'trader_investment_plan', title: '💼 交易员计划', category: '交易团队' },

  { key: 'risky_analyst', title: '⚡ 激进分析师', category: '风险管理团队' },
  { key: 'safe_analyst', title: '🛡️ 保守分析师', category: '风险管理团队' },
  { key: 'neutral_analyst', title: '⚖️ 中性分析师', category: '风险管理团队' },
  { key: 'risk_management_decision', title: '👔 投资组合经理', category: '风险管理团队' },

  { key: 'final_trade_decision', title: '🎯 最终交易决策', category: '最终决策' },

  { key: 'investment_plan', title: '📋 投资建议', category: '其他' },
  { key: 'investment_debate_state', title: '🔬 研究团队决策（旧）', category: '其他' },
  { key: 'risk_debate_state', title: '⚖️ 风险管理团队（旧）', category: '其他' },
]

export const REPORT_NAME_MAP: Record<string, string> = Object.fromEntries(
  REPORT_MAPPINGS.map(m => [m.key, m.title])
)
