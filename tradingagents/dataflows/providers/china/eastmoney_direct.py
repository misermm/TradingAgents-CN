"""
东方财富直接API数据提供器
绕过AKShare中间层，直接调用东方财富API获取行情和财务数据

特点：
- 绕过AKShare版本更新导致的接口失效风险
- 直接调用东方财富公开API，数据更新及时
- 支持批量行情、财务数据、行业数据
- 使用curl_cffi模拟浏览器请求头（如果可用），否则使用标准requests
- 使用ResilientHttpClient包装HTTP请求，提供重试/超时/熔断能力
"""

import logging
import re
import json
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union

import pandas as pd

from ..base_provider import BaseStockDataProvider
from ..resilient_http_client import ResilientHttpClient

logger = logging.getLogger(__name__)


class EastMoneyDirectProvider(BaseStockDataProvider):
    """
    东方财富直接API数据提供器

    支持的数据类型：
    - A股实时行情（单只/批量）
    - 财务数据（利润表、资产负债表等）
    - 行业数据（行业板块行情）
    """

    # 东方财富API地址
    # A股实时行情（单只）
    QUOTE_URL = (
        "http://push2.eastmoney.com/api/qt/stock/get"
        "?secid={secid}&fields=f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171"
    )
    # A股批量行情
    BATCH_QUOTE_URL = (
        "http://push2.eastmoney.com/api/qt/clist/get"
        "?pn=1&pz=5000&po=1&np=1&fltt=2&invt=2&fid=f3"
        "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        "&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f11,f62,f128,f136,f115,f152"
    )
    # 财务数据
    FINANCIAL_URL = (
        "http://datacenter.eastmoney.com/securities/api/data/v1/get"
        "?reportName=RPT_LICO_FN_CPD"
        "&columns=SECURITY_CODE,REPORT_DATE,BASIC_EPS,WEIGHTAVG_ROE,MGJYXJJE,XSMLL,YYZSR,YYZSRTBZZ,GSJLR,GSJLRTBZZ,KCFJCXSYJLR"
        "&filter=(SECURITY_CODE=\"{code}\")"
        "&pageSize=8&sortColumns=REPORT_DATE&sortTypes=-1"
    )
    # 资产负债表
    BALANCE_SHEET_URL = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get"
        "?reportName=RPT_DMSK_FN_BALANCE"
        "&columns=SECURITY_CODE,REPORT_DATE,TOTAL_ASSETS,TOTAL_LIABILITIES,TOTAL_CURRENT_ASSETS,TOTAL_CURRENT_LIABILITIES,MGJZC"
        "&filter=(SECURITY_CODE=%22{code}%22)"
        "&pageSize=5&sortColumns=REPORT_DATE&sortTypes=-1"
    )
    # 现金流量表
    CASH_FLOW_URL = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get"
        "?reportName=RPT_DMSK_FN_CASHFLOW"
        "&columns=SECURITY_CODE,REPORT_DATE,NETCASH_OPERATE,NETCASH_INVEST,NETCASH_FINANCE,BUY_FIX_ASSET"
        "&filter=(SECURITY_CODE=%22{code}%22)"
        "&pageSize=5&sortColumns=REPORT_DATE&sortTypes=-1"
    )
    # 股息率数据
    DIVIDEND_URL = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get"
        "?reportName=RPT_SHAREBONUS_DET"
        "&columns=SECURITY_CODE,REPORT_DATE,BONUS_SHARE_LISTDATE,CASH_PAY_TAX,CONVERT_PRICE,DIVIDEND_YIELD"
        "&filter=(SECURITY_CODE=%22{code}%22)"
        "&pageSize=5&sortColumns=REPORT_DATE&sortTypes=-1"
    )
    # 行业数据
    INDUSTRY_URL = (
        "http://push2.eastmoney.com/api/qt/clist/get"
        "?fs=m:90+t:2&fields=f2,f3,f4,f8,f12,f14,f104,f105,f128,f136,f140"
        "&pn=1&pz=100&po=1&np=1&fltt=2&invt=2&fid=f3"
    )

    # 个股新闻搜索API（东方财富搜索接口，JSONP格式）
    NEWS_SEARCH_URL = (
        "https://search-api-web.eastmoney.com/search/jsonp"
    )

    # 东方财富请求头（模拟浏览器）
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "http://quote.eastmoney.com",
    }

    # curl_cffi浏览器指纹（如果可用）
    CURL_CFFI_IMPERSONATE = "chrome120"

    def __init__(self):
        """初始化东方财富直接API数据提供器"""
        super().__init__(provider_name="eastmoney_direct")

        # 使用ResilientHttpClient包装HTTP请求
        self._http_client = ResilientHttpClient(
            max_retries=3,
            retry_delay=1.0,
            retry_backoff_factor=2.0,
            timeout_seconds=20.0,
            connect_timeout=5.0,
            rate_limit_per_second=1.5,
            name="eastmoney_direct",
        )

        # 尝试使用curl_cffi（更好的浏览器模拟），降级到标准requests
        self._use_curl_cffi = False
        self._requests = None
        try:
            from curl_cffi import requests as curl_requests
            self._requests = curl_requests
            self._use_curl_cffi = True
            self.logger.info("✅ 东方财富提供器使用curl_cffi（浏览器指纹模拟）")
        except ImportError:
            try:
                import requests
                self._requests = requests
                self.logger.info("ℹ️ 东方财富提供器使用标准requests库")
            except ImportError:
                self.logger.warning("⚠️ requests和curl_cffi均未安装，东方财富直接API不可用")

    def _get_secid(self, symbol: str) -> str:
        """
        将股票代码转换为东方财富secid格式

        东方财富secid格式：市场代码.股票代码
        - 沪市: 1.600519
        - 深市: 0.000001
        - 北交所: 0.830799

        Args:
            symbol: 股票代码（如 600519, 000001）

        Returns:
            secid字符串（如 1.600519, 0.000001）
        """
        symbol = str(symbol).strip()
        # 已经是secid格式
        if "." in symbol:
            return symbol

        # 根据代码规则判断市场
        if symbol.startswith(("60", "68", "90")):
            return f"1.{symbol}"  # 沪市
        elif symbol.startswith(("00", "30", "20")):
            return f"0.{symbol}"  # 深市
        elif symbol.startswith(("8", "4")):
            return f"0.{symbol}"  # 北交所
        else:
            return f"1.{symbol}"  # 默认沪市

    def _http_get(self, url: str, **kwargs) -> Any:
        """
        统一HTTP GET请求

        优先使用curl_cffi（带浏览器指纹），降级到标准requests

        Args:
            url: 请求URL
            **kwargs: 额外参数

        Returns:
            响应对象
        """
        if self._use_curl_cffi:
            return self._requests.get(
                url,
                headers=self.HEADERS,
                impersonate=self.CURL_CFFI_IMPERSONATE,
                timeout=15,
                **kwargs,
            )
        else:
            return self._requests.get(
                url,
                headers=self.HEADERS,
                timeout=15,
                **kwargs,
            )

    async def connect(self) -> bool:
        """
        连接到东方财富API

        通过请求上证指数实时行情验证连接可用性

        Returns:
            bool: 连接是否成功
        """
        if self._requests is None:
            self.connected = False
            return False

        try:
            result = self._http_client.call(
                self._fetch_stock_quote, "000001"
            )
            if result.success and result.data:
                self.connected = True
                self.logger.info("✅ 东方财富直接API连接成功")
                return True
            else:
                self.connected = False
                self.logger.warning(f"⚠️ 东方财富直接API连接失败: {result.error}")
                return False
        except Exception as e:
            self.connected = False
            self.logger.warning(f"⚠️ 东方财富直接API连接异常: {e}")
            return False

    # ==================== A股实时行情（单只） ====================

    def _fetch_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取A股实时行情（同步方法，供ResilientHttpClient调用）

        Args:
            symbol: 股票代码（如 600519）

        Returns:
            行情数据字典，失败返回None
        """
        secid = self._get_secid(symbol)
        url = self.QUOTE_URL.format(secid=secid)

        try:
            resp = self._http_get(url)
            data = resp.json()

            if not data or data.get("rc") != 0:
                return None

            item = data.get("data", {})
            if not item:
                return None

            # 东方财富字段映射
            # f43:最新价 f44:最高 f45:最低 f46:开盘 f47:成交量 f48:成交额
            # f50:量比 f51:涨停价 f52:跌停价 f55:换手率 f57:代码 f58:名称
            # f60:昨收 f116:总市值 f117:流通市值 f162:PE(动) f167:PE(TTM)
            # f168:PB f169:涨跌额 f170:涨跌幅 f171:振幅
            current = self._safe_float(item.get("f43"))
            pre_close = self._safe_float(item.get("f60"))
            raw_f43 = item.get("f43")
            raw_f60 = item.get("f60")

            current, pre_close, needs_div = self._normalize_a_share_prices(
                current, pre_close, symbol, raw_f43, raw_f60
            )

            # 计算涨跌额和涨跌幅（东方财富有时返回"-"
            # 表示停牌等异常状态）
            change = self._safe_float(item.get("f169"))
            pct_chg = self._safe_float(item.get("f170"))

            if needs_div:
                if change is not None:
                    change = round(change / 100, 4) if abs(change) > 1 else change
                open_price = self._safe_float(item.get("f46"))
                high = self._safe_float(item.get("f44"))
                low = self._safe_float(item.get("f45"))
                limit_up = self._safe_float(item.get("f51"))
                limit_down = self._safe_float(item.get("f52"))
                if open_price is not None and open_price > 50:
                    open_price = open_price / 100
                if high is not None and high > 50:
                    high = high / 100
                if low is not None and low > 50:
                    low = low / 100
                if limit_up is not None and limit_up > 50:
                    limit_up = limit_up / 100
                if limit_down is not None and limit_down > 50:
                    limit_down = limit_down / 100
            else:
                open_price = self._safe_float(item.get("f46"))
                high = self._safe_float(item.get("f44"))
                low = self._safe_float(item.get("f45"))
                limit_up = self._safe_float(item.get("f51"))
                limit_down = self._safe_float(item.get("f52"))

            # 如果东方财富未返回涨跌数据，自行计算
            if change is None and current is not None and pre_close is not None and pre_close != 0:
                change = round(current - pre_close, 2)
            if pct_chg is None and current is not None and pre_close is not None and pre_close != 0:
                pct_chg = round((current - pre_close) / pre_close * 100, 2)

            return {
                "symbol": str(item.get("f57", symbol)),
                "name": item.get("f58", ""),
                "open": open_price,
                "pre_close": pre_close,
                "close": current,
                "current_price": current,
                "high": high,
                "low": low,
                "volume": self._safe_float(item.get("f47")),
                "amount": self._safe_float(item.get("f48")),
                "change": change,
                "pct_chg": pct_chg,
                "amplitude": self._safe_float(item.get("f171")),
                "turnover_rate": self._safe_float(item.get("f55")),
                "volume_ratio": self._safe_float(item.get("f50")),
                "pe_dynamic": self._safe_float(item.get("f162")),
                "pe_ttm": self._safe_float(item.get("f167")),
                "pb": self._safe_float(item.get("f168")),
                "total_mv": self._safe_float(item.get("f116")),
                "circ_mv": self._safe_float(item.get("f117")),
                "limit_up": limit_up,
                "limit_down": limit_down,
            }

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富获取A股行情失败 {symbol}: {e}")
            return None

    async def get_stock_quotes(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取A股实时行情

        Args:
            symbol: 股票代码（如 600519, 000001）

        Returns:
            标准化的实时行情数据字典
        """
        try:
            result = self._http_client.call(
                self._fetch_stock_quote, symbol
            )

            if result.success and result.data:
                raw_data = result.data
                # 使用基类标准化方法
                standardized = self.standardize_quotes(raw_data)
                # 补充东方财富特有字段
                standardized["name"] = raw_data.get("name", "")
                standardized["turnover_rate"] = raw_data.get("turnover_rate")
                standardized["volume_ratio"] = raw_data.get("volume_ratio")
                standardized["pe_dynamic"] = raw_data.get("pe_dynamic")
                standardized["pe_ttm"] = raw_data.get("pe_ttm")
                standardized["pb"] = raw_data.get("pb")
                standardized["total_mv"] = raw_data.get("total_mv")
                standardized["circ_mv"] = raw_data.get("circ_mv")
                self.logger.info(
                    f"✅ 东方财富获取A股行情成功: {symbol} "
                    f"价格={standardized.get('current_price')} "
                    f"PE={standardized.get('pe_ttm')} PB={standardized.get('pb')}"
                )
                return standardized
            else:
                self.logger.warning(
                    f"⚠️ 东方财富获取A股行情失败: {symbol} - {result.error}"
                )
                return None

        except Exception as e:
            self.logger.error(f"❌ 东方财富获取A股行情异常: {symbol} - {e}")
            return None

    # ==================== A股批量行情 ====================

    def _fetch_batch_stock_quotes(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取A股批量行情（同步方法，供ResilientHttpClient调用）

        Returns:
            批量行情数据列表，失败返回None
        """
        try:
            resp = self._http_get(self.BATCH_QUOTE_URL)
            data = resp.json()

            if not data or data.get("rc") != 0:
                return None

            items = data.get("data", {}).get("diff", [])
            if not items:
                return None

            result = []
            for item in items:
                current = self._safe_float(item.get("f2"))
                pre_close = self._safe_float(item.get("f18"))

                change = self._safe_float(item.get("f4"))
                pct_chg = self._safe_float(item.get("f3"))

                if change is None and current is not None and pre_close is not None and pre_close != 0:
                    change = round(current - pre_close, 2)
                if pct_chg is None and current is not None and pre_close is not None and pre_close != 0:
                    pct_chg = round((current - pre_close) / pre_close * 100, 2)

                result.append({
                    "symbol": str(item.get("f12", "")),
                    "name": item.get("f14", ""),
                    "open": self._safe_float(item.get("f17")),
                    "pre_close": pre_close,
                    "close": current,
                    "current_price": current,
                    "high": self._safe_float(item.get("f15")),
                    "low": self._safe_float(item.get("f16")),
                    "volume": self._safe_float(item.get("f5")),
                    "amount": self._safe_float(item.get("f6")),
                    "change": change,
                    "pct_chg": pct_chg,
                    "amplitude": self._safe_float(item.get("f8")),
                    "turnover_rate": self._safe_float(item.get("f8")),
                    "pe_dynamic": self._safe_float(item.get("f9")),
                    "pb": self._safe_float(item.get("f23")),
                    "total_mv": self._safe_float(item.get("f20")),
                    "circ_mv": self._safe_float(item.get("f21")),
                })

            return result

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富获取批量行情失败: {e}")
            return None

    async def get_batch_stock_quotes(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取A股批量行情

        一次请求获取全市场A股实时行情数据

        Returns:
            批量行情数据列表
        """
        try:
            result = self._http_client.call(
                self._fetch_batch_stock_quotes
            )

            if result.success and result.data:
                self.logger.info(
                    f"✅ 东方财富获取批量行情成功: 共{len(result.data)}只股票"
                )
                return result.data
            else:
                self.logger.warning(
                    f"⚠️ 东方财富获取批量行情失败: {result.error}"
                )
                return None

        except Exception as e:
            self.logger.error(f"❌ 东方财富获取批量行情异常: {e}")
            return None

    # ==================== 财务数据 ====================

    def _fetch_financial_data(self, code: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取财务数据（同步方法，供ResilientHttpClient调用）

        Args:
            code: 股票代码（如 600519）

        Returns:
            财务数据列表，失败返回None
        """
        url = self.FINANCIAL_URL.format(code=code)

        try:
            resp = self._http_get(url)
            data = resp.json()

            if not data or data.get("code") != "0":
                return None

            result_data = data.get("result", {})
            items = result_data.get("data", [])

            if not items:
                return None

            financial_list = []
            for item in items:
                financial_list.append({
                    "symbol": item.get("SECURITY_CODE", code),
                    "report_date": item.get("REPORT_DATE", ""),
                    "basic_eps": self._safe_float(item.get("BASIC_EPS")),
                    "roe": self._safe_float(item.get("WEIGHTAVG_ROE")),
                    "ocf_per_share": self._safe_float(item.get("MGJYXJJE")),
                    "gross_margin": self._safe_float(item.get("XSMLL")),
                    "revenue": self._safe_float(item.get("YYZSR")),
                    "revenue_yoy": self._safe_float(item.get("YYZSRTBZZ")),
                    "net_profit": self._safe_float(item.get("GSJLR")),
                    "net_profit_yoy": self._safe_float(item.get("GSJLRTBZZ")),
                    "deducted_net_profit": self._safe_float(item.get("KCFJCXSYJLR")),
                })

            return financial_list

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富获取财务数据失败 {code}: {e}")
            return None

    def _fetch_balance_sheet_data(self, code: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取资产负债表数据（同步方法，供ResilientHttpClient调用）

        Args:
            code: 股票代码（如 600519）

        Returns:
            资产负债表数据列表，失败返回None
        """
        url = self.BALANCE_SHEET_URL.format(code=code)

        try:
            resp = self._http_get(url)
            data = resp.json()

            if not data or data.get("code") != "0":
                return None

            result_data = data.get("result", {})
            items = result_data.get("data", [])

            if not items:
                return None

            balance_list = []
            for item in items:
                balance_list.append({
                    "symbol": item.get("SECURITY_CODE", code),
                    "report_date": item.get("REPORT_DATE", ""),
                    "total_assets": self._safe_float(item.get("TOTAL_ASSETS")),
                    "total_liabilities": self._safe_float(item.get("TOTAL_LIABILITIES")),
                    "current_assets": self._safe_float(item.get("TOTAL_CURRENT_ASSETS")),
                    "current_liabilities": self._safe_float(item.get("TOTAL_CURRENT_LIABILITIES")),
                    "bvps": self._safe_float(item.get("MGJZC")),
                })

            return balance_list

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富获取资产负债表数据失败 {code}: {e}")
            return None

    def _fetch_cash_flow_data(self, code: str) -> Optional[List[Dict[str, Any]]]:
        url = self.CASH_FLOW_URL.format(code=code)

        try:
            resp = self._http_get(url)
            data = resp.json()

            if not data or data.get("code") != "0":
                return None

            result_data = data.get("result", {})
            items = result_data.get("data", [])

            if not items:
                return None

            cash_flow_list = []
            for item in items:
                ocf = self._safe_float(item.get("NETCASH_OPERATE"))
                capex = self._safe_float(item.get("BUY_FIX_ASSET"))
                fcf = None
                if ocf is not None and capex is not None:
                    fcf = ocf - abs(capex)
                cash_flow_list.append({
                    "symbol": item.get("SECURITY_CODE", code),
                    "report_date": item.get("REPORT_DATE", ""),
                    "operating_cash_flow": ocf,
                    "capital_expenditure": capex,
                    "free_cash_flow": fcf,
                })

            return cash_flow_list

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富获取现金流量表数据失败 {code}: {e}")
            return None

    def _fetch_dividend_data(self, code: str) -> Optional[Dict[str, Any]]:
        url = self.DIVIDEND_URL.format(code=code)

        try:
            resp = self._http_get(url)
            data = resp.json()

            if not data or data.get("code") != "0":
                return None

            result_data = data.get("result", {})
            items = result_data.get("data", [])

            if not items:
                return None

            latest = items[0]
            dividend_yield = self._safe_float(latest.get("DIVIDEND_YIELD"))
            if dividend_yield is not None and dividend_yield != 0.0:
                if dividend_yield > 1:
                    dividend_yield = dividend_yield / 100

            return {
                "symbol": latest.get("SECURITY_CODE", code),
                "dividend_yield": dividend_yield,
                "dividend_cash_per_10_shares": self._safe_float(latest.get("CASH_PAY_TAX")),
                "report_date": latest.get("REPORT_DATE", ""),
            }

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富获取股息率数据失败 {code}: {e}")
            return None

    async def get_financial_data(
        self, symbol: str, report_type: str = "annual"
    ) -> Optional[Dict[str, Any]]:
        """
        获取财务数据

        Args:
            symbol: 股票代码（如 600519）
            report_type: 报告类型 (annual/quarterly)

        Returns:
            财务数据字典，包含最近多期财务数据
        """
        try:
            code = str(symbol).strip()
            result = self._http_client.call(
                self._fetch_financial_data, code
            )

            if result.success and result.data:
                financial_list = result.data

                bs_result = self._http_client.call(
                    self._fetch_balance_sheet_data, code
                )
                if bs_result.success and bs_result.data:
                    bs_map = {}
                    for bs in bs_result.data:
                        rd = bs.get("report_date", "")
                        rd_key = rd[:10] if rd else ""
                        bs_map[rd_key] = bs

                    bs_fields = ["total_assets", "total_liabilities", "current_assets", "current_liabilities", "bvps"]
                    for period in financial_list:
                        rd = period.get("report_date", "")
                        rd_key = rd[:10] if rd else ""
                        matched_bs = bs_map.get(rd_key)
                        for field in bs_fields:
                            period[field] = matched_bs.get(field) if matched_bs else None

                cf_result = self._http_client.call(
                    self._fetch_cash_flow_data, code
                )
                if cf_result.success and cf_result.data:
                    cf_map = {}
                    for cf in cf_result.data:
                        rd = cf.get("report_date", "")
                        rd_key = rd[:10] if rd else ""
                        cf_map[rd_key] = cf

                    cf_fields = ["operating_cash_flow", "capital_expenditure", "free_cash_flow"]
                    for period in financial_list:
                        rd = period.get("report_date", "")
                        rd_key = rd[:10] if rd else ""
                        matched_cf = cf_map.get(rd_key)
                        for field in cf_fields:
                            if field not in period or period[field] is None:
                                period[field] = matched_cf.get(field) if matched_cf else None

                div_result = self._http_client.call(
                    self._fetch_dividend_data, code
                )
                dividend_fields = {}
                if div_result.success and div_result.data:
                    dividend_fields = {
                        "dividend_yield": div_result.data.get("dividend_yield"),
                        "dividend_cash_per_10_shares": div_result.data.get("dividend_cash_per_10_shares"),
                    }

                latest = financial_list[0] if financial_list else {}
                for k, v in dividend_fields.items():
                    if v is not None and k not in latest:
                        latest[k] = v

                summary = {
                    "symbol": code,
                    "data_source": "eastmoney_direct",
                    "report_type": report_type,
                    "periods": financial_list,
                    "latest": latest,
                }

                self.logger.info(
                    f"✅ 东方财富获取财务数据成功: {code} "
                    f"共{len(financial_list)}期数据"
                )
                return summary
            else:
                self.logger.warning(
                    f"⚠️ 东方财富获取财务数据失败: {code} - {result.error}"
                )
                return None

        except Exception as e:
            self.logger.error(f"❌ 东方财富获取财务数据异常: {symbol} - {e}")
            return None

    # ==================== 行业数据 ====================

    def _fetch_industry_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取行业板块数据（同步方法，供ResilientHttpClient调用）

        Returns:
            行业数据列表，失败返回None
        """
        try:
            resp = self._http_get(self.INDUSTRY_URL)
            data = resp.json()

            if not data or data.get("rc") != 0:
                return None

            items = data.get("data", {}).get("diff", [])
            if not items:
                return None

            result = []
            for item in items:
                result.append({
                    "code": str(item.get("f12", "")),
                    "name": item.get("f14", ""),
                    "change_pct": self._safe_float(item.get("f3")),
                    "change_amount": self._safe_float(item.get("f4")),
                    "turnover_rate": self._safe_float(item.get("f8")),
                    "rising_count": self._safe_float(item.get("f104")),
                    "falling_count": self._safe_float(item.get("f105")),
                    "leading_stock": item.get("f128", ""),
                    "leading_stock_change": self._safe_float(item.get("f136")),
                    "amount": self._safe_float(item.get("f140")),
                })

            return result

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富获取行业数据失败: {e}")
            return None

    async def get_industry_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取行业板块数据

        Returns:
            行业板块行情数据列表
        """
        try:
            result = self._http_client.call(
                self._fetch_industry_data
            )

            if result.success and result.data:
                self.logger.info(
                    f"✅ 东方财富获取行业数据成功: 共{len(result.data)}个行业"
                )
                return result.data
            else:
                self.logger.warning(
                    f"⚠️ 东方财富获取行业数据失败: {result.error}"
                )
                return None

        except Exception as e:
            self.logger.error(f"❌ 东方财富获取行业数据异常: {e}")
            return None

    # ==================== 个股新闻数据 ====================

    def _build_news_search_param(self, keyword: str, page_index: int = 1, page_size: int = 10) -> str:
        param = {
            "uid": "",
            "keyword": keyword,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default",
                    "pageIndex": page_index,
                    "pageSize": page_size,
                    "preTag": "",
                    "postTag": "",
                }
            },
        }
        return json.dumps(param, ensure_ascii=False)

    def _strip_jsonp(self, text: str) -> str:
        m = re.search(r"\((\{.*\})\)", text, re.DOTALL)
        if m:
            return m.group(1)
        return text

    def _fetch_stock_news(self, symbol: str, page_size: int = 10) -> Optional[pd.DataFrame]:
        try:
            from urllib.parse import quote

            symbol = str(symbol).strip().zfill(6)
            param_str = self._build_news_search_param(symbol, page_size=page_size)
            encoded_param = quote(param_str, safe='')
            url = f"{self.NEWS_SEARCH_URL}?cb=jQuery&param={encoded_param}"

            resp = self._http_get(url)
            raw_text = resp.text

            json_str = self._strip_jsonp(raw_text)
            data = json.loads(json_str)

            if not data:
                return None

            result = data.get("result", {})
            article_data = result.get("cmsArticleWebOld", [])

            if isinstance(article_data, dict):
                items = article_data.get("list", [])
            elif isinstance(article_data, list):
                items = article_data
            else:
                items = []

            if not items:
                return None

            rows = []
            for item in items:
                title = item.get("title", "")
                title = re.sub(r"<[^>]+>", "", title)

                content = item.get("content", "")
                content = re.sub(r"<[^>]+>", "", content)

                source = item.get("mediaName", "") or item.get("source", "") or "东方财富"
                publish_time = item.get("date", "") or item.get("showTime", "")
                news_url = item.get("url", "") or item.get("docUrl", "")

                rows.append({
                    "新闻标题": title,
                    "新闻内容": content,
                    "文章来源": source,
                    "发布时间": publish_time,
                    "新闻链接": news_url,
                })

            return pd.DataFrame(rows)

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富直接获取个股新闻失败 {symbol}: {e}")
            return None

    def get_stock_news_direct(self, symbol: str, page_size: int = 10) -> Optional[pd.DataFrame]:
        if self._requests is None:
            self.logger.warning("⚠️ HTTP客户端未初始化，无法获取新闻")
            return None

        try:
            result = self._http_client.call(
                self._fetch_stock_news, symbol, page_size
            )

            if result.success and result.data is not None and not result.data.empty:
                self.logger.info(
                    f"✅ 东方财富直接获取个股新闻成功: {symbol} 共{len(result.data)}条"
                )
                return result.data
            else:
                self.logger.warning(
                    f"⚠️ 东方财富直接获取个股新闻失败: {symbol} - {result.error}"
                )
                return None

        except Exception as e:
            self.logger.error(f"❌ 东方财富直接获取个股新闻异常: {symbol} - {e}")
            return None

    # ==================== 情绪数据（千股千评/人气排名/个股新闻） ====================

    COMMENT_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    HOT_RANK_URL = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    HOT_RANK_QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    NEWS_SEARCH_URL = "https://search-api-web.eastmoney.com/search/jsonp"

    COMMENT_TOKEN = "894050c76af8597a853f5b408b759f5d"

    def _fetch_stock_comment_direct(self, code: str) -> Optional[Dict[str, Any]]:
        """
        直接调用东方财富千股千评API（替代 ak.stock_comment_em()）

        API: datacenter-web.eastmoney.com/api/data/v1/get
        reportName: RPT_DMSK_TS_STOCKNEW

        Args:
            code: 股票代码（如 600519）

        Returns:
            千股千评数据字典，失败返回None
        """
        params = {
            "sortColumns": "SECURITY_CODE",
            "sortTypes": "1",
            "pageSize": "5",
            "pageNumber": "1",
            "reportName": "RPT_DMSK_TS_STOCKNEW",
            "quoteColumns": (
                "f2~01~SECURITY_CODE~CLOSE_PRICE,"
                "f8~01~SECURITY_CODE~TURNOVERRATE,"
                "f3~01~SECURITY_CODE~CHANGE_RATE,"
                "f9~01~SECURITY_CODE~PE_DYNAMIC"
            ),
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
            "token": self.COMMENT_TOKEN,
        }

        try:
            resp = self._http_get(self.COMMENT_URL, params=params)
            data = resp.json()

            if not data or (str(data.get("code")) != "0" and data.get("code") != 0):
                return None

            result_data = data.get("result", {})
            items = result_data.get("data", [])

            if not items:
                return None

            item = items[0]

            latest_price = self._safe_float(item.get("CLOSE_PRICE"))
            change_pct = self._safe_float(item.get("CHANGE_RATE"))
            turnover = self._safe_float(item.get("TURNOVERRATE"))
            pe = self._safe_float(item.get("PE_DYNAMIC"))
            main_cost = self._safe_float(item.get("PRIME_COST"))
            institution = self._safe_float(item.get("ORG_PARTICIPATE"))
            score = self._safe_float(item.get("TOTALSCORE"))
            rank = self._safe_float(item.get("RANK"))
            rank_change = self._safe_float(item.get("RANK_UP"))
            attention = self._safe_float(item.get("FOCUS"))
            name = str(item.get("SECURITY_NAME_ABBR", ""))

            if score is None:
                score = 50.0
            if rank is None:
                rank = 0
            if rank_change is None:
                rank_change = 0
            if attention is None:
                attention = 0
            if institution is None:
                institution = 0

            normalized_score = (score - 50) / 50 if score != 0 else 0
            normalized_score = max(-1.0, min(1.0, normalized_score))

            confidence = 0.5
            if attention > 80:
                confidence += 0.2
            elif attention > 60:
                confidence += 0.1
            if institution > 0.4:
                confidence += 0.15
            if turnover is not None and turnover > 1:
                confidence += 0.15
            confidence = min(confidence, 1.0)

            price_vs_cost = 0
            if main_cost and main_cost > 0 and latest_price and latest_price > 0:
                price_vs_cost = (latest_price - main_cost) / main_cost

            return {
                "sentiment_score": normalized_score,
                "confidence": confidence,
                "name": name,
                "score": score,
                "rank": int(rank),
                "rank_change": int(rank_change),
                "attention_index": attention,
                "institution_participation": institution,
                "main_cost": main_cost or 0,
                "latest_price": latest_price or 0,
                "price_vs_main_cost": round(price_vs_cost, 4),
                "change_pct": change_pct or 0,
                "turnover_rate": turnover or 0,
                "pe_ratio": pe or 0,
                "data_source": "eastmoney_comment_direct",
            }

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富直接获取千股千评失败 {code}: {e}")
            return None

    def _fetch_stock_hot_rank_direct(self, code: str) -> Optional[Dict[str, Any]]:
        """
        直接调用东方财富人气排名API（替代 ak.stock_hot_rank_em()）

        Step1: POST emappdata.eastmoney.com/stockrank/getAllCurrentList
        Step2: GET push2.eastmoney.com/api/qt/ulist.np/get

        Args:
            code: 股票代码（如 600519）

        Returns:
            人气排名数据字典，失败返回None
        """
        try:
            payload = {
                "appId": "appId01",
                "globalId": "786e4c21-70dc-435a-93bb-38",
                "marketType": "",
                "pageNo": 1,
                "pageSize": 100,
            }

            if self._use_curl_cffi:
                resp = self._requests.post(
                    self.HOT_RANK_URL,
                    json=payload,
                    headers=self.HEADERS,
                    impersonate=self.CURL_CFFI_IMPERSONATE,
                    timeout=15,
                )
            else:
                resp = self._requests.post(
                    self.HOT_RANK_URL,
                    json=payload,
                    headers=self.HEADERS,
                    timeout=15,
                )

            data = resp.json()
            rank_items = data.get("data", [])

            if not rank_items:
                return None

            code_upper = code.upper()
            target_variants = [f"SZ{code_upper}", f"SH{code_upper}", code, code_upper]

            matched_rank = None
            matched_sc = None
            for item in rank_items:
                sc = item.get("sc", "")
                if sc in target_variants:
                    matched_rank = item.get("rk")
                    matched_sc = sc
                    break

            if matched_rank is None:
                return {
                    "in_top100": False,
                    "sentiment_score": 0,
                    "confidence": 0.3,
                    "data_source": "eastmoney_hot_rank_direct",
                }

            secid = "0." + code if "SZ" in (matched_sc or "") else "1." + code

            params = {
                "ut": "f057cbcbce2a86e2866ab8877db1d059",
                "fltt": "2",
                "invt": "2",
                "fields": "f14,f3,f12,f2",
                "secids": secid,
            }

            resp2 = self._http_get(self.HOT_RANK_QUOTE_URL, params=params)
            data2 = resp2.json()

            name = ""
            change_pct = 0
            latest_price = 0

            diff = data2.get("data", {}).get("diff", [])
            if diff:
                quote = diff[0] if isinstance(diff, list) else diff
                name = str(quote.get("f14", ""))
                change_pct = self._safe_float(quote.get("f3")) or 0
                latest_price = self._safe_float(quote.get("f2")) or 0

            rank_int = int(matched_rank)
            hot_score = (101 - rank_int) / 100 if rank_int > 0 else 0
            hot_score = max(0, min(1.0, hot_score))

            sentiment_from_rank = 0
            if change_pct > 5:
                sentiment_from_rank = 0.5
            elif change_pct > 2:
                sentiment_from_rank = 0.3
            elif change_pct > 0:
                sentiment_from_rank = 0.1
            elif change_pct < -5:
                sentiment_from_rank = -0.5
            elif change_pct < -2:
                sentiment_from_rank = -0.3
            elif change_pct < 0:
                sentiment_from_rank = -0.1

            confidence = 0.6 if rank_int > 0 else 0.3

            return {
                "in_top100": True,
                "rank": rank_int,
                "name": name,
                "latest_price": latest_price,
                "change_pct": change_pct,
                "hot_score": hot_score,
                "sentiment_score": sentiment_from_rank,
                "confidence": confidence,
                "data_source": "eastmoney_hot_rank_direct",
            }

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富直接获取人气排名失败 {code}: {e}")
            return None

    def _fetch_stock_news_direct(self, code: str, page_size: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        直接调用东方财富个股新闻搜索API（替代 ak.stock_news_em()）

        API: search-api-web.eastmoney.com/search/jsonp

        Args:
            code: 股票代码（如 600519）
            page_size: 返回新闻数量

        Returns:
            新闻列表，失败返回None
        """
        import json as _json

        inner_param = {
            "uid": "",
            "keyword": code,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default",
                    "pageIndex": 1,
                    "pageSize": page_size,
                    "preTag": "<em>",
                    "postTag": "</em>",
                }
            },
        }

        cb_name = "jQuery_callback"
        params = {
            "cb": cb_name,
            "param": _json.dumps(inner_param, ensure_ascii=False),
            "_": str(int(datetime.now().timestamp() * 1000)),
        }

        news_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": f"https://so.eastmoney.com/news/s?keyword={code}",
            "Accept": "*/*",
        }

        try:
            if self._use_curl_cffi:
                resp = self._requests.get(
                    self.NEWS_SEARCH_URL,
                    params=params,
                    headers=news_headers,
                    impersonate=self.CURL_CFFI_IMPERSONATE,
                    timeout=15,
                )
            else:
                resp = self._requests.get(
                    self.NEWS_SEARCH_URL,
                    params=params,
                    headers=news_headers,
                    timeout=15,
                )

            text = resp.text

            prefix = cb_name + "("
            if text.startswith(prefix):
                text = text[len(prefix):]
            if text.endswith(")"):
                text = text[:-1]

            data = _json.loads(text)

            articles = data.get("result", {}).get("cmsArticleWebOld", [])
            if not articles:
                return None

            news_list = []
            for article in articles:
                title = str(article.get("title", ""))
                content = str(article.get("content", ""))
                source = str(article.get("mediaName", ""))
                pub_time = str(article.get("date", ""))
                article_code = str(article.get("code", ""))
                url = f"http://finance.eastmoney.com/a/{article_code}.html" if article_code else ""

                news_list.append({
                    "title": title,
                    "content": content[:500],
                    "source": source,
                    "publish_time": pub_time,
                    "url": url,
                })

            return news_list

        except Exception as e:
            self.logger.warning(f"⚠️ 东方财富直接获取个股新闻失败 {code}: {e}")
            return None

    # ==================== 基类抽象方法实现 ====================

    async def get_stock_basic_info(
        self, symbol: str = None
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        获取股票基础信息

        东方财富直接API不提供独立的股票基础信息接口，
        通过实时行情接口获取部分基础信息

        Args:
            symbol: 股票代码

        Returns:
            股票基础信息字典
        """
        if not symbol:
            return None

        quotes = await self.get_stock_quotes(symbol)
        if quotes:
            return {
                "code": quotes.get("code", symbol),
                "name": quotes.get("name", ""),
                "symbol": quotes.get("symbol", symbol),
                "data_source": "eastmoney_direct",
            }
        return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: Union[str, date],
        end_date: Union[str, date] = None,
    ) -> Optional[pd.DataFrame]:
        """
        获取历史数据

        东方财富直接API的历史K线接口较为复杂，
        暂不实现，建议使用新浪财经或AKShare获取历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            历史数据DataFrame
        """
        self.logger.info(
            f"ℹ️ 东方财富直接API暂不支持历史K线，建议使用新浪财经或AKShare: {symbol}"
        )
        return None

    # ==================== 辅助方法 ====================

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """
        安全转换为浮点数

        东方财富API可能返回"-"表示无效值

        Args:
            value: 待转换的值

        Returns:
            浮点数或None
        """
        if value is None or value == "" or value == "-":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _normalize_a_share_prices(
        self,
        current: Optional[float],
        pre_close: Optional[float],
        symbol: str,
        raw_f43: Any = None,
        raw_f60: Any = None,
    ) -> tuple:
        if current is None or pre_close is None:
            return current, pre_close, False

        is_a_share = (
            symbol
            and len(symbol) == 6
            and symbol[:3] in ("000", "001", "002", "003", "300", "301")
            or (len(symbol) == 6 and symbol[:3] in ("600", "601", "603", "605", "688", "689"))
        )
        if not is_a_share:
            return current, pre_close, False

        f43_is_int = isinstance(raw_f43, int) or (
            isinstance(raw_f43, float) and raw_f43 == int(raw_f43)
        )
        f60_is_int = isinstance(raw_f60, int) or (
            isinstance(raw_f60, float) and raw_f60 == int(raw_f60)
        )

        both_large = current > 50 and pre_close > 50
        both_int_like = f43_is_int and f60_is_int
        ratio_normal = 0.8 <= (current / pre_close) <= 1.2 if pre_close != 0 else False
        normalized_current = current / 100
        normalized_pre_close = pre_close / 100
        normalized_reasonable = (
            0.1 <= normalized_current <= 500 and 0.1 <= normalized_pre_close <= 500
        )

        needs_div = both_large and both_int_like and ratio_normal and normalized_reasonable

        if needs_div:
            self.logger.info(
                f"🔧 [价格校正] 检测到东方财富API返回分单位价格: {symbol} "
                f"原始 current={current}, pre_close={pre_close} "
                f"→ 校正后 current={normalized_current}, pre_close={normalized_pre_close}"
            )
            return normalized_current, normalized_pre_close, True

        return current, pre_close, False
