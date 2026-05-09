"""
Alpha Vantage 基本面数据提供者

提供公司基本面数据，包括：
- 公司概况
- 财务报表（资产负债表、现金流量表、利润表）
- 估值指标

参考原版 TradingAgents 实现
"""

from typing import Annotated
import json
from datetime import datetime

from .alpha_vantage_common import _make_api_request, format_response_as_string

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


def _format_large_number(val_str) -> str:
    if val_str is None or val_str == 'None' or val_str == 'N/A':
        return 'N/A'
    try:
        val = float(val_str)
        if abs(val) >= 1e12:
            return f"${val/1e12:.2f}T"
        if abs(val) >= 1e9:
            return f"${val/1e9:.2f}B"
        if abs(val) >= 1e6:
            return f"${val/1e6:.2f}M"
        return f"${val:.2f}"
    except (ValueError, TypeError):
        return str(val_str)


def _safe_format_pct(val_str, is_pct: bool = False) -> str:
    if val_str is None or val_str == 'None' or val_str == 'N/A':
        return 'N/A'
    try:
        val = float(val_str)
        if is_pct:
            return f"{val:.2%}"
        return f"{val:.2f}"
    except (ValueError, TypeError):
        return str(val_str)


def get_fundamentals(
    ticker: Annotated[str, "Ticker symbol of the company"],
    curr_date: Annotated[str, "Current date (not used for Alpha Vantage)"] = None
) -> str:
    """
    获取公司综合基本面数据
    
    包括财务比率和关键指标，如：
    - 市值、PE、PB、ROE等估值指标
    - 收入、利润、EPS等财务指标
    - 行业、板块等公司信息
    
    Args:
        ticker: 股票代码
        curr_date: 当前日期（Alpha Vantage 不使用此参数）
        
    Returns:
        格式化的公司概况数据字符串
        
    Example:
        >>> fundamentals = get_fundamentals("AAPL")
    """
    try:
        logger.info(f"📊 [Alpha Vantage] 获取基本面数据: {ticker}")
        
        # 构建请求参数
        params = {
            "symbol": ticker.upper(),
        }
        
        # 发起 API 请求
        data = _make_api_request("OVERVIEW", params)
        
        # 格式化响应
        if isinstance(data, dict) and data:
            # 提取关键指标
            result = f"# Company Overview: {ticker.upper()}\n"
            result += f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # 基本信息
            result += "## Basic Information\n"
            result += f"**Name**: {data.get('Name', 'N/A')}\n"
            result += f"**Symbol**: {data.get('Symbol', 'N/A')}\n"
            result += f"**Exchange**: {data.get('Exchange', 'N/A')}\n"
            result += f"**Currency**: {data.get('Currency', 'N/A')}\n"
            result += f"**Country**: {data.get('Country', 'N/A')}\n"
            result += f"**Sector**: {data.get('Sector', 'N/A')}\n"
            result += f"**Industry**: {data.get('Industry', 'N/A')}\n\n"
            
            # 公司描述
            description = data.get('Description', 'N/A')
            if len(description) > 500:
                description = description[:500] + "..."
            result += f"**Description**: {description}\n\n"
            
            # 估值指标
            result += "## Valuation Metrics\n"
            result += f"**Market Cap**: {_format_large_number(data.get('MarketCapitalization'))}\n"
            result += f"**PE Ratio**: {_safe_format_pct(data.get('PERatio'))}\n"
            result += f"**PEG Ratio**: {_safe_format_pct(data.get('PEGRatio'))}\n"
            result += f"**Price to Book**: {_safe_format_pct(data.get('PriceToBookRatio'))}\n"
            result += f"**Price to Sales**: {_safe_format_pct(data.get('PriceToSalesRatioTTM'))}\n"
            result += f"**EV to Revenue**: {_safe_format_pct(data.get('EVToRevenue'))}\n"
            result += f"**EV to EBITDA**: {_safe_format_pct(data.get('EVToEBITDA'))}\n\n"
            
            # 财务指标
            result += "## Financial Metrics\n"
            result += f"**Revenue TTM**: {_format_large_number(data.get('RevenueTTM'))}\n"
            result += f"**Gross Profit TTM**: {_format_large_number(data.get('GrossProfitTTM'))}\n"
            result += f"**EBITDA**: {_format_large_number(data.get('EBITDA'))}\n"
            result += f"**Net Income TTM**: {_format_large_number(data.get('NetIncomeTTM'))}\n"
            result += f"**EPS**: {_safe_format_pct(data.get('EPS'))} per share\n"
            result += f"**Diluted EPS TTM**: {_safe_format_pct(data.get('DilutedEPSTTM'))} per share\n\n"
            
            # 盈利能力
            result += "## Profitability\n"
            result += f"**Profit Margin**: {_safe_format_pct(data.get('ProfitMargin'), is_pct=True)}\n"
            result += f"**Operating Margin TTM**: {_safe_format_pct(data.get('OperatingMarginTTM'), is_pct=True)}\n"
            result += f"**Return on Assets TTM**: {_safe_format_pct(data.get('ReturnOnAssetsTTM'), is_pct=True)}\n"
            result += f"**Return on Equity TTM**: {_safe_format_pct(data.get('ReturnOnEquityTTM'), is_pct=True)}\n\n"
            
            # 股息信息
            result += "## Dividend Information\n"
            result += f"**Dividend Per Share**: ${_safe_format_pct(data.get('DividendPerShare'))}\n"
            result += f"**Dividend Yield**: {_safe_format_pct(data.get('DividendYield'), is_pct=True)}\n"
            result += f"**Dividend Date**: {data.get('DividendDate', 'N/A')}\n"
            result += f"**Ex-Dividend Date**: {data.get('ExDividendDate', 'N/A')}\n\n"
            
            # 股票信息
            result += "## Stock Information\n"
            result += f"**52 Week High**: ${data.get('52WeekHigh', 'N/A')}\n"
            result += f"**52 Week Low**: ${data.get('52WeekLow', 'N/A')}\n"
            result += f"**50 Day MA**: ${data.get('50DayMovingAverage', 'N/A')}\n"
            result += f"**200 Day MA**: ${data.get('200DayMovingAverage', 'N/A')}\n"
            result += f"**Shares Outstanding**: {data.get('SharesOutstanding', 'N/A')}\n"
            result += f"**Beta**: {data.get('Beta', 'N/A')}\n\n"
            
            # 财务健康
            result += "## Financial Health\n"
            result += f"**Book Value**: ${data.get('BookValue', 'N/A')}\n"
            result += f"**Debt to Equity**: {data.get('DebtToEquity', 'N/A')}\n"
            result += f"**Current Ratio**: {data.get('CurrentRatio', 'N/A')}\n"
            result += f"**Quick Ratio**: {data.get('QuickRatio', 'N/A')}\n\n"
            
            # 分析师目标价
            result += "## Analyst Targets\n"
            result += f"**Analyst Target Price**: ${data.get('AnalystTargetPrice', 'N/A')}\n"
            result += f"**Analyst Rating Strong Buy**: {data.get('AnalystRatingStrongBuy', 'N/A')}\n"
            result += f"**Analyst Rating Buy**: {data.get('AnalystRatingBuy', 'N/A')}\n"
            result += f"**Analyst Rating Hold**: {data.get('AnalystRatingHold', 'N/A')}\n"
            result += f"**Analyst Rating Sell**: {data.get('AnalystRatingSell', 'N/A')}\n"
            result += f"**Analyst Rating Strong Sell**: {data.get('AnalystRatingStrongSell', 'N/A')}\n\n"
            
            logger.info(f"✅ [Alpha Vantage] 成功获取基本面数据: {ticker}")
            return result
        else:
            return format_response_as_string(data, f"Fundamentals for {ticker}")
            
    except Exception as e:
        logger.error(f"❌ [Alpha Vantage] 获取基本面数据失败 {ticker}: {e}")
        return f"Error retrieving fundamentals for {ticker}: {str(e)}"


