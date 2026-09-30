"""Solana public RPC: mint authority kontrolü ve izlenen cüzdanların alımları.

Ücretsiz public RPC kullanılır, key gerekmez. Ağır kullanım rate-limit yer,
bu yüzden çağrılar arasında küçük bekleme ve 429'da tekrar deneme var.
"""
import time
import requests

import config

_session = requests.Session()

SOL_MINT = "So11111111111111111111111111111111111111112"
QUOTE_MINTS = {
    SOL_MINT: "SOL",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
}


def _rpc(method, params, retries=4):
    for attempt in range(retries + 1):
        resp = _session.post(
            config.SOLANA_RPC_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=15,
        )
        if resp.status_code == 429 and attempt < retries:
            retry_after = resp.headers.get("Retry-After", "")
            time.sleep(float(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json().get("result")


def authorities_are_renounced(mint_address: str) -> bool:
    """Mint authority ve freeze authority ikisi de null mı (config'e göre)."""
    result = _rpc("getAccountInfo", [mint_address, {"encoding": "jsonParsed"}])
    if not result or not result.get("value"):
        return False
    try:
        info = result["value"]["data"]["parsed"]["info"]
    except (KeyError, TypeError):
        return False
    mint_ok = (not config.REQUIRE_MINT_AUTHORITY_NULL) or info.get("mintAuthority") is None
    freeze_ok = (not config.REQUIRE_FREEZE_AUTHORITY_NULL) or info.get("freezeAuthority") is None
    return mint_ok and freeze_ok


def parse_wallet_buys(tx, wallet: str):
    """Tek işlemde cüzdanın aldığı tokenlar ve ödediği quote.

    Dönen: [{"mint": str, "amount": float, "paid": {"SOL": x, "USDC": y}}] (alım yoksa boş)
    """
    meta = tx.get("meta") or {}
    if meta.get("err"):
        return []

    deltas = {}
    for side, sign in (("preTokenBalances", -1), ("postTokenBalances", 1)):
        for b in meta.get(side) or []:
            if b.get("owner") != wallet:
                continue
            amt = (b.get("uiTokenAmount") or {}).get("uiAmount") or 0
            deltas[b["mint"]] = deltas.get(b["mint"], 0) + sign * amt

    # Ödeme = cüzdandan azalan her şey (SOL/USDC/USDT ya da token->token takasında satılan token).
    paid = {}
    for mint, d in deltas.items():
        if d < 0:
            name = QUOTE_MINTS.get(mint, mint)
            paid[name] = paid.get(name, 0) - d

    keys = [k.get("pubkey") if isinstance(k, dict) else k
            for k in ((tx.get("transaction") or {}).get("message") or {}).get("accountKeys") or []]
    if wallet in keys:
        i = keys.index(wallet)
        lamports = (meta["postBalances"][i] - meta["preBalances"][i]) / 1e9
        if lamports < -0.001:  # ücret tozunu alım sayma
            paid["SOL"] = paid.get("SOL", 0) - lamports

    if not paid:
        return []  # karşılığında bir şey ödenmemiş giriş = airdrop/spam toz, alım değil
    return [
        {"mint": mint, "amount": d, "paid": paid}
        for mint, d in deltas.items()
        if d > 0 and mint not in QUOTE_MINTS
    ]


def wallet_buys(wallet: str, since_ts: float):
    """since_ts'den sonra cüzdanın yaptığı alımlar (en yeniden eskiye)."""
    # Tanınmış cüzdanlara saatte onlarca spam işlem gelir; sabit "son N" gerçek alımları kaçırır.
    # O yüzden since_ts'e kadar sayfalayarak geri gidilir (tavan WALLET_MAX_TX_PER_RUN).
    sigs, before = [], None
    while len(sigs) < config.WALLET_MAX_TX_PER_RUN:
        opts = {"limit": 50, **({"before": before} if before else {})}
        page = _rpc("getSignaturesForAddress", [wallet, opts]) or []
        new = [s for s in page if (s.get("blockTime") or 0) > since_ts]
        sigs += new
        if len(new) < len(page) or len(page) < 50:
            break
        before = page[-1]["signature"]
    else:
        print(f"UYARI {wallet[:6]}: {config.WALLET_MAX_TX_PER_RUN}+ yeni işlem, eskileri bu koşuda atlandı")

    buys = []
    for entry in sigs[: config.WALLET_MAX_TX_PER_RUN]:
        if entry.get("err"):
            continue
        time.sleep(0.2)  # public RPC rate-limit koruması
        tx = _rpc("getTransaction", [entry["signature"],
                                     {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
        if not tx:
            continue
        for b in parse_wallet_buys(tx, wallet):
            b.update(ts=entry["blockTime"], tx=entry["signature"])
            buys.append(b)
    return buys
