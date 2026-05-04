import re
from typing import Optional
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

_COMPANY_NAME_CACHE = {}

_US_COMPANY_NAMES = {
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet (Google)",
    "GOOG": "Alphabet (Google)",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "NFLX": "Netflix",
    "BRK.B": "Berkshire Hathaway",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "JNJ": "Johnson & Johnson",
    "WMT": "Walmart",
    "PG": "Procter & Gamble",
    "MA": "Mastercard",
    "HD": "Home Depot",
    "UNH": "UnitedHealth Group",
    "DIS": "Walt Disney",
    "BAC": "Bank of America",
    "XOM": "ExxonMobil",
    "PFE": "Pfizer",
    "CSCO": "Cisco",
    "ADBE": "Adobe",
    "CRM": "Salesforce",
    "INTC": "Intel",
    "AMD": "AMD",
    "PYPL": "PayPal",
    "UBER": "Uber",
    "COIN": "Coinbase",
}


def get_company_name(ticker: str, market_info: dict = None) -> str:
    if not ticker:
        return ticker

    cache_key = ticker.upper()
    if cache_key in _COMPANY_NAME_CACHE:
        return _COMPANY_NAME_CACHE[cache_key]

    result = _resolve_company_name(ticker, market_info)
    _COMPANY_NAME_CACHE[cache_key] = result
    return result


def _resolve_company_name(ticker: str, market_info: dict = None) -> str:
    ticker_upper = ticker.upper().replace(".", "")

    market_type = ""
    if market_info:
        market_type = market_info.get("market_type", market_info.get("market_name", ""))

    if market_type == "us_stocks" or (not market_type and re.match(r'^[A-Z]{1,5}$', ticker_upper)):
        if ticker_upper in _US_COMPANY_NAMES:
            return _US_COMPANY_NAMES[ticker_upper]
        name = _fetch_us_company_name_yfinance(ticker)
        if name:
            return name
        return f"美股{ticker}"

    if market_type == "a_shares" or (not market_type and re.match(r'^\d{6}$', ticker)):
        name = _fetch_cn_company_name(ticker)
        if name:
            return name
        return f"A股{ticker}"

    if market_type == "hk_stocks" or (not market_type and re.match(r'^\d{4,5}$', ticker)):
        name = _fetch_hk_company_name(ticker)
        if name:
            return name
        return f"港股{ticker}"

    return ticker


def _fetch_us_company_name_yfinance(ticker: str) -> Optional[str]:
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        name = info.get("shortName") or info.get("longName")
        if name and len(name) < 100:
            logger.debug(f"[CompanyUtils] yfinance resolved {ticker} -> {name}")
            return name
    except Exception as e:
        logger.debug(f"[CompanyUtils] yfinance failed for {ticker}: {e}")
    return None


def _fetch_cn_company_name(ticker: str) -> Optional[str]:
    try:
        import akshare as ak
        code6 = str(ticker).zfill(6)
        df = ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            row = df[df['code'] == code6]
            if not row.empty:
                name = str(row.iloc[0]['name'])
                if name:
                    return name
    except Exception as e:
        logger.debug(f"[CompanyUtils] AKShare name lookup failed for {ticker}: {e}")
    return None


def _fetch_hk_company_name(ticker: str) -> Optional[str]:
    try:
        import akshare as ak
        df = ak.stock_hk_spot_em()
        if df is not None and not df.empty:
            code_col = None
            for col in df.columns:
                if '代码' in str(col):
                    code_col = col
                    break
            if code_col:
                row = df[df[code_col].astype(str) == str(ticker).zfill(5)]
                if not row.empty:
                    name_col = None
                    for col in df.columns:
                        if '名称' in str(col):
                            name_col = col
                            break
                    if name_col:
                        name = str(row.iloc[0][name_col])
                        if name:
                            return name
    except Exception as e:
        logger.debug(f"[CompanyUtils] AKShare HK name lookup failed for {ticker}: {e}")
    return None
