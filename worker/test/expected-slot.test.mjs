// Uji logika watchdog: jadwal mana yang "seharusnya sudah selesai".
import assert from "node:assert/strict";
import { expectedSlot } from "../src/slots.js";

const env = { PRICE_SLOTS_UTC: "2:15,6:15,10:15,14:15", GRACE_MIN: "45" };
const at = (iso) => new Date(iso);
const slot = (iso) => new Date(expectedSlot(env, at(iso))).toISOString();

assert.equal(slot("2026-10-31T03:45:00Z"), "2026-10-31T02:15:00.000Z"); // 1,5 jam setelah 02:15
assert.equal(slot("2026-10-31T02:45:00Z"), "2026-10-30T14:15:00.000Z"); // 02:15 belum lewat masa tenggang
assert.equal(slot("2026-10-31T23:45:00Z"), "2026-10-31T14:15:00.000Z"); // malam: tetap jadwal terakhir 14:15
assert.equal(slot("2026-10-31T00:45:00Z"), "2026-10-30T14:15:00.000Z"); // lewat tengah malam UTC
console.log("expectedSlot: semua tes lulus");
