"""Multi-agent trade deliberation API.

Pipeline per deliberation:
  1. Analysis agent  — technical analysis of the symbol
  2. Sentiment agent — social/on-chain sentiment context
  3. Decision agent  — BUY / SELL / HOLD verdict with confidence

Each agent response is persisted as a DeliberationMessage, allowing full
replay of the conversation at any time.

Endpoints:
  POST /deliberations/start          — kick off a new deliberation
  GET  /deliberations                — list user's deliberations
  GET  /deliberations/{id}           — full deliberation + messages
  DELETE /deliberations/{id}         — delete record
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.models import AgentDefinition, DeliberationMessage, TradeDeliberation

log = logging.getLogger(__name__)
router = APIRouter()

_OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class StartDeliberation(BaseModel):
    symbol: str = Field(..., max_length=50, description="e.g. BTC/USD, AAPL")
    platform: str = Field(..., max_length=100, description="e.g. alpaca, binance, valr")
    context: str | None = Field(None, description="Optional user-supplied context for agents")


class MessageOut(BaseModel):
    id: int
    agent_slug: str
    agent_name: str
    role: str
    content: str
    sequence: int
    created_at: datetime

    class Config:
        from_attributes = True


class DeliberationOut(BaseModel):
    id: int
    symbol: str
    platform: str
    status: str
    verdict: str | None
    confidence: int | None
    summary: str | None
    created_at: datetime
    completed_at: datetime | None
    messages: list[MessageOut] = []

    class Config:
        from_attributes = True


class DeliberationSummary(BaseModel):
    id: int
    symbol: str
    platform: str
    status: str
    verdict: str | None
    confidence: int | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# LLM helper — falls back to mock if OPENAI_API_KEY not set
# ---------------------------------------------------------------------------

async def _call_llm(system_prompt: str, user_message: str, agent_name: str) -> str:
    if not _OPENAI_KEY:
        return _mock_response(agent_name, user_message)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {_OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        log.warning("LLM call failed for %s: %s — using mock response", agent_name, exc)
        return _mock_response(agent_name, user_message)


def _mock_response(agent_name: str, user_message: str) -> str:
    """Generate a plausible-looking mock response when no LLM key is available."""
    if "analysis" in agent_name.lower():
        return (
            "## Technical Analysis Report\n\n"
            "**Trend**: Sideways / neutral — price consolidating near recent support.\n"
            "**RSI (14)**: 52 — neutral, no extreme readings.\n"
            "**MACD**: Histogram slightly positive; bullish cross forming on 4H.\n"
            "**Bollinger Bands**: Price near mid-band — no squeeze or breakout signal.\n"
            "**Volume**: Below 20-period average — low conviction.\n\n"
            "**Conclusion**: Mixed signals. Monitor for a decisive break above resistance "
            "or below support before committing.\n\n"
            "*Note: This is a mock response. Set OPENAI_API_KEY for live analysis.*"
        )
    if "sentiment" in agent_name.lower():
        return (
            "## Social Sentiment Report\n\n"
            "**LunarCrush Galaxy Score**: 58/100 — bullish sentiment bias.\n"
            "**Social Volume (24h)**: +12% vs 7-day avg.\n"
            "**AltRank**: Improving — top 30% of assets by social momentum.\n"
            "**Twitter/X**: Mixed mentions; retail excitement but no viral narrative.\n\n"
            "**Conclusion**: Slightly positive sentiment; not a strong contrarian signal.\n\n"
            "*Note: This is a mock response. Set OPENAI_API_KEY for live sentiment.*"
        )
    if "decision" in agent_name.lower():
        return (
            "## Trade Decision\n\n"
            "=== TRADE DECISION ===\n"
            "Symbol: see context\n"
            "Decision: HOLD\n"
            "Confidence: 4/10\n"
            "Rationale: Mixed technical signals + neutral sentiment. Risk:Reward does not "
            "meet minimum 2:1 threshold. Awaiting clearer directional conviction.\n"
            "Invalidation: Decisive break above resistance with volume would trigger re-evaluation.\n"
            "=====================\n\n"
            "*Note: This is a mock response. Set OPENAI_API_KEY for live decisions.*"
        )
    return f"[Mock response from {agent_name}]\n\n*Set OPENAI_API_KEY for real agent responses.*"


# ---------------------------------------------------------------------------
# Deliberation pipeline
# ---------------------------------------------------------------------------

async def _get_agent_prompt(platform: str, role: str, db: AsyncSession) -> tuple[str, str, str]:
    """Return (slug, name, system_prompt) for the given platform + role."""
    slug = f"{platform}-{role}"
    row = (await db.execute(select(AgentDefinition).where(AgentDefinition.slug == slug))).scalar_one_or_none()
    if row and row.system_prompt:
        return slug, row.name, row.system_prompt
    # Fallback: generic description
    fallback_prompt = (
        f"You are a financial trading agent specialising in {platform} markets. "
        f"Your role is {role}. Analyse the provided market context and respond professionally."
    )
    name = f"{platform.title()} {role.title()} Agent"
    return slug, name, fallback_prompt


def _extract_verdict(content: str) -> tuple[str | None, int | None]:
    """Parse BUY/SELL/HOLD and confidence from a decision agent's response."""
    decision_match = re.search(r"Decision:\s*(BUY|SELL|HOLD)", content, re.IGNORECASE)
    confidence_match = re.search(r"Confidence:\s*(\d+)", content)
    verdict = decision_match.group(1).upper() if decision_match else None
    confidence = int(confidence_match.group(1)) if confidence_match else None
    return verdict, confidence


