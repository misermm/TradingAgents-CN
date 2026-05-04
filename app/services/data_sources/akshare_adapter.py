"""
AKShare data source adapter
"""
from typing import Optional, Dict
import logging
from datetime import datetime, timedelta
import pandas as pd

from .base import DataSourceAdapter

logger = logging.getLogger(__name__)


class AKShareAdapter(DataSourceAdapter):
    """AKShare数据源适配器"""

    def __init__(self):
        super().__init__()  # 调用父类初始化

    @property
    def name(self) -> str:
        return "akshare"

    def _get_default_priority(self) -> int:
        return 2  # 数字越大优先级越高

    def is_available(self) -> bool:
        """检查AKShare是否可用"""
        try:
            import akshare as ak  # noqa: F401
            return True
        except ImportError:
            return False

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """获取股票列表（使用 AKShare 的 stock_info_a_code_name 接口获取真实股票名称）"""
        if not self.is_available():
            return None
        try:
            import akshare as ak
            logger.info("AKShare: Fetching stock list with real names from stock_info_a_code_name()...")

            # 使用 AKShare 的 stock_info_a_code_name 接口获取股票代码和名称
            df = ak.stock_info_a_code_name()

            if df is None or df.empty:
                logger.warning("AKShare: stock_info_a_code_name() returned empty data")
                return None

            # 标准化列名（AKShare 返回的列名可能是中文）
            # 通常返回的列：code（代码）、name（名称）
            df = df.rename(columns={
                'code': 'symbol',
                '代码': 'symbol',
                'name': 'name',
                '名称': 'name'
            })

            # 确保有必需的列
            if 'symbol' not in df.columns or 'name' not in df.columns:
                logger.error(f"AKShare: Unexpected column names: {df.columns.tolist()}")
                return None

            # 生成 ts_code 和其他字段
            def generate_ts_code(code: str) -> str:
                """根据股票代码生成 ts_code"""
                if not code:
                    return ""
                code = str(code).zfill(6)
                if code.startswith(('60', '68', '90')):
                    return f"{code}.SH"
                elif code.startswith(('00', '30', '20')):
                    return f"{code}.SZ"
                elif code.startswith(('8', '4')):
                    return f"{code}.BJ"
                else:
                    return f"{code}.SZ"  # 默认深圳

            def get_market(code: str) -> str:
                """根据股票代码判断市场"""
                if not code:
                    return ""
                code = str(code).zfill(6)
                if code.startswith('000'):
                    return '主板'
                elif code.startswith('002'):
                    return '中小板'
                elif code.startswith('300'):
                    return '创业板'
                elif code.startswith('60'):
                    return '主板'
                elif code.startswith('688'):
                    return '科创板'
                elif code.startswith('8'):
                    return '北交所'
                elif code.startswith('4'):
                    return '新三板'
                else:
                    return '未知'

            # 添加 ts_code 和 market 字段
            df['ts_code'] = df['symbol'].apply(generate_ts_code)
            df['market'] = df['symbol'].apply(get_market)
            df['area'] = ''
            df['industry'] = ''
            df['list_date'] = ''

            logger.info(f"AKShare: Successfully fetched {len(df)} stocks with real names")
            return df

        except Exception as e:
            logger.error(f"AKShare: Failed to fetch stock list: {e}")
            return None

    def get_daily_basic(self, trade_date: str) -> Optional[pd.DataFrame]:
        """获取每日基础财务数据（增强版：东方财富优先，失败后降级到新浪财经）"""
        if not self.is_available():
            return None

        # 方法1：尝试东方财富接口（功能更全）
        try:
            import akshare as ak
            logger.info(f"AKShare: Fetching enhanced daily basic data for {trade_date} via stock_zh_a_spot_em (EastMoney)")

            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                basic_data = []
                for _, row in df.iterrows():
                    code_raw = str(row.get('代码', '')).strip()
                    if len(code_raw) > 6:
                        code_raw = ''.join(filter(str.isdigit, code_raw))
                    if not code_raw or len(code_raw) != 6:
                        continue

                    def generate_ts_code(code: str) -> str:
                        if code.startswith(('60', '68', '90')):
                            return f"{code}.SH"
                        elif code.startswith(('00', '30', '20')):
                            return f"{code}.SZ"
                        elif code.startswith(('8', '4')):
                            return f"{code}.BJ"
                        else:
                            return f"{code}.SZ"

                    total_mv_raw = self._safe_float(row.get('总市值', None))
                    circ_mv_raw = self._safe_float(row.get('流通市值', None))

                    basic_data.append({
                        'ts_code': generate_ts_code(code_raw),
                        'trade_date': trade_date,
                        'name': str(row.get('名称', '')),
                        'close': self._safe_float(row.get('最新价', None)),
                        'total_mv': total_mv_raw / 1e8 if total_mv_raw else None,
                        'circ_mv': circ_mv_raw / 1e8 if circ_mv_raw else None,
                        'turnover_rate': self._safe_float(row.get('换手率', None)),
                        'volume_ratio': self._safe_float(row.get('量比', None)),
                        'pe': self._safe_float(row.get('市盈率-动态', None)),
                        'pb': self._safe_float(row.get('市净率', None)),
                    })

                if basic_data:
                    result = pd.DataFrame(basic_data)
                    logger.info(f"AKShare: Enhanced daily basic data (EastMoney) for {trade_date}, {len(result)} records")
                    return result
        except Exception as e:
            logger.warning(f"AKShare: EastMoney interface failed: {e}, falling back to Sina Finance")

        # 方法2：降级到新浪财经接口
        try:
            import akshare as ak
            logger.info(f"AKShare: Fetching daily basic data for {trade_date} via stock_zh_a_spot (Sina Finance)")

            df = ak.stock_zh_a_spot()
            if df is None or df.empty:
                logger.warning("AKShare: Sina interface returned empty data")
                return None

            basic_data = []
            for _, row in df.iterrows():
                # 新浪接口列名：name, code, trade, pricechange, changepercent, buy, sell, settlement, open, high, low, volume, amount
                code_raw = str(row.get('code', row.get('股票代码', ''))).strip()
                if len(code_raw) > 6:
                    code_raw = ''.join(filter(str.isdigit, code_raw))
                if not code_raw or len(code_raw) != 6:
                    continue

                def generate_ts_code(code: str) -> str:
                    if code.startswith(('60', '68', '90')):
                        return f"{code}.SH"
                    elif code.startswith(('00', '30', '20')):
                        return f"{code}.SZ"
                    elif code.startswith(('8', '4')):
                        return f"{code}.BJ"
                    else:
                        return f"{code}.SZ"

                basic_data.append({
                    'ts_code': generate_ts_code(code_raw),
                    'trade_date': trade_date,
                    'name': str(row.get('name', row.get('名称', ''))),
                    'close': self._safe_float(row.get('trade', row.get('最新价', None))),
                    'total_mv': None,  # 新浪接口没有市值数据
                    'circ_mv': None,
                    'turnover_rate': None,  # 新浪接口没有换手率
                    'volume_ratio': None,
                    'pe': None,  # 新浪接口没有PE/PB
                    'pb': None,
                })

            if basic_data:
                result = pd.DataFrame(basic_data)
                logger.info(f"AKShare: Daily basic data (Sina) for {trade_date}, {len(result)} records (limited fields)")
                return result
            else:
                logger.warning("AKShare: No daily basic data collected from Sina")
                return None
        except Exception as e:
            logger.error(f"AKShare: All interfaces failed for {trade_date}: {e}")
            return None

    def get_financial_indicators(self, symbol: str) -> Optional[Dict]:
        """获取个股财务分析指标（ROE/ROA/毛利率/净利率/资产负债率等30+指标）"""
        if not self.is_available():
            return None
        try:
            import akshare as ak
            code6 = str(symbol).zfill(6)
            logger.info(f"AKShare: Fetching financial indicators for {code6}")

            df = ak.stock_financial_analysis_indicator(symbol=code6)
            if df is None or df.empty:
                logger.warning(f"AKShare: No financial indicators for {code6}")
                return None

            latest = df.iloc[0] if len(df) > 0 else None
            if latest is None:
                return None

            cn_to_en = {
                '净资产收益率(%)': 'roe',
                '总资产净利率(%)': 'roa',
                '销售毛利率(%)': 'gross_margin',
                '销售净利率(%)': 'net_margin',
                '资产负债率(%)': 'debt_to_assets',
                '流动比率': 'current_ratio',
                '速动比率': 'quick_ratio',
                '营业收入同比增长率(%)': 'revenue_growth',
                '净利润同比增长率(%)': 'profit_growth',
                '营业总收入(元)': 'revenue',
                '净利润(元)': 'net_profit',
                '营业利润(元)': 'operating_profit',
                '投资收益(元)': 'investment_income',
                '营业总成本(元)': 'total_operating_cost',
                '财务费用(元)': 'financial_expense',
                '管理费用(元)': 'admin_expense',
                '销售费用(元)': 'selling_expense',
            }

            result = {}
            for cn_name, en_name in cn_to_en.items():
                for col in df.columns:
                    if cn_name in str(col):
                        val = self._safe_float(latest.get(col))
                        if val is not None:
                            result[en_name] = val
                        break

            if '日期' in df.columns:
                result['report_date'] = str(latest.get('日期', ''))
            elif 'REPORT_DATE' in df.columns:
                result['report_date'] = str(latest.get('REPORT_DATE', ''))

            logger.info(f"AKShare: Financial indicators for {code6}: {len(result)} fields")
            return result
        except Exception as e:
            logger.error(f"AKShare: Failed to fetch financial indicators for {symbol}: {e}")
            return None

    def get_financial_statements(self, symbol: str, statement_type: str = "all") -> Optional[Dict]:
        """获取个股三大财务报表（利润表/资产负债表/现金流量表）"""
        if not self.is_available():
            return None
        try:
            import akshare as ak
            code6 = str(symbol).zfill(6)
            logger.info(f"AKShare: Fetching financial statements for {code6}, type={statement_type}")

            result = {}

            if statement_type in ("all", "income"):
                try:
                    df = ak.stock_profit_sheet_by_report_em(symbol=code6)
                    if df is not None and not df.empty:
                        latest = df.iloc[0]
                        result['income'] = {
                            'report_date': str(latest.get('REPORT_DATE', latest.get('报告期', ''))),
                            'revenue': self._safe_float(latest.get('营业总收入', None)),
                            'operating_revenue': self._safe_float(latest.get('营业收入', None)),
                            'operating_cost': self._safe_float(latest.get('营业成本', None)),
                            'total_operating_cost': self._safe_float(latest.get('营业总成本', None)),
                            'operating_profit': self._safe_float(latest.get('营业利润', None)),
                            'total_profit': self._safe_float(latest.get('利润总额', None)),
                            'net_profit': self._safe_float(latest.get('净利润', None)),
                            'net_profit_parent': self._safe_float(latest.get('归属于母公司所有者的净利润', None)),
                            'selling_expense': self._safe_float(latest.get('销售费用', None)),
                            'admin_expense': self._safe_float(latest.get('管理费用', None)),
                            'financial_expense': self._safe_float(latest.get('财务费用', None)),
                            'rd_expense': self._safe_float(latest.get('研发费用', None)),
                            'investment_income': self._safe_float(latest.get('投资收益', None)),
                        }
                        logger.debug(f"AKShare: Income statement for {code6} fetched")
                except Exception as e:
                    logger.debug(f"AKShare: Income statement failed for {code6}: {e}")

            if statement_type in ("all", "balance"):
                try:
                    df = ak.stock_balance_sheet_by_report_em(symbol=code6)
                    if df is not None and not df.empty:
                        latest = df.iloc[0]
                        result['balance'] = {
                            'report_date': str(latest.get('REPORT_DATE', latest.get('报告期', ''))),
                            'total_assets': self._safe_float(latest.get('资产总额', latest.get('总资产', None))),
                            'total_liabilities': self._safe_float(latest.get('负债总额', latest.get('总负债', None))),
                            'total_equity': self._safe_float(latest.get('所有者权益总额', latest.get('净资产', None))),
                            'equity_parent': self._safe_float(latest.get('归属于母公司所有者权益合计', None)),
                            'current_assets': self._safe_float(latest.get('流动资产合计', None)),
                            'current_liabilities': self._safe_float(latest.get('流动负债合计', None)),
                            'cash': self._safe_float(latest.get('货币资金', None)),
                            'accounts_receivable': self._safe_float(latest.get('应收账款', None)),
                            'inventory': self._safe_float(latest.get('存货', None)),
                            'fixed_assets': self._safe_float(latest.get('固定资产', None)),
                            'goodwill': self._safe_float(latest.get('商誉', None)),
                            'short_term_debt': self._safe_float(latest.get('短期借款', None)),
                            'long_term_debt': self._safe_float(latest.get('长期借款', None)),
                        }
                        logger.debug(f"AKShare: Balance sheet for {code6} fetched")
                except Exception as e:
                    logger.debug(f"AKShare: Balance sheet failed for {code6}: {e}")

            if statement_type in ("all", "cashflow"):
                try:
                    df = ak.stock_cash_flow_sheet_by_report_em(symbol=code6)
                    if df is not None and not df.empty:
                        latest = df.iloc[0]
                        result['cashflow'] = {
                            'report_date': str(latest.get('REPORT_DATE', latest.get('报告期', ''))),
                            'operating_cashflow': self._safe_float(latest.get('经营活动产生的现金流量净额', None)),
                            'investing_cashflow': self._safe_float(latest.get('投资活动产生的现金流量净额', None)),
                            'financing_cashflow': self._safe_float(latest.get('筹资活动产生的现金流量净额', None)),
                            'cash_received_sales': self._safe_float(latest.get('销售商品、提供劳务收到的现金', None)),
                            'cash_paid_goods': self._safe_float(latest.get('购买商品、接受劳务支付的现金', None)),
                            'cash_paid_employees': self._safe_float(latest.get('支付给职工以及为职工支付的现金', None)),
                            'capex': self._safe_float(latest.get('购建固定资产、无形资产和其他长期资产支付的现金', None)),
                        }
                        logger.debug(f"AKShare: Cash flow for {code6} fetched")
                except Exception as e:
                    logger.debug(f"AKShare: Cash flow failed for {code6}: {e}")

            if result:
                logger.info(f"AKShare: Financial statements for {code6}: {list(result.keys())}")
                return result
            else:
                logger.warning(f"AKShare: No financial statements for {code6}")
                return None
        except Exception as e:
            logger.error(f"AKShare: Failed to fetch financial statements for {symbol}: {e}")
            return None

    def _safe_float(self, value) -> Optional[float]:
        try:
            if value is None or value == '' or value == 'None':
                return None
            return float(value)
        except (ValueError, TypeError):
            return None


    def get_realtime_quotes(self, source: str = "eastmoney"):
        """
        获取全市场实时快照，返回以6位代码为键的字典

        Args:
            source: 数据源选择，"eastmoney"（东方财富）或 "sina"（新浪财经），
                    会自动降级：如果eastmoney失败，会自动尝试sina

        Returns:
            Dict[str, Dict]: {code: {close, pct_chg, amount, ...}}
        """
        if not self.is_available():
            return None

        # 方法1：先尝试用户指定的source
        try:
            import akshare as ak  # type: ignore

            # 根据 source 参数选择接口
            if source == "sina":
                df = ak.stock_zh_a_spot()  # 新浪财经接口
                logger.info("使用 AKShare 新浪财经接口获取实时行情")
            else:  # 默认使用东方财富
                df = ak.stock_zh_a_spot_em()  # 东方财富接口
                logger.info("使用 AKShare 东方财富接口获取实时行情")

            if df is not None and not getattr(df, "empty", True):
                return self._parse_realtime_quotes(df, source)

        except Exception as e:
            logger.warning(f"AKShare {source} 获取实时行情失败: {e}")
            if source == "eastmoney":
                logger.info("自动降级到新浪财经接口")
                return self._fetch_realtime_quotes_sina()

        return None

    def _fetch_realtime_quotes_sina(self) -> Optional[Dict]:
        """直接使用新浪财经接口获取实时行情"""
        try:
            import akshare as ak
            logger.info("使用 AKShare 新浪财经接口获取实时行情 (fallback)")

            df = ak.stock_zh_a_spot()
            if df is not None and not getattr(df, "empty", True):
                return self._parse_realtime_quotes(df, "sina")

            logger.warning("AKShare 新浪财经接口返回空数据")
            return None
        except Exception as e:
            logger.error(f"AKShare 新浪财经接口也失败了: {e}")
            return None

    def _parse_realtime_quotes(self, df, source: str) -> Optional[Dict]:
        """解析实时行情数据（公共方法，两个接口共享）"""
        try:
            # 列名兼容（两个接口的列名可能不同）
            code_col = next((c for c in ["代码", "code", "symbol", "股票代码"] if c in df.columns), None)
            price_col = next((c for c in ["最新价", "现价", "最新价(元)", "price", "最新", "trade"] if c in df.columns), None)
            pct_col = next((c for c in ["涨跌幅", "涨跌幅(%)", "涨幅", "pct_chg", "changepercent"] if c in df.columns), None)
            amount_col = next((c for c in ["成交额", "成交额(元)", "amount", "成交额(万元)", "amount(万元)"] if c in df.columns), None)
            open_col = next((c for c in ["今开", "开盘", "open", "今开(元)"] if c in df.columns), None)
            high_col = next((c for c in ["最高", "high"] if c in df.columns), None)
            low_col = next((c for c in ["最低", "low"] if c in df.columns), None)
            pre_close_col = next((c for c in ["昨收", "昨收(元)", "pre_close", "昨收价", "settlement"] if c in df.columns), None)
            volume_col = next((c for c in ["成交量", "成交量(手)", "volume", "成交量(股)", "vol"] if c in df.columns), None)

            if not code_col or not price_col:
                logger.error(f"AKShare {source} 缺少必要列: code={code_col}, price={price_col}, columns={list(df.columns)}")
                return None

            result: Dict[str, Dict[str, Optional[float]]] = {}
            for _, row in df.iterrows():  # type: ignore
                code_raw = row.get(code_col)
                if not code_raw:
                    continue
                # 标准化股票代码：处理交易所前缀（如 sz000001, sh600036）
                code_str = str(code_raw).strip()

                # 如果代码长度超过6位，去掉前面的交易所前缀（如 sz, sh）
                if len(code_str) > 6:
                    # 去掉前面的非数字字符（通常是2个字符的交易所代码）
                    code_str = ''.join(filter(str.isdigit, code_str))

                # 如果是纯数字，移除前导0后补齐到6位
                if code_str.isdigit():
                    code_clean = code_str.lstrip('0') or '0'  # 移除前导0，如果全是0则保留一个0
                    code = code_clean.zfill(6)  # 补齐到6位
                else:
                    # 如果不是纯数字，尝试提取数字部分
                    code_digits = ''.join(filter(str.isdigit, code_str))
                    if code_digits:
                        code = code_digits.zfill(6)
                    else:
                        # 无法提取有效代码，跳过
                        continue

                close = self._safe_float(row.get(price_col))
                pct = self._safe_float(row.get(pct_col)) if pct_col else None
                amt = self._safe_float(row.get(amount_col)) if amount_col else None
                op = self._safe_float(row.get(open_col)) if open_col else None
                hi = self._safe_float(row.get(high_col)) if high_col else None
                lo = self._safe_float(row.get(low_col)) if low_col else None
                pre = self._safe_float(row.get(pre_close_col)) if pre_close_col else None
                vol = self._safe_float(row.get(volume_col)) if volume_col else None

                # 🔥 日志：记录AKShare返回的成交量
                if code in ["300750", "000001", "600000"]:  # 只记录几个示例股票
                    logger.info(f"📊 [AKShare实时] {code} - volume_col={volume_col}, vol={vol}, amount={amt}")

                result[code] = {
                    "close": close,
                    "pct_chg": pct,
                    "amount": amt,
                    "volume": vol,
                    "open": op,
                    "high": hi,
                    "low": lo,
                    "pre_close": pre
                }

            logger.info(f"✅ AKShare {source} 获取到 {len(result)} 只股票的实时行情")
            return result
        except Exception as e:
            logger.error(f"解析AKShare {source} 实时行情失败: {e}")
            return None

    def get_kline(self, code: str, period: str = "day", limit: int = 120, adj: Optional[str] = None):
        """AKShare K-line as fallback. Try daily/week/month via stock_zh_a_hist; minutes via stock_zh_a_minute."""
        if not self.is_available():
            return None
        try:
            import akshare as ak
            code6 = str(code).zfill(6)
            items = []
            if period in ("day", "week", "month"):
                period_map = {"day": "daily", "week": "weekly", "month": "monthly"}
                adjust_map = {None: "", "qfq": "qfq", "hfq": "hfq"}
                df = ak.stock_zh_a_hist(symbol=code6, period=period_map[period], adjust=adjust_map.get(adj, ""))
                if df is None or getattr(df, 'empty', True):
                    return None
                df = df.tail(limit)
                for _, row in df.iterrows():
                    items.append({
                        "time": str(row.get('日期') or row.get('date') or ''),
                        "open": self._safe_float(row.get('开盘') or row.get('open')),
                        "high": self._safe_float(row.get('最高') or row.get('high')),
                        "low": self._safe_float(row.get('最低') or row.get('low')),
                        "close": self._safe_float(row.get('收盘') or row.get('close')),
                        "volume": self._safe_float(row.get('成交量') or row.get('volume')),
                        "amount": self._safe_float(row.get('成交额') or row.get('amount')),
                    })
                return items
            else:
                # minutes
                per_map = {"5m": "5", "15m": "15", "30m": "30", "60m": "60"}
                if period not in per_map:
                    return None
                df = ak.stock_zh_a_minute(symbol=code6, period=per_map[period], adjust=adj if adj in ("qfq", "hfq") else "")
                if df is None or getattr(df, 'empty', True):
                    return None
                df = df.tail(limit)
                for _, row in df.iterrows():
                    items.append({
                        "time": str(row.get('时间') or row.get('day') or ''),
                        "open": self._safe_float(row.get('开盘') or row.get('open')),
                        "high": self._safe_float(row.get('最高') or row.get('high')),
                        "low": self._safe_float(row.get('最低') or row.get('low')),
                        "close": self._safe_float(row.get('收盘') or row.get('close')),
                        "volume": self._safe_float(row.get('成交量') or row.get('volume')),
                        "amount": self._safe_float(row.get('成交额') or row.get('amount')),
                    })
                return items
        except Exception as e:
            logger.error(f"AKShare get_kline failed: {e}")
            return None

    def get_news(self, code: str, days: int = 2, limit: int = 50, include_announcements: bool = True):
        """AKShare-based news/announcements fallback"""
        if not self.is_available():
            return None
        try:
            import akshare as ak
            code6 = str(code).zfill(6)
            items = []
            # news
            try:
                dfn = ak.stock_news_em(symbol=code6)
                if dfn is not None and not dfn.empty:
                    for _, row in dfn.head(limit).iterrows():
                        items.append({
                            # AkShare 将字段标准化为中文列名：新闻标题 / 文章来源 / 发布时间 / 新闻链接
                            "title": str(row.get('新闻标题') or row.get('标题') or row.get('title') or ''),
                            "source": str(row.get('文章来源') or row.get('来源') or row.get('source') or 'akshare'),
                            "time": str(row.get('发布时间') or row.get('time') or ''),
                            "url": str(row.get('新闻链接') or row.get('url') or ''),
                            "type": "news",
                        })
            except Exception:
                pass
            # announcements
            try:
                if include_announcements:
                    dfa = ak.stock_announcement_em(symbol=code6)
                    if dfa is not None and not dfa.empty:
                        for _, row in dfa.head(max(0, limit - len(items))).iterrows():
                            items.append({
                                "title": str(row.get('公告标题') or row.get('title') or ''),
                                "source": "akshare",
                                "time": str(row.get('公告时间') or row.get('time') or ''),
                                "url": str(row.get('公告链接') or row.get('url') or ''),
                                "type": "announcement",
                            })
            except Exception:
                pass
            return items if items else None
        except Exception as e:
            logger.error(f"AKShare get_news failed: {e}")
            return None

    def find_latest_trade_date(self) -> Optional[str]:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        logger.info(f"AKShare: Using yesterday as trade date: {yesterday}")
        return yesterday

