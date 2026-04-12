import os
from math import sin, sqrt

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.models import BacktestRun, HistoricalPrice, Strategy, StrategyVersion, UserBot
from app.routes.agents import provider_response

router = APIRouter()

_PREDEFINED_STRATEGIES = [
    {
        "id": "momentum-breakout",
        "name": "Momentum Breakout",
        "asset_class": "multi",
        "thesis": "Trade with directional strength when price closes above trend filters.",
        "signals": ["close > sma20", "volume > 20-bar avg"],
        "risk_rules": ["risk_per_trade: 1%", "stop: 1.5*ATR"],
    },
    {
        "id": "mean-reversion-rsi",
        "name": "Mean Reversion RSI",
        "asset_class": "multi",
        "thesis": "Fade short-term extremes and exit on reversion to the mean.",
        "signals": ["RSI14 < 30 long setup", "RSI14 > 70 short setup"],
        "risk_rules": ["risk_per_trade: 0.75%", "time-stop: 3 bars"],
    },
    {
        "id": "whale-copy-verified",
        "name": "Whale Copy (Research Verified)",
        "asset_class": "crypto",
        "thesis": "Track whale flow and copy only after a research agent verifies market conditions.",
        "signals": ["whale flow detected", "research verification score >= 65"],
        "risk_rules": ["max copy size: 2% NAV", "abort if volatility spike > 2x baseline"],
    },
    {
        "id": "trailing-stop-5-dollar",
        "name": "Fixed $5 Trailing Stop",
        "asset_class": "multi",
        "thesis": "Use a fixed dollar trailing stop that ratchets upward in $5 increments.",
        "signals": ["entry trigger from primary strategy", "trail by $5 from high-water mark"],
        "risk_rules": ["example: entry $50 -> stop $45", "at $55 move stop to $50"],
    },
]


class StrategyRequest(BaseModel):
    name: str
    thesis: str


class BacktestRequest(BaseModel):
    name: str
    symbol: str
    timeframe: str
    lookback_days: int = Field(ge=5, le=3650)


class StrategySaveRequest(BaseModel):
    name: str
    thesis: str
    signals: list[str]
    risk_rules: list[str]
    user_email: str | None = None


class BotCreateRequest(BaseModel):
    strategy_name: str


class WhaleCopyRequest(BaseModel):
    symbol: str
    side: str = Field(pattern="^(buy|sell)$")
    observed_price: float = Field(gt=0)
    whale_wallet: str
    whale_confidence: int = Field(default=70, ge=0, le=100)
    research_context: str | None = None


class TradeResearchRequest(BaseModel):
    symbol: str
    side: str = Field(pattern="^(buy|sell)$")
    entry_price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    context: str | None = None


class TrailingStopRequest(BaseModel):
    entry_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    highest_price: float = Field(gt=0)
    step: float = Field(default=5.0, gt=0)


async def _send_strategy_notification(user_email: str, strategy_name: str, version: int) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL", "notifications@yourdomain.com")
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
    except Exception:
        pass


