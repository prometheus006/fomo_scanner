"""fomo_scanner ana giriş noktası.

Akış:
1. DexScreener'dan Solana'da likidite/hacim/yaş filtresini geçen yeni tokenlar
2. Her aday için mint/freeze authority kontrolü (Solana public RPC)
3. Filtreyi geçenler için son işlemlerde yüklü alım taraması
4. Yeni bulunan / dedupe süresi dolmuş adaylar için Gmail'e mail
"""
import sys

import config
import dexscreener
import mailer
import seen_store
import solana_rpc


def format_email(pair, whales):
    base = pair["baseToken"]
    lines = [
        f"Token: {base.get('name')} ({base.get('symbol')})",
        f"Mint: {base.get('address')}",
        f"Fiyat: ${pair.get('priceUsd')}",
        f"Likidite: ${(pair.get('liquidity') or {}).get('usd', 0):,.0f}",
        f"24s hacim: ${(pair.get('volume') or {}).get('h24', 0):,.0f}",
        f"DexScreener: {pair.get('url')}",
        "",
        "Mint/freeze authority: kapalı (yeni basım/dondurma yok)",
        "",
    ]
    if whales:
        lines.append(f"Yüklü alım tespit edildi ({len(whales)} adet, >=${config.MIN_WHALE_BUY_USD:,.0f}):")
        for w in whales:
            lines.append(f"  - ${w['usd']:,.0f} | cüzdan {w['buyer']} | tx {w['signature']}")
    else:
        lines.append("Son işlemlerde eşiği geçen yüklü alım yok.")
    return "\n".join(lines)


def run():
    seen = seen_store.load()
    candidates = dexscreener.fetch_candidates()
    print(f"{len(candidates)} aday filtreyi geçti (likidite/hacim/yaş).")

    sent = 0
    for pair in candidates:
        pair_address = pair["pairAddress"]
        mint_address = pair["baseToken"]["address"]

        if not solana_rpc.authorities_are_renounced(mint_address):
            continue

        if not seen_store.should_notify(seen, pair_address):
            continue

        price_usd = float(pair.get("priceUsd") or 0)
        whales = solana_rpc.find_whale_buys(pair_address, mint_address, price_usd)

        subject = f"[fomo_scanner] {pair['baseToken'].get('symbol')} — sağlam sinyal"
        mailer.send(subject, format_email(pair, whales))
        seen_store.mark_notified(seen, pair_address)
        sent += 1

    seen_store.save(seen)
    print(f"{sent} mail gönderildi.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # workflow log'unda görünsün diye
        print(f"HATA: {exc}", file=sys.stderr)
        raise
