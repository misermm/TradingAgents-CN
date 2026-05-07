from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from tradingagents.utils.logging_init import get_logger

logger = get_logger("dataflows")


class ChinaCapitalFlowProvider:
    _instance = None
    _last_request_time = 0.0
    _min_interval = 0.8

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _safe_import_akshare(self):
        try:
            import akshare as ak
            return ak
        except ImportError:
            raise RuntimeError("akshare 未安装，请执行 pip install akshare")

    def _fmt_amount(self, val) -> str:
        try:
            v = float(val)
        except (ValueError, TypeError):
            return "N/A"
        if abs(v) >= 1e8:
            return f"{v / 1e8:.2f}亿"
        if abs(v) >= 1e4:
            return f"{v / 1e4:.2f}万"
        return f"{v:.2f}"

    def _fmt_pct(self, val) -> str:
        try:
            v = float(val)
            return f"{v:.2f}%"
        except (ValueError, TypeError):
            return "N/A"

    def get_northbound_flow(self, days: int = 30) -> str:
        try:
            ak = self._safe_import_akshare()
            self._rate_limit()

            df = None
            try:
                df = ak.stock_hsgt_fund_flow_summary_em()
            except Exception as e1:
                logger.debug(f"stock_hsgt_fund_flow_summary_em 失败: {e1}")
                try:
                    self._rate_limit()
                    df = ak.stock_hsgt_hist_em(symbol="北向资金")
                except Exception as e2:
                    logger.debug(f"stock_hsgt_hist_em 也失败: {e2}")

            if df is None or df.empty:
                return "北向资金数据为空"

            lines = [f"## 北向资金流向\n"]

            date_col = None
            for col in df.columns:
                if "交易日" in str(col) or "日期" in str(col):
                    date_col = col
                    break
            if date_col is None:
                date_col = df.columns[0]

            direction_col = None
            for col in df.columns:
                if "资金方向" in str(col):
                    direction_col = col
                    break

            type_col = None
            for col in df.columns:
                if "板块" in str(col) or "类型" in str(col):
                    type_col = col
                    break

            net_col = None
            for col in df.columns:
                if "成交净买额" in str(col) or "当日成交净买额" in str(col):
                    net_col = col
                    break
            if net_col is None:
                for col in df.columns:
                    if "净流入" in str(col) or "净买额" in str(col):
                        net_col = col
                        break

            inflow_col = None
            for col in df.columns:
                if "资金净流入" in str(col) or "当日资金流入" in str(col):
                    inflow_col = col
                    break

            if direction_col and "北向" in df[direction_col].unique():
                north_df = df[df[direction_col] == "北向"]
            else:
                north_df = df

            if north_df.empty:
                north_df = df

            if date_col:
                north_df = north_df.sort_values(by=date_col, ascending=False)
                cutoff = datetime.now() - timedelta(days=days)
                try:
                    north_df[date_col] = pd.to_datetime(north_df[date_col], errors="coerce")
                    north_df = north_df[north_df[date_col] >= cutoff]
                except Exception:
                    pass

            if north_df.empty:
                return f"近{days}天无北向资金数据"

            if type_col and direction_col:
                lines.append("| 日期 | 板块 | 成交净买额(亿) | 资金净流入(亿) |")
                lines.append("|------|------|---------------|-------------|")
                for _, row in north_df.head(min(10, len(north_df))).iterrows():
                    dt = str(row[date_col])[:10] if pd.notna(row[date_col]) else "N/A"
                    board = str(row[type_col]) if type_col else ""
                    net_val = self._fmt_amount(row[net_col]) if net_col else "N/A"
                    inflow_val = self._fmt_amount(row[inflow_col]) if inflow_col else "N/A"
                    lines.append(f"| {dt} | {board} | {net_val} | {inflow_val} |")
            else:
                lines.append("| 日期 | 成交净买额(亿) | 资金净流入(亿) |")
                lines.append("|------|---------------|-------------|")
                for _, row in north_df.head(min(10, len(north_df))).iterrows():
                    dt = str(row[date_col])[:10] if pd.notna(row[date_col]) else "N/A"
                    net_val = self._fmt_amount(row[net_col]) if net_col else "N/A"
                    inflow_val = self._fmt_amount(row[inflow_col]) if inflow_col else "N/A"
                    lines.append(f"| {dt} | {net_val} | {inflow_val} |")

            if net_col and not north_df.empty:
                lines.append(f"\n**最新数据**:")
                for _, row in north_df.head(2).iterrows():
                    dt = str(row[date_col])[:10] if pd.notna(row[date_col]) else "N/A"
                    board = str(row[type_col]) if type_col else "北向资金"
                    net_val = self._fmt_amount(row[net_col])
                    lines.append(f"- {dt} {board}: 成交净买额 {net_val}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"北向资金数据获取失败: {e}")
            return f"北向资金数据获取失败: {e}"

    def get_margin_data(self, symbol: str) -> str:
        try:
            ak = self._safe_import_akshare()
            clean_code = symbol.replace(".SH", "").replace(".SZ", "").replace(".SS", "")

            is_sh = clean_code.startswith("6") or clean_code.startswith("5")
            df = None
            source = ""

            if is_sh:
                for offset in range(0, 5):
                    try:
                        self._rate_limit()
                        query_date = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
                        df = ak.stock_margin_detail_sse(date=query_date)
                        source = f"上交所({query_date})"
                        if df is not None and not df.empty:
                            code_col = None
                            for col in df.columns:
                                if "标的证券代码" in str(col):
                                    code_col = col
                                    break
                            if code_col:
                                mask = df[code_col].astype(str).str.contains(clean_code, na=False)
                                filtered = df[mask]
                                if not filtered.empty:
                                    df = filtered
                                    break
                                else:
                                    df = df.head(10)
                                    break
                    except Exception:
                        continue
            else:
                for offset in range(0, 5):
                    try:
                        self._rate_limit()
                        query_date = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
                        df = ak.stock_margin_detail_szse(date=query_date)
                        source = f"深交所({query_date})"
                        if df is not None and not df.empty:
                            code_col = None
                            for col in df.columns:
                                if "证券代码" in str(col) or "标的证券代码" in str(col):
                                    code_col = col
                                    break
                            if code_col:
                                mask = df[code_col].astype(str).str.contains(clean_code, na=False)
                                filtered = df[mask]
                                if not filtered.empty:
                                    df = filtered
                                    break
                                else:
                                    df = df.head(10)
                                    break
                    except Exception:
                        continue

                if df is None or df.empty:
                    try:
                        self._rate_limit()
                        df = ak.stock_margin_underlying_info_szse(date=datetime.now().strftime("%Y%m%d"))
                        source = "深交所标的"
                        if df is not None and not df.empty:
                            code_col = None
                            for col in df.columns:
                                if "证券代码" in str(col) or "标的证券代码" in str(col):
                                    code_col = col
                                    break
                            if code_col:
                                mask = df[code_col].astype(str).str.contains(clean_code, na=False)
                                filtered = df[mask]
                                if not filtered.empty:
                                    df = filtered
                    except Exception as e:
                        logger.debug(f"深交所标的融资融券获取失败: {e}")

            if df is None or df.empty:
                return f"融资融券数据暂时无法获取（股票代码: {symbol}）"

            lines = [f"## 融资融券数据（{source}）\n"]

            col_map = {}
            for col in df.columns:
                col_str = str(col)
                if "标的证券代码" in col_str or "证券代码" in col_str:
                    col_map[col] = "证券代码"
                elif "标的证券简称" in col_str or "证券简称" in col_str:
                    col_map[col] = "证券简称"
                elif "融资余额" in col_str:
                    col_map[col] = "融资余额"
                elif "融资买入" in col_str:
                    col_map[col] = "融资买入额"
                elif "融资偿还" in col_str:
                    col_map[col] = "融资偿还额"
                elif "融券余量" in col_str:
                    col_map[col] = "融券余量"
                elif "融券卖出" in col_str:
                    col_map[col] = "融券卖出量"
                elif "融券偿还" in col_str:
                    col_map[col] = "融券偿还量"

            if col_map:
                display_df = df[list(col_map.keys())].rename(columns=col_map)
                lines.append(display_df.to_markdown(index=False))
            else:
                lines.append(df.head(5).to_markdown(index=False))

            rzye_col = None
            for col in df.columns:
                if "融资余额" in str(col):
                    rzye_col = col
                    break

            rqyl_col = None
            for col in df.columns:
                if "融券余量" in str(col):
                    rqyl_col = col
                    break

            if rzye_col and not df.empty:
                latest_row = df.iloc[0]
                lines.append(f"\n**关键指标**:")
                lines.append(f"- 融资余额: {self._fmt_amount(latest_row[rzye_col])}")
                if rqyl_col:
                    lines.append(f"- 融券余量: {self._fmt_amount(latest_row[rqyl_col])}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"融资融券数据获取失败: {e}")
            return f"融资融券数据获取失败: {e}"

    def get_individual_fund_flow(self, symbol: str) -> str:
        try:
            ak = self._safe_import_akshare()
            self._rate_limit()

            clean_code = symbol.replace(".SH", "").replace(".SZ", "").replace(".SS", "")

            market = "sh"
            if clean_code.startswith("0") or clean_code.startswith("3"):
                market = "sz"
            elif clean_code.startswith("8") or clean_code.startswith("4"):
                market = "bj"

            df = None
            source = ""

            try:
                df = ak.stock_individual_fund_flow(stock=clean_code, market=market)
                source = "东方财富个股资金流"
            except Exception as e1:
                logger.debug(f"个股资金流接口1失败: {e1}")
                try:
                    self._rate_limit()
                    df = ak.stock_individual_fund_flow_rank(indicator="今日")
                    source = "东方财富资金流排名"
                except Exception as e2:
                    logger.debug(f"个股资金流接口2失败: {e2}")

            if df is None or df.empty:
                return f"个股资金流向数据暂时无法获取（股票代码: {symbol}）"

            lines = [f"## 个股资金流向（{source}）\n"]

            if source == "东方财富个股资金流":
                date_col = None
                for col in df.columns:
                    if "日期" in str(col):
                        date_col = col
                        break
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df.sort_values(by=date_col, ascending=False)

                col_mapping = {
                    "日期": None,
                    "收盘价": None,
                    "涨跌幅": None,
                    "主力净流入-净额": "主力净流入",
                    "超大单净流入-净额": "超大单净流入",
                    "大单净流入-净额": "大单净流入",
                    "中单净流入-净额": "中单净流入",
                    "小单净流入-净额": "小单净流入",
                }

                display_cols = {}
                for col in df.columns:
                    for key, val in col_mapping.items():
                        if key in str(col):
                            display_cols[col] = val if val else key
                            break

                if display_cols:
                    display_df = df[list(display_cols.keys())].rename(columns=display_cols).head(10)
                    lines.append(display_df.to_markdown(index=False))
                else:
                    lines.append(df.head(10).to_markdown(index=False))

                main_net_col = None
                for col in df.columns:
                    if "主力净流入-净额" in str(col):
                        main_net_col = col
                        break

                super_large_col = None
                for col in df.columns:
                    if "超大单净流入-净额" in str(col):
                        super_large_col = col
                        break

                if main_net_col and len(df) >= 3:
                    recent_3 = df.head(3)[main_net_col].sum()
                    lines.append(f"\n**近3日主力净流入合计**: {self._fmt_amount(recent_3)}")

                if super_large_col and len(df) >= 3:
                    recent_3_super = df.head(3)[super_large_col].sum()
                    lines.append(f"**近3日超大单净流入合计**: {self._fmt_amount(recent_3_super)}")

            else:
                code_col = None
                for col in df.columns:
                    if "代码" in str(col):
                        code_col = col
                        break

                if code_col:
                    mask = df[code_col].astype(str).str.contains(clean_code, na=False)
                    filtered = df[mask]
                    if not filtered.empty:
                        lines.append(filtered.head(5).to_markdown(index=False))
                    else:
                        lines.append(f"未在资金流排名中找到股票 {symbol}，展示前5名：\n")
                        lines.append(df.head(5).to_markdown(index=False))
                else:
                    lines.append(df.head(5).to_markdown(index=False))

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"个股资金流向数据获取失败: {e}")
            return f"个股资金流向数据获取失败: {e}"

    def get_capital_flow_summary(self, symbol: str, days: int = 30) -> str:
        sections = []
        has_data = False

        northbound = self.get_northbound_flow(days=days)
        if "失败" not in northbound and "为空" not in northbound:
            sections.append(northbound)
            has_data = True
        else:
            sections.append(f"## 北向资金\n{northbound}")

        margin = self.get_margin_data(symbol)
        if "失败" not in margin and "无法获取" not in margin:
            sections.append(margin)
            has_data = True
        else:
            sections.append(f"## 融资融券\n{margin}")

        fund_flow = self.get_individual_fund_flow(symbol)
        if "失败" not in fund_flow and "无法获取" not in fund_flow:
            sections.append(fund_flow)
            has_data = True
        else:
            sections.append(f"## 个股资金流向\n{fund_flow}")

        if not has_data:
            return f"股票 {symbol} 的资金面数据全部获取失败，请稍后重试或检查网络连接。"

        summary = f"# {symbol} 资金面综合报告\n\n"
        summary += "\n\n".join(sections)
        summary += f"\n\n---\n*数据来源: 东方财富/AKShare | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"

        return summary


_provider_instance: Optional[ChinaCapitalFlowProvider] = None


def get_capital_flow_provider() -> ChinaCapitalFlowProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = ChinaCapitalFlowProvider()
    return _provider_instance
