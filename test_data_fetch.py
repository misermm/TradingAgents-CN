import sys
print('=== Data Fetch Tests ===')

print('\n1. Testing EastMoneyDirectProvider.get_stock_news_direct...')
try:
    from tradingagents.dataflows.providers.china.eastmoney_direct import EastMoneyDirectProvider
    provider = EastMoneyDirectProvider()
    news_df = provider.get_stock_news_direct('000002')
    if news_df is not None and not news_df.empty:
        print(f'  OK: Got {len(news_df)} news items')
        for col in news_df.columns:
            print(f'    Column: {col}')
    else:
        print('  WARN: No news data returned')
except Exception as e:
    print(f'  WARN: {e}')

print('\n2. Testing snapshot_to_quant_text...')
try:
    from tradingagents.dataflows.china_fundamental_snapshot import snapshot_to_quant_text
    test_snapshot = {
        'fields': {
            'pe_ttm': {'value': 43.2, 'source': 'test', 'status': 'present'},
            'eps': {'value': 0.093, 'source': 'test', 'status': 'present'},
            'pb': {'value': 0.83, 'source': 'test', 'status': 'present'},
            'roe': {'value': -3.13, 'source': 'test', 'status': 'present'},
            'net_margin': {'value': -16.9, 'source': 'test', 'status': 'present'},
            'debt_ratio': {'value': 73.5, 'source': 'test', 'status': 'present'},
            'gross_margin': {'value': 15.2, 'source': 'test', 'status': 'present'},
            'revenue': {'value': 2800e8, 'source': 'test', 'status': 'present'},
            'net_profit': {'value': -60.4e8, 'source': 'test', 'status': 'present'},
            'total_assets': {'value': 18000e8, 'source': 'test', 'status': 'present'},
            'total_liabilities': {'value': 13230e8, 'source': 'test', 'status': 'present'},
            'current_assets': {'value': 12000e8, 'source': 'test', 'status': 'present'},
            'current_liabilities': {'value': 9000e8, 'source': 'test', 'status': 'present'},
            'operating_cash_flow': {'value': 50e8, 'source': 'test', 'status': 'present'},
            'free_cash_flow': {'value': -200e8, 'source': 'test', 'status': 'present'},
            'capital_expenditure': {'value': 100e8, 'source': 'test', 'status': 'present'},
            'book_value_per_share': {'value': 11.2, 'source': 'test', 'status': 'present'},
            'dividend_yield': {'value': 3.2, 'source': 'test', 'status': 'present'},
            'market_cap': {'value': 1100e8, 'source': 'test', 'status': 'present'},
        }
    }
    quant_text = snapshot_to_quant_text(test_snapshot)
    lines = [l for l in quant_text.strip().split('\n') if l.strip()]
    print(f'  OK: Generated {len(lines)} quant data lines')
    for line in lines[:8]:
        print(f'    {line}')
    if len(lines) > 8:
        print(f'    ... ({len(lines)-8} more lines)')
except Exception as e:
    import traceback
    print(f'  FAIL: {e}')
    traceback.print_exc()

print('\n3. Testing validate_data_consistency...')
try:
    from tradingagents.dataflows.china_fundamental_snapshot import validate_data_consistency
    test_data = {
        'fields': {
            'pe_ttm': {'value': 8.0, 'source': 'test', 'status': 'present'},
            'pe': {'value': 8.0, 'source': 'test', 'status': 'present'},
            'eps': {'value': -0.5, 'source': 'test', 'status': 'present'},
            'pb': {'value': 114.0, 'source': 'test', 'status': 'present'},
            'roe': {'value': -3.13, 'source': 'test', 'status': 'present'},
            'net_margin': {'value': 5.0, 'source': 'test', 'status': 'present'},
        }
    }
    warnings = validate_data_consistency(test_data)
    print(f'  OK: Found {len(warnings)} consistency warnings:')
    for w in warnings:
        print(f'    - [{w["rule"]}] {w["description"]}')
except Exception as e:
    import traceback
    print(f'  FAIL: {e}')
    traceback.print_exc()

print('\n4. Testing apply_consistency_fixes...')
try:
    from tradingagents.dataflows.china_fundamental_snapshot import apply_consistency_fixes
    test_data = {
        'fields': {
            'pe_ttm': {'value': 8.0, 'source': 'test', 'status': 'present'},
            'pe': {'value': 8.0, 'source': 'test', 'status': 'present'},
            'eps': {'value': -0.5, 'source': 'test', 'status': 'present'},
            'pb': {'value': 114.0, 'source': 'test', 'status': 'present'},
        }
    }
    fixed = apply_consistency_fixes(test_data)
    issues = fixed.get('consistency_issues', [])
    print(f'  OK: Found {len(issues)} consistency issues')
    pe_ttm_status = fixed['fields']['pe_ttm'].get('status', 'unknown')
    pe_status = fixed['fields']['pe'].get('status', 'unknown')
    pe_ttm_value = fixed['fields']['pe_ttm'].get('value', 'unknown')
    pe_value = fixed['fields']['pe'].get('value', 'unknown')
    print(f'  pe_ttm: value={pe_ttm_value}, status={pe_ttm_status}')
    print(f'  pe: value={pe_value}, status={pe_status}')
    if pe_ttm_status == 'corrected_to_na' and pe_status == 'corrected_to_na':
        print('  PASS: PE values correctly set to N/A due to negative EPS')
    else:
        print('  FAIL: PE values should be corrected to N/A')
except Exception as e:
    import traceback
    print(f'  FAIL: {e}')
    traceback.print_exc()

print('\n5. Testing full snapshot build for 000002...')
try:
    from tradingagents.dataflows.china_fundamental_snapshot import build_china_fundamental_snapshot, format_china_fundamental_snapshot_report
    snapshot = build_china_fundamental_snapshot('000002')
    fields = snapshot.get('fields', {})
    present_count = sum(1 for f in fields.values() if f.get('status') == 'present')
    print(f'  OK: Snapshot built with {present_count} present fields out of {len(fields)}')
    
    key_fields = ['pe_ttm', 'eps', 'pb', 'roe', 'net_margin', 'debt_ratio', 'revenue', 'net_profit']
    for kf in key_fields:
        f = fields.get(kf, {})
        val = f.get('value', 'N/A')
        src = f.get('source', 'N/A')
        status = f.get('status', 'N/A')
        print(f'    {kf}: value={val}, source={src}, status={status}')
    
    report = format_china_fundamental_snapshot_report(snapshot, '000002')
    has_consistency = '数据一致性验证' in report
    print(f'  Report length: {len(report)} chars')
    print(f'  Has consistency check: {has_consistency}')
except Exception as e:
    import traceback
    print(f'  WARN: {e}')
    traceback.print_exc()

print('\n=== All Data Fetch Tests Complete ===')
