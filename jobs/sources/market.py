"""Sumber harga emas dunia (XAU/USD) dan kurs USD/IDR.

Setiap fungsi mencoba beberapa penyedia berurutan (fallback).
Mengembalikan dict: {"price": float, "observed_at": datetime, "source": str}
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

UA = {"User-Agent": "GoldTracker/0.1 (+personal, non-commercial)"}


class SourceError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _yf_last(ticker: str) -> tuple[float, datetime]:
    import yfinance as yf  # impor saat dibutuhkan (berat)
    hist = yf.Ticker(ticker).history(period="5d", interval="1h")
    if hist.empty:
        raise SourceError(f"yfinance {ticker}: data kosong")
    ts = hist.index[-1].to_pydatetime().astimezone(timezone.utc)
    return float(hist["Close"].iloc[-1]), ts


# ---------------- XAU/USD ----------------
def xau_metalcharts() -> dict:
    key = os.getenv("METALCHARTS_API_KEY")
    if not key:
        raise SourceError("METALCHARTS_API_KEY belum diisi")
    r = requests.get("https://api.metalcharts.org/v1/prices",
                     headers={**UA, "Authorization": f"Bearer {key}"}, timeout=15)
    r.raise_for_status()
    price = float(r.json()["data"]["XAU"]["price"])
    return {"price": price, "observed_at": _now(), "source": "metalcharts"}


def xau_yfinance() -> dict:
    # GC=F = kontrak berjangka emas COMEX → proksi harga spot (selisih kecil).
    price, ts = _yf_last("GC=F")
    return {"price": price, "observed_at": ts, "source": "yfinance:GC=F"}


# ---------------- USD/IDR ----------------
def fx_open_er() -> dict:
    r = requests.get("https://open.er-api.com/v6/latest/USD", headers=UA, timeout=15)
    r.raise_for_status()
    j = r.json()
    if j.get("result") != "success":
        raise SourceError(f"open.er-api: {j.get('error-type')}")
    ts = datetime.fromtimestamp(int(j["time_last_update_unix"]), tz=timezone.utc)
    return {"price": float(j["rates"]["IDR"]), "observed_at": ts, "source": "open.er-api"}


def fx_yfinance() -> dict:
    price, ts = _yf_last("IDR=X")
    return {"price": price, "observed_at": ts, "source": "yfinance:IDR=X"}


def first_ok(*providers) -> tuple[dict, list[str]]:
    """Jalankan penyedia berurutan; kembalikan hasil pertama yang berhasil + daftar error."""
    errors = []
    for fn in providers:
        try:
            res = fn()
            if res["price"] <= 0:
                raise SourceError("harga <= 0")
            return res, errors
        except Exception as e:  # noqa: BLE001 — catat semua lalu coba berikutnya
            errors.append(f"{fn.__name__}: {e}")
    raise SourceError("; ".join(errors))


def fetch_xau() -> tuple[dict, list[str]]:
    return first_ok(xau_metalcharts, xau_yfinance)


def fetch_fx() -> tuple[dict, list[str]]:
    return first_ok(fx_open_er, fx_yfinance)
