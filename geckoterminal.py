"""GeckoTerminal public API (ücretsiz, key yok, ~30 istek/dk): havuzdaki büyük işlemler."""
import time
from datetime import datetime

import requests

import config

_BASE = "https://api.geckoterminal.com/api/v2/networks/solana/pools"
_last_call = 0.0


def _get(url, params):
    global _last_call
    wait = config.GECKO_MIN_INTERVAL_SEC - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    for attempt in range(4):
        _last_call = time.time()
        resp = requests.get(url, params=params, timeout=15, headers={"Accept": "application/json"})
        if resp.status_code == 429 and attempt < 3:
            time.sleep(2 ** (attempt + 2))
            continue
        resp.raise_for_status()
        return resp.json()


def _ts(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def big_trades(pair_address: str, since_ts: float):
    """since_ts'den sonraki, MIN_WHALE_BUY_USD üstü işlemler.

    Dönen: [{"kind": "buy"|"sell", "usd": float, "wallet": str, "ts": float, "tx": str}, ...]
    """
    data = _get(
        f"{_BASE}/{pair_address}/trades",
        {"trade_volume_in_usd_greater_than": config.MIN_WHALE_BUY_USD},
    )
    trades = []
    for item in data.get("data") or []:
        a = item.get("attributes") or {}
        try:
            ts = _ts(a["block_timestamp"])
            usd = float(a["volume_in_usd"])
        except (KeyError, TypeError, ValueError):
            continue
        if ts <= since_ts:
            continue
        trades.append({
            "kind": a.get("kind"),
            "usd": usd,
            "wallet": a.get("tx_from_address") or "?",
            "ts": ts,
            "tx": a.get("tx_hash") or "",
        })
    return trades


def summarize(trades):
    """Cüzdan bazında alım toplamı + büyük satış toplamı.

    EXCLUDE_ROUND_TRIP_WALLETS açıksa aynı dönemde hem alıp hem satan cüzdanlar
    (arbitraj/MEV botu) alıcı listesinden çıkarılır; satışları satış toplamında kalır.
    """
    sellers = {t["wallet"] for t in trades if t["kind"] == "sell"} if config.EXCLUDE_ROUND_TRIP_WALLETS else set()
    buyers = {}
    sell_usd = 0.0
    for t in trades:
        if t["kind"] == "buy" and t["wallet"] not in sellers:
            b = buyers.setdefault(t["wallet"], {"usd": 0.0, "count": 0})
            b["usd"] += t["usd"]
            b["count"] += 1
        elif t["kind"] == "sell":
            sell_usd += t["usd"]
    ranked = sorted(buyers.items(), key=lambda kv: kv[1]["usd"], reverse=True)
    return ranked, sell_usd
