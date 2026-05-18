from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.models import FeedbackEntry
from app.db.session import get_db


router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    contact: str | None = Field(default=None, max_length=200)


class FeedbackRead(BaseModel):
    id: str
    message: str
    contact: str | None
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)) -> FeedbackEntry:
    message = payload.message.strip()
    contact = payload.contact.strip() if payload.contact else None
    if not message:
        raise HTTPException(status_code=422, detail="message cannot be blank")

    entry = FeedbackEntry(
        message=message,
        contact=contact or None,
        status="new",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
