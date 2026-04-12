"""Cron job management API.

Endpoints:
  GET  /cron/jobs          — list user's jobs
  POST /cron/jobs          — create job
  PATCH /cron/jobs/{id}    — update (name/cron_expr/enabled/payload)
  DELETE /cron/jobs/{id}   — delete
  POST /cron/jobs/{id}/run — trigger immediately (manual)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import CronJob
from app.scheduler import get_scheduler, schedule_job, unschedule_job

router = APIRouter()


class CronJobCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    cron_expr: str = Field(..., max_length=100, description="Standard 5-field cron expression")
    target_route: str = Field(..., max_length=500, description="Internal API route, e.g. /strategies/backtest")
    payload_json: dict | None = None
    enabled: bool = True


class CronJobUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cron_expr: str | None = None
    target_route: str | None = None
    payload_json: dict | None = None
    enabled: bool | None = None


class CronJobOut(BaseModel):
    id: int
    name: str
    description: str | None
    cron_expr: str
    target_route: str
    payload_json: dict | None
    enabled: bool
    last_run: datetime | None
    run_count: int
    created_at: datetime
    next_run: str | None = None

    class Config:
        from_attributes = True


def _next_run(job_id: int) -> str | None:
    scheduler = get_scheduler()
    j = scheduler.get_job(f"cron_{job_id}")
    if j and j.next_run_time:
        return j.next_run_time.isoformat()
    return None


@router.get("/jobs", response_model=list[CronJobOut])
async def list_jobs(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(CronJob).where(CronJob.user_id == user_id))).scalars().all()
    result = []
    for row in rows:
        out = CronJobOut.model_validate(row)
        out.next_run = _next_run(row.id)
        result.append(out)
    return result


@router.post("/jobs", response_model=CronJobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: CronJobCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = CronJob(
        user_id=user_id,
        name=body.name,
        description=body.description,
        cron_expr=body.cron_expr,
        target_route=body.target_route,
        payload_json=body.payload_json,
        enabled=body.enabled,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    if job.enabled:
        schedule_job(job)
    out = CronJobOut.model_validate(job)
    out.next_run = _next_run(job.id)
    return out


@router.patch("/jobs/{job_id}", response_model=CronJobOut)
async def update_job(
    job_id: int,
    body: CronJobUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(CronJob, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    await db.commit()
    await db.refresh(job)
    schedule_job(job)  # reschedule (or remove if disabled)
    out = CronJobOut.model_validate(job)
    out.next_run = _next_run(job.id)
    return out


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(CronJob, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job not found")
    unschedule_job(job_id)
    await db.delete(job)
    await db.commit()


@router.post("/jobs/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def manual_run(
    job_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the job immediately (one-off)."""
    job = await db.get(CronJob, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.scheduler import _run_job
    import asyncio
    asyncio.create_task(_run_job(job.id, job.target_route, job.payload_json))
    return {"status": "triggered", "job_id": job_id}
