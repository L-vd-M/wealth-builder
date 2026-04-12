import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import agents, market, news, overlays, strategies, trading


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="MarketCommand API", version="0.1.0", lifespan=lifespan)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(news.router, prefix="/news", tags=["news"])
app.include_router(trading.router, prefix="/trading", tags=["trading"])
app.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(overlays.router, prefix="/overlays", tags=["overlays"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
