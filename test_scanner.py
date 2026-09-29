"""Ağa çıkmayan minimum self-check."""
import time

import config
import dexscreener
import geckoterminal
import seen_store
import solana_rpc

W = "WaLLet1111111111111111111111111111111111111"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
MEME = "MeMe111111111111111111111111111111111111111"


def _pair(liquidity=60_000, volume=300_000, age_minutes=60):
    return {
        "chainId": "solana",
        "pairAddress": "P1",
        "liquidity": {"usd": liquidity},
        "volume": {"h24": volume},
        "pairCreatedAt": (time.time() - age_minutes * 60) * 1000,
    }


def test_filters():
    assert dexscreener._passes_filters(_pair())
    assert not dexscreener._passes_filters(_pair(liquidity=1))
    assert not dexscreener._passes_filters(_pair(age_minutes=1))
    assert not dexscreener._passes_filters(_pair(age_minutes=config.MAX_AGE_HOURS * 60 + 10))


def test_since_and_mark():
    seen = {}
    s = seen_store.since(seen, "pool:P1", 1)
    assert abs(s - (time.time() - 3600)) < 5
    seen_store.mark(seen, "pool:P1", 100)
    seen_store.mark(seen, "pool:P1", 50)  # geri gitmez
    assert seen_store.since(seen, "pool:P1", 1) == 100


def test_prune_keeps_wallets():
    old = time.time() - (config.SEEN_PRUNE_HOURS + 1) * 3600
    seen = {"pool:A": old, "wallet:B": old, "pool:C": time.time()}
    seen_store.prune(seen)
    assert set(seen) == {"wallet:B", "pool:C"}


def test_gecko_filters_old_and_summarizes():
    now = time.time()
    iso = lambda ts: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
    fake = {"data": [
        {"attributes": {"kind": "buy", "volume_in_usd": "6000", "tx_from_address": "A", "block_timestamp": iso(now - 10), "tx_hash": "t1"}},
        {"attributes": {"kind": "buy", "volume_in_usd": "9000", "tx_from_address": "A", "block_timestamp": iso(now - 20), "tx_hash": "t2"}},
        {"attributes": {"kind": "sell", "volume_in_usd": "7000", "tx_from_address": "B", "block_timestamp": iso(now - 30), "tx_hash": "t3"}},
        {"attributes": {"kind": "buy", "volume_in_usd": "50000", "tx_from_address": "C", "block_timestamp": iso(now - 5000), "tx_hash": "old"}},
    ]}
    orig = geckoterminal._get
    geckoterminal._get = lambda *a, **k: fake
    try:
        trades = geckoterminal.big_trades("P1", now - 3600)
    finally:
        geckoterminal._get = orig
    assert {t["tx"] for t in trades} == {"t1", "t2", "t3"}
    ranked, sell = geckoterminal.summarize(trades)
    assert ranked == [("A", {"usd": 15000.0, "count": 2})] and sell == 7000.0


def test_whale_filter():
    import scanner
    t = lambda kind, usd, w: {"kind": kind, "usd": usd, "wallet": w, "ts": 0, "tx": ""}
    good = [t("buy", 12000, "A"), t("buy", 11000, "B"), t("sell", 6000, "C")]
    assert scanner.passes_whale_filter(good)
    assert not scanner.passes_whale_filter([t("buy", 30000, "A")])  # tek cüzdan
    assert not scanner.passes_whale_filter([t("buy", 6000, "A"), t("buy", 6000, "B")])  # toplam düşük
    assert not scanner.passes_whale_filter(good + [t("sell", 40000, "D")])  # net negatif
    bot = [t("buy", 12000, "A"), t("buy", 11000, "B"), t("sell", 11000, "B")]  # B al-sat botu
    ranked, _ = geckoterminal.summarize(bot)
    assert [w for w, _ in ranked] == ["A"] and not scanner.passes_whale_filter(bot)


