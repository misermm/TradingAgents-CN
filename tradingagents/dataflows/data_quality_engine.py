#!/usr/bin/env python3
"""
数据质量引擎
整合数据补全、交叉验证、溯源标记三大功能

Phase 1.2: 数据补全引擎 - 质量评分+缺失字段补全
Phase 1.3: 数据交叉验证 - 关键指标多源对比
Phase 1.4: 数据溯源标记 - FieldProvenance
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FieldProvenance:
    source: str
    fetched_at: datetime
    completeness: float = 1.0
    is_estimated: bool = False
    cross_validated: bool = False
    cross_validation_deviation: Optional[float] = None


@dataclass
class DataQualityResult:
    data: Dict[str, Any]
    quality_score: int
    provenance: Dict[str, FieldProvenance]
    missing_fields: List[str]
    complemented_fields: Dict[str, str]
    cross_validated_fields: Dict[str, Dict[str, Any]]
    warnings: List[str] = field(default_factory=list)


CN_CORE_FIELDS = {
    "pe", "pe_ttm", "pb", "total_mv", "circ_mv",
    "turnover_rate", "volume_ratio",
}

CN_SECONDARY_FIELDS = {
    "roe", "roa", "revenue_ttm", "net_profit_ttm",
    "debt_ratio", "current_ratio",
}

CN_CROSS_VALIDATION_FIELDS = {
    "pe": {"threshold": 0.10},
    "pb": {"threshold": 0.10},
    "roe": {"threshold": 0.15},
    "total_mv": {"threshold": 0.05},
}

CN_COMPLEMENT_SOURCES = {
    "pe": ["akshare", "baostock"],
    "pe_ttm": ["akshare", "baostock"],
    "pb": ["akshare", "baostock"],
    "roe": ["akshare", "baostock"],
    "roa": ["akshare", "baostock"],
    "total_mv": ["akshare"],
    "circ_mv": ["akshare"],
    "turnover_rate": ["akshare"],
    "volume_ratio": ["akshare"],
    "revenue_ttm": ["baostock"],
    "net_profit_ttm": ["baostock"],
}


class DataQualityEngine:
    """
    数据质量引擎

    三大功能：
    1. 质量评分：评估数据完整性，0-5分
    2. 数据补全：从备选数据源补全缺失字段
    3. 交叉验证：关键指标多源对比，标注偏差
    4. 溯源标记：每个字段标注来源、时间、可信度
    """

    def __init__(self):
        self._akshare_provider = None
        self._baostock_provider = None

    def _get_akshare_provider(self):
        if self._akshare_provider is None:
            try:
                from tradingagents.dataflows.providers.china.akshare import get_akshare_provider
                self._akshare_provider = get_akshare_provider()
            except Exception as e:
                logger.warning(f"AKShare provider 不可用: {e}")
        return self._akshare_provider

    def _get_baostock_provider(self):
        if self._baostock_provider is None:
            try:
                from tradingagents.dataflows.providers.china.baostock import get_baostock_provider
                self._baostock_provider = get_baostock_provider()
            except Exception as e:
                logger.warning(f"BaoStock provider 不可用: {e}")
        return self._baostock_provider

    def score_quality(self, data: Dict[str, Any], market: str = "cn") -> int:
        """
        评估数据质量评分 (0-5)

        5分: 所有核心字段都有值，数据完整
        4分: 核心字段完整，1-2个次要字段缺失
        3分: 核心字段缺失1个
        2分: 核心字段缺失2-3个
        1分: 大量字段缺失
        0分: 完全无数据
        """
        if not data:
            return 0

        if market == "cn":
            core_fields = CN_CORE_FIELDS
            secondary_fields = CN_SECONDARY_FIELDS
        else:
            return 5

        core_present = sum(1 for f in core_fields if data.get(f) is not None)
        core_total = len(core_fields)
        secondary_present = sum(1 for f in secondary_fields if data.get(f) is not None)
        secondary_total = len(secondary_fields)

        core_ratio = core_present / core_total if core_total > 0 else 0
        secondary_missing = secondary_total - secondary_present

        if core_ratio >= 1.0 and secondary_missing <= 2:
            return 5
        elif core_ratio >= 1.0 and secondary_missing <= 4:
            return 4
        elif core_ratio >= 0.85:
            return 3
        elif core_ratio >= 0.6:
            return 2
        elif core_ratio > 0:
            return 1
        else:
            return 0

    def identify_missing_fields(self, data: Dict[str, Any], market: str = "cn") -> List[str]:
        """识别缺失字段"""
        if not data:
            return list(CN_CORE_FIELDS | CN_SECONDARY_FIELDS)

        if market == "cn":
            all_fields = CN_CORE_FIELDS | CN_SECONDARY_FIELDS
        else:
            return []

        missing = []
        for f in all_fields:
            val = data.get(f)
            if val is None or val == "" or val == "None":
                missing.append(f)
        return missing

    async def complement_data(
        self,
        data: Dict[str, Any],
        symbol: str,
        market: str = "cn",
    ) -> DataQualityResult:
        """
        数据补全主入口

        1. 评分
        2. 识别缺失字段
        3. 从备选数据源补全
        4. 交叉验证
        5. 构建溯源标记
        """
        now = datetime.now(timezone.utc)
        provenance: Dict[str, FieldProvenance] = {}
        complemented_fields: Dict[str, str] = {}
        cross_validated_fields: Dict[str, Dict[str, Any]] = {}
        warnings: List[str] = []

        for key, val in data.items():
            if val is not None and val != 0 and val != "" and val != "None":
                provenance[key] = FieldProvenance(
                    source=data.get("data_source", "unknown"),
                    fetched_at=now,
                    completeness=1.0,
                    is_estimated=key.endswith("_ttm") or key.endswith("_estimated"),
                )

        initial_score = self.score_quality(data, market)
        missing = self.identify_missing_fields(data, market)

        if missing and market == "cn":
            complemented = await self._complement_cn_fields(data, symbol, missing, provenance, complemented_fields, now)
            data.update(complemented)

        if market == "cn":
            await self._cross_validate_cn(data, symbol, provenance, cross_validated_fields, warnings)

        final_score = self.score_quality(data, market)
        remaining_missing = self.identify_missing_fields(data, market)

        if initial_score < final_score:
            logger.info(f"📊 数据补全: {symbol} 质量评分 {initial_score} → {final_score}, 补全了 {len(complemented_fields)} 个字段")

        return DataQualityResult(
            data=data,
            quality_score=final_score,
            provenance=provenance,
            missing_fields=remaining_missing,
            complemented_fields=complemented_fields,
            cross_validated_fields=cross_validated_fields,
            warnings=warnings,
        )

    async def _complement_cn_fields(
        self,
        data: Dict[str, Any],
        symbol: str,
        missing: List[str],
        provenance: Dict[str, FieldProvenance],
        complemented_fields: Dict[str, str],
        now: datetime,
    ) -> Dict[str, Any]:
        """从备选数据源补全A股缺失字段"""
        complemented = {}

        akshare_data = None
        baostock_data = None

        for field_name in missing:
            sources = CN_COMPLEMENT_SOURCES.get(field_name, [])
            if not sources:
                continue

            for source_name in sources:
                value = None
                source_used = None

                if source_name == "akshare":
                    if akshare_data is None:
                        akshare_data = await self._fetch_akshare_complement_data(symbol)
                    if akshare_data:
                        value = akshare_data.get(field_name)
                        source_used = "akshare"

                elif source_name == "baostock":
                    if baostock_data is None:
                        baostock_data = await self._fetch_baostock_complement_data(symbol)
                    if baostock_data:
                        value = baostock_data.get(field_name)
                        source_used = "baostock"

                if value is not None and value != 0 and value != "":
                    complemented[field_name] = value
                    complemented_fields[field_name] = source_used
                    provenance[field_name] = FieldProvenance(
                        source=source_used,
                        fetched_at=now,
                        completeness=1.0,
                        is_estimated=field_name.endswith("_ttm"),
                    )
                    logger.debug(f"补全 {symbol}.{field_name} = {value} (来源: {source_used})")
                    break

        return complemented

    async def _fetch_akshare_complement_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从AKShare获取补全数据"""
        provider = self._get_akshare_provider()
        if not provider or not provider.is_available():
            return None

        try:
            quotes = await provider.get_stock_quotes(symbol)
            if quotes:
                result = {}
                for key in ("pe", "pe_ttm", "pb", "total_mv", "circ_mv",
                            "turnover_rate", "volume_ratio"):
                    val = quotes.get(key)
                    if val is not None and val != 0:
                        result[key] = val
                return result if result else None
        except Exception as e:
            logger.debug(f"AKShare补全数据获取失败 {symbol}: {e}")
        return None

    async def _fetch_baostock_complement_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从BaoStock获取补全数据"""
        provider = self._get_baostock_provider()
        if not provider or not provider.is_available():
            return None

        try:
            result = {}

            valuation = await provider.get_valuation_data(symbol)
            if valuation:
                mapping = {
                    "pe_ttm": "pe_ttm",
                    "pb_mrq": "pb",
                    "ps_ttm": None,
                    "pcf_ttm": None,
                }
                for bs_key, our_key in mapping.items():
                    if our_key is None:
                        continue
                    val = valuation.get(bs_key)
                    if val is not None and val != 0:
                        result[our_key] = val

            financial = await provider.get_financial_data(symbol)
            if financial:
                profit = financial.get("profit_data", {})
                if isinstance(profit, dict):
                    if profit.get("roeAvg"):
                        result["roe"] = float(profit["roeAvg"])
                    if profit.get("roaAvg"):
                        result["roa"] = float(profit["roaAvg"])
                    elif profit.get("roeAvg"):
                        result["roa"] = float(profit["roeAvg"]) * 0.5

                growth = financial.get("growth_data", {})
                if isinstance(growth, dict):
                    if growth.get("YYSRZZL"):
                        result["revenue_ttm"] = float(growth["YYSRZZL"])
                    if growth.get("JLRZZL"):
                        result["net_profit_ttm"] = float(growth["JLRZZL"])

            return result if result else None
        except Exception as e:
            logger.debug(f"BaoStock补全数据获取失败 {symbol}: {e}")
        return None

    async def _cross_validate_cn(
        self,
        data: Dict[str, Any],
        symbol: str,
        provenance: Dict[str, FieldProvenance],
        cross_validated_fields: Dict[str, Dict[str, Any]],
        warnings: List[str],
    ):
        """交叉验证A股关键指标"""
        akshare_data = await self._fetch_akshare_complement_data(symbol)
        baostock_data = await self._fetch_baostock_complement_data(symbol)

        for field_name, config in CN_CROSS_VALIDATION_FIELDS.items():
            threshold = config["threshold"]
            primary_val = data.get(field_name)

            if primary_val is None or primary_val == 0:
                continue

            secondary_val = None
            secondary_source = None

            if baostock_data and baostock_data.get(field_name) is not None:
                secondary_val = baostock_data[field_name]
                secondary_source = "baostock"
            elif akshare_data and akshare_data.get(field_name) is not None:
                secondary_val = akshare_data[field_name]
                secondary_source = "akshare"

            if secondary_val is None or secondary_val == 0:
                continue

            deviation = abs(primary_val - secondary_val) / max(abs(primary_val), abs(secondary_val), 1e-10)

            cross_validated_fields[field_name] = {
                "primary_value": primary_val,
                "primary_source": data.get("data_source", "unknown"),
                "secondary_value": secondary_val,
                "secondary_source": secondary_source,
                "deviation": deviation,
                "within_threshold": deviation <= threshold,
            }

            if field_name in provenance:
                provenance[field_name].cross_validated = True
                provenance[field_name].cross_validation_deviation = deviation

            if deviation > threshold:
                msg = f"⚠️ {symbol}.{field_name} 数据源偏差较大: {primary_val} vs {secondary_val} (偏差{deviation:.1%}, 阈值{threshold:.0%})"
                warnings.append(msg)
                logger.warning(msg)

    def build_provenance_summary(self, result: DataQualityResult) -> str:
        """构建溯源摘要文本，用于分析报告"""
        lines = []
        lines.append(f"数据质量评分: {result.quality_score}/5")

        if result.complemented_fields:
            lines.append(f"补全字段: {', '.join(f'{k}←{v}' for k, v in result.complemented_fields.items())}")

        if result.missing_fields:
            lines.append(f"仍缺失字段: {', '.join(result.missing_fields)}")

        if result.warnings:
            for w in result.warnings:
                lines.append(w)

        estimated = [k for k, v in result.provenance.items() if v.is_estimated]
        if estimated:
            lines.append(f"估算值字段: {', '.join(estimated)}")

        return "\n".join(lines)


_engine = None


def get_data_quality_engine() -> DataQualityEngine:
    global _engine
    if _engine is None:
        _engine = DataQualityEngine()
    return _engine
