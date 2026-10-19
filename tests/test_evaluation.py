import pytest
from src.evaluation.metrics import MetricsCollector
from src.evaluation.benchmarks import CodingBenchmark
from src.evaluation.monitor import Monitor


def test_metrics_counter():
    m = MetricsCollector()
    m.increment("test_count")
    assert m.get_counter("test_count") == 1
    m.increment("test_count")
    assert m.get_counter("test_count") == 2


def test_metrics_gauge():
    m = MetricsCollector()
    m.gauge("temperature", 36.5)
    snapshot = m.snapshot()
    assert snapshot["gauges"]["temperature"] == 36.5


def test_metrics_histogram():
    m = MetricsCollector()
    for v in [1, 2, 3, 4, 5]:
        m.observe("latency", v)
    summary = m.get_histogram_summary("latency")
    assert summary["count"] == 5
    assert summary["min"] == 1
    assert summary["max"] == 5
    assert summary["mean"] == 3.0
    assert summary["p50"] == 3


@pytest.mark.asyncio
async def test_benchmark_run_all():
    bm = CodingBenchmark()
    results = await bm.run_all(lambda prompt: f"def {prompt.split()[0].lower()}(): pass")
    assert len(results) == 5


def test_monitor_summary():
    m = Monitor()
    m.record_request()
    m.record_success()
    summary = m.summary()
    assert summary["requests"]["total"] == 1
    assert summary["requests"]["success"] == 1
