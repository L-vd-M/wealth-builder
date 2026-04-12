import json
import os
from urllib import error, request

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AgentPrompt(BaseModel):
    agent: str
    prompt: str


def provider_response(prompt: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    body = {
        "model": "gpt-4.1-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are a concise quant strategy assistant. Return plain text only."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with request.urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"].strip()
    except (error.URLError, error.HTTPError, KeyError, IndexError, json.JSONDecodeError, TimeoutError):
        return None


@router.post("/chat")
def chat(payload: AgentPrompt) -> dict:
    prompt_lower = payload.prompt.lower()
    suggested_strategy = {
        "name": "Adaptive Momentum",
        "thesis": "Trade with trend strength while volatility is below threshold.",
        "signals": ["ema_20 > ema_50", "rsi_14 > 45"],
        "risk_rules": ["risk_per_trade=1%", "stop_loss=1.5*ATR", "max_open_positions=4"]
    }

    if "mean reversion" in prompt_lower:
        suggested_strategy = {
            "name": "Mean Reversion RSI",
            "thesis": "Fade short-term extremes back to moving average.",
            "signals": ["rsi_14 < 30 => long", "rsi_14 > 70 => short"],
            "risk_rules": ["risk_per_trade=0.75%", "time_stop=3 bars"]
        }

    provider_text = provider_response(payload.prompt)

    return {
        "agent": payload.agent,
        "response": provider_text
        or "I generated a first strategy draft and two immediate chart overlays to validate the hypothesis.",
        "provider": "openai" if provider_text else "mock",
        "strategy": suggested_strategy,
        "actions": [
            {"type": "draft_strategy", "endpoint": "/strategies/draft"},
            {"type": "run_backtest", "endpoint": "/strategies/backtest"},
            {
                "type": "generate_overlay",
                "endpoint": "/overlays/generate",
                "payload": {"symbol": "BTCUSD", "timeframe": "1h", "type": "ema_ribbon", "params": {"fast": 20, "slow": 50}}
            }
        ]
    }
