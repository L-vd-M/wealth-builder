import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.database import AsyncSessionLocal
from app.routes import agents, market, news, overlays, strategies, trading
from app.routes import cron, registry, deliberations, wallets
from app.scheduler import get_scheduler, load_all_jobs
from app.seed import seed_system_agents

log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_system_agents(session)
    await load_all_jobs()
    scheduler = get_scheduler()
    scheduler.start()
    log.info("APScheduler started")
    yield
    scheduler.shutdown(wait=False)
    log.info("APScheduler stopped")


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
app.include_router(cron.router, prefix="/cron", tags=["cron"])
app.include_router(registry.router, prefix="/registry", tags=["registry"])
app.include_router(deliberations.router, prefix="/deliberations", tags=["deliberations"])
app.include_router(wallets.router, prefix="/wallets", tags=["wallets"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
