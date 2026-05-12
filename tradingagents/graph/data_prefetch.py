from datetime import datetime, timedelta

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.stock_utils import StockUtils

logger = get_logger("default")


def create_data_prefetch_node(toolkit):
    def data_prefetch_node(state):
        ticker = state["company_of_interest"]
        trade_date = state["trade_date"]
        log_tag = "[数据预获取]"

        logger.info(f"{log_tag} ===== 开始预获取数据 ===== ticker={ticker}, date={trade_date}")

        fundamentals_data = ""
        market_data = ""
        quant_data = ""
        snapshot_dict = {}
        is_china = False

        try:
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
        except Exception as e:
            logger.error(f"{log_tag} ❌ 市场信息获取失败: {e}")
            return {
                "prefetched_fundamentals_data": f"数据预获取失败: 市场信息获取错误 - {e}",
                "prefetched_market_data": f"数据预获取失败: 市场信息获取错误 - {e}",
                "prefetched_quant_data": "",
                "fundamental_snapshot": {},
                "cn_fact_snapshot": {},
            }

        end_date_dt = None
        try:
            end_date_dt = datetime.strptime(trade_date, "%Y-%m-%d")
            start_date_dt = end_date_dt - timedelta(days=10)
            start_date = start_date_dt.strftime("%Y-%m-%d")
        except Exception:
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            end_date_dt = datetime.now()

        try:
            fundamentals_data = _fetch_with_fallback(
                toolkit.get_stock_fundamentals_unified,
                {"ticker": ticker, "start_date": start_date, "end_date": trade_date, "curr_date": trade_date},
                log_tag, "基本面"
            )
        except Exception as e:
            fundamentals_data = f"基本面数据获取失败: {e}"
            logger.error(f"{log_tag} ❌ 基本面数据获取异常: {e}")

        try:
            market_data = _fetch_with_fallback(
                toolkit.get_stock_market_data_unified,
                {"ticker": ticker, "start_date": start_date, "end_date": trade_date},
                log_tag, "市场"
            )
        except Exception as e:
            market_data = f"市场数据获取失败: {e}"
            logger.error(f"{log_tag} ❌ 市场数据获取异常: {e}")

        try:
            data_quality = _check_data_quality(fundamentals_data, market_info)

            if data_quality["score"] < 3:
                logger.warning(f"{log_tag} ⚠️ 数据质量较低({data_quality['score']}/5)，尝试扩展日期范围重新获取")
                try:
                    extended_start = (end_date_dt - timedelta(days=30)).strftime("%Y-%m-%d")
                    retry_data = _fetch_with_fallback(
                        toolkit.get_stock_fundamentals_unified,
                        {"ticker": ticker, "start_date": extended_start, "end_date": trade_date, "curr_date": trade_date},
                        log_tag, "基本面(扩展范围)"
                    )
                    if retry_data and len(str(retry_data)) > len(str(fundamentals_data)):
                        retry_quality = _check_data_quality(retry_data, market_info)
                        if retry_quality["score"] >= data_quality["score"]:
                            fundamentals_data = retry_data
                            data_quality = retry_quality
                            logger.info(f"{log_tag} ✅ 扩展范围后数据质量提升: {data_quality['score']}/5")
                        else:
                            logger.warning(f"{log_tag} ⚠️ 扩展范围后数据质量未提升(重试:{retry_quality['score']}/5 vs 原始:{data_quality['score']}/5)，保留原始数据")
                    else:
                        logger.warning(f"{log_tag} ⚠️ 扩展范围后数据未变长，保留原始数据")
                except Exception as e:
                    logger.warning(f"{log_tag} 扩展范围重试失败: {e}")

                if data_quality["score"] < 3:
                    logger.warning(f"{log_tag} ⚠️ 数据质量仍然较低({data_quality['score']}/5)，下游分析可能受影响")
        except Exception as e:
            logger.warning(f"{log_tag} 数据质量检查失败: {e}")

        try:
            industry_context = _get_industry_context(ticker, market_info, log_tag)
        except Exception as e:
            industry_context = ""
            logger.warning(f"{log_tag} 行业对比数据获取失败: {e}")

        capital_flow_data = ""
        announcement_data = ""
        if is_china:
            try:
                capital_flow_data = _get_china_capital_flow(ticker, log_tag)
            except Exception as e:
                capital_flow_data = f"资金面数据获取失败: {e}"
                logger.warning(f"{log_tag} 资金面数据获取失败: {e}")
            try:
                announcement_data = _get_china_announcement_signals(ticker, log_tag)
            except Exception as e:
                announcement_data = f"公告信号数据获取失败: {e}"
                logger.warning(f"{log_tag} 公告信号数据获取失败: {e}")
            try:
                quant_data, snapshot_dict = _get_china_quant_data(ticker, log_tag)
            except Exception as e:
                quant_data = f"量化数据获取失败: {e}"
                snapshot_dict = {}
                logger.warning(f"{log_tag} 量化数据获取失败: {e}")

        moat_context = ""
        try:
            moat_context = _get_moat_context(ticker, market_info, fundamentals_data, snapshot_dict, log_tag)
        except Exception as e:
            logger.warning(f"{log_tag} 护城河分析上下文生成失败: {e}")

        cn_fact_snapshot = {}
        try:
            from tradingagents.graph.cn_fact_snapshot import build_cn_fact_snapshot
            cn_fact_snapshot = build_cn_fact_snapshot(ticker, market_info, snapshot_dict, trade_date)
        except Exception as e:
            logger.warning(f"{log_tag} A股事实快照生成失败: {e}")

        logger.info(f"{log_tag} ===== 预获取完成 =====")

        fundamentals_with_industry = str(fundamentals_data) if fundamentals_data else ""
        if industry_context:
            fundamentals_with_industry += f"\n\n## 📊 同行业对比数据\n{industry_context}"
        if capital_flow_data:
            fundamentals_with_industry += f"\n\n## 💰 资金面数据\n{capital_flow_data}"
        if announcement_data:
            fundamentals_with_industry += f"\n\n## 📋 公告信号数据\n{announcement_data}"
        if moat_context:
            fundamentals_with_industry += f"\n\n## 🏰 护城河定性分析参考\n{moat_context}"

        return {
            "prefetched_fundamentals_data": fundamentals_with_industry,
            "prefetched_market_data": str(market_data) if market_data else "",
            "prefetched_quant_data": quant_data,
            "fundamental_snapshot": snapshot_dict,
            "cn_fact_snapshot": cn_fact_snapshot,
        }

    return data_prefetch_node


