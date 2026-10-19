from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    success: bool
    duration: float
    score: float
    details: dict[str, Any] = field(default_factory=dict)


class CodingBenchmark:
    def __init__(self) -> None:
        self._tasks: list[dict[str, Any]] = self._default_tasks()

    def _default_tasks(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "FizzBuzz",
                "prompt": "Write a function that prints numbers 1-100, replacing multiples of 3 with Fizz, 5 with Buzz, 15 with FizzBuzz",
                "checks": ["fizz", "buzz", "15"],
                "category": "basics",
            },
            {
                "name": "Binary Search",
                "prompt": "Implement binary search on a sorted array",
                "checks": ["def binary_search", "return"],
                "category": "algorithms",
            },
            {
                "name": "Quick Sort",
                "prompt": "Implement quicksort",
                "checks": ["def quick_sort", "return"],
                "category": "algorithms",
            },
            {
                "name": "API Endpoint",
                "prompt": "Create a FastAPI endpoint that accepts POST requests with JSON body and returns a response",
                "checks": ["fastapi", "app.", "@"],
                "category": "web",
            },
            {
                "name": "Unit Test",
                "prompt": "Write pytest tests for a calculator module with add, subtract, multiply, divide",
                "checks": ["def test_", "assert", "pytest"],
                "category": "testing",
            },
        ]

    async def run_all(self, code_generator: Callable[[str], str]) -> list[BenchmarkResult]:
        results = []
        for task in self._tasks:
            start = time.perf_counter()
            try:
                code = code_generator(task["prompt"])
                duration = time.perf_counter() - start
                passes = sum(1 for check in task["checks"] if check.lower() in code.lower())
                score = passes / len(task["checks"]) if task["checks"] else 0.0
                results.append(BenchmarkResult(
                    name=task["name"],
                    success=score >= 0.5,
                    duration=duration,
                    score=score,
                    details={
                        "checks_passed": passes,
                        "checks_total": len(task["checks"]),
                        "code_length": len(code),
                    },
                ))
            except Exception as exc:
                results.append(BenchmarkResult(
                    name=task["name"],
                    success=False,
                    duration=time.perf_counter() - start,
                    score=0.0,
                    details={"error": str(exc)},
                ))
        return results

    def summarize(self, results: list[BenchmarkResult]) -> dict[str, Any]:
        if not results:
            return {"error": "No results"}
        successes = sum(1 for r in results if r.success)
        return {
            "total": len(results),
            "passed": successes,
            "failed": len(results) - successes,
            "pass_rate": successes / len(results) * 100,
            "avg_duration": sum(r.duration for r in results) / len(results),
            "avg_score": sum(r.score for r in results) / len(results),
            "category_breakdown": self._category_breakdown(results),
        }

    def _category_breakdown(self, results: list[BenchmarkResult]) -> dict[str, dict[str, float]]:
        from collections import defaultdict
        by_cat = defaultdict(list)
        for r in results:
            for task in self._tasks:
                if task["name"] == r.name:
                    by_cat[task["category"]].append(r.score)
                    break
        return {
            cat: {"avg_score": sum(scores) / len(scores), "count": len(scores)}
            for cat, scores in by_cat.items()
        }
