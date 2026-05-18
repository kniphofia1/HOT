from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter

from app.services.source_market import SourcePlatformCapability, list_source_platform_capabilities


router = APIRouter(prefix="/api/source-market", tags=["source-market"])


class SourcePlatformCapabilityRead(BaseModel):
    platform: str
    source_type: str = Field(alias="sourceType")
    category: str
    access_mode: str = Field(alias="accessMode")
    automation_level: str = Field(alias="automationLevel")
    status: str
    requires_credential: bool = Field(alias="requiresCredential")
    requires_approval: bool = Field(alias="requiresApproval")
    supports_metrics: bool = Field(alias="supportsMetrics")
    cost_level: str = Field(alias="costLevel")
    notes: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("", response_model=list[SourcePlatformCapabilityRead])
def list_source_market() -> list[SourcePlatformCapability]:
    return list_source_platform_capabilities()
