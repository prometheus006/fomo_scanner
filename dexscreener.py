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
