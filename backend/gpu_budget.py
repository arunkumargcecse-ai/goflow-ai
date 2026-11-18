"""Conservative monthly spend guard for remote ComfyUI GPU submissions.

This records an estimated maximum-runtime reservation per accepted job. It is
not a cloud-provider billing integration and cannot stop a provider instance.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _db_path() -> Path:
    return Path(os.getenv("GOFLOW_DATA_DIR", Path(__file__).parent / "data")).resolve() / "goflow.sqlite3"


def _remote_worker() -> bool:
    url = os.getenv("GOFLOW_COMFYUI_URL", "http://127.0.0.1:8188").lower()
    return not any(host in url for host in ("127.0.0.1", "localhost", "[::1]"))


def _config() -> tuple[float, float, float]:
    cap = float(os.getenv("GOFLOW_GPU_MONTHLY_BUDGET_INR", "1000"))
    hourly = float(os.getenv("GOFLOW_GPU_HOURLY_RATE_INR", "0"))
    minutes = float(os.getenv("GOFLOW_GPU_JOB_MAX_MINUTES", "20"))
    if cap <= 0 or hourly < 0 or minutes <= 0:
        raise ValueError("GPU budget must be positive; hourly rate cannot be negative; job minutes must be positive.")
    return cap, hourly, minutes


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS gpu_budget_reservations (
            id TEXT PRIMARY KEY,
            month TEXT NOT NULL,
            estimated_inr REAL NOT NULL,
            hourly_rate_inr REAL NOT NULL,
            max_runtime_minutes REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db.commit()
    return db


def budget_status() -> dict:
    cap, hourly, minutes = _config()
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    with _connect() as db:
        row = db.execute(
            "SELECT COALESCE(SUM(estimated_inr), 0) AS used, COUNT(*) AS jobs "
            "FROM gpu_budget_reservations WHERE month = ?", (month,)
        ).fetchone()
    used = float(row["used"])
    return {
        "currency": "INR",
        "month_utc": month,
        "monthly_cap_inr": round(cap, 2),
        "estimated_reserved_inr": round(used, 2),
        "remaining_inr": round(max(0.0, cap - used), 2),
        "estimated_jobs_reserved": int(row["jobs"]),
        "configured_hourly_rate_inr": round(hourly, 2),
        "max_runtime_minutes_per_job": round(minutes, 2),
        "remote_worker": _remote_worker(),
        "accounting": "estimated maximum-runtime reservations; verify actual provider invoices",
    }


def reserve_remote_job(job_id: str) -> dict:
    """Reserve one job's worst-case configured compute estimate or fail closed."""
    if not _remote_worker():
        return {"remote_worker": False, "estimated_cost_inr": 0.0, "budget_enforced": False}
    cap, hourly, minutes = _config()
    if hourly <= 0:
        raise RuntimeError(
            "Remote GPU submissions are blocked: set GOFLOW_GPU_HOURLY_RATE_INR to the worker's INR/hour rate."
        )
    estimate = round(hourly * minutes / 60.0, 2)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT COALESCE(SUM(estimated_inr), 0) AS used FROM gpu_budget_reservations WHERE month = ?",
            (month,),
        ).fetchone()
        used = float(row["used"])
        if used + estimate > cap + 1e-9:
            db.rollback()
            raise RuntimeError(
                f"Remote GPU budget limit reached: this job reserves ₹{estimate:.2f}, "
                f"but only ₹{max(0.0, cap-used):.2f} remains in the ₹{cap:.2f} monthly cap."
            )
        db.execute(
            "INSERT INTO gpu_budget_reservations "
            "(id, month, estimated_inr, hourly_rate_inr, max_runtime_minutes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, month, estimate, hourly, minutes, now),
        )
        db.commit()
    return {
        "remote_worker": True,
        "estimated_cost_inr": estimate,
        "budget_enforced": True,
        "monthly_cap_inr": round(cap, 2),
        "max_runtime_minutes": round(minutes, 2),
        "note": "Worst-case estimate reserved; actual provider billing may differ.",
    }
