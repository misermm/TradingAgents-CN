#!/usr/bin/env python3
"""检查新浪资产负债表的列名"""

import sys
sys.path.insert(0, '/app')

import akshare as ak

code = '000001'

print("=" * 50)
print("检查新浪资产负债表列名")
print("=" * 50)

# 资产负债表
bs_sina = ak.stock_financial_report_sina(stock=code, symbol='资产负债表')
if bs_sina is not None and not bs_sina.empty:
    print(f"\n资产负债表列名 ({len(bs_sina.columns)} 列):")
    for i, col in enumerate(bs_sina.columns):
        print(f"  {i}: {col}")
else:
    print("❌ 获取资产负债表失败")

# 利润表
is_sina = ak.stock_financial_report_sina(stock=code, symbol='利润表')
if is_sina is not None and not is_sina.empty:
    print(f"\n利润表列名 ({len(is_sina.columns)} 列):")
    for i, col in enumerate(is_sina.columns):
        print(f"  {i}: {col}")
else:
    print("❌ 获取利润表失败")

print("\n" + "=" * 50)
