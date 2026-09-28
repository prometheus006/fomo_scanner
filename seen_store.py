"""seen.json: havuz/cüzdan başına son bakılan zaman. Sadece bundan yeni işlemler bildirilir."""
import json
import os
import time

import config


def load():
    if not os.path.exists(config.SEEN_FILE):
        return {}
    try:
        with open(config.SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save(seen: dict):
    with open(config.SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, sort_keys=True)


def since(seen: dict, key: str, first_lookback_hours: float) -> float:
    """Bu anahtar için en son bakılan zaman; hiç bakılmadıysa şimdi - lookback."""
    return seen.get(key, time.time() - first_lookback_hours * 3600)


def mark(seen: dict, key: str, ts: float):
    seen[key] = max(ts, seen.get(key, 0))


def prune(seen: dict):
    cutoff = time.time() - config.SEEN_PRUNE_HOURS * 3600
    for key in [k for k, v in seen.items() if v < cutoff and not k.startswith("wallet:")]:
        del seen[key]
