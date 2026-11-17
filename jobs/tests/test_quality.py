from datetime import datetime, timedelta, timezone

import pytest

from jobs.common.quality import hour_slot, jump_status, parse_rupiah, spot_idr_per_gram
from jobs.common.supa import auth_headers


def test_spot_conversion():
    # 1 troy oz = 31.1034768 g → harga per gram = xau * kurs / 31.1034768
    assert spot_idr_per_gram(3110.34768, 10_000) == pytest.approx(1_000_000)


def test_spot_rejects_zero():
    with pytest.raises(ValueError):
        spot_idr_per_gram(0, 16000)


def test_hour_slot_same_hour_same_key():
    a = datetime(2026, 10, 31, 2, 15, tzinfo=timezone.utc)
    b = a + timedelta(minutes=25)  # jadwal cadangan :40
    assert hour_slot(a) == hour_slot(b)


def test_hour_slot_converts_wib_to_utc():
    wib = timezone(timedelta(hours=7))
    assert hour_slot(datetime(2026, 10, 31, 9, 15, tzinfo=wib)).hour == 2


@pytest.mark.parametrize("new,last,expected", [
    (100, None, "ok"), (104, 100, "ok"), (106, 100, "needs_review"), (94, 100, "needs_review"),
])
def test_jump_status(new, last, expected):
    assert jump_status(new, last, 5) == expected


@pytest.mark.parametrize("text,value", [
    ("Rp 2.480.000", 2480000), ("Rp2,480,000", 2480000), ("2.480.000,00", 2480000),
    ("Harga: Rp. 1.234.567", 1234567),
])
def test_parse_rupiah(text, value):
    assert parse_rupiah(text) == value


def test_auth_headers_new_key_has_no_bearer():
    assert "Authorization" not in auth_headers("sb_secret_abc")


def test_auth_headers_legacy_jwt_has_bearer():
    assert auth_headers("eyJhbGciOi.x.y")["Authorization"].startswith("Bearer ")
