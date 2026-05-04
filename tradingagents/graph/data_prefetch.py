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

        market_info = StockUtils.get_market_info(ticker)
        is_china = market_info['is_china']
        is_hk = market_info['is_hk']
        is_us = market_info['is_us']

        end_date_dt = None
        try:
            end_date_dt = datetime.strptime(trade_date, "%Y-%m-%d")
            start_date_dt = end_date_dt - timedelta(days=10)
            start_date = start_date_dt.strftime("%Y-%m-%d")
        except Exception:
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            end_date_dt = datetime.now()

        fundamentals_data = _fetch_with_fallback(
            toolkit.get_stock_fundamentals_unified,
            {"ticker": ticker, "start_date": start_date, "end_date": trade_date, "curr_date": trade_date},
            log_tag, "基本面"
        )

        market_data = _fetch_with_fallback(
            toolkit.get_stock_market_data_unified,
            {"ticker": ticker, "start_date": start_date, "end_date": trade_date},
            log_tag, "市场"
        )

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
                    fundamentals_data = retry_data
                    data_quality = _check_data_quality(fundamentals_data, market_info)
                    logger.info(f"{log_tag} ✅ 扩展范围后数据质量提升: {data_quality['score']}/5")
            except Exception as e:
                logger.warning(f"{log_tag} 扩展范围重试失败: {e}")

        industry_context = _get_industry_context(ticker, market_info, log_tag)

        logger.info(f"{log_tag} 数据质量: {data_quality}")
        logger.info(f"{log_tag} ===== 预获取完成 =====")

        fundamentals_with_industry = str(fundamentals_data) if fundamentals_data else ""
        if industry_context:
            fundamentals_with_industry += f"\n\n## 📊 同行业对比数据\n{industry_context}"

        return {
            "prefetched_fundamentals_data": fundamentals_with_industry,
            "prefetched_market_data": str(market_data) if market_data else "",
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