def get_balance_sheet(
    ticker: Annotated[str, "Ticker symbol of the company"],
    freq: Annotated[str, "Reporting frequency: annual/quarterly (not used)"] = "quarterly",
    curr_date: Annotated[str, "Current date (not used)"] = None
) -> str:
    """
    获取资产负债表数据
    
    Args:
        ticker: 股票代码
        freq: 报告频率（Alpha Vantage 返回所有数据）
        curr_date: 当前日期（不使用）
        
    Returns:
        格式化的资产负债表数据字符串
    """
    try:
        logger.info(f"📊 [Alpha Vantage] 获取资产负债表: {ticker}")
        
        params = {"symbol": ticker.upper()}
        data = _make_api_request("BALANCE_SHEET", params)
        
        return format_response_as_string(data, f"Balance Sheet for {ticker}")
        
    except Exception as e:
        logger.error(f"❌ [Alpha Vantage] 获取资产负债表失败 {ticker}: {e}")
        return f"Error retrieving balance sheet for {ticker}: {str(e)}"


def get_cashflow(
    ticker: Annotated[str, "Ticker symbol of the company"],
    freq: Annotated[str, "Reporting frequency: annual/quarterly (not used)"] = "quarterly",
    curr_date: Annotated[str, "Current date (not used)"] = None
) -> str:
    """
    获取现金流量表数据
    
    Args:
        ticker: 股票代码
        freq: 报告频率（Alpha Vantage 返回所有数据）
        curr_date: 当前日期（不使用）
        
    Returns:
        格式化的现金流量表数据字符串
    """
    try:
        logger.info(f"📊 [Alpha Vantage] 获取现金流量表: {ticker}")
        
        params = {"symbol": ticker.upper()}
        data = _make_api_request("CASH_FLOW", params)
        
        return format_response_as_string(data, f"Cash Flow for {ticker}")
        
    except Exception as e:
        logger.error(f"❌ [Alpha Vantage] 获取现金流量表失败 {ticker}: {e}")
        return f"Error retrieving cash flow for {ticker}: {str(e)}"


def get_income_statement(
    ticker: Annotated[str, "Ticker symbol of the company"],
    freq: Annotated[str, "Reporting frequency: annual/quarterly (not used)"] = "quarterly",
    curr_date: Annotated[str, "Current date (not used)"] = None
) -> str:
    """
    获取利润表数据
    
    Args:
        ticker: 股票代码
        freq: 报告频率（Alpha Vantage 返回所有数据）
        curr_date: 当前日期（不使用）
        
    Returns:
        格式化的利润表数据字符串
    """
    try:
        logger.info(f"📊 [Alpha Vantage] 获取利润表: {ticker}")
        
        params = {"symbol": ticker.upper()}
        data = _make_api_request("INCOME_STATEMENT", params)
        
        return format_response_as_string(data, f"Income Statement for {ticker}")
        
    except Exception as e:
        logger.error(f"❌ [Alpha Vantage] 获取利润表失败 {ticker}: {e}")
        return f"Error retrieving income statement for {ticker}: {str(e)}"

