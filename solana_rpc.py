"""Solana public RPC üzerinden mint authority kontrolü ve yüklü alım tespiti.

Ücretsiz public RPC kullanılır, key gerekmez. Ağır kullanım rate-limit yer,
bu yüzden çağrılar arasında küçük bekleme var.
"""
import time
import requests

import config

_session = requests.Session()


def _rpc(method, params):
    resp = _session.post(
        config.SOLANA_RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("result")


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


def find_whale_buys(pair_address: str, mint_address: str, price_usd: float):
    """pair_address'teki son işlemlerde mint_address için yüklü alım arar.

    Dönen: [{"signature": str, "buyer": str, "usd": float}, ...]
    """
    if price_usd <= 0:
        return []

    sigs = _rpc("getSignaturesForAddress", [pair_address, {"limit": config.WHALE_LOOKBACK_TX}])
    if not sigs:
        return []

    whales = []
    for entry in sigs:
        sig = entry.get("signature")
        if not sig or entry.get("err"):
            continue
        time.sleep(0.15)  # public RPC rate-limit koruması
        try:
            tx = _rpc(
                "getTransaction",
                [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
            )
        except requests.RequestException:
            continue
        if not tx or not tx.get("meta"):
            continue

        meta = tx["meta"]
        pre = {b["accountIndex"]: b for b in meta.get("preTokenBalances", []) if b.get("mint") == mint_address}
        post = {b["accountIndex"]: b for b in meta.get("postTokenBalances", []) if b.get("mint") == mint_address}

        for idx, post_bal in post.items():
            pre_amt = pre.get(idx, {}).get("uiTokenAmount", {}).get("uiAmount") or 0
            post_amt = post_bal.get("uiTokenAmount", {}).get("uiAmount") or 0
            delta = post_amt - pre_amt
            if delta <= 0:
                continue  # token azalan/pool tarafı, alıcı değil
            usd_value = delta * price_usd
            if usd_value >= config.MIN_WHALE_BUY_USD:
                whales.append({
                    "signature": sig,
                    "buyer": post_bal.get("owner", "?"),
                    "usd": usd_value,
                })
    return whales