async def _run_deliberation(deliberation_id: int, platform: str, symbol: str, user_context: str | None) -> None:
    """Background task: run the agent pipeline and persist all messages."""
    async with AsyncSessionLocal() as db:
        delib = await db.get(TradeDeliberation, deliberation_id)
        if not delib:
            return
        delib.status = "running"
        await db.commit()

        sequence = 0
        prior_messages: list[str] = []

        async def run_agent(role: str) -> str:
            nonlocal sequence
            slug, name, prompt = await _get_agent_prompt(platform, role, db)

            user_msg_parts = [f"Symbol: {symbol}", f"Platform: {platform}"]
            if user_context:
                user_msg_parts.append(f"Additional context: {user_context}")
            if prior_messages:
                user_msg_parts.append("\n=== Prior Agent Reports ===\n" + "\n\n---\n\n".join(prior_messages))

            user_msg = "\n".join(user_msg_parts)
            content = await _call_llm(prompt, user_msg, name)
            prior_messages.append(f"**{name}:**\n{content}")

            sequence += 1
            msg = DeliberationMessage(
                deliberation_id=deliberation_id,
                agent_slug=slug,
                agent_name=name,
                role=role,
                content=content,
                sequence=sequence,
            )
            db.add(msg)
            await db.commit()
            log.info("Deliberation %d: %s (%s) completed", deliberation_id, name, role)
            return content

        try:
            await run_agent("analysis")
            await run_agent("sentiment")
            decision_content = await run_agent("decision")

            verdict, confidence = _extract_verdict(decision_content)

            # Build summary from decision block
            summary_match = re.search(r"Rationale:(.+?)(?:Invalidation:|$)", decision_content, re.DOTALL)
            summary = summary_match.group(1).strip()[:500] if summary_match else None

            delib = await db.get(TradeDeliberation, deliberation_id)
            if delib:
                delib.status = "completed"
                delib.verdict = verdict
                delib.confidence = confidence
                delib.summary = summary
                delib.completed_at = datetime.now(timezone.utc)
                await db.commit()

        except Exception as exc:
            log.exception("Deliberation %d failed: %s", deliberation_id, exc)
            delib = await db.get(TradeDeliberation, deliberation_id)
            if delib:
                delib.status = "failed"
                await db.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/start", response_model=DeliberationSummary, status_code=status.HTTP_202_ACCEPTED)
async def start_deliberation(
    body: StartDeliberation,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delib = TradeDeliberation(
        user_id=user_id,
        symbol=body.symbol.upper(),
        platform=body.platform.lower(),
        status="pending",
    )
    db.add(delib)
    await db.commit()
    await db.refresh(delib)
    background_tasks.add_task(
        _run_deliberation,
        delib.id,
        delib.platform,
        delib.symbol,
        body.context,
    )
    return delib


@router.get("", response_model=list[DeliberationSummary])
async def list_deliberations(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(TradeDeliberation)
            .where(TradeDeliberation.user_id == user_id)
            .order_by(TradeDeliberation.created_at.desc())
        )
    ).scalars().all()
    return rows


@router.get("/{deliberation_id}", response_model=DeliberationOut)
async def get_deliberation(
    deliberation_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(TradeDeliberation, deliberation_id)
    if not row or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Deliberation not found")
    # Eagerly load messages
    msgs = (
        await db.execute(
            select(DeliberationMessage)
            .where(DeliberationMessage.deliberation_id == deliberation_id)
            .order_by(DeliberationMessage.sequence)
        )
    ).scalars().all()
    out = DeliberationOut.model_validate(row)
    out.messages = [MessageOut.model_validate(m) for m in msgs]
    return out


@router.delete("/{deliberation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deliberation(
    deliberation_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(TradeDeliberation, deliberation_id)
    if not row or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Deliberation not found")
    await db.delete(row)
    await db.commit()
