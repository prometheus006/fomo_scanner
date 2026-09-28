"""seen.json ile dedupe — aynı token için DEDUPE_HOURS içinde ikinci mail atılmaz."""
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
        json.dump(seen, f, indent=2)


def should_notify(seen: dict, pair_address: str) -> bool:
    last_sent = seen.get(pair_address)
    if last_sent is None:
        return True
    return (time.time() - last_sent) > config.DEDUPE_HOURS * 3600


def mark_notified(seen: dict, pair_address: str):
    seen[pair_address] = time.time()
