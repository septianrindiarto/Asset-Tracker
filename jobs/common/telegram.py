"""Kirim pesan Telegram via Bot API (gratis)."""
from __future__ import annotations

import os

import requests


def send(text: str, chat_id: str | int | None = None, token: str | None = None) -> bool:
    token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    if not token or not chat_id:
        print("[telegram] dilewati: TELEGRAM_BOT_TOKEN / TELEGRAM_ADMIN_CHAT_ID belum diisi")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=15,
        )
        ok = r.status_code == 200 and r.json().get("ok")
        if not ok:
            print(f"[telegram] gagal {r.status_code}: {r.text[:200]}")
        return bool(ok)
    except requests.RequestException as e:  # notifikasi tidak boleh menggagalkan job
        print(f"[telegram] error: {e}")
        return False
