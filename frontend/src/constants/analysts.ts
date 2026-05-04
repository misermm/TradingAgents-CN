export interface Analyst {
  id: string
  name: string
  description: string
  icon?: string
  group?: 'regular' | 'master'
}

export const ANALYSTS: Analyst[] = [
  {
    id: 'market',
    name: '市场分析师',
    description: '分析市场趋势、行业动态和宏观经济环境',
    icon: 'TrendCharts',
    group: 'regular'
  },
  {
    id: 'fundamentals',
    name: '基本面分析师',
    description: '分析公司财务状况、业务模式和竞争优势',
    icon: 'DataAnalysis',
    group: 'regular'
  },
  {
    id: 'news',
    name: '新闻分析师',
    description: '分析相关新闻、公告和市场事件的影响',
    icon: 'Document',
    group: 'regular'
  },
  {
    id: 'social',
    name: '社媒分析师',
    description: '分析社交媒体情绪、投资者心理和舆论导向',
    icon: 'ChatDotRound',
    group: 'regular'
  }
]

export const MASTER_ANALYSTS: Analyst[] = [
  {
    id: 'warren_buffett',
    name: '巴菲特',
    description: '价值投资：护城河+安全边际+能力圈',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'peter_lynch',
    name: '彼得·林奇',
    description: '成长投资：六种分类+PEG+翻番股',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'ben_graham',
    name: '格雷厄姆',
    description: '价值投资之父：量化筛选+安全边际',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'charlie_munger',
    name: '芒格',
    description: '理性投资：反向思考+多元思维模型',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'cathie_wood',
    name: '凯瑟琳·伍德',
    description: '颠覆式创新：5年视野+技术融合',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'bill_ackman',
    name: '阿克曼',
    description: '激进投资：集中投资+维权价值',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'phil_fisher',
    name: '费舍尔',
    description: '长期成长：十五要点+闲聊法',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'stanley_druckenmiller',
    name: '德鲁肯米勒',
    description: '宏观交易：宏观驱动+不对称风险收益',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'aswath_damodaran',
    name: '达莫达兰',
    description: '估值院长：DCF估值+故事与数字统一',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'michael_burry',
    name: '布瑞',
    description: '逆向投资：大空头+深度价值+安全边际至上',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'mohnish_pabrai',
    name: '帕伯莱',
    description: '丹霍投资：低风险高回报+不对称机会',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'nassim_taleb',
    name: '塔勒布',
    description: '黑天鹅风险：反脆弱+尾部对冲+杠铃策略',
    icon: 'User',
    group: 'master'
  },
  {
    id: 'rakesh_jhunjhunwala',
    name: '朱朱瓦拉',
    description: '新兴市场成长：宏观驱动+成长优先+长期信念',
    icon: 'User',
    group: 'master'
  }
]

export const ALL_ANALYSTS: Analyst[] = [...ANALYSTS, ...MASTER_ANALYSTS]

export const ANALYST_NAMES = ALL_ANALYSTS.map(analyst => analyst.name)

export const DEFAULT_ANALYSTS = ['市场分析师', '基本面分析师']

export const getAnalystByName = (name: string): Analyst | undefined => {
  return ALL_ANALYSTS.find(analyst => analyst.name === name)
}

export const getAnalystById = (id: string): Analyst | undefined => {
  return ALL_ANALYSTS.find(analyst => analyst.id === id)
}

export const isValidAnalyst = (name: string): boolean => {
  return ANALYST_NAMES.includes(name)
}

export const ANALYST_NAME_TO_ID_MAP: Record<string, string> = {
  '市场分析师': 'market',
  '基本面分析师': 'fundamentals',
  '新闻分析师': 'news',
  '社媒分析师': 'social',
  '巴菲特': 'warren_buffett',
  '彼得·林奇': 'peter_lynch',
  '格雷厄姆': 'ben_graham',
  '芒格': 'charlie_munger',
  '凯瑟琳·伍德': 'cathie_wood',
  '阿克曼': 'bill_ackman',
  '费舍尔': 'phil_fisher',
  '德鲁肯米勒': 'stanley_druckenmiller',
  '达莫达兰': 'aswath_damodaran',
  '布瑞': 'michael_burry',
  '帕伯莱': 'mohnish_pabrai',
  '塔勒布': 'nassim_taleb',
  '朱朱瓦拉': 'rakesh_jhunjhunwala'
}

export const convertAnalystNamesToIds = (names: string[]): string[] => {
  return names.map(name => ANALYST_NAME_TO_ID_MAP[name] || name)
}

export const convertAnalystIdsToNames = (ids: string[]): string[] => {
  const idToNameMap = Object.fromEntries(
    Object.entries(ANALYST_NAME_TO_ID_MAP).map(([name, id]) => [id, name])
  )
  return ids.map(id => idToNameMap[id] || id)
}

export const MODEL_TO_PROVIDER_MAP: Record<string, string> = {
  'qwen-turbo': 'dashscope',
  'qwen-plus': 'dashscope',
  'qwen-max': 'dashscope',
  'qwen-plus-latest': 'dashscope',
  'qwen-max-longcontext': 'dashscope',
  'gpt-3.5-turbo': 'openai',
  'gpt-4': 'openai',
  'gpt-4-turbo': 'openai',
  'gpt-4o': 'openai',
  'gpt-4o-mini': 'openai',
  'gemini-pro': 'google',
  'gemini-2.0-flash': 'google',
  'gemini-2.0-flash-thinking-exp': 'google',
  'deepseek-chat': 'deepseek',
  'deepseek-coder': 'deepseek',
  'glm-4': 'zhipu',
  'glm-3-turbo': 'zhipu',
  'chatglm3-6b': 'zhipu'
}

export const getProviderByModel = (modelName: string): string => {
  return MODEL_TO_PROVIDER_MAP[modelName] || 'dashscope'
}
