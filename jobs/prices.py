"""Job: ambil harga emas → simpan ke Supabase → lapor ke Telegram admin.

Contoh:
  python -m jobs.prices --trigger manual
  python -m jobs.prices --dry-run                      # tanpa menulis ke DB
  python -m jobs.prices --simulate-fail xau            # uji T-06 (sumber gagal)
  python -m jobs.prices --skip-if-recent-min 60        # dipakai jadwal cadangan GitHub
"""
from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .common import telegram
from .common.env import load_dotenv
from .common.jobrun import JobRun
from .common.quality import hour_slot, jump_status, spot_idr_per_gram
from .common.supa import Supa
from .sources import antam, market

WIB = "Asia/Jakarta"


def row(instrument, price_type, price, currency, unit, source, observed_at, slot, quality="ok", note=None):
    return {
        "instrument": instrument, "price_type": price_type, "price": round(float(price), 4),
        "currency": currency, "unit": unit, "source": source,
        "observed_at": observed_at.isoformat(), "slot": slot.isoformat(),
        "quality_status": quality, "note": note,
    }


def last_ok_price(db: Supa | None, instrument: str, price_type: str) -> float | None:
    if db is None:
        return None
    r = db.select("price_snapshots", select="price", instrument=f"eq.{instrument}",
                  price_type=f"eq.{price_type}", quality_status="in.(ok,manual)",
                  order="observed_at.desc", limit=1)
    return float(r[0]["price"]) if r else None


def run(args) -> int:
    db = None if args.dry_run else Supa()
    cfg = db.config() if db else {}
    sources = cfg.get("sources", {"xau": True, "fx": True, "antam": True})
    max_jump = float(cfg.get("quality", {}).get("max_jump_pct", 5))
    notify_each = cfg.get("notify", {}).get("admin_each_run", True)
    simulate = set(filter(None, (args.simulate_fail or "").split(",")))

    job = JobRun(db, "prices", args.trigger, dry_run=args.dry_run)
    if args.skip_if_recent_min and job.recent_success(args.skip_if_recent_min):
        print(f"[job] dilewati: sudah sukses dalam {args.skip_if_recent_min} menit terakhir")
        job.start().finish("skipped")
        return 0
    job.start()

    now = datetime.now(timezone.utc)
    slot = hour_slot(now)
    rows, errors, summary = [], {}, []

    def checked(instrument, price_type, price):
        return jump_status(price, last_ok_price(db, instrument, price_type), max_jump)

    # 1) XAU/USD
    xau = fx = None
    if sources.get("xau", True):
        try:
            if "xau" in simulate:
                raise market.SourceError("simulasi gagal (--simulate-fail xau)")
            xau, warn = market.fetch_xau()
            q = checked("XAU_USD", "spot", xau["price"])
            rows.append(row("XAU_USD", "spot", xau["price"], "USD", "troy_oz", xau["source"], xau["observed_at"], slot, q,
                            "; ".join(warn) or None))
            summary.append(f"XAU/USD ${xau['price']:,.2f} ({xau['source']}){' ⚠️' if q != 'ok' else ''}")
        except Exception as e:  # noqa: BLE001
            errors["xau"] = str(e)

    # 2) USD/IDR
    if sources.get("fx", True):
        try:
            if "fx" in simulate:
                raise market.SourceError("simulasi gagal (--simulate-fail fx)")
            fx, warn = market.fetch_fx()
            q = checked("USD_IDR", "rate", fx["price"])
            rows.append(row("USD_IDR", "rate", fx["price"], "IDR", "usd", fx["source"], fx["observed_at"], slot, q,
                            "; ".join(warn) or None))
            summary.append(f"USD/IDR {fx['price']:,.0f} ({fx['source']})")
        except Exception as e:  # noqa: BLE001
            errors["fx"] = str(e)

    # 3) Spot IDR/gram (turunan)
    if xau and fx:
        spot = spot_idr_per_gram(xau["price"], fx["price"])
        q = checked("SPOT_IDR_G", "spot", spot)
        rows.append(row("SPOT_IDR_G", "spot", spot, "IDR", "gram", "derived", now, slot, q))
        summary.append(f"Spot Rp {spot:,.0f}/g")

    # 4) Produk dengan metode scrape
    products = db.select("products", select="id,name,source_ref", pricing_method="eq.scrape", active="is.true") if db else [
        {"id": "antam", "name": "Logam Mulia Antam",
         "source_ref": {"sell_url": "https://www.logammulia.com/id/harga-emas-hari-ini",
                        "buyback_url": "https://www.logammulia.com/id/sell/gold"}}]
    for p in products:
        if not sources.get(p["id"], True):
            continue
        if p["id"] != "antam":
            errors[p["id"]] = "parser belum tersedia (Fase 2)"
            continue
        if p["id"] in simulate:
            errors[p["id"]] = "simulasi gagal"
            continue
        res = antam.fetch(p["source_ref"] or {})
        for kind in ("sell", "buyback"):
            if res[kind]:
                q = checked(p["id"], kind, res[kind])
                rows.append(row(p["id"], kind, res[kind], "IDR", "gram", "logammulia.com", res["observed_at"], slot, q))
        if res["sell"] or res["buyback"]:
            sell_txt = f"Rp {res['sell']:,.0f}" if res["sell"] else "-"
            bb_txt = f"Rp {res['buyback']:,.0f}" if res["buyback"] else "-"
            summary.append(f"{p['name']}: jual {sell_txt} · buyback {bb_txt}")
        if res["errors"]:
            errors[p["id"]] = "; ".join(res["errors"])

    # 5) Simpan (idempotent: kunci instrument+price_type+source+slot)
    if rows and db:
        saved = db.upsert("price_snapshots", rows, on_conflict="instrument,price_type,source,slot")
        job.rows = len(saved)
    else:
        job.rows = len(rows)
        for r in rows:
            print("  ", r["instrument"], r["price_type"], r["price"], r["source"], r["quality_status"])

    status = "success" if not errors else ("partial" if rows else "failed")
    job.detail = {"errors": errors, "count": len(rows)}
    job.finish(status)

    # 6) Lapor admin
    icon = {"success": "✅", "partial": "⚠️", "failed": "❌"}[status]
    local = now.astimezone(ZoneInfo(WIB)).strftime("%d %b %H:%M WIB")
    msg = (f"{icon} <b>Gold Tracker · prices</b> ({status})\n{local} · trigger {html.escape(args.trigger)}\n"
           + "\n".join(html.escape(s) for s in summary))
    if errors:
        msg += "\n\n<b>Gagal:</b>\n" + "\n".join(f"• {html.escape(k)}: {html.escape(v[:160])}" for k, v in errors.items())
        msg += "\nData lama tetap dipakai."
    if notify_each or status != "success":
        if args.dry_run:
            print("\n[telegram dry-run]\n" + msg)
        else:
            telegram.send(msg)
    return 1 if status == "failed" else 0


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description="Ambil & simpan harga emas")
    ap.add_argument("--trigger", default="manual")
    ap.add_argument("--dry-run", action="store_true", help="tidak menulis ke database/Telegram")
    ap.add_argument("--simulate-fail", default="", help="mis. 'xau' atau 'xau,antam' untuk uji kegagalan")
    ap.add_argument("--skip-if-recent-min", type=int, default=0)
    sys.exit(run(ap.parse_args()))


if __name__ == "__main__":
    main()
