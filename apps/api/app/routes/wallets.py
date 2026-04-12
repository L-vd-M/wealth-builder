"""Linked trading account management + wallet balance fetching.

API keys are stored encrypted in the database using Fernet symmetric encryption.
The ENCRYPTION_KEY environment variable must be set (see apps/api/app/crypto.py).

Supported platforms: alpaca, binance, coinbase, kraken, oanda, luno, valr, ibkr

Endpoints:
    POST /wallets/validate               — validate platform credentials without saving
  GET  /wallets/accounts               — list linked accounts
  POST /wallets/accounts               — link a new account
  DELETE /wallets/accounts/{id}        — unlink an account
  GET  /wallets/accounts/{id}/balance  — fetch live balance for one account
  GET  /wallets/balances               — fetch balances across all linked accounts
"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crypto import decrypt, encrypt
from app.database import get_db
from app.models import LinkedAccount

log = logging.getLogger(__name__)
router = APIRouter()

_SUPPORTED_PLATFORMS = ["alpaca", "binance", "coinbase", "kraken", "oanda", "luno", "valr", "ibkr"]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AccountCreate(BaseModel):
    platform: str = Field(..., description="Platform slug, e.g. alpaca")
    nickname: str = Field(..., max_length=255)
    api_key: str = Field(..., description="API key — stored encrypted")
    api_secret: str | None = Field(None, description="API secret — stored encrypted")
    extra: dict | None = Field(
        None,
        description=(
            "Extra fields. Coinbase: {passphrase}. "
            "IBKR: {base_url, token, account_id}."
        ),
    )


class AccountOut(BaseModel):
    id: int
    platform: str
    nickname: str
    created_at: datetime
    last_synced: datetime | None

    class Config:
        from_attributes = True


class BalanceEntry(BaseModel):
    asset: str
    available: float
    total: float
    usd_value: float | None = None


class AccountBalance(BaseModel):
    account_id: int
    platform: str
    nickname: str
    balances: list[BalanceEntry]
    error: str | None = None
    fetched_at: str


class AccountValidate(BaseModel):
    platform: str = Field(..., description="Platform slug, e.g. alpaca")
    api_key: str = Field(..., description="API key or token")
    api_secret: str | None = Field(None, description="API secret when required")
    extra: dict | None = Field(
        None,
        description=(
            "Extra fields. Coinbase: {passphrase}. "
            "IBKR: {base_url, token, account_id}."
        ),
    )


class AccountValidationResult(BaseModel):
    platform: str
    valid: bool
    message: str
    balance_count: int = 0
    sample_assets: list[str] = []
    checked_at: str


# ---------------------------------------------------------------------------
# Balance fetchers per platform
# ---------------------------------------------------------------------------

async def _fetch_alpaca(api_key: str, api_secret: str, extra: dict | None = None) -> list[BalanceEntry]:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://api.alpaca.markets/v2/account",
            headers={"APCA-API-KEY-ID": api_key, "APCA-API-SECRET-KEY": api_secret},
        )
        r.raise_for_status()
        data = r.json()
        equity = float(data.get("equity", 0))
        cash = float(data.get("cash", 0))
        return [
            BalanceEntry(asset="USD", available=cash, total=equity, usd_value=equity)
        ]


async def _fetch_binance(api_key: str, api_secret: str, extra: dict | None = None) -> list[BalanceEntry]:
    timestamp = int(time.time() * 1000)
    params = f"timestamp={timestamp}"
    sig = hmac.new(api_secret.encode(), params.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com/api/v3/account?{params}&signature={sig}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers={"X-MBX-APIKEY": api_key})
        r.raise_for_status()
        data = r.json()
        entries = []
        for b in data.get("balances", []):
            free = float(b["free"])
            locked = float(b["locked"])
            total = free + locked
            if total > 0:
                entries.append(BalanceEntry(asset=b["asset"], available=free, total=total))
        return entries


async def _fetch_kraken(api_key: str, api_secret: str, extra: dict | None = None) -> list[BalanceEntry]:
    import base64
    import hashlib
    nonce = str(int(time.time() * 1000))
    data = f"nonce={nonce}".encode()
    sha256_hash = hashlib.sha256((nonce + data.decode()).encode()).digest()
    secret_decoded = base64.b64decode(api_secret)
    path = "/0/private/Balance"
    sig = hmac.new(secret_decoded, path.encode() + sha256_hash, hashlib.sha512)
    b64sig = base64.b64encode(sig.digest()).decode()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"https://api.kraken.com{path}",
            data={"nonce": nonce},
            headers={"API-Key": api_key, "API-Sign": b64sig},
        )
        r.raise_for_status()
        result = r.json().get("result", {})
        return [
            BalanceEntry(asset=k, available=float(v), total=float(v))
            for k, v in result.items()
            if float(v) > 0
        ]


async def _fetch_luno(api_key: str, api_secret: str, extra: dict | None = None) -> list[BalanceEntry]:
    async with httpx.AsyncClient(timeout=15, auth=(api_key, api_secret)) as client:
        r = await client.get("https://api.luno.com/api/1/balance")
        r.raise_for_status()
        balances = r.json().get("balance", [])
        return [
            BalanceEntry(
                asset=b["asset"],
                available=float(b["balance"]) - float(b["reserved"]),
                total=float(b["balance"]),
            )
            for b in balances
            if float(b["balance"]) > 0
        ]


async def _fetch_valr(api_key: str, api_secret: str, extra: dict | None = None) -> list[BalanceEntry]:
    timestamp = str(int(time.time() * 1000))
    path = "/v1/account/balances"
    verb = "GET"
    payload = ""
    sig_data = f"{timestamp}{verb}{path}{payload}"
    sig = hmac.new(api_secret.encode(), sig_data.encode(), hashlib.sha512).hexdigest()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"https://api.valr.com{path}",
            headers={
                "X-VALR-API-KEY": api_key,
                "X-VALR-SIGNATURE": sig,
                "X-VALR-TIMESTAMP": timestamp,
            },
        )
        r.raise_for_status()
        data = r.json()
        return [
            BalanceEntry(
                asset=item["currency"],
                available=float(item.get("available", 0)),
                total=float(item.get("total", 0)),
            )
            for item in data
            if float(item.get("total", 0)) > 0
        ]


async def _fetch_coinbase(api_key: str, api_secret: str, extra: dict | None = None) -> list[BalanceEntry]:
    """Coinbase Exchange private API balance fetch.

    Required:
      - api_key
      - api_secret (base64 encoded)
      - extra.passphrase
    """
    import base64

    passphrase = (extra or {}).get("passphrase")
    if not passphrase:
        raise ValueError("Coinbase requires extra.passphrase")

    timestamp = str(time.time())
    method = "GET"
    request_path = "/accounts"
    body = ""
    message = f"{timestamp}{method}{request_path}{body}".encode()

    try:
        secret = base64.b64decode(api_secret)
    except Exception as exc:
        raise ValueError("Coinbase api_secret must be base64 encoded") from exc

    signature = hmac.new(secret, message, hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature).decode()

    headers = {
        "CB-ACCESS-KEY": api_key,
        "CB-ACCESS-SIGN": signature_b64,
        "CB-ACCESS-TIMESTAMP": timestamp,
        "CB-ACCESS-PASSPHRASE": passphrase,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"https://api.exchange.coinbase.com{request_path}", headers=headers)
        r.raise_for_status()
        data = r.json()
        return [
            BalanceEntry(
                asset=row.get("currency", "UNKNOWN"),
                available=float(row.get("available", 0)),
                total=float(row.get("balance", 0)),
            )
            for row in data
            if float(row.get("balance", 0)) > 0
        ]


async def _fetch_ibkr(api_key: str, api_secret: str, extra: dict | None = None) -> list[BalanceEntry]:
    """IBKR Client Portal gateway balance fetch.

    This integration expects the user to run IBKR Client Portal Gateway and provide:
      extra.base_url   (default: https://localhost:5000/v1/api)
      extra.token      (Bearer token, optional if gateway already authenticated)
      extra.account_id (optional; first account will be used if omitted)

    The api_key/api_secret fields are retained for schema consistency and can be
    used by future IBKR auth flows. Current flow reads token from extra.
    """
    cfg = extra or {}
    base_url = cfg.get("base_url", "https://localhost:5000/v1/api").rstrip("/")
    bearer = cfg.get("token") or api_key

    headers = {}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

    # Client Portal Gateway commonly uses self-signed certs on localhost.
    verify_tls = not base_url.startswith("https://localhost")

    async with httpx.AsyncClient(timeout=20, verify=verify_tls) as client:
        r_accounts = await client.get(f"{base_url}/portfolio/accounts", headers=headers)
        r_accounts.raise_for_status()
        accounts = r_accounts.json()
        if not accounts:
            return []

        account_id = cfg.get("account_id")
        if not account_id:
            first = accounts[0]
            account_id = first.get("id") or first.get("accountId") or first.get("acctId")
        if not account_id:
            raise ValueError("Unable to resolve IBKR account_id")

        r_ledger = await client.get(f"{base_url}/portfolio/{account_id}/ledger", headers=headers)
        r_ledger.raise_for_status()
        ledger = r_ledger.json()

        entries: list[BalanceEntry] = []
        for currency, payload in ledger.items():
            if not isinstance(payload, dict):
                continue
            total = payload.get("cashbalance")
            if total is None:
                total = payload.get("netliquidationvalue")
            if total is None:
                continue
            total_f = float(total)
            if total_f <= 0:
                continue
            available = payload.get("settledcash")
            if available is None:
                available = total_f
            entries.append(
                BalanceEntry(
                    asset=currency,
                    available=float(available),
                    total=total_f,
                )
            )

        return entries


async def _fetch_oanda(api_key: str, api_secret: str = "", extra: dict | None = None) -> list[BalanceEntry]:
    """OANDA uses a single Bearer token (no secret). Fetches first account balance."""
    async with httpx.AsyncClient(timeout=15) as client:
        # Get list of accounts first
        r = await client.get(
            "https://api-fxtrade.oanda.com/v3/accounts",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        accounts = r.json().get("accounts", [])
        if not accounts:
            return []
        acct_id = accounts[0]["id"]
        r2 = await client.get(
            f"https://api-fxtrade.oanda.com/v3/accounts/{acct_id}/summary",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r2.raise_for_status()
        summary = r2.json().get("account", {})
        balance = float(summary.get("balance", 0))
        currency = summary.get("currency", "USD")
        return [BalanceEntry(asset=currency, available=balance, total=balance)]


async def _platform_not_supported(platform: str, **_) -> list[BalanceEntry]:
    raise NotImplementedError(f"Balance fetching for {platform} is not yet implemented")


_FETCHERS = {
    "alpaca": _fetch_alpaca,
    "binance": _fetch_binance,
    "coinbase": _fetch_coinbase,
    "ibkr": _fetch_ibkr,
    "kraken": _fetch_kraken,
    "luno": _fetch_luno,
    "valr": _fetch_valr,
    "oanda": _fetch_oanda,
}


async def _validate_credentials(
    platform: str,
    api_key: str,
    api_secret: str,
    extra: dict | None,
) -> AccountValidationResult:
    checked_at = datetime.now(timezone.utc).isoformat()
    fetcher = _FETCHERS.get(platform)
    if not fetcher:
        return AccountValidationResult(
            platform=platform,
            valid=False,
            message=f"Unsupported platform. Supported: {', '.join(_SUPPORTED_PLATFORMS)}",
            checked_at=checked_at,
        )

    try:
        balances = await fetcher(api_key, api_secret, extra)
        sample_assets = [b.asset for b in balances[:5]]
        return AccountValidationResult(
            platform=platform,
            valid=True,
            message="Credentials validated successfully",
            balance_count=len(balances),
            sample_assets=sample_assets,
            checked_at=checked_at,
        )
    except Exception as exc:
        return AccountValidationResult(
            platform=platform,
            valid=False,
            message=str(exc),
            checked_at=checked_at,
        )


async def _fetch_balance(account: LinkedAccount) -> AccountBalance:
    fetched_at = datetime.now(timezone.utc).isoformat()
    platform = account.platform
    try:
        api_key = decrypt(account.api_key_enc)
        api_secret = decrypt(account.api_secret_enc) if account.api_secret_enc else ""
        extra = json.loads(decrypt(account.extra_enc)) if account.extra_enc else None
        fetcher = _FETCHERS.get(platform)
        if not fetcher:
            return AccountBalance(
                account_id=account.id,
                platform=platform,
                nickname=account.nickname,
                balances=[],
                error=f"Balance fetching not yet supported for {platform}",
                fetched_at=fetched_at,
            )
        balances = await fetcher(api_key, api_secret, extra)
        return AccountBalance(
            account_id=account.id,
            platform=platform,
            nickname=account.nickname,
            balances=balances,
            fetched_at=fetched_at,
        )
    except Exception as exc:
        log.warning("Balance fetch failed for account %d: %s", account.id, exc)
        return AccountBalance(
            account_id=account.id,
            platform=platform,
            nickname=account.nickname,
            balances=[],
            error=str(exc),
            fetched_at=fetched_at,
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/accounts", response_model=list[AccountOut])
async def list_accounts(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(LinkedAccount).where(LinkedAccount.user_id == user_id))).scalars().all()
    return rows


@router.post("/validate", response_model=AccountValidationResult)
async def validate_account_credentials(
    body: AccountValidate,
    user_id: str = Depends(get_current_user),
):
    """Lightweight credentials check for a platform without saving an account."""
    if body.platform not in _SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform. Supported: {', '.join(_SUPPORTED_PLATFORMS)}",
        )

    api_secret = body.api_secret or ""
    return await _validate_credentials(
        platform=body.platform,
        api_key=body.api_key,
        api_secret=api_secret,
        extra=body.extra,
    )


@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def link_account(
    body: AccountCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.platform not in _SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform. Supported: {', '.join(_SUPPORTED_PLATFORMS)}",
        )
    account = LinkedAccount(
        user_id=user_id,
        platform=body.platform,
        nickname=body.nickname,
        api_key_enc=encrypt(body.api_key),
        api_secret_enc=encrypt(body.api_secret) if body.api_secret else None,
        extra_enc=encrypt(json.dumps(body.extra)) if body.extra else None,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_account(
    account_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(LinkedAccount, account_id)
    if not account or account.user_id != user_id:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()


@router.get("/accounts/{account_id}/balance", response_model=AccountBalance)
async def get_account_balance(
    account_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(LinkedAccount, account_id)
    if not account or account.user_id != user_id:
        raise HTTPException(status_code=404, detail="Account not found")
    result = await _fetch_balance(account)
    if not result.error:
        account.last_synced = datetime.now(timezone.utc)
        await db.commit()
    return result


@router.get("/balances", response_model=list[AccountBalance])
async def get_all_balances(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accounts = (await db.execute(select(LinkedAccount).where(LinkedAccount.user_id == user_id))).scalars().all()
    if not accounts:
        return []
    import asyncio
    results = await asyncio.gather(*[_fetch_balance(a) for a in accounts])
    # Update last_synced for accounts with successful fetches
    for i, result in enumerate(results):
        if not result.error:
            accounts[i].last_synced = datetime.now(timezone.utc)
    await db.commit()
    return list(results)


@router.get("/platforms", response_model=list[str])
async def list_platforms():
    return _SUPPORTED_PLATFORMS
