#!/usr/bin/env python3
"""Run a small concurrent health/readiness smoke against an Agent API instance."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RequestResult:
    elapsed_ms: float
    status: int | None
    error: str | None


def parse_base_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("base URL must be an absolute http(s) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise argparse.ArgumentTypeError(
            "base URL cannot include credentials, a query, or a fragment"
        )
    if parsed.path not in {"", "/"}:
        raise argparse.ArgumentTypeError("base URL must not include a path")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def parse_paths(value: str) -> list[str]:
    paths = [item.strip() for item in value.split(",") if item.strip()]
    if not paths:
        raise argparse.ArgumentTypeError("provide at least one path")
    for path in paths:
        parsed = urlsplit(path)
        if (
            not path.startswith("/")
            or path.startswith("//")
            or parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise argparse.ArgumentTypeError(
                "paths must be comma-separated absolute paths without query or fragment"
            )
    return paths


def percentile_nearest_rank(samples: Sequence[float], percentile: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def make_request(url: str, timeout_seconds: float) -> RequestResult:
    started = time.perf_counter()
    try:
        request = Request(url, method="GET", headers={"User-Agent": "crista-load-smoke/1"})
        with urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
        error = None if status == 200 else f"unexpected HTTP {status}"
    except HTTPError as exc:
        status = exc.code
        error = f"HTTP {exc.code}"
    except (TimeoutError, URLError, OSError) as exc:
        status = None
        error = type(exc).__name__
    elapsed_ms = (time.perf_counter() - started) * 1000
    return RequestResult(elapsed_ms=elapsed_ms, status=status, error=error)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", type=parse_base_url, help="API origin, e.g. https://api.example.test")
    parser.add_argument("--requests", type=int, default=50, help="total requests to send (default: 50)")
    parser.add_argument("--concurrency", type=int, default=5, help="parallel requests (default: 5)")
    parser.add_argument("--timeout-seconds", type=float, default=10.0, help="per-request timeout (default: 10)")
    parser.add_argument("--paths", type=parse_paths, default=["/health", "/ready"], help="comma-separated paths")
    parser.add_argument("--max-p95-ms", type=float, help="fail if p95 latency exceeds this value")
    parser.add_argument(
        "--max-error-rate",
        type=float,
        help="allowed failed-request fraction from 0 through 1; omitted means zero failures allowed",
    )
    args = parser.parse_args()
    if args.requests < 1:
        parser.error("--requests must be at least 1")
    if not 1 <= args.concurrency <= args.requests:
        parser.error("--concurrency must be between 1 and --requests")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    if args.max_p95_ms is not None and args.max_p95_ms <= 0:
        parser.error("--max-p95-ms must be positive")
    if args.max_error_rate is not None and not 0 <= args.max_error_rate <= 1:
        parser.error("--max-error-rate must be from 0 through 1")
    return args


def main() -> int:
    args = parse_args()
    urls = [f"{args.base_url}{args.paths[index % len(args.paths)]}" for index in range(args.requests)]
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(lambda url: make_request(url, args.timeout_seconds), urls))
    wall_clock_ms = (time.perf_counter() - started) * 1000

    successful = [result for result in results if result.error is None]
    latencies = [result.elapsed_ms for result in results]
    errors = len(results) - len(successful)
    error_rate = errors / len(results)
    p95_ms = percentile_nearest_rank(latencies, 0.95)
    status_counts = Counter(str(result.status) if result.status is not None else "network_error" for result in results)

    summary = {
        "base_url": args.base_url,
        "paths": args.paths,
        "request_count": len(results),
        "concurrency": args.concurrency,
        "success_count": len(successful),
        "error_count": errors,
        "error_rate": round(error_rate, 6),
        "latency_ms": {
            "min": round(min(latencies), 3),
            "p50": round(statistics.median(latencies), 3),
            "p95": round(p95_ms, 3) if p95_ms is not None else None,
            "max": round(max(latencies), 3),
        },
        "wall_clock_ms": round(wall_clock_ms, 3),
        "status_counts": dict(sorted(status_counts.items())),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    allowed_error_rate = args.max_error_rate if args.max_error_rate is not None else 0.0
    failures = []
    if error_rate > allowed_error_rate:
        failures.append(f"error rate {error_rate:.4f} exceeds {allowed_error_rate:.4f}")
    if args.max_p95_ms is not None and p95_ms is not None and p95_ms > args.max_p95_ms:
        failures.append(f"p95 {p95_ms:.3f}ms exceeds {args.max_p95_ms:.3f}ms")
    if failures:
        print("load smoke failed: " + "; ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
