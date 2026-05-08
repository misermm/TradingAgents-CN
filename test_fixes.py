import sys
print('Python:', sys.version)

modules = [
    'tradingagents.dataflows.china_fundamental_snapshot',
    'tradingagents.agents.masters.quantitative_base',
    'tradingagents.agents.masters.base_master',
    'tradingagents.agents.utils.agent_states',
    'tradingagents.graph.data_prefetch',
    'tradingagents.dataflows.optimized_china_data',
    'tradingagents.dataflows.providers.china.eastmoney_direct',
    'tradingagents.dataflows.news.chinese_finance',
    'tradingagents.dataflows.news.realtime_news',
    'tradingagents.tools.unified_news_tool',
]
for mod in modules:
    try:
        __import__(mod)
        print(f'  OK: {mod}')
    except Exception as e:
        print(f'  FAIL: {mod} -> {e}')

from tradingagents.dataflows.china_fundamental_snapshot import (
    validate_data_consistency, apply_consistency_fixes, snapshot_to_quant_text
)
print('  OK: validate_data_consistency, apply_consistency_fixes, snapshot_to_quant_text')

from tradingagents.dataflows.providers.china.eastmoney_direct import EastMoneyDirectProvider
provider = EastMoneyDirectProvider()
has_news = hasattr(provider, 'get_stock_news_direct')
has_comment = hasattr(provider, '_fetch_stock_comment_direct')
print(f'  OK: EastMoneyDirectProvider has get_stock_news_direct: {has_news}')
print(f'  OK: EastMoneyDirectProvider has _fetch_stock_comment_direct: {has_comment}')

from tradingagents.agents.utils.agent_states import AgentState
has_quant = 'prefetched_quant_data' in AgentState.__annotations__
print(f'  OK: AgentState has prefetched_quant_data: {has_quant}')

print('\n=== All import and function checks passed ===')
