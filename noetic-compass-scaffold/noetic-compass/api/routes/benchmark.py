"""POST /benchmark — multi-provider statistical comparison."""

from __future__ import annotations

import asyncio
import statistics
import time

from fastapi import APIRouter

from api.llm_connectors.registry import get_connector
from api.models import (
    BenchmarkRequest,
    BenchmarkResponse,
    ProviderBenchmarkResult,
)
from api.pipeline.runner import WrapPipelineRunner

router = APIRouter()

VARIANCE_THRESHOLD = 5.0


@router.post("/benchmark", response_model=BenchmarkResponse)
async def benchmark(req: BenchmarkRequest) -> BenchmarkResponse:
    """Run each provider N times on the same prompt and compute statistics."""
    semaphore = asyncio.Semaphore(req.max_concurrency)
    results: list[ProviderBenchmarkResult] = []

    for provider in req.providers:
        try:
            connector = get_connector(provider)
        except Exception:
            # Provider unavailable (missing API key, unknown name, etc.)
            results.append(
                ProviderBenchmarkResult(
                    provider=provider,
                    scores=[],
                    mean=0.0,
                    std_dev=0.0,
                    min=0.0,
                    max=0.0,
                    certification_counts={},
                    high_variance=False,
                    failed_runs=req.runs_per_provider,
                    avg_latency_ms=0.0,
                )
            )
            continue

        runner = WrapPipelineRunner(connector=connector, dial_config=req.dial_config)
        scores: list[float] = []
        certs: list[str] = []
        latencies: list[float] = []
        failed = 0

        async def run_once() -> None:
            nonlocal failed
            async with semaphore:
                try:
                    start = time.monotonic()
                    result = await runner.run(req.text)
                    elapsed = (time.monotonic() - start) * 1000
                    scores.append(result.nccs.composite)
                    certs.append(result.nccs.certification)
                    latencies.append(
                        result.provenance.get("elapsed_ms", elapsed)
                    )
                except Exception:
                    failed += 1

        tasks = [run_once() for _ in range(req.runs_per_provider)]
        await asyncio.gather(*tasks)

        if scores:
            mean = statistics.mean(scores)
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
            cert_counts: dict[str, int] = {}
            for c in certs:
                cert_counts[c] = cert_counts.get(c, 0) + 1
            results.append(
                ProviderBenchmarkResult(
                    provider=provider,
                    scores=scores,
                    mean=round(mean, 2),
                    std_dev=round(std_dev, 2),
                    min=round(min(scores), 2),
                    max=round(max(scores), 2),
                    certification_counts=cert_counts,
                    high_variance=std_dev > VARIANCE_THRESHOLD,
                    failed_runs=failed,
                    avg_latency_ms=round(statistics.mean(latencies), 1),
                )
            )
        else:
            results.append(
                ProviderBenchmarkResult(
                    provider=provider,
                    scores=[],
                    mean=0.0,
                    std_dev=0.0,
                    min=0.0,
                    max=0.0,
                    certification_counts={},
                    high_variance=False,
                    failed_runs=req.runs_per_provider,
                    avg_latency_ms=0.0,
                )
            )

    return BenchmarkResponse(
        results=results,
        prompt_preview=req.text[:200],
        runs_per_provider=req.runs_per_provider,
        total_runs=len(req.providers) * req.runs_per_provider,
        variance_threshold=VARIANCE_THRESHOLD,
    )
