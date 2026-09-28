"""Ağa çıkmayan minimum self-check: filtre + dedupe mantığı."""
import time

import config
import dexscreener
import seen_store


def _pair(liquidity=50_000, volume=100_000, age_minutes=60):
    return {
        "chainId": "solana",
        "pairAddress": "P1",
        "liquidity": {"usd": liquidity},
        "volume": {"h24": volume},
        "pairCreatedAt": (time.time() - age_minutes * 60) * 1000,
    }


def test_passes_filters_ok():
    assert dexscreener._passes_filters(_pair())


def test_passes_filters_low_liquidity():
    assert not dexscreener._passes_filters(_pair(liquidity=1))


def test_passes_filters_too_new():
    assert not dexscreener._passes_filters(_pair(age_minutes=1))


def test_passes_filters_too_old():
    assert not dexscreener._passes_filters(_pair(age_minutes=config.MAX_AGE_HOURS * 60 + 10))


def test_dedupe_first_seen_notifies():
    seen = {}
    assert seen_store.should_notify(seen, "P1")
    seen_store.mark_notified(seen, "P1")
    assert not seen_store.should_notify(seen, "P1")


def test_dedupe_expired_notifies_again():
    seen = {"P1": time.time() - (config.DEDUPE_HOURS + 1) * 3600}
    assert seen_store.should_notify(seen, "P1")


def test_rpc_retries_on_429():
    import solana_rpc

    class Resp:
        def __init__(self, code):
            self.status_code, self.headers = code, {"Retry-After": "0"}
        def raise_for_status(self):
            assert self.status_code == 200
        def json(self):
            return {"result": "ok"}

    codes = iter([429, 429, 200])
    orig = solana_rpc._session.post
    solana_rpc._session.post = lambda *a, **k: Resp(next(codes))
    try:
        assert solana_rpc._rpc("x", []) == "ok"
    finally:
        solana_rpc._session.post = orig


def test_email_whale_check_failed():
    import scanner
    pair = {"baseToken": {"name": "T", "symbol": "T", "address": "M"}, "priceUsd": "1"}
    assert "kontrol edilemedi" in scanner.format_email(pair, None)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} test geçti.")
