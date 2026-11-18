"""Sumber harga merek emas dari galeri24.co.id (Pegadaian).

Satu halaman berisi banyak merek (ANTAM, UBS, GALERI 24, LOTUS ARCHI, dll.)
beserta harga jual & buyback per pecahan. Dipilih karena logammulia.com
memblokir akses otomatis (403 Akamai) — lihat hasil probe Fase 1.

Catatan: "buyback" di sini = harga beli-kembali di outlet Galeri24/Pegadaian,
bisa berbeda dengan buyback butik Logam Mulia.

Strategi parsing (2 lapis):
  1. Data JSON terstruktur `__NUXT_DATA__` (stabil, ada tanggal update).
  2. Cadangan: membaca teks tabel "Harga <MEREK> / Berat / Harga Jual / Harga Buyback".
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from ..common.quality import parse_rupiah

URL = "https://galeri24.co.id/harga-emas"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

BULAN = {"januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7,
         "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12}


class ParseError(Exception):
    pass


# ---------------- Lapis 1: __NUXT_DATA__ ----------------
def _devalue(data: list):
    """Dekode format 'devalue' Nuxt: elemen 0 = root, angka = referensi indeks."""
    wrappers = {"Reactive", "ShallowReactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef"}
    seen: dict[int, object] = {}

    def rev(i):
        if not isinstance(i, int) or i < 0:
            return None
        if i in seen:
            return seen[i]
        v = data[i]
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in wrappers:
                out = rev(v[1]) if len(v) > 1 else None
            elif v and isinstance(v[0], str) and v[0] == "Date":
                out = v[1]
            else:
                out = []
                seen[i] = out
                out.extend(rev(x) for x in v)
        elif isinstance(v, dict):
            out = {}
            seen[i] = out
            out.update({k: rev(x) for k, x in v.items()})
        else:
            out = v
        seen[i] = out
        return out

    return rev(0)


def parse_json(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("script", id="__NUXT_DATA__")
    if not tag or not tag.string:
        raise ParseError("__NUXT_DATA__ tidak ditemukan")
    root = _devalue(json.loads(tag.string))
    try:
        items = root["data"]["goldPrice"]
    except (KeyError, TypeError) as e:
        raise ParseError(f"struktur data berubah: {e}") from e
    rows = []
    for it in items or []:
        try:
            rows.append({
                "vendor": str(it["vendorName"]).strip().upper(),
                "gram": float(it["denomination"]),
                "sell": float(it["sellingPrice"]),
                "buyback": float(it.get("buybackPrice") or 0),
                "updated_at": it.get("updatedAt") or it.get("date"),
            })
        except (KeyError, TypeError, ValueError):
            continue
    if not rows:
        raise ParseError("goldPrice kosong")
    return rows


# ---------------- Lapis 2: teks halaman ----------------
_UPDATED = re.compile(r"Diperbarui\s+\w+,\s*(\d{1,2})\s+(\w+)\s+(\d{4})", re.I)


def parse_text(html: str) -> list[dict]:
    lines = BeautifulSoup(html, "html.parser").get_text("\n", strip=True).split("\n")
    rows, vendor, date = [], None, None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _UPDATED.match(line)
        if m:
            d, mon, y = m.groups()
            if mon.lower() in BULAN:
                date = f"{y}-{BULAN[mon.lower()]:02d}-{int(d):02d}"
        elif line.startswith("Harga ") and i + 3 < len(lines) and lines[i + 1] == "Berat":
            vendor = line[6:].strip().upper()
            i += 4  # lewati "Berat", "Harga Jual", "Harga Buyback"
            while i + 2 < len(lines) and re.fullmatch(r"\d+(?:[.,]\d+)?", lines[i]):
                try:
                    rows.append({"vendor": vendor, "gram": float(lines[i].replace(",", ".")),
                                 "sell": parse_rupiah(lines[i + 1]),
                                 "buyback": parse_rupiah(lines[i + 2]) if re.search(r"\d", lines[i + 2]) else 0.0,
                                 "updated_at": date})
                except ValueError:
                    pass
                i += 3
            continue
        i += 1
    if not rows:
        raise ParseError("tabel harga tidak ditemukan")
    return rows


def parse(html: str) -> tuple[list[dict], str]:
    """Kembalikan (rows, metode). Coba JSON dulu, lalu teks."""
    try:
        return parse_json(html), "json"
    except ParseError:
        return parse_text(html), "text"


# ---------------- Ambil harga per gram satu merek ----------------
def per_gram(rows: list[dict], vendor: str) -> dict:
    """Harga per gram untuk merek: pakai pecahan 1 g; bila tidak ada, pecahan terkecil ≥ 1 g dibagi beratnya."""
    v = vendor.strip().upper()
    mine = [r for r in rows if r["vendor"] == v and r["sell"] > 0]
    if not mine:
        raise ParseError(f"merek '{vendor}' tidak ada di halaman")
    exact = [r for r in mine if abs(r["gram"] - 1) < 1e-9]
    pick = exact[0] if exact else min((r for r in mine if r["gram"] >= 1), key=lambda r: r["gram"], default=None)
    if pick is None:
        raise ParseError(f"merek '{vendor}' tidak punya pecahan ≥ 1 g")
    g = pick["gram"]
    return {"sell": pick["sell"] / g, "buyback": (pick["buyback"] / g) if pick["buyback"] > 0 else None,
            "denomination": g, "updated_at": pick["updated_at"]}


def observed_at(value: str | None) -> datetime:
    if value:
        try:
            if len(value) == 10:
                return datetime.fromisoformat(value + "T00:00:00+07:00").astimezone(timezone.utc)
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def fetch_html(url: str = URL) -> str:
    r = requests.get(url, headers=UA, timeout=25)
    if r.status_code != 200:
        raise ParseError(f"HTTP {r.status_code} dari {url}")
    return r.text
