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


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} test geçti.")
