from __future__ import annotations

import time
import json
import logging
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricRecord:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    def __init__(self) -> None:
        self._records: list[MetricRecord] = []
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, tags: dict[str, str] | None = None) -> None:
        self._counters[name] += 1
        self._records.append(MetricRecord(name="counter:" + name, value=self._counters[name], tags=tags or {}))

    def gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value
        self._records.append(MetricRecord(name="gauge:" + name, value=value))

    def observe(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self._histograms[name].append(value)
        self._records.append(MetricRecord(name="histogram:" + name, value=value, tags=tags or {}))

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_histogram_summary(self, name: str) -> dict[str, float]:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "p50": 0, "p95": 0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "mean": sum(sorted_vals) / n,
            "p50": sorted_vals[int(n * 0.5)],
            "p95": sorted_vals[int(n * 0.95)],
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: self.get_histogram_summary(k) for k in self._histograms
            },
        }

    def export_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")
        logger.info("Metrics exported to %s", path)