def _fetch_with_fallback(tool_func, params: dict, log_tag: str, data_name: str):
    try:
        logger.info(f"{log_tag} 获取{data_name}数据: {params.get('ticker')}")
        result = tool_func.invoke(params)
        if result:
            logger.info(f"{log_tag} ✅ {data_name}数据获取成功，长度={len(str(result))}")
            return result
        else:
            logger.warning(f"{log_tag} ⚠️ {data_name}数据为空")
            return ""
    except Exception as e:
        logger.error(f"{log_tag} ❌ {data_name}数据获取失败: {e}")
        return f"{data_name}数据获取失败: {e}"


def _check_data_quality(data: str, market_info: dict) -> dict:
    if not data or "获取失败" in data:
        return {"has_data": False, "score": 0, "data_length": 0,
                "has_pe": False, "has_pb": False, "has_roe": False, "has_revenue": False}

    quality = {
        "has_data": len(data) > 50,
        "has_pe": "市盈率" in data or "PE" in data.upper() or "P/E" in data.upper(),
        "has_pb": "市净率" in data or "PB" in data.upper() or "P/B" in data.upper(),
        "has_roe": "ROE" in data.upper() or "净资产收益率" in data,
        "has_revenue": "营收" in data or "营业收入" in data or "revenue" in data.lower(),
        "data_length": len(data),
    }
    quality["score"] = sum([
        quality["has_data"],
        quality["has_pe"],
        quality["has_pb"],
        quality["has_roe"],
        quality["has_revenue"],
    ])
    return quality


