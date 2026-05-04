"""
新浪财经数据提供器
直接调用新浪财经API获取A股和港股行情数据

特点：
- 新浪财经API稳定运行10+年，反爬策略宽松
- 实时行情数据延迟<3秒
- 无需API Key
- 使用ResilientHttpClient包装HTTP请求，提供重试/超时/熔断能力
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union

import pandas as pd

from ..base_provider import BaseStockDataProvider
from ..resilient_http_client import ResilientHttpClient

logger = logging.getLogger(__name__)


class SinaFinanceProvider(BaseStockDataProvider):
    """
    新浪财经数据提供器

    支持的数据类型：
    - A股实时行情（沪深两市）
    - A股历史K线数据
    - 港股实时行情
    """

    # 新浪财经API地址
    A_STOCK_QUOTE_URL = "http://hq.sinajs.cn/list={symbol}"
    A_STOCK_KLINE_URL = (
        "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        "CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={datalen}"
    )
    HK_STOCK_QUOTE_URL = "http://hq.sinajs.cn/list=rt_hk{code}"

    # 新浪财经请求头（必须包含Referer，否则可能被拒绝）
    HEADERS = {
        "Referer": "http://finance.sina.com.cn",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def __init__(self):
        """初始化新浪财经数据提供器"""
        super().__init__(provider_name="sina_finance")

        # 使用ResilientHttpClient包装HTTP请求
        self._http_client = ResilientHttpClient(
            max_retries=3,
            retry_delay=1.0,
            retry_backoff_factor=2.0,
            timeout_seconds=15.0,
            connect_timeout=5.0,
            rate_limit_per_second=2.0,
            name="sina_finance",
        )

        # 尝试导入requests
        self._requests = None
        try:
            import requests
            self._requests = requests
        except ImportError:
            logger.warning("⚠️ requests库未安装，新浪财经数据源不可用")

    async def connect(self) -> bool:
        """
        连接到新浪财经数据源

        通过请求上证指数实时行情验证连接可用性

        Returns:
            bool: 连接是否成功
        """
        if self._requests is None:
            self.connected = False
            return False

        try:
            result = self._http_client.call(
                self._fetch_a_stock_quote, "sh000001"
            )
            if result.success and result.data:
                self.connected = True
                self.logger.info("✅ 新浪财经数据源连接成功")
                return True
            else:
                self.connected = False
                self.logger.warning(f"⚠️ 新浪财经数据源连接失败: {result.error}")
                return False
        except Exception as e:
            self.connected = False
            self.logger.warning(f"⚠️ 新浪财经数据源连接异常: {e}")
            return False

    # ==================== A股实时行情 ====================

    def _normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码为新浪格式

        Args:
            symbol: 原始股票代码（如 600519, 000001）

        Returns:
            新浪格式代码（如 sh600519, sz000001）
        """
        symbol = str(symbol).strip()
        # 已经带有前缀的直接返回
        if symbol.startswith(("sh", "sz", "bj")):
            return symbol
        # 根据代码规则判断市场
        if symbol.startswith(("60", "68", "90")):
            return f"sh{symbol}"
        elif symbol.startswith(("00", "30", "20")):
            return f"sz{symbol}"
        elif symbol.startswith(("8", "4")):
            return f"bj{symbol}"
        else:
            # 默认按沪市处理
            return f"sh{symbol}"

    def _fetch_a_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取A股实时行情（同步方法，供ResilientHttpClient调用）

        Args:
            symbol: 新浪格式代码（如 sh600519）

        Returns:
            行情数据字典，失败返回None
        """
        sina_symbol = self._normalize_symbol(symbol)
        url = self.A_STOCK_QUOTE_URL.format(symbol=sina_symbol)

        try:
            resp = self._requests.get(url, headers=self.HEADERS, timeout=10)
            resp.encoding = "gbk"

            # 解析新浪行情数据
            # 格式: var hq_str_sh600519="贵州茅台,开盘价,昨收,当前价,..."
            match = re.search(r'="([^"]*)"', resp.text)
            if not match:
                return None

            fields = match.group(1).split(",")
            if len(fields) < 32:
                return None

            # 新浪行情字段顺序：
            # 0:名称 1:开盘 2:昨收 3:当前价 4:最高 5:最低
            # 6:买一 7:卖一 8:成交量(股) 9:成交额(元)
            # 30:日期 31:时间
            raw_name = fields[0]
            raw_open = self._safe_float(fields[1])
            raw_pre_close = self._safe_float(fields[2])
            raw_current = self._safe_float(fields[3])
            raw_high = self._safe_float(fields[4])
            raw_low = self._safe_float(fields[5])
            raw_volume = self._safe_float(fields[8])
            raw_amount = self._safe_float(fields[9])
            raw_date = fields[30] if len(fields) > 30 else ""
            raw_time = fields[31] if len(fields) > 31 else ""

            # 计算涨跌额和涨跌幅
            change = None
            pct_chg = None
            if raw_current is not None and raw_pre_close is not None and raw_pre_close != 0:
                change = round(raw_current - raw_pre_close, 2)
                pct_chg = round((raw_current - raw_pre_close) / raw_pre_close * 100, 2)

            # 提取纯数字代码
            code = sina_symbol[2:] if sina_symbol[:2] in ("sh", "sz", "bj") else symbol

            return {
                "symbol": code,
                "name": raw_name,
                "open": raw_open,
                "pre_close": raw_pre_close,
                "close": raw_current,
                "current_price": raw_current,
                "high": raw_high,
                "low": raw_low,
                "volume": raw_volume / 100 if raw_volume else None,  # 股→手
                "amount": raw_amount,
                "change": change,
                "pct_chg": pct_chg,
                "trade_date": raw_date,
                "trade_time": raw_time,
            }

        except Exception as e:
            self.logger.warning(f"⚠️ 新浪财经获取A股行情失败 {symbol}: {e}")
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
                self._fetch_a_stock_quote, symbol
            )

            if result.success and result.data:
                raw_data = result.data
                # 使用基类标准化方法
                standardized = self.standardize_quotes(raw_data)
                standardized["name"] = raw_data.get("name", "")
                standardized["trade_time"] = raw_data.get("trade_time", "")
                self.logger.info(
                    f"✅ 新浪财经获取A股行情成功: {symbol} "
                    f"价格={standardized.get('current_price')}"
                )
                return standardized
            else:
                self.logger.warning(f"⚠️ 新浪财经获取A股行情失败: {symbol} - {result.error}")
                return None

        except Exception as e:
            self.logger.error(f"❌ 新浪财经获取A股行情异常: {symbol} - {e}")
            return None

    # ==================== A股历史K线 ====================

    def _fetch_historical_kline(
        self, symbol: str, datalen: int = 250
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取A股历史K线数据（同步方法，供ResilientHttpClient调用）

        Args:
            symbol: 新浪格式代码（如 sh600519）
            datalen: 返回的数据条数

        Returns:
            K线数据列表，失败返回None
        """
        sina_symbol = self._normalize_symbol(symbol)
        url = self.A_STOCK_KLINE_URL.format(symbol=sina_symbol, datalen=datalen)

        try:
            resp = self._requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"

            # 新浪K线返回JSON数组格式
            if not resp.text or resp.text.strip() == "null":
                return None

            import json
            kline_data = json.loads(resp.text)

            if not isinstance(kline_data, list) or len(kline_data) == 0:
                return None

            # 标准化K线数据
            result = []
            for item in kline_data:
                result.append({
                    "date": item.get("day", ""),
                    "open": self._safe_float(item.get("open")),
                    "high": self._safe_float(item.get("high")),
                    "low": self._safe_float(item.get("low")),
                    "close": self._safe_float(item.get("close")),
                    "volume": self._safe_float(item.get("volume")),
                })

            return result

        except Exception as e:
            self.logger.warning(f"⚠️ 新浪财经获取历史K线失败 {symbol}: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: Union[str, date],
        end_date: Union[str, date] = None,
    ) -> Optional[pd.DataFrame]:
        """
        获取A股历史K线数据

        Args:
            symbol: 股票代码（如 600519）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            历史K线DataFrame
        """
        try:
            # 计算需要获取的数据条数（按交易日估算）
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                start_dt = datetime.combine(start_date, datetime.min.time())

            if end_date:
                if isinstance(end_date, str):
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                else:
                    end_dt = datetime.combine(end_date, datetime.min.time())
            else:
                end_dt = datetime.now()

            # 估算交易日数（一年约250个交易日）
            days_diff = (end_dt - start_dt).days
            datalen = min(max(int(days_diff * 250 / 365) + 50, 30), 1500)

            result = self._http_client.call(
                self._fetch_historical_kline, symbol, datalen
            )

            if result.success and result.data:
                kline_list = result.data

                # 转换为DataFrame
                df = pd.DataFrame(kline_list)

                if df.empty:
                    return None

                # 日期过滤
                df["date"] = pd.to_datetime(df["date"])
                df = df[df["date"] >= pd.Timestamp(start_dt)]
                if end_date:
                    df = df[df["date"] <= pd.Timestamp(end_dt)]

                # 设置索引
                df.set_index("date", inplace=True)
                df.sort_index(inplace=True)

                # 添加涨跌幅
                if "close" in df.columns and len(df) > 1:
                    df["pct_chg"] = df["close"].pct_change() * 100

                self.logger.info(
                    f"✅ 新浪财经获取历史K线成功: {symbol} "
                    f"共{len(df)}条数据"
                )
                return df
            else:
                self.logger.warning(
                    f"⚠️ 新浪财经获取历史K线失败: {symbol} - {result.error}"
                )
                return None

        except Exception as e:
            self.logger.error(f"❌ 新浪财经获取历史K线异常: {symbol} - {e}")
            return None

    # ==================== 港股实时行情 ====================

    def _fetch_hk_stock_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取港股实时行情（同步方法，供ResilientHttpClient调用）

        Args:
            code: 港股代码（如 00700, 09988）

        Returns:
            港股行情数据字典，失败返回None
        """
        # 新浪港股代码格式：rt_hk00700
        hk_code = code.lstrip("0") if len(code) == 5 and code.startswith("0") else code
        url = self.HK_STOCK_QUOTE_URL.format(code=hk_code)

        try:
            resp = self._requests.get(url, headers=self.HEADERS, timeout=10)
            resp.encoding = "gbk"

            # 解析港股行情数据
            match = re.search(r'="([^"]*)"', resp.text)
            if not match:
                return None

            fields = match.group(1).split(",")
            if len(fields) < 13:
                return None

            # 新浪港股行情字段顺序：
            # 0:英文名 1:中文名 2:开盘 3:昨收 4:最高 5:最低
            # 6:当前价 7:涨跌额 8:涨跌幅 9:买一 10:卖一
            # 11:成交量(股) 12:成交额(港元)
            raw_name = fields[1]
            raw_open = self._safe_float(fields[2])
            raw_pre_close = self._safe_float(fields[3])
            raw_high = self._safe_float(fields[4])
            raw_low = self._safe_float(fields[5])
            raw_current = self._safe_float(fields[6])
            raw_change = self._safe_float(fields[7])
            raw_pct_chg = self._safe_float(fields[8])
            raw_volume = self._safe_float(fields[11])
            raw_amount = self._safe_float(fields[12])

            return {
                "symbol": code,
                "name": raw_name,
                "open": raw_open,
                "pre_close": raw_pre_close,
                "close": raw_current,
                "current_price": raw_current,
                "high": raw_high,
                "low": raw_low,
                "change": raw_change,
                "pct_chg": raw_pct_chg,
                "volume": raw_volume,
                "amount": raw_amount,
                "market": "HK",
            }

        except Exception as e:
            self.logger.warning(f"⚠️ 新浪财经获取港股行情失败 {code}: {e}")
            return None

    async def get_hk_stock_quotes(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取港股实时行情

        Args:
            symbol: 港股代码（如 00700, 09988）

        Returns:
            标准化的港股行情数据字典
        """
        try:
            # 标准化港股代码（去除可能的前缀）
            code = str(symbol).strip()
            code = code.replace(".HK", "").replace(".hk", "")

            result = self._http_client.call(
                self._fetch_hk_stock_quote, code
            )

            if result.success and result.data:
                raw_data = result.data
                # 使用基类标准化方法
                standardized = self.standardize_quotes(raw_data)
                standardized["name"] = raw_data.get("name", "")
                standardized["market"] = "HK"
                self.logger.info(
                    f"✅ 新浪财经获取港股行情成功: {code} "
                    f"价格={standardized.get('current_price')}"
                )
                return standardized
            else:
                self.logger.warning(
                    f"⚠️ 新浪财经获取港股行情失败: {code} - {result.error}"
                )
                return None

        except Exception as e:
            self.logger.error(f"❌ 新浪财经获取港股行情异常: {symbol} - {e}")
            return None

    # ==================== 基类抽象方法实现 ====================

    async def get_stock_basic_info(
        self, symbol: str = None
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        获取股票基础信息

        新浪财经不提供独立的股票基础信息接口，
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
                "data_source": "sina_finance",
            }
        return None

    # ==================== 辅助方法 ====================

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """
        安全转换为浮点数

        Args:
            value: 待转换的值

        Returns:
            浮点数或None
        """
        if value is None or value == "" or value == "0.00":
            try:
                if value == "0.00":
                    return 0.0
            except Exception:
                pass
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
