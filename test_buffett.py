#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

from tradingagents.dataflows.providers.china.akshare import get_akshare_provider
import asyncio

akshare_provider = get_akshare_provider()
if akshare_provider.connected:
    loop = asyncio.get_event_loop()
    financial_data = loop.run_until_complete(akshare_provider.get_financial_data('600519'))
    
    main_indicators = financial_data.get('main_indicators')
    if main_indicators is not None:
        if hasattr(main_indicators, 'columns'):
            print('=== MAIN INDICATORS COLUMNS ===')
            print(list(main_indicators.columns))
            print()
            print('=== ALL INDICATOR NAMES ===')
            for _, row in main_indicators.iterrows():
                print(f'  {row["指标"]}')
        elif isinstance(main_indicators, list) and main_indicators:
            import pandas as pd
            df = pd.DataFrame(main_indicators)
            print('=== MAIN INDICATORS COLUMNS ===')
            print(list(df.columns))
            print()
            print('=== ALL INDICATOR NAMES ===')
            for _, row in df.iterrows():
                print(f'  {row["指标"]}')
    else:
        print('main_indicators is None')
else:
    print('AKShare not connected')
