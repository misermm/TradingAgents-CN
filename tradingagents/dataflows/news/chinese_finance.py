#!/usr/bin/env python3
"""
中国财经数据聚合工具
集成东方财富股吧评论、人气排名、新闻情绪等多源数据
"""

import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class ChineseFinanceDataAggregator:

    def __init__(self):
        self._comment_cache = None
        self._comment_cache_time = None
        self._hot_rank_cache = None
        self._hot_rank_cache_time = None
        self._cache_ttl = 300

    def _get_akshare(self):
        try:
            import akshare as ak
            return ak
        except ImportError:
            logger.warning("akshare not installed")
            return None

    def _normalize_code(self, ticker: str) -> str:
        code = str(ticker).replace('.SH', '').replace('.SZ', '').replace('.SS', '') \
                   .replace('.XSHE', '').replace('.XSHG', '').replace('.BJ', '')
        return code.zfill(6)

    def get_stock_sentiment_summary(self, ticker: str, days: int = 7) -> Dict:
        try:
            forum_sentiment = self._get_stock_forum_sentiment(ticker, days)
            hot_rank = self._get_stock_hot_rank(ticker)
            news_sentiment = self._get_finance_news_sentiment(ticker, days)

            overall_sentiment = self._calculate_overall_sentiment(
                news_sentiment, forum_sentiment, hot_rank
            )

            return {
                'ticker': ticker,
                'analysis_period': f'{days} days',
                'overall_sentiment': overall_sentiment,
                'news_sentiment': news_sentiment,
                'forum_sentiment': forum_sentiment,
                'hot_rank': hot_rank,
                'summary': self._generate_sentiment_summary(overall_sentiment),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"get_stock_sentiment_summary failed: {e}")
            return {
                'ticker': ticker,
                'error': f'数据获取失败: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    def _get_eastmoney_direct_provider(self):
        try:
            from tradingagents.dataflows.providers.china.eastmoney_direct import EastMoneyDirectProvider
            if not hasattr(self, '_em_direct_provider') or self._em_direct_provider is None:
                self._em_direct_provider = EastMoneyDirectProvider()
            return self._em_direct_provider
        except Exception as e:
            logger.warning(f"EastMoneyDirectProvider unavailable: {e}")
            return None

    def _get_stock_forum_sentiment(self, ticker: str, days: int) -> Dict:
        try:
            ak = self._get_akshare()
            if ak is None:
                logger.info("AKShare不可用，尝试东方财富直接API获取千股千评")
                return self._get_stock_forum_sentiment_direct(ticker)

            code = self._normalize_code(ticker)

            now = time.time()
            if self._comment_cache is not None and self._comment_cache_time and (now - self._comment_cache_time) < self._cache_ttl:
                df = self._comment_cache
            else:
                try:
                    df = ak.stock_comment_em()
                    self._comment_cache = df
                    self._comment_cache_time = time.time()
                except Exception as e:
                    logger.warning(f"stock_comment_em failed: {e}, 降级到直接API")
                    return self._get_stock_forum_sentiment_direct(ticker)

            row = df[df['代码'] == code]
            if row.empty:
                logger.info(f"AKShare千股千评未找到{code}，尝试直接API")
                return self._get_stock_forum_sentiment_direct(ticker)

            r = row.iloc[0]
            score = float(r.get('综合得分', 0)) if pd.notna(r.get('综合得分')) else 0
            rank = int(r.get('目前排名', 0)) if pd.notna(r.get('目前排名')) else 0
            attention = float(r.get('关注指数', 0)) if pd.notna(r.get('关注指数')) else 0
            institution = float(r.get('机构参与度', 0)) if pd.notna(r.get('机构参与度')) else 0
            main_cost = float(r.get('主力成本', 0)) if pd.notna(r.get('主力成本')) else 0
            latest_price = float(r.get('最新价', 0)) if pd.notna(r.get('最新价')) else 0
            change_pct = float(r.get('涨跌幅', 0)) if pd.notna(r.get('涨跌幅')) else 0
            turnover = float(r.get('换手率', 0)) if pd.notna(r.get('换手率')) else 0
            pe = float(r.get('市盈率', 0)) if pd.notna(r.get('市盈率')) else 0
            rank_change = int(r.get('上升', 0)) if pd.notna(r.get('上升')) else 0
            name = str(r.get('名称', ''))

            normalized_score = (score - 50) / 50 if score != 0 else 0
            normalized_score = max(-1.0, min(1.0, normalized_score))

            confidence = 0.5
            if attention > 80:
                confidence += 0.2
            elif attention > 60:
                confidence += 0.1
            if institution > 0.4:
                confidence += 0.15
            if turnover > 1:
                confidence += 0.15
            confidence = min(confidence, 1.0)

            price_vs_cost = 0
            if main_cost > 0 and latest_price > 0:
                price_vs_cost = (latest_price - main_cost) / main_cost

            return {
                'sentiment_score': normalized_score,
                'confidence': confidence,
                'name': name,
                'score': score,
                'rank': rank,
                'rank_change': rank_change,
                'attention_index': attention,
                'institution_participation': institution,
                'main_cost': main_cost,
                'latest_price': latest_price,
                'price_vs_main_cost': round(price_vs_cost, 4),
                'change_pct': change_pct,
                'turnover_rate': turnover,
                'pe_ratio': pe,
                'data_source': 'eastmoney_comment'
            }

        except Exception as e:
            logger.error(f"_get_stock_forum_sentiment failed: {e}, 降级到直接API")
            return self._get_stock_forum_sentiment_direct(ticker)

    def _get_stock_forum_sentiment_direct(self, ticker: str) -> Dict:
        try:
            provider = self._get_eastmoney_direct_provider()
            if provider is None:
                return {'sentiment_score': 0, 'confidence': 0, 'data_source': 'unavailable'}

            code = self._normalize_code(ticker)
            result = provider._fetch_stock_comment_direct(code)

            if result is not None:
                logger.info(f"✅ 东方财富直接API获取千股千评成功: {code}")
                return result

            return {'sentiment_score': 0, 'confidence': 0, 'data_source': 'failed'}

        except Exception as e:
            logger.error(f"_get_stock_forum_sentiment_direct failed: {e}")
            return {'sentiment_score': 0, 'confidence': 0, 'error': str(e)}

    def _get_stock_hot_rank(self, ticker: str) -> Dict:
        try:
            ak = self._get_akshare()
            if ak is None:
                logger.info("AKShare不可用，尝试东方财富直接API获取人气排名")
                return self._get_stock_hot_rank_direct(ticker)

            code = self._normalize_code(ticker)

            now = time.time()
            if self._hot_rank_cache is not None and self._hot_rank_cache_time and (now - self._hot_rank_cache_time) < self._cache_ttl:
                df = self._hot_rank_cache
            else:
                try:
                    df = ak.stock_hot_rank_em()
                    self._hot_rank_cache = df
                    self._hot_rank_cache_time = time.time()
                except Exception as e:
                    logger.warning(f"stock_hot_rank_em failed: {e}, 降级到直接API")
                    return self._get_stock_hot_rank_direct(ticker)

            hot_code_variants = [code, f"SZ{code}", f"SH{code}"]
            row = df[df['代码'].isin(hot_code_variants)]
            if row.empty:
                row = df[df['代码'] == code]

            if row.empty:
                return self._get_stock_hot_rank_direct(ticker)

            r = row.iloc[0]
            rank = int(r.get('当前排名', 0)) if pd.notna(r.get('当前排名')) else 0
            name = str(r.get('股票名称', ''))
            change_pct = float(r.get('涨跌幅', 0)) if pd.notna(r.get('涨跌幅')) else 0

            hot_score = (101 - rank) / 100 if rank > 0 else 0
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

            confidence = 0.6 if rank > 0 else 0.3

            return {
                'in_top100': True,
                'rank': rank,
                'name': name,
                'change_pct': change_pct,
                'hot_score': hot_score,
                'sentiment_score': sentiment_from_rank,
                'confidence': confidence,
                'data_source': 'eastmoney_hot_rank'
            }

        except Exception as e:
            logger.error(f"_get_stock_hot_rank failed: {e}, 降级到直接API")
            return self._get_stock_hot_rank_direct(ticker)

    def _get_stock_hot_rank_direct(self, ticker: str) -> Dict:
        try:
            provider = self._get_eastmoney_direct_provider()
            if provider is None:
                return {'sentiment_score': 0, 'confidence': 0, 'data_source': 'unavailable'}

            code = self._normalize_code(ticker)
            result = provider._fetch_stock_hot_rank_direct(code)

            if result is not None:
                logger.info(f"✅ 东方财富直接API获取人气排名成功: {code}")
                return result

            return {
                'in_top100': False,
                'sentiment_score': 0,
                'confidence': 0.3,
                'data_source': 'eastmoney_hot_rank_direct'
            }

        except Exception as e:
            logger.error(f"_get_stock_hot_rank_direct failed: {e}")
            return {'sentiment_score': 0, 'confidence': 0, 'error': str(e)}

    def _get_finance_news_sentiment(self, ticker: str, days: int) -> Dict:
        try:
            ak = self._get_akshare()
            code = self._normalize_code(ticker)

            news_items = []
            if ak is not None:
                try:
                    try:
                        pd.options.future.infer_string = False
                    except Exception:
                        pass
                    news_df = ak.stock_news_em(symbol=code)
                    if news_df is not None and not news_df.empty:
                        for _, row in news_df.head(20).iterrows():
                            title = str(row.get('新闻标题', '') or row.get('标题', ''))
                            content = str(row.get('新闻内容', '') or row.get('内容', ''))
                            source = str(row.get('文章来源', '') or row.get('来源', ''))
                            pub_time = str(row.get('发布时间', '') or row.get('时间', ''))
                            url = str(row.get('新闻链接', '') or row.get('链接', ''))
                            news_items.append({
                                'title': title,
                                'content': content[:500],
                                'source': source,
                                'publish_time': pub_time,
                                'url': url
                            })
                except Exception as e:
                    logger.warning(f"stock_news_em failed for {code}: {e}")

                if not news_items:
                    try:
                        from tradingagents.dataflows.providers.china.akshare import AKShareProvider
                        provider = AKShareProvider()
                        fallback_df = provider.get_stock_news_sync(symbol=code, limit=15)
                        if fallback_df is not None and not fallback_df.empty:
                            for _, row in fallback_df.head(15).iterrows():
                                title = str(row.get('新闻标题', '') or row.get('标题', ''))
                                content = str(row.get('新闻内容', '') or row.get('内容', ''))
                                source = str(row.get('文章来源', '') or row.get('来源', ''))
                                pub_time = str(row.get('发布时间', '') or row.get('时间', ''))
                                url = str(row.get('新闻链接', '') or row.get('链接', ''))
                                news_items.append({
                                    'title': title,
                                    'content': content[:500],
                                    'source': source,
                                    'publish_time': pub_time,
                                    'url': url
                                })
                    except Exception as e2:
                        logger.warning(f"AKShareProvider fallback also failed for {code}: {e2}")

            if not news_items:
                logger.info(f"AKShare新闻获取失败，尝试东方财富直接API获取新闻: {code}")
                news_items = self._get_finance_news_direct(code)

            if not news_items:
                return {'sentiment_score': 0, 'confidence': 0, 'news_count': 0}

            positive_count = 0
            negative_count = 0
            neutral_count = 0

            for item in news_items:
                sentiment = self._analyze_text_sentiment(
                    item.get('title', '') + ' ' + item.get('content', '')
                )
                if sentiment > 0.1:
                    positive_count += 1
                elif sentiment < -0.1:
                    negative_count += 1
                else:
                    neutral_count += 1

            total = len(news_items)
            if total == 0:
                return {'sentiment_score': 0, 'confidence': 0, 'news_count': 0}

            sentiment_score = (positive_count - negative_count) / total

            return {
                'sentiment_score': sentiment_score,
                'positive_ratio': positive_count / total,
                'negative_ratio': negative_count / total,
                'neutral_ratio': neutral_count / total,
                'news_count': total,
                'confidence': min(total / 10, 1.0),
                'recent_news': news_items[:5],
                'data_source': 'eastmoney_news'
            }

        except Exception as e:
            logger.error(f"_get_finance_news_sentiment failed: {e}")
            return {'error': str(e), 'sentiment_score': 0, 'confidence': 0, 'news_count': 0}

    def _get_finance_news_direct(self, code: str) -> List[Dict]:
        try:
            provider = self._get_eastmoney_direct_provider()
            if provider is None:
                return []

            result = provider._fetch_stock_news_direct(code, page_size=20)

            if result is not None and len(result) > 0:
                logger.info(f"✅ 东方财富直接API获取新闻成功: {code}, 共{len(result)}条")
                return result

            return []

        except Exception as e:
            logger.error(f"_get_finance_news_direct failed: {e}")
            return []

    def _get_company_chinese_name(self, ticker: str) -> Optional[str]:
        try:
            ak = self._get_akshare()
            code = self._normalize_code(ticker)

            if ak is not None:
                now = time.time()
                if self._comment_cache is not None and self._comment_cache_time and (now - self._comment_cache_time) < self._cache_ttl:
                    df = self._comment_cache
                else:
                    try:
                        df = ak.stock_comment_em()
                        self._comment_cache = df
                        self._comment_cache_time = time.time()
                    except Exception:
                        df = None

                if df is not None:
                    row = df[df['代码'] == code]
                    if not row.empty:
                        name = str(row.iloc[0].get('名称', ''))
                        if name and name != 'nan':
                            return name

            provider = self._get_eastmoney_direct_provider()
            if provider is not None:
                result = provider._fetch_stock_comment_direct(code)
                if result is not None:
                    name = result.get('name', '')
                    if name and name != 'nan':
                        return name

            return None

        except Exception:
            return None

    def _analyze_text_sentiment(self, text: str) -> float:
        if not text:
            return 0

        positive_words = [
            '上涨', '增长', '利好', '看好', '买入', '推荐', '强势', '突破', '创新高',
            '盈利', '增收', '超预期', '反弹', '回升', '景气', '龙头', '领涨',
            '增持', '回购', '分红', '业绩预增', '扭亏', '涨停'
        ]
        negative_words = [
            '下跌', '下降', '利空', '看空', '卖出', '风险', '跌破', '创新低', '亏损',
            '减持', '退市', '违规', '处罚', '暴雷', '违约', '跌停', '下滑',
            '预警', '商誉减值', '诉讼', '调查', '停牌', '爆仓'
        ]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        if positive_count + negative_count == 0:
            return 0

        return (positive_count - negative_count) / (positive_count + negative_count)

    def _calculate_overall_sentiment(self, news_sentiment: Dict, forum_sentiment: Dict, hot_rank: Dict) -> Dict:
        news_weight = news_sentiment.get('confidence', 0) * 0.4
        forum_weight = forum_sentiment.get('confidence', 0) * 0.4
        hot_weight = hot_rank.get('confidence', 0) * 0.2

        total_weight = news_weight + forum_weight + hot_weight

        if total_weight == 0:
            return {'sentiment_score': 0, 'confidence': 0, 'level': 'neutral'}

        weighted_sentiment = (
            news_sentiment.get('sentiment_score', 0) * news_weight +
            forum_sentiment.get('sentiment_score', 0) * forum_weight +
            hot_rank.get('sentiment_score', 0) * hot_weight
        ) / total_weight

        if weighted_sentiment > 0.3:
            level = 'very_positive'
        elif weighted_sentiment > 0.1:
            level = 'positive'
        elif weighted_sentiment > -0.1:
            level = 'neutral'
        elif weighted_sentiment > -0.3:
            level = 'negative'
        else:
            level = 'very_negative'

        return {
            'sentiment_score': weighted_sentiment,
            'confidence': min(total_weight, 1.0),
            'level': level
        }

    def _generate_sentiment_summary(self, overall_sentiment: Dict) -> str:
        level = overall_sentiment.get('level', 'neutral')
        score = overall_sentiment.get('sentiment_score', 0)
        confidence = overall_sentiment.get('confidence', 0)

        level_descriptions = {
            'very_positive': '非常积极',
            'positive': '积极',
            'neutral': '中性',
            'negative': '消极',
            'very_negative': '非常消极'
        }

        description = level_descriptions.get(level, '中性')
        confidence_level = '高' if confidence > 0.7 else '中' if confidence > 0.3 else '低'

        return f"市场情绪: {description} (评分: {score:.2f}, 置信度: {confidence_level})"


def get_chinese_social_sentiment(ticker: str, curr_date: str) -> str:
    aggregator = ChineseFinanceDataAggregator()

    try:
        code = aggregator._normalize_code(ticker)
        sentiment_data = aggregator.get_stock_sentiment_summary(ticker, days=7)

        if 'error' in sentiment_data and 'overall_sentiment' not in sentiment_data:
            return f"""中国市场情绪分析报告 - {ticker}
分析日期: {curr_date}

数据获取遇到问题: {sentiment_data.get('error', '未知错误')}

建议:
1. 重点关注财经新闻和基本面分析
2. 参考官方财报和业绩指导
3. 关注行业政策和监管动态

生成时间: {sentiment_data.get('timestamp', datetime.now().isoformat())}
"""

        overall = sentiment_data.get('overall_sentiment', {})
        news = sentiment_data.get('news_sentiment', {})
        forum = sentiment_data.get('forum_sentiment', {})
        hot = sentiment_data.get('hot_rank', {})

        sections = []
        sections.append(f"""中国市场情绪分析报告 - {ticker}
分析日期: {curr_date}
分析周期: {sentiment_data.get('analysis_period', '7天')}

综合情绪评估:
{sentiment_data.get('summary', '数据不足')}""")

        if forum.get('data_source') == 'eastmoney_comment':
            name = forum.get('name', '')
            score = forum.get('score', 0)
            rank = forum.get('rank', 0)
            rank_change = forum.get('rank_change', 0)
            attention = forum.get('attention_index', 0)
            institution = forum.get('institution_participation', 0)
            main_cost = forum.get('main_cost', 0)
            latest_price = forum.get('latest_price', 0)
            price_vs_cost = forum.get('price_vs_main_cost', 0)
            change_pct = forum.get('change_pct', 0)
            turnover = forum.get('turnover_rate', 0)

            rank_change_str = f"↑{abs(rank_change)}" if rank_change > 0 else f"↓{abs(rank_change)}" if rank_change < 0 else "→0"
            cost_signal = "股价高于主力成本(偏多)" if price_vs_cost > 0 else "股价低于主力成本(偏空)" if price_vs_cost < 0 else "股价接近主力成本"

            sections.append(f"""
东方财富股吧数据:
- 股票名称: {name}({code})
- 综合得分: {score:.1f}/100
- 当前排名: 第{rank}名 ({rank_change_str})
- 关注指数: {attention:.1f}
- 机构参与度: {institution:.2%}
- 主力成本: {main_cost:.2f}元 | 最新价: {latest_price:.2f}元
- {cost_signal} (偏离{abs(price_vs_cost):.2%})
- 涨跌幅: {change_pct:.2f}% | 换手率: {turnover:.2f}%""")

        if hot.get('in_top100'):
            hot_rank_val = hot.get('rank', 0)
            hot_name = hot.get('name', '')
            hot_change = hot.get('change_pct', 0)
            hot_score = hot.get('hot_score', 0)
            sections.append(f"""
东方财富人气排名:
- 排名: 第{hot_rank_val}名 (TOP100)
- 股票名称: {hot_name}
- 涨跌幅: {hot_change:.2f}%
- 人气热度: {hot_score:.2f}""")
        else:
            sections.append(f"""
东方财富人气排名:
- 未进入TOP100人气榜""")

        news_count = news.get('news_count', 0)
        if news_count > 0:
            sections.append(f"""
财经新闻情绪:
- 情绪评分: {news.get('sentiment_score', 0):.2f}
- 正面新闻: {news.get('positive_ratio', 0):.1%}
- 负面新闻: {news.get('negative_ratio', 0):.1%}
- 中性新闻: {news.get('neutral_ratio', 0):.1%}
- 新闻数量: {news_count}条""")

            recent = news.get('recent_news', [])
            if recent:
                sections.append("\n近期重要新闻:")
                for i, item in enumerate(recent[:5], 1):
                    title = item.get('title', '')
                    source = item.get('source', '')
                    pub_time = item.get('publish_time', '')
                    sections.append(f"  {i}. {title} [{source}] {pub_time}")

        sections.append(f"""
数据来源: 东方财富股吧评论 + 人气排名 + 新闻情绪
生成时间: {sentiment_data.get('timestamp', datetime.now().isoformat())}""")

        return "\n".join(sections)

    except Exception as e:
        logger.error(f"get_chinese_social_sentiment failed: {e}")
        return f"""中国市场情绪分析 - {ticker}
分析日期: {curr_date}

分析失败: {str(e)}

建议:
1. 查看财经新闻网站的相关报道
2. 关注东方财富、同花顺等投资社区讨论
3. 参考专业机构的研究报告
4. 重点分析基本面和技术面数据
"""
