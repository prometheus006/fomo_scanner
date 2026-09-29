"""fomo_scanner ana giriş noktası. Koşu başına EN FAZLA 1 özet mail.

1. Havuzlar: DexScreener'da filtreyi geçen yeni Solana tokenları -> GeckoTerminal'de
   son bakıştan beri >= MIN_WHALE_BUY_USD alım var mı -> authority kontrolü -> tabloya.
2. Cüzdanlar: WATCH_WALLETS'taki her adresin son bakıştan beri yaptığı alımlar -> tabloya.
"""
import os
import sys
import time

import requests

import config
import dexscreener
import geckoterminal
import mailer
import report
import seen_store
import solana_rpc

SAFETY_SEC = 120  # indekslemesi geciken işlemleri kaçırmamak için bir sonraki koşu bu kadar geriden başlar


def _short(addr: str) -> str:
    return f"{addr[:4]}…{addr[-4:]}" if len(addr) > 10 else addr


def pool_row(pair, trades, renounced):
    ranked, sell_usd = geckoterminal.summarize(trades)
    buy_usd = sum(b["usd"] for _, b in ranked)
    base = pair["baseToken"]
    return {
        "symbol": base.get("symbol") or "?",
        "name": base.get("name"),
        "url": pair.get("url") or f"https://dexscreener.com/solana/{pair['pairAddress']}",
        "price": float(pair.get("priceUsd") or 0),
        "liquidity": (pair.get("liquidity") or {}).get("usd") or 0,
        "vol24": (pair.get("volume") or {}).get("h24") or 0,
        "wallets": len(ranked),
        "buy_usd": buy_usd,
        "sell_usd": sell_usd,
        "net": buy_usd - sell_usd,
        "renounced": renounced,
        "top": [(w, b["usd"], b["count"]) for w, b in ranked[:3]],
    }


def wallet_rows(name, buys, tokens):
    rows = []
    for b in buys:
        t = tokens.get(b["mint"], {})
        rows.append({
            "name": name,
            "ts": b["ts"],
            "symbol": t.get("symbol") or _short(b["mint"]),
            "url": t.get("url") or f"https://dexscreener.com/solana/{b['mint']}",
            "amount": b["amount"],
            "usd": b["amount"] * t.get("price_usd", 0),
            "paid": ", ".join(f"{v:,.4g} {_short(k)}" for k, v in b["paid"].items()),
            "tx": b["tx"],
        })
    return rows


def passes_whale_filter(trades) -> bool:
    ranked, sell_usd = geckoterminal.summarize(trades)
    buy_usd = sum(b["usd"] for _, b in ranked)
    if len(ranked) < config.MIN_WHALE_WALLETS or buy_usd < config.MIN_TOTAL_WHALE_BUY_USD:
        return False
    return not (config.REQUIRE_NET_POSITIVE and buy_usd <= sell_usd)


def scan_pools(seen):
    candidates = dexscreener.fetch_candidates()
    print(f"{len(candidates)} aday filtreyi geçti (likidite/hacim/yaş).")
    rows = []
    for pair in candidates:
        addr = pair["pairAddress"]
        key = "pool:" + addr
        try:
            trades = geckoterminal.big_trades(addr, seen_store.since(seen, key, config.FIRST_SEEN_LOOKBACK_HOURS))
        except requests.RequestException as exc:
            print(f"ATLANDI {addr}: GeckoTerminal hatası ({exc})")
            continue

        seen_store.mark(seen, key, max((t["ts"] for t in trades), default=time.time() - SAFETY_SEC))
        if not passes_whale_filter(trades):
            continue

        try:
            renounced = solana_rpc.authorities_are_renounced(pair["baseToken"]["address"])
        except requests.RequestException:
            renounced = None
        if renounced is False and config.EXCLUDE_OPEN_AUTHORITY:
            continue
        rows.append(pool_row(pair, trades, renounced))

    rows.sort(key=lambda r: r["buy_usd"], reverse=True)
    return rows


def scan_wallets(seen):
    rows = []
    for name, wallet in config.WATCH_WALLETS.items():
        key = "wallet:" + wallet
        try:
            buys = solana_rpc.wallet_buys(wallet, seen_store.since(seen, key, config.WALLET_FIRST_RUN_HOURS))
        except requests.RequestException as exc:
            print(f"ATLANDI cüzdan {name}: RPC hatası ({exc})")
            continue

        seen_store.mark(seen, key, max((b["ts"] for b in buys), default=time.time() - SAFETY_SEC))
        if buys:
            rows += wallet_rows(name, buys, dexscreener.token_info([b["mint"] for b in buys]))
    return rows


def enable_test_mode():
    """Elle tetiklenen test: gevşek filtre + 6 saat geriye bakış, mail her durumda gider."""
    config.MIN_WHALE_WALLETS = 1
    config.MIN_TOTAL_WHALE_BUY_USD = config.MIN_WHALE_BUY_USD
    config.REQUIRE_NET_POSITIVE = False
    config.FIRST_SEEN_LOOKBACK_HOURS = 6


def run(test=False):
    if test:
        enable_test_mode()
        seen = {}
    else:
        seen = seen_store.load()
        seen_store.prune(seen)
    pools = scan_pools(seen)
    wallets = scan_wallets(seen)
    print(f"{len(pools)} token yüklü alım, {len(wallets)} izlenen cüzdan alımı.")

    if pools or wallets or test:
        subject = f"🐋 FOMO Tarama — {len(pools)} token yüklü alım"
        if wallets:
            subject += f", {len(wallets)} cüzdan alımı"
        if test:
            subject = "[TEST — gevşek filtre] " + subject
        mailer.send(subject, report.build_text(pools, wallets),
                    report.build_html(pools, wallets, config.MIN_WHALE_BUY_USD))
        print("Özet mail gönderildi.")
    if test:
        return  # test koşusu gerçek taramanın durumuna dokunmaz
    # Mail atılamazsa exception buraya gelmeden çıkar -> seen kaydedilmez -> sonraki koşu aynı işlemleri tekrar dener.
    seen_store.save(seen)


if __name__ == "__main__":
    try:
        run(test=os.environ.get("TEST_MAIL") == "true")
    except Exception as exc:  # workflow log'unda görünsün diye
        print(f"HATA: {exc}", file=sys.stderr)
        raise
