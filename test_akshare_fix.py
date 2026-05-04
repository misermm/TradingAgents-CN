#!/usr/bin/env python3
"""测试修复后的AKShare适配器降级机制"""
import sys
import os
sys.path.insert(0, '/app')

from app.services.data_sources.akshare_adapter import AKShareAdapter
from datetime import datetime

print("="*60)
print("测试AKShare适配器降级机制")
print("="*60)
print()

adapter = AKShareAdapter()

print("1. 测试get_realtime_quotes - 东方财富接口（应该失败后降级到新浪）")
print("-"*60)
try:
    result = adapter.get_realtime_quotes(source="eastmoney")
    if result:
        print(f"✅ 成功获取 {len(result)} 只股票的实时行情")
        codes = list(result.keys())[:3]
        for code in codes:
            data = result[code]
            print(f"  {code}: close={data.get('close')}, pct={data.get('pct_chg')}%")
    else:
        print("❌ 实时行情获取失败")
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    print(traceback.format_exc())
print()

print("2. 测试get_daily_basic - 东方财富失败后降级到新浪")
print("-"*60)
today = datetime.now().strftime("%Y%m%d")
try:
    df = adapter.get_daily_basic(today)
    if df is not None:
        print(f"✅ 成功获取 {len(df)} 只股票的每日基础数据")
        print(f"  列: {list(df.columns)}")
        if len(df) > 0:
            print(f"  示例: {df.iloc[0]['ts_code']} - {df.iloc[0]['name']}")
    else:
        print("❌ 每日基础数据获取失败")
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    print(traceback.format_exc())
print()

print("3. 测试get_stock_list")
print("-"*60)
try:
    df = adapter.get_stock_list()
    if df is not None:
        print(f"✅ 成功获取 {len(df)} 只股票的列表")
        if len(df) > 0:
            print(f"  示例: {df.iloc[0]['symbol']} - {df.iloc[0]['name']}")
    else:
        print("❌ 股票列表获取失败")
except Exception as e:
    print(f"❌ 异常: {e}")
print()

print("="*60)
print("测试完成")
print("="*60)