def _get_industry_context(ticker: str, market_info: dict, log_tag: str) -> str:
    if not market_info.get('is_china'):
        return ""

    try:
        import akshare as ak

        try:
            stock_info = ak.stock_individual_info_em(symbol=ticker)
            industry = ""
            for _, row in stock_info.iterrows():
                if "行业" in str(row.iloc[0]):
                    industry = str(row.iloc[1])
                    break

            if not industry:
                return ""

            logger.info(f"{log_tag} 股票行业: {industry}")

            try:
                peers_df = ak.stock_board_industry_cons_em(symbol=industry)
                if peers_df is not None and len(peers_df) > 0:
                    peer_count = min(5, len(peers_df))
                    peers = peers_df.head(peer_count)
                    context_lines = [f"行业: {industry}", f"行业内公司数: {len(peers_df)}", "", "同行业主要公司:"]
                    for _, peer in peers.iterrows():
                        name = peer.get('股票名称', '') if '股票名称' in peer else ''
                        code = peer.get('代码', '') if '代码' in peer else str(peer.iloc[0] if len(peer) > 0 else '')
                        context_lines.append(f"  - {name}({code})")
                    result = "\n".join(context_lines)
                    logger.info(f"{log_tag} ✅ 行业对比数据获取成功")
                    return result
            except Exception as e:
                logger.debug(f"{log_tag} 行业成分股获取失败: {e}")

        except Exception as e:
            logger.debug(f"{log_tag} 股票信息获取失败: {e}")

        return ""
    except ImportError:
        logger.debug(f"{log_tag} akshare不可用，跳过行业对比")
        return ""
    except Exception as e:
        logger.debug(f"{log_tag} 行业对比数据获取失败: {e}")
        return ""


def _get_china_capital_flow(ticker: str, log_tag: str) -> str:
    try:
        from tradingagents.dataflows.capital_flow import ChinaCapitalFlowProvider
        provider = ChinaCapitalFlowProvider()
        summary = provider.get_capital_flow_summary(ticker, days=30)
        if summary and len(summary) > 50:
            logger.info(f"{log_tag} ✅ 资金面数据获取成功")
            return summary
        return ""
    except Exception as e:
        logger.debug(f"{log_tag} 资金面数据获取失败: {e}")
        return ""


def _get_china_announcement_signals(ticker: str, log_tag: str) -> str:
    try:
        from tradingagents.dataflows.china_fundamental_snapshot import (
            collect_china_announcement_payload,
            format_china_fundamental_snapshot_report,
        )
        payload = collect_china_announcement_payload(ticker, days=90, limit=50)
        if payload and payload.get("data"):
            signals = payload["data"]
            lines = [f"公告信号分析（近90天）:"]
            key_fields = [
                ("dividend_events", "分红公告"),
                ("buyback_events", "回购公告"),
                ("pledge_risk_events", "质押风险"),
                ("litigation_risk_events", "诉讼风险"),
                ("management_change_events", "管理层变更"),
                ("insider_increase_events", "高管增持"),
                ("insider_decrease_events", "高管减持"),
                ("earnings_positive_events", "业绩利好"),
                ("earnings_negative_events", "业绩利空"),
                ("regulatory_penalty_events", "监管处罚"),
                ("goodwill_impairment_events", "商誉减值"),
            ]
            for field, label in key_fields:
                val = signals.get(field)
                if val:
                    lines.append(f"  - {label}: {val}")
            summary_fields = [
                ("shareholder_return_summary", "股东回报摘要"),
                ("governance_risk_summary", "治理风险摘要"),
                ("management_alignment_summary", "管理层增减持摘要"),
                ("earnings_guidance_summary", "业绩预告摘要"),
            ]
            for field, label in summary_fields:
                val = signals.get(field)
                if val:
                    lines.append(f"  - {label}: {val}")
            if len(lines) > 1:
                result = "\n".join(lines)
                logger.info(f"{log_tag} ✅ 公告信号数据获取成功")
                return result
        return ""
    except Exception as e:
        logger.debug(f"{log_tag} 公告信号数据获取失败: {e}")
        return ""


def _get_china_quant_data(ticker: str, log_tag: str) -> tuple:
    try:
        from tradingagents.dataflows.china_fundamental_snapshot import (
            collect_china_free_source_payloads,
            build_china_fundamental_snapshot,
            snapshot_to_quant_text,
        )

        payloads = collect_china_free_source_payloads(ticker)
        if not payloads:
            logger.debug(f"{log_tag} 快照数据源为空，跳过量化数据生成")
            return "", {}

        snapshot = build_china_fundamental_snapshot(ticker, payloads)
        if not snapshot:
            logger.debug(f"{log_tag} 快照构建返回空，跳过量化数据生成")
            return "", {}

        quant_text = snapshot_to_quant_text(snapshot)

        if quant_text:
            field_count = len(quant_text.splitlines())
            logger.info(f"{log_tag} ✅ 量化分析专用数据生成成功，{field_count}个字段")
        else:
            logger.debug(f"{log_tag} 量化分析专用数据为空")

        return quant_text, snapshot
    except Exception as e:
        logger.debug(f"{log_tag} 量化分析专用数据生成失败: {e}")
        return "", {}


