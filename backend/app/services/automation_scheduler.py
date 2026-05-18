from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from typing import Any

from fastapi import FastAPI

from app.db.session import SessionLocal
from app.services.automation import run_due_automation


SCHEDULER_STATE_KEY = "automation_scheduler_task"
logger = logging.getLogger(__name__)


def start_automation_scheduler(app: FastAPI) -> None:
    if _scheduler_disabled():
        return
    if getattr(app.state, SCHEDULER_STATE_KEY, None) is not None:
        return
    task = asyncio.create_task(_scheduler_loop())
    setattr(app.state, SCHEDULER_STATE_KEY, task)


async def stop_automation_scheduler(app: FastAPI) -> None:
    task: asyncio.Task[Any] | None = getattr(app.state, SCHEDULER_STATE_KEY, None)
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    setattr(app.state, SCHEDULER_STATE_KEY, None)


async def _scheduler_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(_run_due_automation_once)
        except Exception:  # noqa: BLE001 - background scheduler must survive transient failures.
            logger.exception("Automation scheduler tick failed")
        await asyncio.sleep(60)


def _run_due_automation_once() -> None:
    with SessionLocal() as db:
        run_due_automation(db)


def _scheduler_disabled() -> bool:
    value = os.getenv("ENABLE_AUTOMATION_SCHEDULER", "").strip().lower()
    if value in {"0", "false", "no", "off"}:
        return True
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    return False
