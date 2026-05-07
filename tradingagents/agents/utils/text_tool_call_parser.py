import re
import json
from typing import List, Dict, Any, Optional, Tuple

from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")

_TOOL_NAME_PATTERNS = [
    r"get_stock_fundamentals_unified",
    r"get_stock_fundamental_data_unified",
    r"get_stock_sentiment_unified",
    r"get_stock_market_data_unified",
    r"get_finnhub_news",
    r"get_reddit_news",
    r"get_google_news",
    r"get_chinese_social_sentiment",
    r"get_china_stock_info_unified",
]

_TOOL_NAME_PREFIX_RE = re.compile(
    r"get_stock_(?:fundamental|sentiment|market)"
)


class TextToolCallParser:

    _TOOL_NAME_RE = re.compile(
        r"(?:" + "|".join(re.escape(p) for p in _TOOL_NAME_PATTERNS) + r")"
    )

    _KV_BLOCK_RE = re.compile(
        r"(get_stock_(?:fundamental[s]?_data|fundamentals|sentiment|market_data|market)_unified)"
        r"\s*\n((?:\w+\s*\n[^\n]*\n?)*)",
        re.MULTILINE,
    )

    _JSON_BLOCK_RE = re.compile(
        r'\{[^{}]*"name"\s*:\s*"('
        + "|".join(re.escape(p) for p in _TOOL_NAME_PATTERNS)
        + r')"[^{}]*\}',
        re.DOTALL,
    )

    _XML_BLOCK_RE = re.compile(
        r"<tool_call\w*>\s*(\{.*?\})\s*</tool_call\w*>",
        re.DOTALL | re.IGNORECASE,
    )

    @staticmethod
    def detect_text_tool_call(content: str) -> bool:
        if not content or not isinstance(content, str):
            return False
        if TextToolCallParser._TOOL_NAME_RE.search(content):
            return True
        if _TOOL_NAME_PREFIX_RE.search(content):
            return True
        if TextToolCallParser._XML_BLOCK_RE.search(content):
            return True
        json_match = TextToolCallParser._JSON_BLOCK_RE.search(content)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if "name" in data:
                    return True
            except (json.JSONDecodeError, ValueError):
                pass
        return False

    @staticmethod
    def parse_text_tool_calls(content: str) -> List[Dict[str, Any]]:
        if not content or not isinstance(content, str):
            return []

        calls: List[Dict[str, Any]] = []

        for match in TextToolCallParser._KV_BLOCK_RE.finditer(content):
            tool_name = match.group(1).strip()
            args_block = match.group(2).strip()
            args = TextToolCallParser._parse_kv_args(args_block)
            calls.append({"name": tool_name, "args": args})

        if calls:
            return calls

        for match in TextToolCallParser._XML_BLOCK_RE.finditer(content):
            try:
                data = json.loads(match.group(1))
                name = data.get("name", "")
                args = data.get("arguments", data.get("args", {}))
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except (json.JSONDecodeError, ValueError):
                        args = {"raw": args}
                if name:
                    calls.append({"name": name, "args": args})
            except (json.JSONDecodeError, ValueError):
                continue

        if calls:
            return calls

        for match in TextToolCallParser._JSON_BLOCK_RE.finditer(content):
            try:
                data = json.loads(match.group(0))
                name = data.get("name", "")
                args = data.get("arguments", data.get("args", {}))
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except (json.JSONDecodeError, ValueError):
                        args = {"raw": args}
                if name:
                    calls.append({"name": name, "args": args})
            except (json.JSONDecodeError, ValueError):
                continue

        return calls

    @staticmethod
    def _parse_kv_args(args_block: str) -> Dict[str, Any]:
        args: Dict[str, Any] = {}
        lines = args_block.strip().split("\n")
        i = 0
        while i < len(lines) - 1:
            key = lines[i].strip()
            value = lines[i + 1].strip()
            if key and not key.startswith("#"):
                args[key] = value
            i += 2
        return args

    @staticmethod
    def _fuzzy_match_tool(name: str, tool_map: Dict[str, Any]) -> Optional[Any]:
        if name in tool_map:
            return tool_map[name]
        for registered_name, tool in tool_map.items():
            if name.replace("_data", "") == registered_name.replace("_data", ""):
                return tool
            if name in registered_name or registered_name in name:
                return tool
        return None

    @staticmethod
    def execute_text_tool_calls(
        content: str,
        available_tools: List[Any],
    ) -> List[Tuple[str, str]]:
        calls = TextToolCallParser.parse_text_tool_calls(content)
        if not calls:
            return []

        results: List[Tuple[str, str]] = []
        tool_map = {}
        for tool in available_tools:
            name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
            if name:
                tool_map[name] = tool

        for call in calls:
            tool_name = call["name"]
            tool_args = call["args"]
            tool = TextToolCallParser._fuzzy_match_tool(tool_name, tool_map)
            if tool is None:
                logger.warning(f"⚠️ [TextToolCallParser] 工具未找到: {tool_name}")
                results.append((tool_name, f"工具 {tool_name} 不可用"))
                continue

            try:
                cleaned_args = TextToolCallParser._clean_args(tool_args)
                result = tool.invoke(cleaned_args)
                result_str = str(result) if result else "无数据返回"
                logger.info(f"✅ [TextToolCallParser] 工具执行成功: {tool_name}, 结果长度: {len(result_str)}")
                results.append((tool_name, result_str))
            except Exception as e:
                logger.error(f"❌ [TextToolCallParser] 工具执行失败: {tool_name} - {e}")
                results.append((tool_name, f"工具执行错误: {str(e)}"))

        return results

    @staticmethod
    def _clean_args(args: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = {}
        for k, v in args.items():
            if isinstance(v, str):
                v = v.strip()
                if v.lower() in ("none", "null", "undefined", ""):
                    continue
            cleaned[k] = v
        return cleaned

    @staticmethod
    def execute_and_generate_report(
        content: str,
        available_tools: List[Any],
        llm: Any,
        analyst_name: str = "分析师",
        analysis_prompt_template: str = None,
    ) -> Optional[str]:
        if not TextToolCallParser.detect_text_tool_call(content):
            return None

        logger.info(f"🔧 [TextToolCallParser] 检测到文本工具调用，开始解析执行 ({analyst_name})")

        tool_results = TextToolCallParser.execute_text_tool_calls(content, available_tools)
        if not tool_results:
            logger.warning(f"⚠️ [TextToolCallParser] 未能解析出有效的工具调用 ({analyst_name})")
            return None

        combined_data = "\n\n".join(
            f"## {name} 返回数据\n{result}" for name, result in tool_results
        )

        if analysis_prompt_template:
            analysis_request = analysis_prompt_template.format(data=combined_data)
        else:
            analysis_request = (
                f"基于以下真实数据，进行详细的股票分析：\n\n"
                f"{combined_data}\n\n"
                f"请提供详细、专业的中文分析报告，包含具体的投资建议。"
            )

        try:
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是专业的股票分析师，基于提供的真实数据进行分析。使用中文撰写报告。"),
                ("human", "{analysis_request}")
            ])
            chain = prompt | llm
            result = chain.invoke({"analysis_request": analysis_request})
            report = result.content if hasattr(result, "content") else str(result)
            logger.info(f"✅ [TextToolCallParser] 报告生成成功 ({analyst_name}), 长度: {len(report)}")
            return report
        except Exception as e:
            logger.error(f"❌ [TextToolCallParser] 报告生成失败 ({analyst_name}): {e}")
            return None
