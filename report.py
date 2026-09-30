"""Koşu başına tek özet mail: HTML (crypto_scanner stili, koyu tema) + düz metin yedeği.

Gmail <style> bloklarını güvenilir işlemediği için stiller inline.
"""
import time
from html import escape

BG, CARD, LINE, TXT, MUTED = "#0d1117", "#161b22", "#30363d", "#e6edf3", "#8b949e"
GREEN, RED, AMBER, BLUE = "#3fb950", "#f85149", "#d29922", "#58a6ff"

_TH = f"padding:8px 10px;text-align:left;color:{MUTED};font-size:12px;border-bottom:1px solid {LINE};white-space:nowrap"
_TD = f"padding:8px 10px;color:{TXT};font-size:13px;border-bottom:1px solid {LINE};white-space:nowrap"


def _usd(x):
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.2f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:,.1f}k"
    return f"${x:,.0f}"


def _short(a):
    return f"{a[:4]}…{a[-4:]}" if len(a) > 10 else a


def _a(url, label, color=BLUE):
    return f'<a href="{escape(url)}" style="color:{color};text-decoration:none">{escape(label)}</a>'


def _table(title, color, headers, rows):
    head = "".join(f'<th style="{_TH}">{h}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f'<td style="{_TD}">{c}</td>' for c in r) + "</tr>" for r in rows)
    return (
        f'<div style="margin-top:20px;border:1px solid {LINE};border-radius:8px;overflow:hidden">'
        f'<div style="background:{color};color:#fff;font-weight:bold;padding:10px 14px;font-size:14px">{title}</div>'
        f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;background:{CARD}">'
        f"<tr>{head}</tr>{body}</table></div></div>"
    )


def _authority(r):
    return {True: f'<span style="color:{GREEN}">kapalı</span>',
            False: f'<span style="color:{RED};font-weight:bold">AÇIK</span>',
            None: f'<span style="color:{MUTED}">?</span>'}[r]


def build_html(pool_rows, wallet_rows, min_whale_usd, run_ts=None):
    run_ts = run_ts or time.time()
    parts = [
        f'<div style="background:{BG};padding:24px;font-family:Segoe UI,Arial,sans-serif;color:{TXT}">',
        f'<div style="background:{CARD};border:1px solid {LINE};border-radius:8px;padding:18px;text-align:center">',
        '<div style="font-size:20px;font-weight:bold;letter-spacing:1px">🐋 FOMO YÜKLÜ ALIM TARAYICI</div>',
        f'<div style="color:{MUTED};font-size:12px;margin-top:6px">{time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(run_ts))}</div>',
        f'<div style="margin-top:12px">'
        f'<span style="border:1px solid {GREEN};color:{GREEN};padding:5px 12px;border-radius:4px;font-size:13px">▲ Token: {len(pool_rows)}</span> '
        f'<span style="border:1px solid {BLUE};color:{BLUE};padding:5px 12px;border-radius:4px;font-size:13px">👤 Cüzdan alımı: {len(wallet_rows)}</span>'
        "</div></div>",
    ]

    if pool_rows:
        rows = []
        for r in pool_rows:
            net_color = GREEN if r["net"] >= 0 else RED
            top = "<br>".join(
                _a(f"https://solscan.io/account/{w}", f"{_short(w)} {_usd(u)}" + (f" ×{c}" if c > 1 else ""))
                for w, u, c in r["top"]
            )
            rows.append([
                f'<b style="color:{GREEN}">▲ {_a(r["url"], r["symbol"], GREEN)}</b>'
                f'<div style="color:{MUTED};font-size:11px">{escape(r["name"] or "")}</div>',
                f"${r['price']:.6g}",
                _usd(r["liquidity"]),
                _usd(r["vol24"]),
                f'<b>{r["wallets"]}</b>',
                f'<span style="color:{GREEN}">{_usd(r["buy_usd"])}</span>',
                f'<span style="color:{RED}">{_usd(r["sell_usd"])}</span>',
                f'<b style="color:{net_color}">{"+" if r["net"] >= 0 else "-"}{_usd(abs(r["net"]))}</b>',
                _authority(r["renounced"]),
                top,
            ])
        parts.append(_table(
            f"▲ YÜKLÜ ALIM GELEN TOKENLAR ({len(pool_rows)})", "#1f7a3a",
            ["Token", "Fiyat", "Likidite", "24s Hacim", "Cüzdan", "Alım", "Satış", "Net", "Mint/Freeze", "En büyük alıcılar"],
            rows,
        ))

    if wallet_rows:
        rows = [[
            f'<b>{escape(r["name"])}</b>',
            time.strftime("%H:%M", time.gmtime(r["ts"])),
            f'<b style="color:{GREEN}">{_a(r["url"], r["symbol"], GREEN)}</b>',
            f"{r['amount']:,.4g}",
            (f'<b>{"~" if r.get("estimated") else ""}{_usd(r["usd"])}</b>' if r["usd"]
             else f'<span style="color:{MUTED}">?</span>'),
            escape(r["paid"]),
            _a(f"https://solscan.io/tx/{r['tx']}", "tx"),
        ] for r in wallet_rows]
        parts.append(_table(
            f"👤 İZLENEN CÜZDAN ALIMLARI ({len(wallet_rows)})", "#1f4f8a",
            ["Cüzdan", "Saat", "Token", "Adet", "Tutar*", "Ödenen", "İşlem"],
            rows,
        ))

    parts.append(
        f'<div style="margin-top:20px;background:{CARD};border:1px solid {LINE};border-radius:8px;padding:12px 14px;'
        f'color:{MUTED};font-size:12px;line-height:1.6">'
        f"<b>Kolon rehberi:</b> Cüzdan = son taramadan beri tek işlemde ≥{_usd(min_whale_usd)} alan farklı cüzdan sayısı | "
        "Alım/Satış = aynı dönemdeki yüklü işlemlerin toplamı | Net = alım − satış | "
        "Mint/Freeze = token yeni basılabilir/dondurulabilir mi (AÇIK = risk) | "
        "*Tutar = alım için ödenen USDC/SOL'un dolar karşılığı; başında ~ varsa ödeme başka bir token'la "
        "yapılmış ve tutar güncel fiyattan tahmin edilmiştir.<br>"
        "Bu mail yalnızca filtreden geçen işlemleri listeler; alım önerisi değildir. "
        "Büyük alıcıların bir kısmı arbitraj/MEV botu olabilir.</div></div>"
    )
    return "".join(parts)


def build_text(pool_rows, wallet_rows):
    lines = []
    for r in pool_rows:
        lines.append(f"{r['symbol']}: {r['wallets']} cüzdan, alım {_usd(r['buy_usd'])}, satış {_usd(r['sell_usd'])}, "
                     f"net {_usd(r['net'])} | {r['url']}")
    for r in wallet_rows:
        lines.append(f"{r['name']} {r['symbol']} {r['amount']:,.4g} adet (~{_usd(r['usd'])}) ödenen: {r['paid']} | "
                     f"https://solscan.io/tx/{r['tx']}")
    return "\n".join(lines)
