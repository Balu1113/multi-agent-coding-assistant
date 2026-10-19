from __future__ import annotations

import time
import threading
from collections import defaultdict
from typing import Any

_lock = threading.Lock()
_calls: dict[str, list[float]] = defaultdict(list)
_rate_limits: dict[str, dict[str, Any]] = {}  # model_id -> {limit, remaining, reset}


def _day_start() -> float:
    now = time.time()
    return now - (now % 86400)


def track(model_id: str) -> None:
    with _lock:
        ts_list = _calls[model_id]
        cutoff = _day_start()
        ts_list[:] = [t for t in ts_list if t >= cutoff]
        ts_list.append(time.time())


def update_rate_limit(model_id: str, limit: int, remaining: int, reset: int | None = None) -> None:
    """Store real rate limit info obtained from API response headers."""
    with _lock:
        _rate_limits[model_id] = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset,
            "updated_at": time.time(),
        }


def get_usage(model_id: str, daily_limit: int) -> dict:
    # Prefer real rate limit info from API headers
    with _lock:
        rl = _rate_limits.get(model_id)
        if rl is not None:
            return {
                "used": max(0, rl["limit"] - rl["remaining"]),
                "limit": rl["limit"],
                "percent": round((1 - rl["remaining"] / rl["limit"]) * 100, 1) if rl["limit"] > 0 else 0,
                "remaining": rl["remaining"],
                "source": "api",
            }
    # Fall back to local counter
    if daily_limit <= 0:
        return {"used": 0, "limit": 0, "percent": 0, "remaining": 0, "source": "local"}
    with _lock:
        ts_list = _calls.get(model_id, [])
        cutoff = _day_start()
        ts_list[:] = [t for t in ts_list if t >= cutoff]
        used = len(ts_list)
    pct = round(used / daily_limit * 100, 1)
    return {
        "used": used,
        "limit": daily_limit,
        "percent": pct,
        "remaining": max(0, daily_limit - used),
        "source": "local",
    }


def get_all_usage(models: list[dict]) -> dict[str, dict]:
    return {
        m["id"]: get_usage(m["id"], m.get("daily_limit", 0))
        for m in models
    }
