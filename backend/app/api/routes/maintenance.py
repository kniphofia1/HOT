from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.models import LocalCredential
from app.db.session import get_db
from app.services.maintenance import (
    export_backup,
    refresh_local_credentials,
    restore_backup,
    source_health_summary,
    upsert_local_credential,
)


router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


class SourceHealthRead(BaseModel):
    source_id: str = Field(alias="sourceId")
    name: str
    type: str
    status: str
    enabled: bool
    is_due: bool = Field(alias="isDue")
    last_fetched_at: datetime | None = Field(alias="lastFetchedAt")
    next_fetch_at: datetime | None = Field(alias="nextFetchAt")
    last_run_status: str | None = Field(alias="lastRunStatus")
    last_run_at: datetime | None = Field(alias="lastRunAt")
    last_error: str | None = Field(alias="lastError")
    total_runs: int = Field(alias="totalRuns")
    failed_runs: int = Field(alias="failedRuns")
    consecutive_failures: int = Field(alias="consecutiveFailures")

    model_config = ConfigDict(populate_by_name=True)


class SystemHealthRead(BaseModel):
    status: str
    generated_at: datetime = Field(alias="generatedAt")
    source_count: int = Field(alias="sourceCount")
    enabled_source_count: int = Field(alias="enabledSourceCount")
    failing_source_count: int = Field(alias="failingSourceCount")
    stale_source_count: int = Field(alias="staleSourceCount")
    disabled_source_count: int = Field(alias="disabledSourceCount")
    never_fetched_source_count: int = Field(alias="neverFetchedSourceCount")
    sources: list[SourceHealthRead]

    model_config = ConfigDict(populate_by_name=True)


class BackupRead(BaseModel):
    version: int
    generated_at: str = Field(alias="generatedAt")
    tables: dict[str, list[dict[str, Any]]]

    model_config = ConfigDict(populate_by_name=True)


class RestoreRead(BaseModel):
    status: str
    restored: dict[str, int]


class LocalCredentialUpsert(BaseModel):
    key: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=255)
    provider: str | None = None
    environment_key: str | None = Field(default=None, alias="environmentKey")
    notes: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class LocalCredentialRead(BaseModel):
    id: str
    key: str
    label: str
    provider: str | None
    environment_key: str | None = Field(alias="environmentKey")
    secret_hint: str | None = Field(alias="secretHint")
    configured: bool
    notes: str | None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("/health", response_model=SystemHealthRead)
def get_maintenance_health(db: Session = Depends(get_db)) -> dict[str, Any]:
    return source_health_summary(db)


@router.get("/backup", response_model=BackupRead)
def get_backup(db: Session = Depends(get_db)) -> dict[str, Any]:
    return export_backup(db)


@router.post("/restore", response_model=RestoreRead)
def restore_from_backup(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return restore_backup(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/backup/download")
def download_backup(db: Session = Depends(get_db)) -> Response:
    backup = export_backup(db)
    content = BackupRead.model_validate(backup).model_dump_json(by_alias=True, indent=2)
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="hot-radar-backup.json"'},
    )


@router.get("/credentials", response_model=list[LocalCredentialRead])
def list_credentials(db: Session = Depends(get_db)) -> list[LocalCredential]:
    return refresh_local_credentials(db)


@router.post("/credentials", response_model=LocalCredentialRead, status_code=status.HTTP_201_CREATED)
def save_credential(payload: LocalCredentialUpsert, db: Session = Depends(get_db)) -> LocalCredential:
    return upsert_local_credential(
        db,
        key=payload.key.strip(),
        label=payload.label.strip(),
        provider=payload.provider.strip() if payload.provider else None,
        environment_key=payload.environment_key.strip() if payload.environment_key else None,
        notes=payload.notes.strip() if payload.notes else None,
    )


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(credential_id: str, db: Session = Depends(get_db)) -> Response:
    credential = db.get(LocalCredential, credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LocalCredential not found")
    db.delete(credential)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
