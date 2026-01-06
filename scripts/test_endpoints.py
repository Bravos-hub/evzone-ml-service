#!/usr/bin/env python3
"""Test EVzone ML Service endpoints and print a tabular report."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import httpx
from tabulate import tabulate

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - defensive fallback
    load_dotenv = None


def _load_env() -> None:
    if load_dotenv:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()


def _default_base_url() -> str:
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8000")
    if host in {"0.0.0.0", "127.0.0.1"}:
        host = "localhost"
    return f"http://{host}:{port}"


def _iso_timestamp(days_ago: int) -> str:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return ts.isoformat().replace("+00:00", "Z")


def _build_metrics(
    charger_id: str,
    connector_status: str,
    temperature: float,
    error_codes: Sequence[str],
    uptime_hours: float,
    total_sessions: int,
) -> Dict[str, Any]:
    return {
        "charger_id": charger_id,
        "connector_status": connector_status,
        "energy_delivered": 42.5,
        "power": 7.2,
        "temperature": temperature,
        "error_codes": list(error_codes),
        "uptime_hours": uptime_hours,
        "total_sessions": total_sessions,
        "last_maintenance": _iso_timestamp(days_ago=120),
        "metadata": {"source": "endpoint-test"},
    }


def _check_service_up(base_url: str, timeout: float) -> bool:
    try:
        response = httpx.get(f"{base_url}/health", timeout=timeout)
        if response.status_code == 200:
            return True
    except httpx.RequestError:
        pass

    try:
        response = httpx.get(f"{base_url}/", timeout=timeout)
        return response.status_code == 200
    except httpx.RequestError:
        return False


def _expected_to_list(expected: Any) -> List[int]:
    if isinstance(expected, (list, tuple, set)):
        return list(expected)
    return [int(expected)]


def _run_test(
    client: httpx.Client,
    test: Dict[str, Any],
    api_key: str,
    tenant_id: Optional[str],
) -> Dict[str, Any]:
    headers: Dict[str, str] = {}
    auth_mode = test.get("auth", "valid")
    if auth_mode == "valid":
        headers["X-API-Key"] = api_key
    elif auth_mode == "invalid":
        headers["X-API-Key"] = f"{api_key}-invalid"
    elif auth_mode == "missing":
        pass

    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    method = test["method"].upper()
    path = test["path"]
    payload = test.get("json")
    expected_statuses = _expected_to_list(test["expected_status"])

    start = time.perf_counter()
    status_code: Optional[int] = None
    error: Optional[str] = None
    try:
        response = client.request(method, path, headers=headers, json=payload)
        status_code = response.status_code
        ok = status_code in expected_statuses
        if not ok:
            error = response.text.strip()[:300]
    except httpx.RequestError as exc:
        ok = False
        error = str(exc)
    latency_ms = (time.perf_counter() - start) * 1000.0

    return {
        "name": test["name"],
        "method": method,
        "path": path,
        "category": test["category"],
        "expected_status": expected_statuses,
        "status_code": status_code,
        "ok": ok,
        "latency_ms": round(latency_ms, 2),
        "error": error,
    }


def _summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    fastest = min(results, key=lambda r: r["latency_ms"]) if results else None
    slowest = max(results, key=lambda r: r["latency_ms"]) if results else None

    categories: Dict[str, Dict[str, Any]] = {}
    for r in results:
        cat = r["category"]
        stats = categories.setdefault(cat, {"total": 0, "passed": 0, "failed": 0, "latencies": []})
        stats["total"] += 1
        stats["passed"] += 1 if r["ok"] else 0
        stats["failed"] += 0 if r["ok"] else 1
        stats["latencies"].append(r["latency_ms"])

    category_rows = []
    for cat, stats in categories.items():
        cat_avg = sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0.0
        category_rows.append(
            {
                "category": cat,
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "avg_latency_ms": round(cat_avg, 2),
            }
        )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "success_rate": round((passed / total * 100.0) if total else 0.0, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "fastest": {
            "name": fastest["name"],
            "path": fastest["path"],
            "latency_ms": fastest["latency_ms"],
        } if fastest else None,
        "slowest": {
            "name": slowest["name"],
            "path": slowest["path"],
            "latency_ms": slowest["latency_ms"],
        } if slowest else None,
        "categories": category_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test EVzone ML Service endpoints.")
    parser.add_argument("--base-url", default=None, help="Base URL for the service.")
    parser.add_argument("--api-key", default=None, help="API key for authenticated endpoints.")
    parser.add_argument("--tenant-id", default=None, help="Optional tenant ID header value.")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds.")
    parser.add_argument("--json-out", default=None, help="Optional JSON report path.")
    args = parser.parse_args()

    _load_env()

    base_url = (args.base_url or _default_base_url()).rstrip("/")
    api_key = args.api_key or os.getenv("API_KEY")

    if not _check_service_up(base_url, args.timeout):
        print(f"Service not reachable at {base_url}. Start the service before testing.")
        return 1

    if not api_key:
        print("API key not found. Set API_KEY in .env or pass --api-key.")
        return 1

    chg_1 = "CHG_TEST_001"
    chg_2 = "CHG_TEST_002"

    metrics_1 = _build_metrics(
        charger_id=chg_1,
        connector_status="CHARGING",
        temperature=58.0,
        error_codes=["E_OVER_TEMP"],
        uptime_hours=2400.0,
        total_sessions=520,
    )
    metrics_2 = _build_metrics(
        charger_id=chg_2,
        connector_status="AVAILABLE",
        temperature=32.0,
        error_codes=[],
        uptime_hours=1100.0,
        total_sessions=240,
    )

    tests: List[Dict[str, Any]] = [
        {
            "name": "Root",
            "method": "GET",
            "path": "/",
            "category": "root",
            "auth": "none",
            "expected_status": 200,
        },
        {
            "name": "Health",
            "method": "GET",
            "path": "/health",
            "category": "health",
            "auth": "none",
            "expected_status": 200,
        },
        {
            "name": "Health (detailed)",
            "method": "GET",
            "path": "/api/v1/health",
            "category": "health",
            "auth": "none",
            "expected_status": 200,
        },
        {
            "name": "Models (list)",
            "method": "GET",
            "path": "/api/v1/models",
            "category": "models",
            "auth": "valid",
            "expected_status": 200,
        },
        {
            "name": "Models (reload)",
            "method": "POST",
            "path": "/api/v1/models/reload",
            "category": "models",
            "auth": "valid",
            "expected_status": 200,
        },
        {
            "name": "Prediction (failure)",
            "method": "POST",
            "path": "/api/v1/predictions/failure",
            "category": "predictions",
            "auth": "valid",
            "expected_status": 200,
            "json": {"charger_id": chg_1, "metrics": metrics_1},
        },
        {
            "name": "Prediction (maintenance)",
            "method": "POST",
            "path": "/api/v1/predictions/maintenance",
            "category": "predictions",
            "auth": "valid",
            "expected_status": 200,
            "json": {"charger_id": chg_1, "metrics": metrics_1},
        },
        {
            "name": "Prediction (anomaly)",
            "method": "POST",
            "path": "/api/v1/predictions/anomaly",
            "category": "predictions",
            "auth": "valid",
            "expected_status": 200,
            "json": {"charger_id": chg_2, "metrics": metrics_2},
        },
        {
            "name": "Prediction (batch)",
            "method": "POST",
            "path": "/api/v1/predictions/batch",
            "category": "predictions",
            "auth": "valid",
            "expected_status": 200,
            "json": {"chargers": [metrics_1, metrics_2]},
        },
        {
            "name": "Prediction (cached)",
            "method": "GET",
            "path": f"/api/v1/predictions/{chg_1}",
            "category": "predictions",
            "auth": "valid",
            "expected_status": 200,
        },
        {
            "name": "Auth (invalid key)",
            "method": "GET",
            "path": "/api/v1/models",
            "category": "auth",
            "auth": "invalid",
            "expected_status": 401,
        },
        {
            "name": "Auth (missing key)",
            "method": "GET",
            "path": "/api/v1/models",
            "category": "auth",
            "auth": "missing",
            "expected_status": 422,
        },
    ]

    results: List[Dict[str, Any]] = []
    with httpx.Client(base_url=base_url, timeout=args.timeout) as client:
        for test in tests:
            results.append(_run_test(client, test, api_key, args.tenant_id))

    summary = _summarize(results)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    report_path = Path(args.json_out) if args.json_out else Path("reports") / f"endpoint_report_{timestamp}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "base_url": base_url,
        "summary": summary,
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    table_rows = []
    for idx, r in enumerate(results, start=1):
        table_rows.append([
            idx,
            r["name"],
            r["method"],
            r["path"],
            r["category"],
            ",".join(str(s) for s in r["expected_status"]),
            r["status_code"] if r["status_code"] is not None else "-",
            "PASS" if r["ok"] else "FAIL",
            f"{r['latency_ms']:.2f}",
        ])

    print(f"Endpoint Test Report ({base_url})")
    print(tabulate(
        table_rows,
        headers=["#", "Endpoint", "Method", "Path", "Category", "Expected", "HTTP", "Status", "Latency (ms)"],
        tablefmt="github",
    ))
    print()
    print(
        f"Summary: total={summary['total']} passed={summary['passed']} failed={summary['failed']} "
        f"success_rate={summary['success_rate']}% avg_latency={summary['avg_latency_ms']}ms"
    )
    if summary["fastest"] and summary["slowest"]:
        print(
            "Performance: "
            f"fastest={summary['fastest']['name']} ({summary['fastest']['latency_ms']}ms), "
            f"slowest={summary['slowest']['name']} ({summary['slowest']['latency_ms']}ms), "
            f"average={summary['avg_latency_ms']}ms"
        )

    category_rows = [
        [c["category"], c["total"], c["passed"], c["failed"], f"{c['avg_latency_ms']:.2f}"]
        for c in summary["categories"]
    ]
    print()
    print("Category Breakdown")
    print(tabulate(
        category_rows,
        headers=["Category", "Total", "Passed", "Failed", "Avg Latency (ms)"],
        tablefmt="github",
    ))

    failures = [r for r in results if not r["ok"]]
    if failures:
        print()
        print("Failures")
        for r in failures:
            detail = f"expected {r['expected_status']} got {r['status_code']}"
            if r["error"]:
                detail = f"{detail} - {r['error']}"
            print(f"- {r['name']} ({r['method']} {r['path']}): {detail}")

    print()
    print(f"JSON report saved to {report_path}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
