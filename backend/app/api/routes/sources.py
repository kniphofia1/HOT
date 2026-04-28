from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Source
from app.db.session import get_db


router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceBase(BaseModel):
    type: str
    name: str
    url: str | None = None
    enabled: bool = True
    weight: int = 1
    poll_interval_minutes: int = Field(default=60, alias="pollIntervalMinutes")
    config_json: dict[str, Any] = Field(default_factory=dict, alias="configJson")

    model_config = ConfigDict(populate_by_name=True)


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    type: str | None = None
    name: str | None = None
    url: str | None = None
    enabled: bool | None = None
    weight: int | None = None
    poll_interval_minutes: int | None = Field(default=None, alias="pollIntervalMinutes")
    config_json: dict[str, Any] | None = Field(default=None, alias="configJson")
    last_error: str | None = Field(default=None, alias="lastError")

    model_config = ConfigDict(populate_by_name=True)


class SourceRead(BaseModel):
    id: str
    type: str
    name: str
    url: str | None
    enabled: bool
    weight: int
    poll_interval_minutes: int = Field(alias="pollIntervalMinutes")
    config_json: dict[str, Any] = Field(alias="configJson")
    last_fetched_at: datetime | None = Field(alias="lastFetchedAt")
    last_error: str | None = Field(alias="lastError")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.created_at.desc())).all())


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> Source:
    source = Source(
        type=payload.type,
        name=payload.name,
        url=payload.url,
        enabled=payload.enabled,
        weight=payload.weight,
        poll_interval_minutes=payload.poll_interval_minutes,
        config_json=payload.config_json,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: str, db: Session = Depends(get_db)) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.patch("/{source_id}", response_model=SourceRead)
def update_source(source_id: str, payload: SourceUpdate, db: Session = Depends(get_db)) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(source, key, value)

    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db)) -> Response:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    db.delete(source)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
