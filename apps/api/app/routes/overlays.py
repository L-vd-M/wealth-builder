from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Overlay(BaseModel):
    symbol: str
    timeframe: str
    type: str
    params: dict


@router.post("/generate")
def generate_overlay(payload: Overlay) -> dict:
    fast = float(payload.params.get("fast", 20))
    slow = float(payload.params.get("slow", 50))
    points = []
    for idx in range(60):
        base = 100 + (idx * 0.35)
        points.append(
            {
                "x": idx,
                "fast": round(base + (fast * 0.08), 2),
                "slow": round(base + (slow * 0.04), 2)
            }
        )

    return {
        "symbol": payload.symbol,
        "timeframe": payload.timeframe,
        "type": payload.type,
        "params": payload.params,
        "points": points,
        "tv_overlay_schema": {
            "study": payload.type,
            "inputs": payload.params
        }
    }


@router.get("/catalog")
def overlay_catalog() -> dict:
    return {
        "overlays": [
            {"type": "ema_ribbon", "params": ["fast", "slow"]},
            {"type": "vwap_band", "params": ["stdev"]},
            {"type": "atr_channel", "params": ["length", "multiplier"]},
            {"type": "trendline", "params": ["x1", "y1", "x2", "y2"]}
        ]
    }
