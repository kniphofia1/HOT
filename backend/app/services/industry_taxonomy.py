from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IndustryDefinition:
    key: str
    label: str
    short_label: str
    english_label: str
    description: str


INDUSTRIES: tuple[IndustryDefinition, ...] = (
    IndustryDefinition(
        key="ai",
        label="AI",
        short_label="AI",
        english_label="AI",
        description="模型发布、Agent、AI 编程、多模态、推理能力、MCP / 工具调用、AI 产品和开发者生态。",
    ),
    IndustryDefinition(
        key="semiconductor",
        label="半导体",
        short_label="半导体",
        english_label="SEMICONDUCTOR",
        description="GPU、AI 芯片、HBM、先进封装、数据中心、液冷、云厂商资本开支与电力约束。",
    ),
    IndustryDefinition(
        key="embodied_ai",
        label="具身智能",
        short_label="具身智能",
        english_label="EMBODIED AI",
        description="人形机器人、工业机器人、仓储物流机器人、机器人基础模型、灵巧手与量产交付。",
    ),
    IndustryDefinition(
        key="energy",
        label="新能源",
        short_label="新能源",
        english_label="ENERGY",
        description="数据中心用电、电网扩容、储能订单、绿电直连、可再生能源、核电、光伏、风电与电池。",
    ),
    IndustryDefinition(
        key="technology",
        label="技术",
        short_label="技术",
        english_label="TECHNOLOGY",
        description="计算机技术、编程语言、数据库、云原生、开源基础设施、网络安全、操作系统、开发者工具与框架更新。",
    ),
    IndustryDefinition(
        key="products",
        label="产品",
        short_label="产品",
        english_label="PRODUCTS",
        description="AI 产品、软件产品、电脑、手机、消费电子、硬件新品、应用发布与平台功能更新。",
    ),
)

LEGACY_INDUSTRY_ALIASES = {
    "ai_tech": "ai",
    "ai_compute_semiconductor_datacenter": "semiconductor",
    "robotics_embodied_ai": "embodied_ai",
    "energy_power_storage": "energy",
}

INDUSTRY_LABELS = {industry.key: industry.label for industry in INDUSTRIES}
INDUSTRY_SHORT_LABELS = {industry.key: industry.short_label for industry in INDUSTRIES}
INDUSTRY_ENGLISH_LABELS = {industry.key: industry.english_label for industry in INDUSTRIES}
INDUSTRY_DESCRIPTIONS = {industry.key: industry.description for industry in INDUSTRIES}
INDUSTRY_KEYS = tuple(industry.key for industry in INDUSTRIES)
INDUSTRY_QUERY_PATTERN = f"^({'|'.join((*INDUSTRY_KEYS, *LEGACY_INDUSTRY_ALIASES))})$"
INDUSTRY_CLASSIFICATION_REASON_KEY = "industry_classification"


def normalize_industry_key(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned in INDUSTRY_LABELS:
        return cleaned
    return LEGACY_INDUSTRY_ALIASES.get(cleaned)


def industry_values_from_config(config: dict[str, Any] | None) -> list[str]:
    config = config or {}
    values: list[str] = []
    raw_values = config.get("industries")
    if isinstance(raw_values, list):
        values.extend(str(value) for value in raw_values)
    raw_value = config.get("industry")
    if isinstance(raw_value, str):
        values.append(raw_value)
    return _valid_industries(values)


def industry_values_from_domains(domains: list[Any] | None) -> list[str]:
    return _valid_industries((str(value) for value in domains or []), allow_legacy_aliases=False)


def labels_for_industries(industry_keys: list[str]) -> list[str]:
    return [INDUSTRY_LABELS[key] for key in industry_keys if key in INDUSTRY_LABELS]


def classification_primary_industry(reasons: list[Any] | None) -> str | None:
    reason = _industry_classification_reason(reasons)
    if not reason:
        return None
    primary = normalize_industry_key(str(reason.get("primaryIndustry") or ""))
    if primary:
        return primary
    industries = reason.get("industries")
    if isinstance(industries, list) and industries:
        return normalize_industry_key(str(industries[0]))
    return None


def classification_related_industries(reasons: list[Any] | None) -> list[str]:
    reason = _industry_classification_reason(reasons)
    if not reason:
        return []
    values = reason.get("relatedIndustries")
    if not isinstance(values, list):
        values = []
    primary = classification_primary_industry(reasons)
    return [key for key in _valid_industries(values) if key != primary]


def has_industry_classification(reasons: list[Any] | None) -> bool:
    return _industry_classification_reason(reasons) is not None


def industry_classification_blocks_source_fallback(reasons: list[Any] | None) -> bool:
    reason = _industry_classification_reason(reasons)
    if not reason:
        return False
    return bool(reason.get("offTopic") or reason.get("noise"))


def _industry_classification_reason(reasons: list[Any] | None) -> dict[str, Any] | None:
    for reason in reasons or []:
        if isinstance(reason, dict) and reason.get("key") == INDUSTRY_CLASSIFICATION_REASON_KEY:
            return reason
    return None


def _valid_industries(values, *, allow_legacy_aliases: bool = True) -> list[str]:
    unique: list[str] = []
    for value in values:
        raw = str(value).strip()
        normalized = normalize_industry_key(raw) if allow_legacy_aliases else raw if raw in INDUSTRY_LABELS else None
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique
