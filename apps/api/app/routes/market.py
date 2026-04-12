from math import sin

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/snapshot")
def market_snapshot() -> dict:
    return {
        "indices": [{"symbol": "SPX", "change": 0.41}, {"symbol": "NQ", "change": 0.62}],
        "crypto": [{"symbol": "BTCUSD", "change": -1.25}],
        "fx": [{"symbol": "EURUSD", "change": 0.08}]
    }


@router.get("/regions")
def region_heat_map() -> dict:
    return {
        "regions": [
            {"name": "North America", "change": 0.74, "sentiment": "risk-on"},
            {"name": "Europe", "change": 0.31, "sentiment": "neutral"},
            {"name": "Middle East", "change": -0.19, "sentiment": "mixed"},
            {"name": "Africa", "change": 0.16, "sentiment": "neutral"},
            {"name": "Asia Pacific", "change": -0.42, "sentiment": "risk-off"},
            {"name": "South America", "change": 0.58, "sentiment": "risk-on"}
        ],
        "macro_events": [
            {"time": "08:30 UTC", "event": "US CPI Release", "impact": "high"},
            {"time": "10:00 UTC", "event": "ECB Policy Statement", "impact": "high"},
            {"time": "13:00 UTC", "event": "OPEC Supply Update", "impact": "medium"}
        ]
    }


@router.get("/quant")
def quant_factors() -> dict:
    return {
        "factors": [
            {"name": "Momentum", "value": 0.67, "signal": "bullish"},
            {"name": "Value", "value": 0.28, "signal": "neutral"},
            {"name": "Quality", "value": 0.59, "signal": "bullish"},
            {"name": "Volatility", "value": -0.44, "signal": "cautious"}
        ],
        "leaders": [
            {"symbol": "NVDA", "score": 91},
            {"symbol": "MSFT", "score": 88},
            {"symbol": "BTCUSD", "score": 85},
            {"symbol": "EURUSD", "score": 73}
        ]
    }


@router.get("/financial")
def financial_kpis() -> dict:
    return {
        "valuation": {"forward_pe": 19.7, "ev_ebitda": 13.2, "fcf_yield": 3.9},
        "balance_sheet": {"cash_ratio": 1.34, "debt_to_equity": 0.58, "interest_coverage": 8.1},
        "events": [
            {"date": "2026-04-15", "name": "Earnings: JPM, C", "type": "earnings"},
            {"date": "2026-04-16", "name": "Retail Sales (US)", "type": "macro"},
            {"date": "2026-04-18", "name": "FOMC Minutes", "type": "macro"}
        ]
    }


@router.get("/candles")
def candles(symbol: str = Query(default="BTCUSD"), points: int = Query(default=60, ge=20, le=400)) -> dict:
    base = 64000.0 if symbol.upper().startswith("BTC") else 100.0
    rows = []
    for idx in range(points):
        wave = sin(idx / 5) * (base * 0.004)
        trend = idx * (base * 0.0005)
        close = base + trend + wave
        open_price = close - (base * 0.0007)
        high = close + (base * 0.0012)
        low = close - (base * 0.0011)
        rows.append(
            {
                "t": idx,
                "o": round(open_price, 2),
                "h": round(high, 2),
                "l": round(low, 2),
                "c": round(close, 2),
                "v": round(120 + (idx % 17) * 5.5, 2)
            }
        )
    return {"symbol": symbol.upper(), "points": rows}
