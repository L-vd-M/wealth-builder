"""Agent registry API — browse system agents and manage custom agents.

Endpoints:
  GET  /registry           — list all agents (system + user's custom)
  GET  /registry/{slug}    — get one agent (including system_prompt)
  POST /registry           — create custom agent (auth required)
  PATCH /registry/{slug}   — update custom agent (owner only)
  DELETE /registry/{slug}  — delete custom agent (owner only)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.models import AgentDefinition

router = APIRouter()

_PLATFORMS = [
    "alpaca", "binance", "coinbase", "ibkr", "kraken", "luno", "oanda", "valr",
    "market-data", "general",
]
_ROLES = ["analysis", "chart", "decision", "execution", "data", "sentiment", "analyst", "orchestrator"]


class AgentOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None
    platform: str | None
    role: str | None
    tools_json: list | None
    is_system: bool
    user_id: str | None

    class Config:
        from_attributes = True


class AgentDetailOut(AgentOut):
    system_prompt: str | None


class AgentCreate(BaseModel):
    slug: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    description: str | None = None
    platform: str | None = None
    role: str | None = None
    system_prompt: str | None = None
    tools_json: list | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    platform: str | None = None
    role: str | None = None
    system_prompt: str | None = None
    tools_json: list | None = None


@router.get("", response_model=list[AgentOut])
async def list_agents(
    platform: str | None = None,
    role: str | None = None,
    user_id: str | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Return system agents (visible to all) plus the caller's custom agents."""
    conditions = [AgentDefinition.is_system == True]
    if user_id:
        conditions.append(AgentDefinition.user_id == user_id)
    query = select(AgentDefinition).where(or_(*conditions))
    if platform:
        query = query.where(AgentDefinition.platform == platform)
    if role:
        query = query.where(AgentDefinition.role == role)
    rows = (await db.execute(query.order_by(AgentDefinition.platform, AgentDefinition.role, AgentDefinition.name))).scalars().all()
    return rows


@router.get("/platforms", response_model=list[str])
async def list_platforms():
    return _PLATFORMS


@router.get("/roles", response_model=list[str])
async def list_roles():
    return _ROLES


@router.get("/{slug}", response_model=AgentDetailOut)
async def get_agent(
    slug: str,
    user_id: str | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(AgentDefinition).where(AgentDefinition.slug == slug))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    # System agents are public; custom agents only visible to owner
    if not row.is_system and row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return row


@router.post("", response_model=AgentDetailOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(AgentDefinition).where(AgentDefinition.slug == body.slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="An agent with this slug already exists")
    agent = AgentDefinition(
        slug=body.slug,
        name=body.name,
        description=body.description,
        platform=body.platform,
        role=body.role,
        system_prompt=body.system_prompt,
        tools_json=body.tools_json,
        is_system=False,
        user_id=user_id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.patch("/{slug}", response_model=AgentDetailOut)
async def update_agent(
    slug: str,
    body: AgentUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(AgentDefinition).where(AgentDefinition.slug == slug))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    if row.is_system:
        raise HTTPException(status_code=403, detail="System agents cannot be modified")
    if row.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your agent")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    slug: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(AgentDefinition).where(AgentDefinition.slug == slug))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    if row.is_system:
        raise HTTPException(status_code=403, detail="System agents cannot be deleted")
    if row.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your agent")
    await db.delete(row)
    await db.commit()
