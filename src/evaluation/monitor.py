from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.evaluation.metrics import MetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class RequestLog:
    prompt: str
    success: bool
    duration: float
    agents_used: int = 0
    error: str | None = None


class Monitor:
    def __init__(self) -> None:
        self.metrics = MetricsCollector()
        self._request_logs: list[RequestLog] = []
        self._start_time = time.time()

    def record_request(self) -> None:
        self.metrics.increment("requests_total")

    def record_success(self) -> None:
        self.metrics.increment("requests_success")

    def record_failure(self) -> None:
        self.metrics.increment("requests_failed")

    def record_duration(self, seconds: float) -> None:
        self.metrics.observe("request_duration_seconds", seconds)

    def record_llm_call(self, model: str, tokens: int, duration: float) -> None:
        self.metrics.increment("llm_calls_total", {"model": model})
        self.metrics.observe("llm_tokens", tokens, {"model": model})
        self.metrics.observe("llm_duration_seconds", duration, {"model": model})

    def log_request(self, log: RequestLog) -> None:
        self._request_logs.append(log)

    def summary(self) -> dict[str, Any]:
        total = self.metrics.get_counter("requests_total")
        success = self.metrics.get_counter("requests_success")
        failed = self.metrics.get_counter("requests_failed")
        uptime = time.time() - self._start_time

        return {
            "uptime_seconds": uptime,
            "requests": {
                "total": total,
                "success": success,
                "failed": failed,
                "success_rate": (success / total * 100) if total else 0.0,
            },
            "latency": self.metrics.get_histogram_summary("request_duration_seconds"),
            "llm_calls": self.metrics.get_counter("llm_calls_total"),
        }

    def export_report(self, path: str | Path = "./reports/monitor_report.json") -> None:
        report = {
            "summary": self.summary(),
            "recent_requests": [
                {
                    "prompt": r.prompt[:100],
                    "success": r.success,
                    "duration": r.duration,
                    "error": r.error,
                }
                for r in self._request_logs[-50:]
            ],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("Monitor report exported to %s", path)
