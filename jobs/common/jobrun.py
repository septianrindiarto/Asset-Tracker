"""Pencatatan job ke tabel job_runs (dipantau watchdog)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .supa import Supa


class JobRun:
    def __init__(self, db: Supa | None, job: str, trigger: str, dry_run: bool = False):
        self.db, self.job, self.trigger, self.dry = db, job, trigger, dry_run
        self.id = None
        self.rows = 0
        self.detail: dict = {}

    def start(self) -> "JobRun":
        if not self.dry:
            row = self.db.insert("job_runs", {"job": self.job, "trigger": self.trigger})[0]
            self.id = row["id"]
        print(f"[job] {self.job} mulai (trigger={self.trigger}, id={self.id})")
        return self

    def finish(self, status: str) -> None:
        print(f"[job] {self.job} selesai: {status}, rows={self.rows}, detail={self.detail}")
        if not self.dry and self.id:
            self.db.update("job_runs", {"id": self.id}, {
                "status": status, "rows_written": self.rows, "detail": self.detail,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })

    def recent_success(self, minutes: int) -> bool:
        """True bila job yang sama sukses dalam N menit terakhir (cegah dobel jalan)."""
        if self.dry:
            return False
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        rows = self.db.select("job_runs", select="id", job=f"eq.{self.job}",
                              status="in.(success,partial)", finished_at=f"gte.{since}", limit=1)
        return bool(rows)
