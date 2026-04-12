"""APScheduler integration for cron job execution.

The scheduler is started during the FastAPI lifespan and shut down cleanly on exit.
On startup, all enabled CronJob rows are loaded from the database and registered.
"""
import logging
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import CronJob

log = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")

# Base URL for internal HTTP calls (same process in production is fine; override via env)
import os
_INTERNAL_BASE = os.getenv("INTERNAL_API_BASE", "http://localhost:8000")


async def _run_job(job_id: int, target_route: str, payload: dict | None) -> None:
    """Execute a single cron job: POST to target_route and update last_run."""
    url = f"{_INTERNAL_BASE}{target_route}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload or {})
            r.raise_for_status()
        log.info("Cron job %d → %s succeeded (%d)", job_id, target_route, r.status_code)
    except Exception as exc:
        log.warning("Cron job %d → %s failed: %s", job_id, target_route, exc)

    async with AsyncSessionLocal() as session:
        row = await session.get(CronJob, job_id)
        if row:
            row.last_run = datetime.now(timezone.utc)
            row.run_count += 1
            await session.commit()


def schedule_job(job: CronJob) -> None:
    """Add (or replace) a single CronJob in the in-memory scheduler."""
    job_key = f"cron_{job.id}"
    if _scheduler.get_job(job_key):
        _scheduler.remove_job(job_key)
    if not job.enabled:
        return
    try:
        trigger = CronTrigger.from_crontab(job.cron_expr, timezone="UTC")
    except ValueError:
        log.warning("Invalid cron expression for job %d: %s", job.id, job.cron_expr)
        return
    _scheduler.add_job(
        _run_job,
        trigger=trigger,
        id=job_key,
        args=[job.id, job.target_route, job.payload_json],
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,
    )
    log.info("Scheduled cron job %d (%s) → %s", job.id, job.cron_expr, job.target_route)


def unschedule_job(job_id: int) -> None:
    job_key = f"cron_{job_id}"
    if _scheduler.get_job(job_key):
        _scheduler.remove_job(job_key)


async def load_all_jobs() -> None:
    """Load every enabled CronJob from the DB into the scheduler at startup."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(CronJob).where(CronJob.enabled == True))).scalars().all()
        for row in rows:
            schedule_job(row)
    log.info("Loaded %d cron jobs into scheduler", len(rows))


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler
