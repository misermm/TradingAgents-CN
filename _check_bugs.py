import sys, os, importlib, traceback

os.chdir(r'e:\AI\TradingAgents-CN')
sys.path.insert(0, r'e:\AI\TradingAgents-CN')

bugs = []

# 1. Check akshare_utils.py import issue
print("=" * 60)
print("BUG #1: akshare_utils.py ImportError")
print("=" * 60)
try:
    import tradingagents.dataflows.akshare_utils
except ImportError as e:
    print(f"  File: tradingagents/dataflows/akshare_utils.py")
    print(f"  Line: 9-12")
    print(f"  Error: {e}")
    print(f"  Cause: get_hk_stock_data_akshare and get_hk_stock_info_akshare")
    print(f"         are in hk_data_service.py but not re-exported by interface.py")
    bugs.append({
        'file': 'tradingagents/dataflows/akshare_utils.py',
        'line': '9-12',
        'type': 'ImportError',
        'message': 'cannot import name get_hk_stock_data_akshare from tradingagents.dataflows.interface; these functions exist in hk_data_service.py but are not re-exported by interface.py'
    })

# 2. Check each module for runtime attribute errors
print()
print("=" * 60)
print("Runtime import check for all modules")
print("=" * 60)

modules = [
    'tradingagents.dataflows.china_fundamental_snapshot',
    'tradingagents.agents.masters.base_master',
    'tradingagents.agents.masters.quantitative_base',
    'tradingagents.agents.masters.quant_buffett',
    'tradingagents.agents.masters.quant_lynch',
    'tradingagents.agents.utils.agent_states',
    'tradingagents.graph.data_prefetch',
    'tradingagents.dataflows.optimized_china_data',
    'tradingagents.dataflows.providers.china.eastmoney_direct',
    'tradingagents.dataflows.news.chinese_finance',
    'tradingagents.dataflows.news.realtime_news',
    'tradingagents.tools.unified_news_tool',
    'tradingagents.agents.analysts.fundamentals_analyst',
    'tradingagents.dataflows.akshare_utils',
]

for mod_name in modules:
    try:
        mod = importlib.import_module(mod_name)
        print(f"OK: {mod_name}")
    except ImportError as e:
        tb = traceback.format_exc()
        lines = tb.strip().split('\n')
        error_line = None
        for line in lines:
            if 'File' in line and mod_name.replace('.', '/') in line:
                error_line = line.strip()
        print(f"FAIL: {mod_name}")
        print(f"  ImportError: {e}")
        if error_line:
            print(f"  Location: {error_line}")
        bugs.append({
            'file': mod_name.replace('.', '/') + '.py',
            'line': '?',
            'type': 'ImportError',
            'message': str(e)
        })
    except Exception as e:
        tb = traceback.format_exc()
        print(f"FAIL: {mod_name}")
        print(f"  {type(e).__name__}: {e}")
        bugs.append({
            'file': mod_name.replace('.', '/') + '.py',
            'line': '?',
            'type': type(e).__name__,
            'message': str(e)
        })

# 3. Check for specific known issues
print()
print("=" * 60)
print("Cross-module dependency checks")
print("=" * 60)

# Check if interface.py re-exports hk akshare functions
import tradingagents.dataflows.interface as iface
import tradingagents.dataflows.hk_data_service as hk_svc

hk_akshare_funcs = ['get_hk_stock_data_akshare', 'get_hk_stock_info_akshare']
for func_name in hk_akshare_funcs:
    in_iface = hasattr(iface, func_name)
    in_hk = hasattr(hk_svc, func_name)
    if not in_iface and in_hk:
        print(f"BUG: {func_name} exists in hk_data_service but NOT re-exported by interface.py")
        bugs.append({
            'file': 'tradingagents/dataflows/interface.py',
            'line': '20-23',
            'type': 'MissingReExport',
            'message': f'{func_name} exists in hk_data_service.py but is not re-exported by interface.py, causing ImportError in akshare_utils.py'
        })

# 4. Check fundamentals_analyst for import issues
print()
print("Checking fundamentals_analyst imports...")
try:
    from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst
    print("OK: create_fundamentals_analyst importable")
except ImportError as e:
    print(f"FAIL: {e}")
    bugs.append({
        'file': 'tradingagents/agents/analysts/fundamentals_analyst.py',
        'line': '?',
        'type': 'ImportError',
        'message': str(e)
    })

# 5. Check data_prefetch for import issues
print()
print("Checking data_prefetch imports...")
try:
    from tradingagents.graph.data_prefetch import DataPrefetch
    print("OK: DataPrefetch importable")
except ImportError as e:
    print(f"FAIL: {e}")
    bugs.append({
        'file': 'tradingagents/graph/data_prefetch.py',
        'line': '?',
        'type': 'ImportError',
        'message': str(e)
    })

# 6. Check quant agents
print()
print("Checking quant agent imports...")
for name in ['quant_buffett', 'quant_lynch', 'quantitative_base']:
    mod_name = f'tradingagents.agents.masters.{name}'
    try:
        mod = importlib.import_module(mod_name)
        print(f"OK: {mod_name}")
    except Exception as e:
        print(f"FAIL: {mod_name}: {e}")
        bugs.append({
            'file': f'tradingagents/agents/masters/{name}.py',
            'line': '?',
            'type': type(e).__name__,
            'message': str(e)
        })

# 7. Check agent_states
print()
print("Checking agent_states...")
try:
    from tradingagents.agents.utils.agent_states import AgentState
    print("OK: AgentState importable")
    fields = AgentState.__annotations__ if hasattr(AgentState, '__annotations__') else {}
    print(f"  Fields: {list(fields.keys())[:10]}...")
except Exception as e:
    print(f"FAIL: {e}")
    bugs.append({
        'file': 'tradingagents/agents/utils/agent_states.py',
        'line': '?',
        'type': type(e).__name__,
        'message': str(e)
    })

# Summary
print()
print("=" * 60)
print(f"TOTAL BUGS FOUND: {len(bugs)}")
print("=" * 60)
for i, bug in enumerate(bugs, 1):
    print(f"\nBug #{i}:")
    print(f"  File: {bug['file']}")
    print(f"  Line: {bug['line']}")
    print(f"  Type: {bug['type']}")
    print(f"  Message: {bug['message']}")
