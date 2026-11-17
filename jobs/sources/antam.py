"""Scraping harga Logam Mulia (Antam): harga jual 1 gram & buyback.

Struktur halaman situs dapat berubah sewaktu-waktu. Parser dibuat toleran
(mencari baris '1 gr' & kata 'buyback'), dan selalu diuji dengan fixture.
Jika gagal → job menandai sumber gagal, data lama TIDAK ditimpa, admin
bisa mengisi manual.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from ..common.quality import parse_rupiah

BROWSER_UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}


class ParseError(Exception):
    pass


ONE_GRAM = re.compile(r"^\s*1(?:[.,]0+)?\s*(gr|gram|g)\b", re.I)
RP_NUMBER = re.compile(r"(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3}){2,})")


def parse_sell_1g(html: str) -> float:
    """Cari baris tabel yang diawali '1 gr' lalu ambil angka rupiah pertama di baris itu."""
    soup = BeautifulSoup(html, "html.parser")
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if cells and ONE_GRAM.match(cells[0]):
            for c in cells[1:]:
                m = RP_NUMBER.search(c)
                if m:
                    return parse_rupiah(m.group(1))
    raise ParseError("baris '1 gr' dengan harga tidak ditemukan")


def parse_buyback(html: str) -> float:
    """Cari angka rupiah terdekat setelah kata 'buyback'."""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    m = re.search(r"buy\s*back.{0,120}?" + RP_NUMBER.pattern, text, re.I | re.S)
    if not m:
        raise ParseError("harga buyback tidak ditemukan")
    return parse_rupiah(m.group(1))


def fetch_html(url: str) -> str:
    r = requests.get(url, headers=BROWSER_UA, timeout=25)
    if r.status_code != 200:
        raise ParseError(f"HTTP {r.status_code} dari {url}")
    return r.text


def fetch(source_ref: dict) -> dict:
    """Mengembalikan {'sell': float|None, 'buyback': float|None, 'errors': [...], 'observed_at': dt}."""
    out = {"sell": None, "buyback": None, "errors": [], "observed_at": datetime.now(timezone.utc)}
    try:
        out["sell"] = parse_sell_1g(fetch_html(source_ref["sell_url"]))
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"sell: {e}")
    if source_ref.get("buyback_url"):
        try:
            out["buyback"] = parse_buyback(fetch_html(source_ref["buyback_url"]))
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"buyback: {e}")
    return out
