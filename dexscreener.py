"""DexScreener'dan Solana aday token/pair listesi (ücretsiz, key gerekmez)."""
import time
import requests

import config


def fetch_candidates():
    """Filtreyi geçen adayları liquidity'ye göre azalan sırada döner."""
    seen_pairs = {}
    for query in config.DEXSCREENER_SEARCH_QUERIES:
        try:
            resp = requests.get(config.DEXSCREENER_SEARCH_URL, params={"q": query}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            continue
        for pair in resp.json().get("pairs") or []:
            if pair.get("chainId") != config.CHAIN_ID:
                continue
            addr = pair.get("pairAddress")
            if not addr or addr in seen_pairs:
                continue
            if _passes_filters(pair):
                seen_pairs[addr] = pair

    candidates = list(seen_pairs.values())
    candidates.sort(key=lambda p: (p.get("volume") or {}).get("h24") or 0, reverse=True)
    return candidates[: config.MAX_TOP_PAIR_CANDIDATES]


def token_info(mints):
    """mint -> {"symbol", "price_usd", "url"} (en likit Solana havuzundan). Bulunamayan atlanır."""
    info = {}
    mints = list(dict.fromkeys(mints))
    for i in range(0, len(mints), 30):  # endpoint en fazla 30 adres alır
        try:
            resp = requests.get(config.DEXSCREENER_TOKENS_URL + ",".join(mints[i:i + 30]), timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            continue
        pairs = [p for p in resp.json().get("pairs") or [] if p.get("chainId") == config.CHAIN_ID]
        pairs.sort(key=lambda p: (p.get("liquidity") or {}).get("usd") or 0, reverse=True)
        for p in pairs:
            mint = (p.get("baseToken") or {}).get("address")
            if mint in info or mint not in mints:
                continue
            info[mint] = {
                "symbol": p["baseToken"].get("symbol"),
                "price_usd": float(p.get("priceUsd") or 0),
                "url": p.get("url"),
            }
    return info


def _passes_filters(pair) -> bool:
    liquidity_usd = (pair.get("liquidity") or {}).get("usd") or 0
    if liquidity_usd < config.MIN_LIQUIDITY_USD:
        return False

    volume_h24 = (pair.get("volume") or {}).get("h24") or 0
    if volume_h24 < config.MIN_VOLUME_H24_USD:
        return False

    created_at_ms = pair.get("pairCreatedAt")
    if not created_at_ms:
        return False
    age_minutes = (time.time() * 1000 - created_at_ms) / 60_000
    if age_minutes < config.MIN_AGE_MINUTES or age_minutes > config.MAX_AGE_HOURS * 60:
        return False

    return True
