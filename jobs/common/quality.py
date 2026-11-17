"""Aturan kualitas & konversi — fungsi murni (mudah diuji)."""
from __future__ import annotations

import re
from datetime import datetime, timezone

TROY_OUNCE_GRAM = 31.1034768


def spot_idr_per_gram(xau_usd_per_oz: float, usd_idr: float) -> float:
    """Harga spot emas murni per gram dalam rupiah (bukan harga toko)."""
    if xau_usd_per_oz <= 0 or usd_idr <= 0:
        raise ValueError("harga dan kurs harus > 0")
    return xau_usd_per_oz * usd_idr / TROY_OUNCE_GRAM


def hour_slot(dt: datetime) -> datetime:
    """Bulatkan ke jam (UTC) — dipakai sebagai kunci anti-duplikat."""
    return dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def jump_status(new: float, last: float | None, max_jump_pct: float) -> str:
    """'ok' atau 'needs_review' bila berubah lebih dari max_jump_pct dibanding data terakhir."""
    if new <= 0:
        raise ValueError("harga harus > 0")
    if not last:
        return "ok"
    change = abs(new / last - 1) * 100
    return "needs_review" if change > max_jump_pct else "ok"


_NUM = re.compile(r"\d[\d.,]*")


def parse_rupiah(text: str) -> float:
    """'Rp 2.480.000' / 'Rp2,480,000' / '2.480.000,00' → 2480000.0"""
    m = _NUM.search(text or "")
    if not m:
        raise ValueError(f"tidak ada angka di: {text!r}")
    s = m.group(0)
    # Buang desimal ',00' / '.00' di akhir, lalu buang semua pemisah ribuan.
    s = re.sub(r"[.,]\d{2}$", "", s) if re.search(r"[.,]\d{3}", s) else s
    s = s.replace(".", "").replace(",", "")
    value = float(s)
    if value <= 0:
        raise ValueError("angka harus > 0")
    return value
