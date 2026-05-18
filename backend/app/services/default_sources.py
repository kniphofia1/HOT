from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors import connectors_by_type
from app.db.models import Source
from app.services.industry_taxonomy import normalize_industry_key


@dataclass(frozen=True)
class DefaultSourceSpec:
    type: str
    name: str
    url: str | None = None
    weight: int = 1
    poll_interval_minutes: int = 60
    config_json: dict[str, Any] = field(default_factory=dict)


AI = "ai"
SEMICONDUCTOR = "semiconductor"
EMBODIED_AI = "embodied_ai"
ENERGY = "energy"
TECHNOLOGY = "technology"
PRODUCTS = "products"


def _industry_config(industry: str, source_group: str, topics: list[str], **extra: Any) -> dict[str, Any]:
    source_tier = str(extra.pop("sourceTier", extra.pop("priority", "P0")))
    return {
        "industry": industry,
        "industries": [industry],
        "priority": source_tier,
        "sourceTier": source_tier,
        "sourceGroup": source_group,
        "topics": topics,
        "retryAttempts": 1,
        **extra,
    }


DEFAULT_SOURCE_SPECS = [
    DefaultSourceSpec(
        type="rss",
        name="OpenAI News RSS",
        url="https://openai.com/news/rss.xml",
        weight=4,
        poll_interval_minutes=120,
        config_json=_industry_config(AI, "official_rss", ["openai", "model_release", "product_update"]),
    ),
    DefaultSourceSpec(
        type="github_release",
        name="Claude Code GitHub Releases",
        url="https://github.com/anthropics/claude-code",
        weight=4,
        poll_interval_minutes=120,
        config_json=_industry_config(
            AI,
            "official_rss",
            ["claude_code", "github_release", "ai_coding", "developer_tools"],
            owner="anthropics",
            repo="claude-code",
            limit=10,
        ),
    ),
    DefaultSourceSpec(
        type="rss",
        name="The Decoder AI News RSS",
        url="https://the-decoder.com/feed/",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(AI, "official_rss", ["ai_news", "models", "products", "research"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="IT之家 RSS",
        url="https://www.ithome.com/rss/",
        weight=3,
        poll_interval_minutes=120,
        config_json=_industry_config(AI, "official_rss", ["china_ai_news", "product_update", "industry_news"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Anthropic Newsroom",
        url="https://www.anthropic.com/news",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(AI, "official_web", ["anthropic", "claude", "company_news", "model_release"], extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Claude Blog",
        url="https://www.claude.com/blog",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(AI, "official_web", ["claude", "blog", "model_release", "product_update"], extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="xAI News",
        url="https://x.ai/news",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(AI, "official_web", ["xai", "grok", "model_release", "company_news"], extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Hugging Face Blog",
        url="https://huggingface.co/blog",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(AI, "official_web", ["hugging_face", "open_source", "models", "developer_tools"], extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Tomer Tunguz Blog",
        url="https://tomtunguz.com/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(AI, "official_web", ["tomer_tunguz", "ai_investment", "industry_analysis"], extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Dwarkesh Patel Podcast & Blog",
        url="https://www.dwarkesh.com/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(AI, "official_web", ["dwarkesh", "podcast", "ai_research", "frontier_models"], extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="hacker_news",
        name="Hacker News AI Hot",
        weight=1,
        poll_interval_minutes=45,
        config_json=_industry_config(AI, "low_priority_or_noisy", ["hacker_news", "community", "ai_hot"], sourceTier="P2", listType="top", limit=30),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Google AI for Developers",
        url="https://ai.google.dev/",
        weight=2,
        poll_interval_minutes=360,
        config_json=_industry_config(AI, "low_priority_or_noisy", ["google_ai", "developer_tools"], sourceTier="P2", extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Baidu AI",
        url="https://cloud.baidu.com/product/wenxinworkshop",
        weight=2,
        poll_interval_minutes=360,
        config_json=_industry_config(AI, "low_priority_or_noisy", ["baidu", "wenxin", "china_ai"], sourceTier="P2", extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Alibaba Cloud AI",
        url="https://www.alibabacloud.com/blog/ai-machine-learning",
        weight=2,
        poll_interval_minutes=360,
        config_json=_industry_config(AI, "low_priority_or_noisy", ["alibaba_cloud", "ai_cloud", "china_ai"], sourceTier="P2", extractionMode="public_webpage"),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Epoch AI",
        url="https://epoch.ai/blog",
        weight=2,
        poll_interval_minutes=360,
        config_json=_industry_config(AI, "low_priority_or_noisy", ["epoch_ai", "research", "ai_trends"], sourceTier="P2", extractionMode="public_webpage"),
    ),
]


INDUSTRY_SOURCE_SPECS = [
    DefaultSourceSpec(
        type="rss",
        name="NVIDIA Newsroom / Blog RSS",
        url="https://blogs.nvidia.com/feed/",
        weight=4,
        poll_interval_minutes=120,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["gpu", "ai_chip", "datacenter", "cuda", "dgx"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="AMD Newsroom",
        url="https://www.amd.com/en/newsroom.html",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["mi_gpu", "epyc", "datacenter_ai"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="TSMC Press Center",
        url="https://pr.tsmc.com/english/news",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["advanced_process", "cowos", "foundry"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="ASML News",
        url="https://www.asml.com/en/news",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["lithography", "capex", "advanced_process"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="SK hynix Newsroom",
        url="https://news.skhynix.com/",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["hbm", "dram", "ai_memory"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Micron Newsroom",
        url="https://www.micron.com/about/news-and-events",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["hbm", "datacenter_memory", "storage"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Samsung Semiconductor News",
        url="https://semiconductor.samsung.com/news-events/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["hbm", "storage", "foundry"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Intel Newsroom",
        url="https://www.intel.com/content/www/us/en/newsroom/home.html",
        weight=3,
        poll_interval_minutes=180,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["ai_pc", "gaudi", "foundry", "advanced_packaging"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Broadcom Newsroom",
        url="https://www.broadcom.com/company/news",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["ai_asic", "networking", "datacenter_network"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Marvell Newsroom",
        url="https://www.marvell.com/company/newsroom.html",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(SEMICONDUCTOR, "company_official", ["datacenter_interconnect", "ai_networking"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="SemiAnalysis",
        url="https://www.semianalysis.com/feed",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(SEMICONDUCTOR, "high_signal_analysis", ["gpu_supply", "datacenter", "power", "ai_infrastructure"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="TrendForce AI / HBM / Server",
        url="https://www.trendforce.com/news/",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(SEMICONDUCTOR, "industry_data", ["hbm", "ai_server", "memory_price", "supply_chain"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="ServeTheHome AI / Data Center",
        url="https://www.servethehome.com/feed/",
        weight=3,
        poll_interval_minutes=180,
        config_json=_industry_config(SEMICONDUCTOR, "technical_media", ["ai_server", "datacenter_hardware", "liquid_cooling"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="MLCommons / MLPerf",
        url="https://mlcommons.org/benchmarks/",
        weight=4,
        poll_interval_minutes=360,
        config_json=_industry_config(SEMICONDUCTOR, "benchmark_data", ["mlperf", "training", "inference", "hardware_benchmark"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="SIA Semiconductor Industry Association",
        url="https://www.semiconductors.org/news-events/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(SEMICONDUCTOR, "industry_association", ["semiconductor_sales", "policy", "industry_trend"]),
    ),
    DefaultSourceSpec(
        type="sec_edgar_filings",
        name="SEC EDGAR AI Infrastructure Filings",
        url="https://www.sec.gov/search-filings",
        weight=4,
        poll_interval_minutes=360,
        config_json=_industry_config(
            SEMICONDUCTOR,
            "company_filings",
            ["capex", "earnings", "filings", "datacenter"],
            forms=["10-K", "10-Q", "8-K"],
            limit=40,
            companies=[
                {"ticker": "NVDA", "name": "NVIDIA", "cik": "1045810"},
                {"ticker": "AMD", "name": "Advanced Micro Devices", "cik": "2488"},
                {"ticker": "INTC", "name": "Intel", "cik": "50863"},
                {"ticker": "MSFT", "name": "Microsoft", "cik": "789019"},
                {"ticker": "META", "name": "Meta Platforms", "cik": "1326801"},
                {"ticker": "GOOGL", "name": "Alphabet", "cik": "1652044"},
                {"ticker": "AMZN", "name": "Amazon", "cik": "1018724"},
            ],
        ),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Microsoft Investor Relations",
        url="https://www.microsoft.com/en-us/Investor",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(SEMICONDUCTOR, "company_filings", ["ai_capex", "azure_ai", "datacenter"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Meta Investor Relations",
        url="https://investor.fb.com/investor-news/default.aspx",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(SEMICONDUCTOR, "company_filings", ["ai_capex", "gpu_cluster", "datacenter"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Alphabet Investor Relations",
        url="https://abc.xyz/investor/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(SEMICONDUCTOR, "company_filings", ["tpu", "google_cloud", "ai_capex"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Amazon Investor Relations",
        url="https://ir.aboutamazon.com/news-release/news-release-details/default.aspx",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(SEMICONDUCTOR, "company_filings", ["aws", "trainium", "datacenter_investment"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Figure AI News",
        url="https://www.figure.ai/news",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(EMBODIED_AI, "company_official", ["humanoid", "helix", "logistics", "home_robot"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Agility Robotics Press Releases",
        url="https://agilityrobotics.com/news",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "company_official", ["digit", "warehouse", "commercial_deployment"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Boston Dynamics News",
        url="https://bostondynamics.com/news/",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "company_official", ["atlas", "spot", "industrial_robot", "ai_robotics"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Tesla AI / Optimus",
        url="https://www.tesla.com/AI",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "company_official", ["optimus", "humanoid", "manufacturing"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Unitree Robotics News",
        url="https://www.unitree.com/news",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "company_official", ["g1", "h1", "quadruped", "humanoid"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="UBTECH Investor Relations",
        url="https://www.ubtrobot.com/en/investor-relations",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(EMBODIED_AI, "company_filings", ["walker", "humanoid_order", "mass_production"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Fourier Intelligence News",
        url="https://www.fftai.com/news",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "company_official", ["gr_series", "humanoid", "rehabilitation_robot"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Apptronik News",
        url="https://apptronik.com/news",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "company_official", ["apollo", "humanoid", "industrial_partner"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Sanctuary AI News",
        url="https://www.sanctuary.ai/news",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "company_official", ["general_purpose_robot", "embodied_ai"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="NVIDIA Isaac / Robotics Blog",
        url="https://developer.nvidia.com/blog/category/robotics/feed/",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "platform_official", ["isaac", "simulation", "robot_foundation_model", "jetson"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="The Robot Report",
        url="https://www.therobotreport.com/feed/",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(EMBODIED_AI, "industry_media", ["robotics_industry", "funding", "product_launch"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="IEEE Spectrum Robotics",
        url="https://spectrum.ieee.org/rss/robotics/fulltext",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "technical_media", ["robotics_research", "technology_trend", "case_study"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Robotics Business Review",
        url="https://www.roboticsbusinessreview.com/feed/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "industry_media", ["commercialization", "industry_application", "investment"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="arXiv cs.RO",
        url="https://rss.arxiv.org/rss/cs.RO",
        weight=3,
        poll_interval_minutes=720,
        config_json=_industry_config(EMBODIED_AI, "paper", ["robotics_research", "cs_ro"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="arXiv cs.CV",
        url="https://rss.arxiv.org/rss/cs.CV",
        weight=2,
        poll_interval_minutes=720,
        config_json=_industry_config(EMBODIED_AI, "paper", ["computer_vision", "embodied_perception"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="arXiv cs.LG",
        url="https://rss.arxiv.org/rss/cs.LG",
        weight=2,
        poll_interval_minutes=720,
        config_json=_industry_config(EMBODIED_AI, "paper", ["learning", "control", "foundation_model"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="ROS Discourse",
        url="https://discourse.ros.org/latest.rss",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "open_source_community", ["ros", "robotics_software_stack"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="GitHub Robotics Topic",
        url="https://github.com/topics/robotics",
        weight=2,
        poll_interval_minutes=360,
        config_json=_industry_config(EMBODIED_AI, "open_source_ecosystem", ["github", "robotics_open_source"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="高工机器人",
        url="https://www.gg-robot.com/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "chinese_industry_media", ["china_robotics", "supply_chain", "funding"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="机器人大讲堂",
        url="https://www.robotlecture.com/",
        weight=2,
        poll_interval_minutes=240,
        config_json=_industry_config(EMBODIED_AI, "chinese_industry_media", ["china_robotics", "industry_news"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="甲子光年机器人",
        url="https://www.jazzyear.com/",
        weight=2,
        poll_interval_minutes=360,
        config_json=_industry_config(EMBODIED_AI, "chinese_venture_media", ["embodied_ai", "funding", "startup"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="36氪机器人",
        url="https://www.36kr.com/information/technology/",
        weight=2,
        poll_interval_minutes=360,
        config_json=_industry_config(EMBODIED_AI, "chinese_venture_media", ["robotics", "startup", "funding"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="国家能源局",
        url="https://www.nea.gov.cn/",
        weight=4,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "policy_data", ["china_energy_policy", "renewable_energy", "charging_infrastructure"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="发改委能源政策",
        url="https://www.ndrc.gov.cn/xxgk/zcfb/",
        weight=4,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "policy", ["electricity_price", "energy_investment", "datacenter_energy_policy"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="工信部绿色数据中心 / 算力政策",
        url="https://www.miit.gov.cn/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "policy", ["green_datacenter", "compute_infrastructure", "energy_efficiency"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="IEA Energy and AI",
        url="https://www.iea.org/topics/artificial-intelligence",
        weight=4,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "international_agency", ["global_energy", "ai_power_demand", "datacenter_energy"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="EIA Today in Energy",
        url="https://www.eia.gov/rss/todayinenergy.xml",
        weight=4,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "us_energy_data", ["electricity_demand", "power_price", "generation_mix"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="NREL News",
        url="https://www.nrel.gov/news/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "research_institute", ["storage", "renewable_energy", "grid_research"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="European Commission Energy",
        url="https://energy.ec.europa.eu/news_en",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "policy", ["europe_energy_policy", "green_power", "storage"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="CNESA 中关村储能产业技术联盟",
        url="https://www.cnesa.org/",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "industry_association", ["china_storage", "installed_capacity", "policy", "project"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="EnergyTrend",
        url="https://www.energytrend.com/",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "industry_data", ["storage", "photovoltaic", "battery_price", "orders"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="InfoLink Consulting",
        url="https://www.infolink-group.com/energy-article",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "industry_data", ["solar", "storage", "supply_chain_price"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="BloombergNEF",
        url="https://about.bnef.com/blog/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "premium_data_public", ["datacenter_power", "clean_energy", "storage_forecast"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Wood Mackenzie Power & Renewables",
        url="https://www.woodmac.com/news/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "premium_data_public", ["power", "storage", "solar", "wind"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Rystad Energy",
        url="https://www.rystadenergy.com/news/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "premium_data_public", ["energy_investment", "power", "renewables"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="宁德时代 CATL",
        url="https://www.catl.com/en/news/",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "company_official", ["storage_battery", "overseas_order", "battery_technology"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="比亚迪储能 BYD Energy Storage",
        url="https://www.bydenergy.com/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "company_official", ["storage_system", "overseas_project"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="阳光电源 Sungrow",
        url="https://en.sungrowpower.com/news",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "company_official", ["storage_pcs", "inverter", "overseas_order"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="特斯拉能源 Tesla Energy",
        url="https://www.tesla.com/megapack",
        weight=4,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "company_official", ["megapack", "storage_deployment", "energy_business"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="隆基绿能 LONGi",
        url="https://www.longi.com/en/news/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "company_official", ["pv_module", "bc_cell", "capacity"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="通威股份",
        url="https://www.tongwei.com.cn/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(ENERGY, "company_official", ["silicon_material", "solar_cell", "pv_supply_chain"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="First Solar Investor Relations",
        url="https://investor.firstsolar.com/news/default.aspx",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "company_filings", ["us_solar_manufacturing", "thin_film_module"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="NextEra Energy Investor Relations",
        url="https://www.investor.nexteraenergy.com/news-and-events/news-releases",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "company_filings", ["utility", "datacenter_power", "renewable_power"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Dominion Energy Investor Relations",
        url="https://investors.dominionenergy.com/news-events/press-releases",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "company_filings", ["utility", "datacenter_region", "power_demand"]),
    ),
    DefaultSourceSpec(
        type="webpage",
        name="Grid Strategies",
        url="https://gridstrategiesllc.com/reports/",
        weight=3,
        poll_interval_minutes=360,
        config_json=_industry_config(ENERGY, "research_report", ["us_grid", "electricity_demand", "datacenter"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Data Center Dynamics",
        url="https://www.datacenterdynamics.com/en/rss/",
        weight=3,
        poll_interval_minutes=180,
        config_json=_industry_config(ENERGY, "industry_media", ["datacenter", "power", "liquid_cooling", "site_selection"]),
    ),
]


TECHNOLOGY_SOURCE_SPECS = [
    DefaultSourceSpec(
        type="rss",
        name="GitHub Changelog",
        url="https://github.blog/changelog/feed/",
        weight=4,
        poll_interval_minutes=120,
        config_json=_industry_config(TECHNOLOGY, "official_changelog", ["github", "developer_tools", "platform_updates"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="GitHub Engineering Blog",
        url="https://github.blog/engineering/feed/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(TECHNOLOGY, "technical_blog", ["software_engineering", "developer_platform", "open_source"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="AWS News Blog",
        url="https://aws.amazon.com/blogs/aws/feed/",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(TECHNOLOGY, "official_changelog", ["cloud", "infrastructure", "developer_platform"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Microsoft DevBlogs",
        url="https://devblogs.microsoft.com/feed/",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(TECHNOLOGY, "official_changelog", ["developer_tools", "windows_dev", "dotnet", "typescript"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Cloudflare Blog",
        url="https://blog.cloudflare.com/rss/",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(TECHNOLOGY, "technical_blog", ["networking", "security", "edge_compute", "developer_platform"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="CNCF Blog",
        url="https://www.cncf.io/feed/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(TECHNOLOGY, "open_source_community", ["cloud_native", "kubernetes", "open_source"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Kubernetes Blog",
        url="https://kubernetes.io/feed.xml",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(TECHNOLOGY, "official_changelog", ["kubernetes", "cloud_native", "containers"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Rust Blog",
        url="https://blog.rust-lang.org/feed.xml",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(TECHNOLOGY, "official_changelog", ["rust", "programming_language", "compiler"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Python Insider",
        url="https://blog.python.org/feeds/posts/default?alt=rss",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(TECHNOLOGY, "official_changelog", ["python", "programming_language", "release"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Node.js Blog",
        url="https://nodejs.org/en/feed/blog.xml",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(TECHNOLOGY, "official_changelog", ["nodejs", "javascript", "runtime"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Mozilla Hacks",
        url="https://hacks.mozilla.org/feed/",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(TECHNOLOGY, "technical_blog", ["web_platform", "browser", "developer_tools"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="InfoQ",
        url="https://feed.infoq.com/",
        weight=3,
        poll_interval_minutes=180,
        config_json=_industry_config(TECHNOLOGY, "technical_media", ["architecture", "software_engineering", "cloud_native"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="ACM TechNews",
        url="https://technews.acm.org/rss/technews.xml",
        weight=3,
        poll_interval_minutes=240,
        config_json=_industry_config(TECHNOLOGY, "research_media", ["computer_science", "research", "technology_news"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="The Register Software",
        url="https://www.theregister.com/software/headlines.atom",
        weight=2,
        poll_interval_minutes=180,
        config_json=_industry_config(TECHNOLOGY, "technical_media", ["software", "infrastructure", "security"], sourceTier="P1"),
    ),
]


PRODUCT_SOURCE_SPECS = [
    DefaultSourceSpec(
        type="rss",
        name="Apple Newsroom",
        url="https://www.apple.com/newsroom/rss-feed.rss",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(PRODUCTS, "official_newsroom", ["apple", "hardware", "software", "consumer_electronics"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Google The Keyword",
        url="https://blog.google/rss/",
        weight=4,
        poll_interval_minutes=180,
        config_json=_industry_config(PRODUCTS, "official_newsroom", ["google", "ai_products", "consumer_products"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Microsoft Windows Blog",
        url="https://blogs.windows.com/feed/",
        weight=3,
        poll_interval_minutes=180,
        config_json=_industry_config(PRODUCTS, "official_newsroom", ["windows", "surface", "pc", "copilot"]),
    ),
    DefaultSourceSpec(
        type="rss",
        name="The Verge",
        url="https://www.theverge.com/rss/index.xml",
        weight=3,
        poll_interval_minutes=90,
        config_json=_industry_config(PRODUCTS, "product_media", ["ai_products", "gadgets", "computers", "consumer_electronics"], sourceTier="P1"),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Ars Technica Gear & Gadgets",
        url="https://feeds.arstechnica.com/arstechnica/gadgets",
        weight=3,
        poll_interval_minutes=120,
        config_json=_industry_config(PRODUCTS, "product_media", ["gadgets", "computers", "hardware"], sourceTier="P1"),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Engadget",
        url="https://www.engadget.com/rss.xml",
        weight=3,
        poll_interval_minutes=120,
        config_json=_industry_config(PRODUCTS, "product_media", ["gadgets", "ai_products", "consumer_electronics"], sourceTier="P1"),
    ),
    DefaultSourceSpec(
        type="rss",
        name="TechCrunch AI",
        url="https://techcrunch.com/category/artificial-intelligence/feed/",
        weight=3,
        poll_interval_minutes=120,
        config_json=_industry_config(PRODUCTS, "product_media", ["ai_products", "startups", "apps"], sourceTier="P1"),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Tom's Hardware",
        url="https://www.tomshardware.com/feeds/all",
        weight=2,
        poll_interval_minutes=180,
        config_json=_industry_config(PRODUCTS, "product_media", ["pc", "hardware", "consumer_electronics"], sourceTier="P1"),
    ),
    DefaultSourceSpec(
        type="rss",
        name="PCWorld",
        url="https://www.pcworld.com/feed",
        weight=2,
        poll_interval_minutes=180,
        config_json=_industry_config(PRODUCTS, "product_media", ["pc", "laptop", "consumer_software"], sourceTier="P1"),
    ),
    DefaultSourceSpec(
        type="rss",
        name="Android Developers Blog",
        url="https://android-developers.googleblog.com/feeds/posts/default?alt=rss",
        weight=3,
        poll_interval_minutes=180,
        config_json=_industry_config(PRODUCTS, "official_changelog", ["android", "apps", "developer_platform"]),
    ),
]


def _x_config(source_group: str, topics: list[str], handles: list[str], **extra: Any) -> dict[str, Any]:
    query = "(" + " OR ".join(f"from:{handle.lstrip('@')}" for handle in handles) + ") -is:retweet -is:reply"
    source_tier = str(extra.pop("sourceTier", extra.pop("priority", "P0")))
    return {
        "query": query,
        "limit": 50,
        "pageLimit": 2,
        "fetchMode": "user_timelines",
        "lookbackHours": 24,
        "bearerTokenEnv": "X_BEARER_TOKEN",
        "requiresCredential": True,
        "priority": source_tier,
        "sourceTier": source_tier,
        "sourceGroup": source_group,
        "topics": topics,
        "handles": handles,
        "retryAttempts": 1,
        **extra,
    }


X_SOURCE_SPECS = [
    DefaultSourceSpec(
        type="x_recent_search",
        name="X AI High Signal Accounts",
        weight=3,
        poll_interval_minutes=60,
        config_json=_x_config(
            "high_signal_x",
            ["ai_models", "ai_products", "developer_tools", "ai_media"],
            [
                "berryxia",
                "AYi_AInotes",
                "op7418",
                "dotey",
                "kimmonismus",
                "steipete",
                "rohanpaul_ai",
                "OpenAIDevs",
                "ClaudeDevs",
                "runwayml",
                "krea_ai",
                "MiniMax_AI",
                "Replit",
            ],
            sourceTier="P0",
            industry=AI,
        ),
    ),
    DefaultSourceSpec(
        type="x_recent_search",
        name="X AI Product Company Accounts",
        weight=3,
        poll_interval_minutes=90,
        config_json=_x_config(
            "product_company_x",
            ["ai_products", "model_platform", "video_generation", "music_generation", "developer_tools"],
            ["OpenRouter", "perplexity_ai", "suno", "LumaLabsAI", "PixVerse_", "Kling_ai", "SenseTime_AI"],
            sourceTier="P1",
            industry=AI,
        ),
    ),
    DefaultSourceSpec(
        type="x_recent_search",
        name="X AI Opinion / Research Accounts",
        weight=3,
        poll_interval_minutes=90,
        config_json=_x_config(
            "opinion_research_x",
            ["ai_research", "ai_strategy", "industry_opinion", "frontier_models"],
            ["swyx", "emollick", "ylecun", "pmarca", "gdb", "sama", "SemiAnalysis_", "ArtificialAnlys"],
            sourceTier="P1",
            industry=AI,
        ),
    ),
    DefaultSourceSpec(
        type="x_recent_search",
        name="X AI Low Priority / Noisy Accounts",
        weight=1,
        poll_interval_minutes=180,
        config_json=_x_config(
            "low_priority_or_noisy",
            ["ai_research", "ai_commentary", "technical_opinion"],
            ["omarsar0", "deedydas", "natolambert", "polynoamial"],
            sourceTier="P2",
            industry=AI,
        ),
    ),
    DefaultSourceSpec(
        type="x_recent_search",
        name="X AI Compute / Semiconductor Watchlist",
        weight=3,
        poll_interval_minutes=90,
        config_json=_x_config(
            "expert_x",
            ["gpu", "semiconductor", "ai_infrastructure", "datacenter"],
            ["dylan522p", "SemiAnalysis_", "IanCutress", "ArtificialAnlys", "ServeTheHome", "PatrickMoorhead"],
            industry=SEMICONDUCTOR,
        ),
    ),
    DefaultSourceSpec(
        type="x_recent_search",
        name="X Robotics / Embodied AI Watchlist",
        weight=3,
        poll_interval_minutes=90,
        config_json=_x_config(
            "expert_x",
            ["robotics", "embodied_ai", "humanoid", "robot_foundation_model"],
            [
                "svlevine",
                "chelseabfinn",
                "NVIDIARobotics",
                "Figure_robot",
                "AgilityRobotics",
                "BostonDynamics",
                "UnitreeRobotics",
                "DrJimFan",
            ],
            industry=EMBODIED_AI,
        ),
    ),
    DefaultSourceSpec(
        type="x_recent_search",
        name="X Energy / Power / Storage Watchlist",
        weight=3,
        poll_interval_minutes=90,
        config_json=_x_config(
            "expert_x",
            ["power_grid", "clean_energy", "storage", "datacenter_power"],
            ["JigarShahDC", "JesseJenkins", "CanaryMediaInc", "MLiebreich", "NatBullard", "drvolts"],
            industry=ENERGY,
        ),
    ),
    DefaultSourceSpec(
        type="x_recent_search",
        name="X Technology Official / Expert Watchlist",
        weight=3,
        poll_interval_minutes=90,
        config_json=_x_config(
            "expert_x",
            ["developer_tools", "cloud_native", "security", "open_source"],
            [
                "github",
                "awscloud",
                "GoogleDevs",
                "msdev",
                "CloudflareDev",
                "kubernetesio",
                "CloudNativeFdn",
                "rustlang",
                "nodejs",
                "ThePSF",
                "mozilla",
            ],
            industry=TECHNOLOGY,
        ),
    ),
    DefaultSourceSpec(
        type="x_recent_search",
        name="X Product Official / Media Watchlist",
        weight=3,
        poll_interval_minutes=90,
        config_json=_x_config(
            "product_company_x",
            ["ai_products", "pc", "consumer_electronics", "product_launch"],
            [
                "OpenAI",
                "AnthropicAI",
                "Google",
                "Microsoft",
                "Windows",
                "surface",
                "Apple",
                "verge",
                "arstechnica",
                "engadget",
                "TechCrunch",
                "tomshardware",
            ],
            sourceTier="P1",
            industry=PRODUCTS,
        ),
    ),
]


DEFAULT_SOURCE_SPECS = [
    *DEFAULT_SOURCE_SPECS,
    *INDUSTRY_SOURCE_SPECS,
    *TECHNOLOGY_SOURCE_SPECS,
    *PRODUCT_SOURCE_SPECS,
    *X_SOURCE_SPECS,
]

DEPRECATED_DEFAULT_SOURCE_KEYS = {
    ("rss", "AI HOT RSS"),
    ("rss", "Google AI Blog RSS"),
    ("rss", "Simon Willison Atom"),
    ("hacker_news", "HN Top"),
    ("hacker_news", "HN New"),
    ("hacker_news", "HN Best"),
    ("hacker_news", "HN Show"),
    ("github_repo", "MCP Servers Repo"),
    ("github_release", "Next.js Releases"),
    ("reddit_subreddit", "Reddit r/MachineLearning Hot"),
    ("bluesky_search", "Bluesky AI Search"),
    ("bluesky_actor_feed", "Bluesky bsky.app Feed"),
    ("mastodon_timeline", "Mastodon AI Tag"),
    ("x_recent_search", "X AI Recent Search"),
    ("youtube_channel", "YouTube AI Search"),
    ("linkedin_posts", "LinkedIn Posts Template"),
    ("tiktok_research", "TikTok Research AI Query"),
    ("telegram_updates", "Telegram Bot Updates"),
    ("discord_channel", "Discord Channel Template"),
    ("slack_channel", "Slack Channel Template"),
    ("webpage", "Anthropic News Page"),
    ("webpage", "P0 / Anthropic Newsroom"),
    ("webpage", "P0 / Claude Blog"),
    ("rss", "P0 / Claude Code GitHub Releases"),
    ("rss", "P0 / Dwarkesh Podcast & Blog"),
    ("rss", "P0 / Hugging Face Blog"),
    ("rss", "P0 / IT之家 RSS"),
    ("rss", "P0 / OpenAI News RSS"),
    ("rss", "P0 / The Decoder AI News"),
    ("rss", "P0 / Tomer Tunguz Blog"),
    ("webpage", "P0 / xAI News"),
}


def _normalized_config(spec: DefaultSourceSpec, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    config = {**spec.config_json, **(existing or {})}
    industries = _normalize_industries(config)
    if not industries:
        industries = [AI]

    source_tier = _normalize_source_tier(config.get("sourceTier") or config.get("priority"))
    source_group = str(config.get("sourceGroup") or _infer_source_group(spec))
    topics = _normalize_topics(config) or [source_group]

    config["industries"] = industries
    config["industry"] = industries[0]
    config["sourceTier"] = source_tier
    config["priority"] = source_tier
    config["sourceGroup"] = source_group
    config["topics"] = topics
    config.pop("topic", None)
    return config


def _normalize_industries(config: dict[str, Any]) -> list[str]:
    values: list[str] = []
    raw_values = config.get("industries")
    if isinstance(raw_values, list):
        values.extend(str(value) for value in raw_values)
    raw_value = config.get("industry")
    if isinstance(raw_value, str):
        values.append(raw_value)
    return _dedupe(value for value in (normalize_industry_key(value) for value in values) if value)


def _normalize_source_tier(value: object) -> str:
    raw = str(value or "P0").upper()
    if raw.startswith("P0"):
        return "P0"
    if raw.startswith("P1"):
        return "P1"
    if raw.startswith("P2"):
        return "P2"
    return "P0"


def _normalize_topics(config: dict[str, Any]) -> list[str]:
    topics = config.get("topics")
    if isinstance(topics, list):
        values = [str(topic) for topic in topics if str(topic).strip()]
    else:
        values = []
    topic = config.get("topic")
    if isinstance(topic, str) and topic.strip():
        values.append(topic)
    return _dedupe(values)


def _infer_source_group(spec: DefaultSourceSpec) -> str:
    if spec.type == "rss":
        return "official_rss" if any(name in spec.name.lower() for name in ["openai", "nvidia", "eia"]) else "rss"
    if spec.type == "webpage":
        return "official_web"
    if spec.type == "github_release":
        return "github_release"
    if spec.type == "github_repo":
        return "github_repo"
    if spec.type == "hacker_news":
        return "community"
    if spec.type == "sec_edgar_filings":
        return "filings"
    if spec.type == "x_recent_search":
        return "expert_x"
    if spec.type in {"reddit_subreddit", "bluesky_search", "bluesky_actor_feed", "mastodon_timeline"}:
        return "public_social"
    return spec.type


def _dedupe(values) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def ensure_default_sources(db: Session) -> list[Source]:
    connector_types = set(connectors_by_type)
    existing_sources = db.scalars(select(Source)).all()
    existing_by_key = {(source.type, source.name): source for source in existing_sources}
    configured_sources: list[Source] = []

    for spec in DEFAULT_SOURCE_SPECS:
        if spec.type not in connector_types:
            continue

        source = existing_by_key.get((spec.type, spec.name))
        config = _normalized_config(spec, source.config_json if source is not None else None)
        if source is None:
            source = Source(
                type=spec.type,
                name=spec.name,
                url=spec.url,
                enabled=True,
                weight=spec.weight,
                poll_interval_minutes=spec.poll_interval_minutes,
                config_json=config,
            )
            db.add(source)
            configured_sources.append(source)
            continue

        if source.url is None and spec.url is not None:
            source.url = spec.url
        source.config_json = config
        db.add(source)
        configured_sources.append(source)

    configured_keys = {(spec.type, spec.name) for spec in DEFAULT_SOURCE_SPECS}
    for source in existing_sources:
        key = (source.type, source.name)
        if key in DEPRECATED_DEFAULT_SOURCE_KEYS and key not in configured_keys:
            source.enabled = False
            source.config_json = {
                **(source.config_json or {}),
                "replacedBySourceList": "ai_p0_p1_p2_2026",
            }
            db.add(source)

    db.commit()
    for source in configured_sources:
        db.refresh(source)
    return sorted(configured_sources, key=lambda item: (item.type, item.name))

