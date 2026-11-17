"""Uji parser Antam dengan HTML contoh.

Setelah probe (lihat panduan Fase 1, langkah I) berhasil, salin HTML asli ke
jobs/tests/fixtures/antam_sell.html & antam_buyback.html — tes di bawah
otomatis ikut memakainya.
"""
import pathlib

import pytest

from jobs.sources.antam import ParseError, parse_buyback, parse_sell_1g

FIX = pathlib.Path(__file__).parent / "fixtures"

SAMPLE_SELL = """
<table><tr><th>Berat</th><th>Harga Dasar</th><th>Harga (+Pajak PPh 0.25%)</th></tr>
<tr><td>0.5 gr</td><td>Rp1,290,000</td><td>Rp1,293,225</td></tr>
<tr><td>1 gr</td><td>Rp2,480,000</td><td>Rp2,486,200</td></tr>
<tr><td>2 gr</td><td>Rp4,900,000</td><td>Rp4,912,250</td></tr></table>"""

SAMPLE_BUYBACK = "<div><h3>Harga Buyback</h3><p>Rp 2.320.000</p><small>per gram</small></div>"


def test_sell_sample():
    assert parse_sell_1g(SAMPLE_SELL) == 2_480_000


def test_sell_ignores_half_gram_row():
    assert parse_sell_1g(SAMPLE_SELL) != 1_290_000


def test_buyback_sample():
    assert parse_buyback(SAMPLE_BUYBACK) == 2_320_000


def test_sell_missing_raises():
    with pytest.raises(ParseError):
        parse_sell_1g("<table><tr><td>5 gr</td><td>Rp1</td></tr></table>")


@pytest.mark.skipif(not (FIX / "antam_sell.html").exists(), reason="fixture asli belum ada")
def test_real_sell_page():
    assert 500_000 < parse_sell_1g((FIX / "antam_sell.html").read_text(encoding="utf-8")) < 20_000_000


@pytest.mark.skipif(not (FIX / "antam_buyback.html").exists(), reason="fixture asli belum ada")
def test_real_buyback_page():
    assert 500_000 < parse_buyback((FIX / "antam_buyback.html").read_text(encoding="utf-8")) < 20_000_000