def _sma(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    rolling = 0.0
    for i, v in enumerate(values):
        rolling += v
        if i >= window:
            rolling -= values[i - window]
        if i + 1 >= window:
            out.append(rolling / window)
        else:
            out.append(None)
    return out


def _rsi(values: list[float], period: int = 14) -> list[float | None]:
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gains = _sma(gains, period)
    avg_losses = _sma(losses, period)

    out: list[float | None] = []
    for g, l in zip(avg_gains, avg_losses):
        if g is None or l is None:
            out.append(None)
            continue
        if l == 0:
            out.append(100.0)
            continue
        rs = g / l
        out.append(100 - (100 / (1 + rs)))
    return out


async def _ensure_historical_data(
    db: AsyncSession,
    symbol: str,
    timeframe: str,
    lookback_days: int,
) -> list[HistoricalPrice]:
    bars_needed = lookback_days * (24 if timeframe == "1h" else 1)

    result = await db.execute(
        select(HistoricalPrice)
        .where(HistoricalPrice.symbol == symbol.upper(), HistoricalPrice.timeframe == timeframe)
        .order_by(HistoricalPrice.t.asc())
    )
    existing = result.scalars().all()

    if len(existing) >= bars_needed:
        return existing[-bars_needed:]

    # Seed deterministic pseudo-historical bars so backtesting has persisted data.
    base = 64000.0 if symbol.upper().startswith("BTC") else 100.0
    seeded: list[HistoricalPrice] = []
    for idx in range(bars_needed):
        wave = sin(idx / 8) * (base * 0.005)
        trend = idx * (base * 0.00035)
        close = base + trend + wave
        open_price = close - (base * 0.0006)
        high = close + (base * 0.0011)
        low = close - (base * 0.0010)
        volume = 150 + (idx % 19) * 6.0
        seeded.append(
            HistoricalPrice(
                symbol=symbol.upper(),
                timeframe=timeframe,
                t=idx,
                o=round(open_price, 4),
                h=round(high, 4),
                l=round(low, 4),
                c=round(close, 4),
                v=round(volume, 4),
                source="synthetic",
            )
        )

    # Replace synthetic dataset for same symbol/timeframe to keep timeline clean.
    await db.execute(
        HistoricalPrice.__table__.delete().where(
            HistoricalPrice.symbol == symbol.upper(),
            HistoricalPrice.timeframe == timeframe,
            HistoricalPrice.source == "synthetic",
        )
    )
    db.add_all(seeded)
    await db.commit()

    return seeded


def _backtest_engine(strategy_name: str, prices: list[HistoricalPrice]) -> dict:
    closes = [p.c for p in prices]
    highs = [p.h for p in prices]
    vols = [p.v for p in prices]
    sma20 = _sma(closes, 20)
    rsi14 = _rsi(closes, 14)

    equity = 10000.0
    peak = equity
    max_dd = 0.0
    in_position = False
    entry = 0.0
    stop = 0.0
    high_water = 0.0
    trades = 0
    wins = 0
    returns: list[float] = []

    for i in range(20, len(closes)):
        price = closes[i]
        avg = sma20[i]
        if avg is None:
            continue

        if strategy_name == "mean-reversion-rsi":
            signal = rsi14[i] is not None and rsi14[i] < 30 and not in_position
            exit_signal = in_position and rsi14[i] is not None and rsi14[i] > 55
        elif strategy_name == "whale-copy-verified":
            # Proxy whale signal: volume spike and trend alignment.
            vol_ref = sum(vols[max(0, i - 20):i]) / max(1, len(vols[max(0, i - 20):i]))
            signal = (not in_position) and vols[i] > (vol_ref * 1.4) and price > avg
            exit_signal = in_position and price < avg
        elif strategy_name == "trailing-stop-5-dollar":
            signal = (not in_position) and price > avg
            exit_signal = False  # trailing stop controls exits
        else:  # momentum-breakout and default
            signal = (not in_position) and price > avg
            exit_signal = in_position and price < avg

        if signal:
            in_position = True
            entry = price
            high_water = highs[i]
            if strategy_name == "trailing-stop-5-dollar":
                stop = entry - 5.0
            else:
                stop = entry * 0.985
            continue

        if in_position:
            high_water = max(high_water, highs[i])

            if strategy_name == "trailing-stop-5-dollar":
                stepped = max(0, int((high_water - entry) // 5))
                stop = (entry - 5.0) + (stepped * 5.0)

            if closes[i] <= stop or exit_signal:
                ret = (closes[i] - entry) / entry
                pnl = equity * ret * 0.1  # fixed 10% capital allocation per trade
                equity += pnl
                returns.append(ret)
                trades += 1
                if ret > 0:
                    wins += 1
                in_position = False

        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    if in_position:
        ret = (closes[-1] - entry) / entry
        pnl = equity * ret * 0.1
        equity += pnl
        returns.append(ret)
        trades += 1
        if ret > 0:
            wins += 1

    total_return = (equity / 10000.0) - 1
    years = max(len(closes) / (24 * 365), 0.1)
    cagr = ((equity / 10000.0) ** (1 / years)) - 1

    if returns:
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std = sqrt(variance)
        sharpe = (mean_ret / std) * sqrt(252) if std > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "cagr": round(cagr, 4),
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "win_rate": round((wins / trades), 4) if trades else 0.0,
        "trades": trades,
        "ending_equity": round(equity, 2),
        "total_return": round(total_return, 4),
    }


def _research_verify_trade(symbol: str, side: str, entry_price: float, quantity: float, context: str | None) -> dict:
    prompt = (
        "You are a strict quant risk research agent. "
        "Given the trade proposal, return: verdict (approve/reject), confidence (0-100), and short rationale.\n"
        f"symbol={symbol}\nside={side}\nentry_price={entry_price}\nquantity={quantity}\ncontext={context or 'none'}"
    )
    provider_text = provider_response(prompt)

    # Deterministic fallback heuristic if no LLM key.
    notional = entry_price * quantity
    risk_ok = notional <= 10000
    confidence = 72 if risk_ok else 41
    verdict = "approve" if risk_ok else "reject"
    rationale = "Position sizing within risk budget" if risk_ok else "Position size exceeds risk budget"

    if provider_text:
        text = provider_text.lower()
        if "reject" in text or "avoid" in text:
            verdict = "reject"
            confidence = 35
        elif "approve" in text or "valid" in text:
            verdict = "approve"
            confidence = 75
        rationale = provider_text[:300]

    return {
        "verdict": verdict,
        "confidence": confidence,
        "rationale": rationale,
        "provider": "openai" if provider_text else "heuristic",
    }


def _trailing_stop(step: float, entry_price: float, highest_price: float) -> float:
    base_stop = entry_price - step
    stepped = max(0, int((highest_price - entry_price) // step))
    return base_stop + (stepped * step)


@router.post("/draft")
def draft_strategy(payload: StrategyRequest) -> dict:
    return {
        "strategy": {
            "name": payload.name,
            "thesis": payload.thesis,
            "signals": [
                "trend_filter: close > sma(20)",
                "entry: momentum and volume confirmation",
                "exit: close < sma(20) or stop triggered",
            ],
            "risk_rules": [
                "max_risk_per_trade: 1%",
                "position_size: 10% equity",
                "use trailing stop when applicable",
            ],
        }
    }


@router.get("/templates")
def templates() -> dict:
    return {"templates": [{"id": s["id"], "name": s["name"], "asset_class": s["asset_class"]} for s in _PREDEFINED_STRATEGIES]}


@router.get("/predefined")
def predefined() -> dict:
    return {"strategies": _PREDEFINED_STRATEGIES}


@router.post("/verify-trade")
def verify_trade(payload: TradeResearchRequest) -> dict:
    research = _research_verify_trade(
        symbol=payload.symbol,
        side=payload.side,
        entry_price=payload.entry_price,
        quantity=payload.quantity,
        context=payload.context,
    )
    return {
        "trade": payload.model_dump(),
        "research": research,
        "approved": research["verdict"] == "approve",
    }


@router.post("/whale-copy/plan")
def whale_copy_plan(payload: WhaleCopyRequest) -> dict:
    research = _research_verify_trade(
        symbol=payload.symbol,
        side=payload.side,
        entry_price=payload.observed_price,
        quantity=max(1.0, payload.observed_price / 1000),
        context=(payload.research_context or "") + f" | whale_wallet={payload.whale_wallet}",
    )

    should_copy = research["verdict"] == "approve" and payload.whale_confidence >= 60
    copied_notional = round(min(2500.0, payload.observed_price * 0.04), 2)

    return {
        "whale_signal": payload.model_dump(),
        "research": research,
        "should_copy": should_copy,
        "copy_order": {
            "symbol": payload.symbol.upper(),
            "side": payload.side,
            "notional": copied_notional,
            "entry_price": payload.observed_price,
            "status": "ready" if should_copy else "blocked",
        },
    }


@router.post("/trailing-stop")
def trailing_stop(payload: TrailingStopRequest) -> dict:
    highest = max(payload.highest_price, payload.current_price)
    stop = _trailing_stop(payload.step, payload.entry_price, highest)
    return {
        "entry_price": payload.entry_price,
        "current_price": payload.current_price,
        "highest_price": highest,
        "step": payload.step,
        "stop_loss": round(stop, 4),
        "example": "If entry is 50, stop starts at 45 and moves to 50 when price reaches 55.",
    }


@router.post("/backtest")
async def backtest(
    payload: BacktestRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_optional_user),
) -> dict:
    prices = await _ensure_historical_data(
        db=db,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        lookback_days=payload.lookback_days,
    )

    strategy_id = payload.name.lower().strip()
    result = _backtest_engine(strategy_id, prices)

    run = BacktestRun(
        user_id=user_id,
        strategy_name=payload.name,
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        lookback_days=payload.lookback_days,
        cagr=result["cagr"],
        sharpe=result["sharpe"],
        max_drawdown=result["max_drawdown"],
        win_rate=result["win_rate"],
        trades=result["trades"],
        metadata_json={
            "ending_equity": result["ending_equity"],
            "total_return": result["total_return"],
            "data_source": "historical_prices",
        },
    )
    db.add(run)
    await db.commit()

    return {
        "request": payload.model_dump(),
        "result": {
            "cagr": result["cagr"],
            "sharpe": result["sharpe"],
            "max_drawdown": result["max_drawdown"],
            "win_rate": result["win_rate"],
            "trades": result["trades"],
        },
        "dataset": {
            "source": "historical_prices",
            "points": len(prices),
            "symbol": payload.symbol.upper(),
            "timeframe": payload.timeframe,
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
            {"name": "whale-watch-verified", "status": "idle", "strategy": "whale-copy-verified"},
            {"name": "trail-guard-5d", "status": "idle", "strategy": "trailing-stop-5-dollar"},
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
        predefined_ids = {s["id"] for s in _PREDEFINED_STRATEGIES}
        if payload.strategy_name not in predefined_ids:
            raise HTTPException(status_code=404, detail="Strategy not found for this user")

    bot = UserBot(user_id=user_id, strategy_name=payload.strategy_name, status="idle")
    db.add(bot)
    await db.commit()
    return {"status": "created", "bot": {"name": payload.strategy_name, "status": "idle"}}
