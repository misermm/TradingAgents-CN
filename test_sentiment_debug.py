import sys
sys.path.insert(0, r'e:\AI\TradingAgents-CN')
from tradingagents.dataflows.news.chinese_finance import get_chinese_social_sentiment

print("=== 测试报告生成: 600519 ===")
report = get_chinese_social_sentiment('600519', '2026-05-08')
print(report)
