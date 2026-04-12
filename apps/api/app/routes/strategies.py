from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.models import Strategy, StrategyVersion, UserBot

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class StrategyRequest(BaseModel):
    name: str
    thesis: str


class BacktestRequest(BaseModel):
    name: str
    symbol: str
    timeframe: str
    lookback_days: int


class StrategySaveRequest(BaseModel):
    name: str
    thesis: str
    signals: list[str]
    risk_rules: list[str]
    user_email: str | None = None  # forwarded from frontend for Resend notification


class BotCreateRequest(BaseModel):
    strategy_name: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_strategy_notification(user_email: str, strategy_name: str, version: int) -> None:
    """Fire-and-forget Resend email notification (no-op if RESEND_API_KEY not set)."""
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL", "notifications@marketcommand.app")
    if not api_key:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_email,
                    "to": [user_email],
                    "subject": f"Strategy saved: {strategy_name} v{version}",
                    "html": (
                        f"<p>Your strategy <strong>{strategy_name}</strong> "
                        f"has been saved as version <strong>{version}</strong>.</p>"
                    ),
                },
                timeout=8.0,
            )
    except Exception:  # noqa: BLE001 – best-effort only
        pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/draft")
def draft_strategy(payload: StrategyRequest) -> dict:
    return {
        "strategy": {
            "name": payload.name,
            "thesis": payload.thesis,
            "signals": [
                "trend_filter: close > ema(50)",
                "entry: rsi(14) crosses above 40",
                "exit: close < ema(20)",
            ],
            "risk_rules": [
                "max_risk_per_trade: 1%",
                "stop_loss_atr_multiple: 1.5",
                "take_profit_rr: 2.0",
            ],
        }
    }


@router.get("/templates")
def templates() -> dict:
    return {
        "templates": [
            {"id": "momentum-breakout", "name": "Momentum Breakout", "asset_class": "stocks"},
            {"id": "mean-reversion-rsi", "name": "Mean Reversion RSI", "asset_class": "crypto"},
            {"id": "fx-carry-trend", "name": "FX Carry Trend", "asset_class": "forex"},
        ]
    }


@router.post("/backtest")
def backtest(payload: BacktestRequest) -> dict:
    return {
        "request": payload.model_dump(),
        "result": {
            "cagr": 0.173,
            "sharpe": 1.42,
            "max_drawdown": 0.091,
            "win_rate": 0.56,
            "trades": 214,
        },
    }


@router.post("/save")
async def save_strategy(
    payload: StrategySaveRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Strategy).where(Strategy.name == payload.name, Strategy.user_id == user_id)
    )
    strategy = result.scalar_one_or_none()

    if strategy is None:
        strategy = Strategy(name=payload.name, user_id=user_id)
        db.add(strategy)
        await db.flush()

    count_result = await db.execute(
        select(func.count()).where(StrategyVersion.strategy_id == strategy.id)
    )
    next_version = (count_result.scalar() or 0) + 1

    sv = StrategyVersion(
        strategy_id=strategy.id,
        version=next_version,
        thesis=payload.thesis,
        signals=payload.signals,
        risk_rules=payload.risk_rules,
    )
    db.add(sv)
    await db.commit()

    if payload.user_email:
        await _send_strategy_notification(payload.user_email, payload.name, next_version)

    return {"status": "saved", "strategy": {"name": payload.name, "version": next_version}}


@router.get("/history")
async def strategy_history(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Strategy)
        .where(Strategy.user_id == user_id)
        .options(selectinload(Strategy.versions))
    )
    strategies = result.scalars().all()
    return {
        "strategies": [
            {
                "name": s.name,
                "latest_version": s.versions[-1].version if s.versions else 0,
                "versions": len(s.versions),
            }
            for s in strategies
        ]
    }


@router.get("/history/{name}")
async def strategy_versions(
    name: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Strategy)
        .where(Strategy.name == name, Strategy.user_id == user_id)
        .options(selectinload(Strategy.versions))
    )
    strategy = result.scalar_one_or_none()
    if strategy is None:
        return {"name": name, "versions": []}
    return {
        "name": name,
        "versions": [
            {
                "version": v.version,
                "thesis": v.thesis,
                "signals": v.signals,
                "risk_rules": v.risk_rules,
                "saved_at": v.saved_at.isoformat(),
            }
            for v in strategy.versions
        ],
    }


@router.get("/bots")
async def bots(
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_optional_user),
) -> dict:
    if user_id:
        result = await db.execute(select(UserBot).where(UserBot.user_id == user_id))
        user_bots = result.scalars().all()
        if user_bots:
            return {
                "bots": [
                    {"name": b.strategy_name, "status": b.status, "strategy": b.strategy_name}
                    for b in user_bots
                ]
            }
    return {
        "bots": [
            {"name": "alpha-runner-01", "status": "running", "strategy": "momentum-breakout"},
            {"name": "fx-scout-02", "status": "idle", "strategy": "fx-carry-trend"},
        ]
    }


@router.post("/bots")
async def create_bot(
    payload: BotCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Strategy).where(
            Strategy.name == payload.strategy_name, Strategy.user_id == user_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Strategy not found for this user")

    bot = UserBot(user_id=user_id, strategy_name=payload.strategy_name, status="idle")
    db.add(bot)
    await db.commit()
    return {"status": "created", "bot": {"name": payload.strategy_name, "status": "idle"}}
