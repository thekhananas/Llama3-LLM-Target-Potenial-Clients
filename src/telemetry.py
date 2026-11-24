"""Latency instrumentation and structured JSONL run logging for LlamaMail."""

from __future__ import annotations

import json
import math
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DEFAULT_RUN_LOG_PATH = Path("benchmarks/run_logs.jsonl")


class PipelineTimer:
    """Tracks per-stage and total wall-clock latencies in milliseconds."""

    def __init__(self) -> None:
        self._start = time.perf_counter()
        self.stages_ms: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        """Time a named pipeline stage and record elapsed milliseconds."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.stages_ms[name] = round(elapsed_ms, 2)

    def total_ms(self) -> float:
        """Return total elapsed wall-clock milliseconds since timer creation."""
        return round((time.perf_counter() - self._start) * 1000.0, 2)


def append_run_log(record: dict[str, Any], log_path: str | Path = DEFAULT_RUN_LOG_PATH) -> Path:
    """Append one structured telemetry record as JSONL."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def build_run_record(
    *,
    source_type: str,
    llm_model: str,
    embedding_model: str,
    corpus_docs: int,
    corpus_chunks: int,
    timings_ms: dict[str, float],
    retrieved_doc_ids: list[str],
    retrieved_links: list[str],
    status: str,
    extracted_skills: list[str] | None = None,
    error: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a standardized telemetry dictionary for a pipeline run."""
    return {
        "run_id": run_id or str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_type": source_type,
        "llm_model": llm_model,
        "embedding_model": embedding_model,
        "corpus_docs": corpus_docs,
        "corpus_chunks": corpus_chunks,
        "timings_ms": timings_ms,
        "extracted_skills": extracted_skills or [],
        "retrieved_doc_ids": retrieved_doc_ids,
        "retrieved_links": retrieved_links,
        "error": error,
    }


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute linear-interpolated percentile on a non-empty sorted list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return round(sorted_values[0], 2)
    idx = (len(sorted_values) - 1) * (pct / 100.0)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return round(sorted_values[lo], 2)
    frac = idx - lo
    val = sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])
    return round(val, 2)


def summarize_latencies(values_ms: list[float]) -> dict[str, float]:
    """Compute count, mean, min, p50, p95, and max for latency samples (ms)."""
    if not values_ms:
        return {"count": 0, "mean_ms": 0.0, "min_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    ordered = sorted(float(v) for v in values_ms)
    mean_val = sum(ordered) / len(ordered)
    return {
        "count": len(ordered),
        "mean_ms": round(mean_val, 2),
        "min_ms": round(ordered[0], 2),
        "p50_ms": _percentile(ordered, 50.0),
        "p95_ms": _percentile(ordered, 95.0),
        "max_ms": round(ordered[-1], 2),
    }
