"""Alat bantu: cek apakah sebuah situs bisa diambil & seperti apa isinya.

Dipakai di Fase 1 untuk memastikan parser Antam cocok dengan halaman asli.
  python -m jobs.probe_source --name antam_sell --url https://www.logammulia.com/id/harga-emas-hari-ini
Hasil: file probe_out/<name>.html + ringkasan di layar (status, ukuran, hasil parser).
"""
from __future__ import annotations

import argparse
import pathlib
import re

import requests

from .sources.antam import BROWSER_UA, parse_buyback, parse_sell_1g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--name", default="probe")
    a = ap.parse_args()

    out = pathlib.Path("probe_out")
    out.mkdir(exist_ok=True)
    try:
        r = requests.get(a.url, headers=BROWSER_UA, timeout=25)
    except requests.RequestException as e:
        print(f"GAGAL KONEKSI: {e}")
        return
    path = out / f"{a.name}.html"
    path.write_text(r.text, encoding="utf-8")
    print(f"Status HTTP : {r.status_code}")
    print(f"Ukuran      : {len(r.text):,} karakter → {path}")
    print(f"Server      : {r.headers.get('server')}  |  cf-ray: {r.headers.get('cf-ray')}")
    lines = [l.strip() for l in re.sub(r"<[^>]+>", "\n", r.text).splitlines() if re.search(r"\b1\s*gr|buy\s*back", l, re.I)]
    print("Baris relevan (maks 10):")
    for l in lines[:10]:
        print("   ", l[:120])
    for label, fn in (("parse_sell_1g", parse_sell_1g), ("parse_buyback", parse_buyback)):
        try:
            print(f"{label:14}: Rp {fn(r.text):,.0f}")
        except Exception as e:  # noqa: BLE001
            print(f"{label:14}: GAGAL — {e}")


if __name__ == "__main__":
    main()
