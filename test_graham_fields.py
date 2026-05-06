#!/usr/bin/env python3
"""测试格雷厄姆关键字段提取"""

import sys
sys.path.insert(0, '/app')

from tradingagents.dataflows.optimized_china_data import OptimizedChinaDataProvider
from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")

print("=" * 50)
print("格雷厄姆关键字段测试")
print("=" * 50)

# 直接调用 _get_real_financial_metrics 获取 metrics 字典
print("\n[测试] 获取格雷厄姆关键字段...")
try:
    provider = OptimizedChinaDataProvider()

    # 直接获取 financial_estimates (metrics)
    result = provider._get_real_financial_metrics('000001', 11.36)

    if result:
        print(f"✅ 获取到财务指标: {len(result)} 个字段")

        # 检查关键格雷厄姆字段
        fields_to_check = [
            'eps', 'book_value_per_share', 'total_assets', 'total_liabilities',
            'current_assets', 'current_liabilities', 'revenue', 'net_profit'
        ]

        print("\n格雷厄姆关键字段检查:")
        for f in fields_to_check:
            val = result.get(f)
            if val and val != 'N/A':
                print(f"  ✅ {f}: {val}")
            else:
                print(f"  ❌ {f}: {val}")
    else:
        print("❌ 无法获取财务指标")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
