from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FetchRun
from app.db.session import get_db


router = APIRouter(prefix="/api/runs", tags=["runs"])


class FetchRunRead(BaseModel):
    id: str
    source_id: str = Field(alias="sourceId")
    status: str
    items_found: int = Field(alias="itemsFound")
    items_created: int = Field(alias="itemsCreated")
    error_message: str | None = Field(alias="errorMessage")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("/fetch", response_model=list[FetchRunRead])
def list_fetch_runs(db: Session = Depends(get_db)) -> list[FetchRun]:
    return list(db.scalars(select(FetchRun).order_by(FetchRun.started_at.desc())).all())
