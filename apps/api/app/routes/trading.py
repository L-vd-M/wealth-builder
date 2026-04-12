from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class OrderRequest(BaseModel):
    symbol: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)
    order_type: str = "market"


PAPER_POSITIONS = [
    {"symbol": "BTCUSD", "qty": 0.35, "entry": 64100, "mark": 65230},
    {"symbol": "NVDA", "qty": 20, "entry": 830, "mark": 846}
]


@router.get("/watchlist")
def watchlist() -> dict:
    return {
        "watchlist": [
            {"symbol": "BTCUSD", "price": 65230, "change": 1.9},
            {"symbol": "ETHUSD", "price": 3310, "change": -0.4},
            {"symbol": "EURUSD", "price": 1.0823, "change": 0.08},
            {"symbol": "SPY", "price": 529.2, "change": 0.44},
            {"symbol": "NVDA", "price": 846.0, "change": 1.1}
        ]
    }


@router.get("/positions")
def positions() -> dict:
    enriched = []
    for position in PAPER_POSITIONS:
        pnl = (position["mark"] - position["entry"]) * position["qty"]
        enriched.append({**position, "pnl": round(pnl, 2)})
    return {"positions": enriched}


@router.get("/risk")
def risk_summary() -> dict:
    gross_exposure = sum(abs(position["mark"] * position["qty"]) for position in PAPER_POSITIONS)
    return {
        "gross_exposure": round(gross_exposure, 2),
        "daily_var_95": round(gross_exposure * 0.023, 2),
        "max_drawdown_limit": 0.08,
        "portfolio_beta": 1.18
    }


@router.post("/order")
def paper_order(payload: OrderRequest) -> dict:
    notional = payload.quantity * 100
    return {
        "status": "accepted",
        "mode": "paper",
        "order": {
            "symbol": payload.symbol.upper(),
            "side": payload.side,
            "quantity": payload.quantity,
            "type": payload.order_type,
            "estimated_notional": round(notional, 2)
        }
    }


@router.get("/platforms")
def platforms() -> dict:
    return {
        "platforms": [
            {"name": "Binance", "category": "crypto", "fee_bps": 10, "api_score": 9, "regions": ["global"]},
            {"name": "Kraken", "category": "crypto", "fee_bps": 16, "api_score": 8, "regions": ["us", "eu"]},
            {"name": "Coinbase", "category": "crypto", "fee_bps": 40, "api_score": 8, "regions": ["us", "eu"]},
            {"name": "VALR", "category": "crypto", "fee_bps": 10, "api_score": 7, "regions": ["za"]},
            {"name": "OANDA", "category": "forex", "fee_bps": 12, "api_score": 8, "regions": ["global"]},
            {"name": "Interactive Brokers", "category": "forex", "fee_bps": 8, "api_score": 9, "regions": ["global"]},
            {"name": "Alpaca", "category": "stocks", "fee_bps": 0, "api_score": 8, "regions": ["us"]},
            {"name": "Interactive Brokers", "category": "stocks", "fee_bps": 7, "api_score": 9, "regions": ["global"]},
            {"name": "Trading212", "category": "stocks", "fee_bps": 5, "api_score": 6, "regions": ["eu", "uk"]}
        ]
    }