def _tx(pre, post, lamports=(10_000_000_000, 10_000_000_000)):
    bal = lambda mint, amt: {"accountIndex": 1, "mint": mint, "owner": W, "uiTokenAmount": {"uiAmount": amt}}
    return {
        "meta": {"err": None,
                 "preTokenBalances": [bal(m, a) for m, a in pre],
                 "postTokenBalances": [bal(m, a) for m, a in post],
                 "preBalances": [lamports[0]], "postBalances": [lamports[1]]},
        "transaction": {"message": {"accountKeys": [{"pubkey": W}]}},
    }


def test_wallet_buy_with_sol():
    buys = solana_rpc.parse_wallet_buys(_tx([], [(MEME, 1000)], (10_000_000_000, 8_000_000_000)), W)
    assert len(buys) == 1 and buys[0]["mint"] == MEME and abs(buys[0]["paid"]["SOL"] - 2) < 1e-9


def test_wallet_buy_with_usdc():
    buys = solana_rpc.parse_wallet_buys(_tx([(USDC, 500), (MEME, 10)], [(USDC, 100), (MEME, 110)]), W)
    assert buys[0]["amount"] == 100 and buys[0]["paid"] == {"USDC": 400}


def test_wallet_token_to_token_swap():
    OTHER = "OtHeR11111111111111111111111111111111111111"
    buys = solana_rpc.parse_wallet_buys(_tx([(OTHER, 500)], [(OTHER, 0), (MEME, 70)]), W)
    assert buys[0]["mint"] == MEME and buys[0]["paid"] == {OTHER: 500}


def test_airdrop_dust_is_not_buy():
    assert solana_rpc.parse_wallet_buys(_tx([], [(MEME, 0.00001)]), W) == []


def test_wallet_sell_is_not_buy():
    assert solana_rpc.parse_wallet_buys(_tx([(MEME, 1000)], [], (8_000_000_000, 10_000_000_000)), W) == []


def test_rpc_retries_on_429():
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


def test_report_render():
    import report
    import scanner
    pair = {"pairAddress": "P1", "baseToken": {"name": "<T>", "symbol": "TOK", "address": "M"}, "priceUsd": "1"}
    trades = [{"kind": "buy", "usd": 6000.0, "wallet": "A", "ts": 0, "tx": "t"},
              {"kind": "sell", "usd": 9000.0, "wallet": "B", "ts": 0, "tx": "u"}]
    prow = scanner.pool_row(pair, trades, False)
    assert prow["wallets"] == 1 and prow["net"] == -3000.0
    buys = [{"mint": MEME, "amount": 10.0, "paid": {"SOL": 1.5}, "ts": 0, "tx": "x"}]
    wrows = scanner.wallet_rows("K", buys, {MEME: {"symbol": "MEME", "price_usd": 2.0, "url": "u"}})
    assert wrows[0]["usd"] == 20.0 and wrows[0]["paid"] == "1.5 SOL"
    html = report.build_html([prow], wrows, 5000)
    assert "TOK" in html and "AÇIK" in html and "MEME" in html and "&lt;T&gt;" in html and "<T>" not in html
    assert "TOK" in report.build_text([prow], wrows)


def test_test_mode_mails_and_keeps_state():
    import mailer
    import scanner
    saved = {k: getattr(config, k) for k in ("MIN_WHALE_WALLETS", "MIN_TOTAL_WHALE_BUY_USD",
                                             "REQUIRE_NET_POSITIVE", "FIRST_SEEN_LOOKBACK_HOURS")}
    sent, saves = [], []
    orig = (scanner.scan_pools, scanner.scan_wallets, mailer.send, seen_store.save)
    scanner.scan_pools = scanner.scan_wallets = lambda seen: []
    mailer.send = lambda s, t, h=None: sent.append(s)
    seen_store.save = lambda seen: saves.append(1)
    try:
        scanner.run(test=True)
        assert len(sent) == 1 and sent[0].startswith("[TEST") and saves == []
        sent.clear()
        for k, v in saved.items():
            setattr(config, k, v)
        scanner.run(test=False)  # boş normal koşu: mail yok, durum kaydedilir
        assert sent == [] and saves == [1]
    finally:
        scanner.scan_pools, scanner.scan_wallets, mailer.send, seen_store.save = orig
        for k, v in saved.items():
            setattr(config, k, v)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} test geçti.")
