"""
中国市场数据提供器
包含 A股、港股等中国市场的数据源
"""

# 导入 AKShare 提供器
try:
    from .akshare import AKShareProvider
    AKSHARE_AVAILABLE = True
except ImportError:
    AKShareProvider = None
    AKSHARE_AVAILABLE = False

# 导入 Tushare 提供器
try:
    from .tushare import TushareProvider
    TUSHARE_AVAILABLE = True
except ImportError:
    TushareProvider = None
    TUSHARE_AVAILABLE = False

# 导入 Baostock 提供器
try:
    from .baostock import BaostockProvider
    BAOSTOCK_AVAILABLE = True
except ImportError:
    BaostockProvider = None
    BAOSTOCK_AVAILABLE = False

# 导入新浪财经提供器
try:
    from .sina_finance import SinaFinanceProvider
    SINA_AVAILABLE = True
except ImportError:
    SinaFinanceProvider = None
    SINA_AVAILABLE = False

# 导入东方财富直接API提供器
try:
    from .eastmoney_direct import EastMoneyDirectProvider
    EASTMONEY_AVAILABLE = True
except ImportError:
    EastMoneyDirectProvider = None
    EASTMONEY_AVAILABLE = False

# 导入基本面快照工具
try:
    from .fundamentals_snapshot import get_fundamentals_snapshot
    FUNDAMENTALS_SNAPSHOT_AVAILABLE = True
except ImportError:
    get_fundamentals_snapshot = None
    FUNDAMENTALS_SNAPSHOT_AVAILABLE = False

__all__ = [
    'AKShareProvider',
    'AKSHARE_AVAILABLE',
    'TushareProvider',
    'TUSHARE_AVAILABLE',
    'BaostockProvider',
    'BAOSTOCK_AVAILABLE',
    'SinaFinanceProvider',
    'SINA_AVAILABLE',
    'EastMoneyDirectProvider',
    'EASTMONEY_AVAILABLE',
    'get_fundamentals_snapshot',
    'FUNDAMENTALS_SNAPSHOT_AVAILABLE',
]

