"""Klien kecil untuk Supabase REST (PostgREST) — tanpa library tambahan.

Dipakai oleh job di server (GitHub Actions) dengan SECRET/service key,
sehingga melewati RLS. Jangan pernah memakai key ini di browser.
"""
from __future__ import annotations

import os
from typing import Any

import requests


def auth_headers(key: str) -> dict[str, str]:
    """Header autentikasi.

    - Key baru Supabase (diawali 'sb_') bukan JWT → cukup header `apikey`.
    - Key lama (JWT 'eyJ...') → `apikey` + `Authorization: Bearer`.
    """
    h = {"apikey": key}
    if not key.startswith("sb_"):
        h["Authorization"] = f"Bearer {key}"
    return h


class Supa:
    def __init__(self, url: str | None = None, key: str | None = None, timeout: int = 20):
        url = url or os.environ["SUPABASE_URL"]
        key = key or os.environ["SUPABASE_SERVICE_KEY"]
        self.base = url.rstrip("/") + "/rest/v1"
        self.h = {**auth_headers(key), "Content-Type": "application/json"}
        self.timeout = timeout

    def _req(self, method: str, table: str, params: dict | None = None, json: Any = None,
             prefer: str | None = None) -> Any:
        headers = dict(self.h)
        if prefer:
            headers["Prefer"] = prefer
        r = requests.request(method, f"{self.base}/{table}", params=params, json=json,
                             headers=headers, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"Supabase {method} {table} → {r.status_code}: {r.text[:300]}")
        return r.json() if r.text else None

    def select(self, table: str, **params) -> list[dict]:
        return self._req("GET", table, params=params) or []

    def insert(self, table: str, rows: list[dict] | dict) -> list[dict]:
        return self._req("POST", table, json=rows, prefer="return=representation") or []

    def upsert(self, table: str, rows: list[dict], on_conflict: str) -> list[dict]:
        if not rows:
            return []
        return self._req("POST", table, params={"on_conflict": on_conflict}, json=rows,
                         prefer="resolution=merge-duplicates,return=representation") or []

    def update(self, table: str, match: dict[str, Any], values: dict) -> list[dict]:
        params = {k: f"eq.{v}" for k, v in match.items()}
        return self._req("PATCH", table, params=params, json=values, prefer="return=representation") or []

    def config(self) -> dict[str, Any]:
        """Semua baris app_config sebagai dict {key: value}."""
        return {r["key"]: r["value"] for r in self.select("app_config", select="key,value")}
