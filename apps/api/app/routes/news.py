from fastapi import APIRouter

router = APIRouter()


@router.get("/categories")
def news_categories() -> dict:
    return {
        "categories": ["financial", "crypto", "world"],
        "top_headlines": []
    }


@router.get("/headlines")
def headlines() -> dict:
    return {
        "financial": [
            {"title": "US Banks Rally Ahead of Earnings", "source": "MarketWire", "sentiment": "positive"},
            {"title": "Bond Yields Hold Near Weekly High", "source": "MacroDesk", "sentiment": "neutral"}
        ],
        "crypto": [
            {"title": "BTC Options Open Interest Climbs", "source": "ChainPulse", "sentiment": "positive"},
            {"title": "Regulators Review Stablecoin Framework", "source": "CryptoPolicy", "sentiment": "neutral"}
        ],
        "world": [
            {"title": "Trade Talks Resume Across G20 Bloc", "source": "WorldReport", "sentiment": "neutral"},
            {"title": "Energy Supply Routes Stabilize", "source": "GlobalEnergy", "sentiment": "positive"}
        ]
    }