def _get_moat_context(ticker: str, market_info: dict, fundamentals_data: str, snapshot_dict: dict, log_tag: str) -> str:
    if not market_info.get('is_china'):
        return ""

    lines = []
    roe_value = None
    gross_margin = None
    revenue_growth = None

    if snapshot_dict:
        for key in ['roe', 'ROE', '净资产收益率', 'roe_trend']:
            val = snapshot_dict.get(key)
            if val is not None:
                try:
                    roe_value = float(str(val).replace('%', '').strip())
                except (ValueError, TypeError):
                    pass
                break
        for key in ['gross_margin', '毛利率', 'gross_profit_margin']:
            val = snapshot_dict.get(key)
            if val is not None:
                try:
                    gross_margin = float(str(val).replace('%', '').strip())
                except (ValueError, TypeError):
                    pass
                break
        for key in ['revenue_growth', '营收增长率', 'revenue_yoy']:
            val = snapshot_dict.get(key)
            if val is not None:
                try:
                    revenue_growth = float(str(val).replace('%', '').strip())
                except (ValueError, TypeError):
                    pass
                break

    data_str = str(fundamentals_data) if fundamentals_data else ""

    if roe_value is None:
        import re
        roe_patterns = [r'ROE[：:]\s*([\d.]+)', r'净资产收益率[：:]\s*([\d.]+)', r'ROE.*?([\d.]+)%']
        for pattern in roe_patterns:
            match = re.search(pattern, data_str)
            if match:
                try:
                    roe_value = float(match.group(1))
                except ValueError:
                    pass
                break

    if gross_margin is None:
        import re
        gm_patterns = [r'毛利率[：:]\s*([\d.]+)', r'gross_margin[：:]\s*([\d.]+)']
        for pattern in gm_patterns:
            match = re.search(pattern, data_str)
            if match:
                try:
                    gross_margin = float(match.group(1))
                except ValueError:
                    pass
                break

    if roe_value is not None:
        if roe_value > 20:
            lines.append(f"- ROE={roe_value}%，持续高于15%阈值，暗示可能存在竞争优势（护城河）")
        elif roe_value > 15:
            lines.append(f"- ROE={roe_value}%，接近15%阈值，存在一定竞争壁垒")
        else:
            lines.append(f"- ROE={roe_value}%，低于15%阈值，护城河可能较窄或不存在")

    if gross_margin is not None:
        if gross_margin > 50:
            lines.append(f"- 毛利率={gross_margin}%，显著高于行业均值，品牌溢价或成本优势明显")
        elif gross_margin > 30:
            lines.append(f"- 毛利率={gross_margin}%，处于中等水平，存在一定定价能力")
        else:
            lines.append(f"- 毛利率={gross_margin}%，偏低，定价能力有限")

    if revenue_growth is not None:
        if revenue_growth > 15:
            lines.append(f"- 营收增长率={revenue_growth}%，增长强劲，市场份额可能扩张")
        elif revenue_growth > 5:
            lines.append(f"- 营收增长率={revenue_growth}%，稳定增长")
        else:
            lines.append(f"- 营收增长率={revenue_growth}%，增长乏力")

    try:
        import akshare as ak
        stock_info_df = ak.stock_individual_info_em(symbol=ticker)
        industry = ""
        for _, row in stock_info_df.iterrows():
            if "行业" in str(row.iloc[0]):
                industry = str(row.iloc[1])
                break
        if industry:
            lines.append(f"- 所属行业: {industry}")
            moat_industries = ["白酒", "银行", "保险", "医药", "互联网", "软件", "半导体", "新能源", "食品饮料"]
            for mi in moat_industries:
                if mi in industry:
                    lines.append(f"  行业'{mi}'通常具有较强护城河特征（品牌/许可/网络效应）")
                    break
    except Exception:
        pass

    if lines:
        logger.info(f"{log_tag} ✅ 护城河分析上下文生成成功，{len(lines)}个指标")
        return "\n".join(lines)
    return ""
