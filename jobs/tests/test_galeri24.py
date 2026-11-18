"""Uji parser Galeri24 dengan halaman ASLI (diambil probe GitHub, 17 Nov 2026)."""
import pathlib

import pytest

from jobs.sources import galeri24 as g

HTML = (pathlib.Path(__file__).parent / "fixtures" / "galeri24.html").read_text(encoding="utf-8")


def test_json_layer_reads_many_rows():
    rows = g.parse_json(HTML)
    assert len(rows) > 50
    assert {"ANTAM", "UBS", "GALERI 24"} <= {r["vendor"] for r in rows}


def test_antam_1g_from_json():
    p = g.per_gram(g.parse_json(HTML), "ANTAM")
    assert p["sell"] == 2_553_000 and p["buyback"] == 2_281_000 and p["denomination"] == 1


def test_text_fallback_matches_json():
    """Lapis cadangan harus memberi angka yang sama dengan lapis JSON."""
    a = g.per_gram(g.parse_json(HTML), "ANTAM")
    b = g.per_gram(g.parse_text(HTML), "ANTAM")
    assert (a["sell"], a["buyback"]) == (b["sell"], b["buyback"])


@pytest.mark.parametrize("vendor", ["ANTAM", "UBS", "GALERI 24", "LOTUS ARCHI"])
def test_main_brands_sane(vendor):
    p = g.per_gram(g.parse(HTML)[0], vendor)
    assert 1_500_000 < p["sell"] < 5_000_000
    assert p["buyback"] is None or p["buyback"] < p["sell"]


def test_text_fallback_used_when_json_missing():
    html = HTML.replace('id="__NUXT_DATA__"', 'id="x"')
    rows, method = g.parse(html)
    assert method == "text" and g.per_gram(rows, "antam")["sell"] == 2_553_000


def test_unknown_vendor_raises():
    with pytest.raises(g.ParseError):
        g.per_gram(g.parse(HTML)[0], "MEREK TIDAK ADA")


def test_observed_at_date_only_is_wib_midnight():
    assert g.observed_at("2026-11-17").isoformat() == "2026-11-16T17:00:00+00:00"
