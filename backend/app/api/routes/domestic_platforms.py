from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter

from app.services.domestic_platforms import DomesticPlatformPolicy, list_domestic_platform_policies


router = APIRouter(prefix="/api/domestic-platforms", tags=["domestic-platforms"])


class DomesticPlatformPolicyRead(BaseModel):
    platform: str
    source_type: str = Field(alias="sourceType")
    status: str
    automation_level: str = Field(alias="automationLevel")
    requires_credential: bool = Field(alias="requiresCredential")
    requires_approval: bool = Field(alias="requiresApproval")
    allowed_paths: list[str] = Field(alias="allowedPaths")
    prohibited_paths: list[str] = Field(alias="prohibitedPaths")
    manual_source_name: str = Field(alias="manualSourceName")
    notes: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("", response_model=list[DomesticPlatformPolicyRead])
def list_domestic_platforms() -> list[DomesticPlatformPolicy]:
    return list_domestic_platform_policies()
