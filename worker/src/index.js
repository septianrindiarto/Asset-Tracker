/**
 * Gold Tracker — Cloudflare Worker (gratis)
 *  1. PEMICU  : pada jadwal, memanggil GitHub Actions `workflow_dispatch`
 *  2. WATCHDOG: tiap jam, cek job_runs di Supabase; bila job terlambat → Telegram admin
 * Kerja Worker hanya memanggil API (ringan), aman di batas CPU paket gratis.
 */
import { expectedSlot } from "./slots.js";

const CRON_PRICES = "15 2,6,10,14 * * *";
const CRON_WATCHDOG = "45 * * * *";

export default {
  async scheduled(event, env, ctx) {
    if (event.cron === CRON_PRICES) ctx.waitUntil(dispatch(env, "prices.yml", "cloudflare-cron"));
    if (event.cron === CRON_WATCHDOG) ctx.waitUntil(watchdog(env, false));
  },

  // Pemicu manual untuk testing:
  //   https://<worker>.workers.dev/run?job=prices&key=<MANUAL_KEY>
  //   https://<worker>.workers.dev/watchdog?key=<MANUAL_KEY>&test=1
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!env.MANUAL_KEY || url.searchParams.get("key") !== env.MANUAL_KEY) {
      return new Response("forbidden", { status: 403 });
    }
    if (url.pathname === "/run") {
      const job = (url.searchParams.get("job") || "prices").replace(/[^a-z0-9_-]/gi, "");
      return json(await dispatch(env, `${job}.yml`, "manual-url"));
    }
    if (url.pathname === "/watchdog") {
      return json(await watchdog(env, url.searchParams.get("test") === "1"));
    }
    return new Response("not found", { status: 404 });
  },
};

async function dispatch(env, workflow, trigger) {
  const r = await fetch(
    `https://api.github.com/repos/${env.GH_OWNER}/${env.GH_REPO}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GH_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gold-tracker-worker",
      },
      body: JSON.stringify({ ref: env.GH_REF || "main", inputs: { trigger } }),
    },
  );
  const ok = r.status === 204;
  if (!ok) {
    const body = (await r.text()).slice(0, 200);
    await telegram(env, `❌ <b>Gold Tracker</b>: gagal memicu ${workflow} (HTTP ${r.status})\n${escapeHtml(body)}\nJadwal cadangan GitHub akan mencoba.`);
    return { ok, status: r.status, body };
  }
  return { ok, workflow, trigger };
}

async function watchdog(env, test) {
  const now = new Date();
  const headers = { apikey: env.SUPABASE_SERVICE_KEY };
  if (!env.SUPABASE_SERVICE_KEY.startsWith("sb_")) headers.Authorization = `Bearer ${env.SUPABASE_SERVICE_KEY}`;
  const q = "job_runs?job=eq.prices&status=in.(success,partial)&order=finished_at.desc&limit=1&select=finished_at,status";
  const r = await fetch(`${env.SUPABASE_URL}/rest/v1/${q}`, { headers });
  if (!r.ok) {
    await telegram(env, `❌ <b>Watchdog</b>: tidak bisa membaca Supabase (HTTP ${r.status}).`);
    return { ok: false, status: r.status };
  }
  const rows = await r.json();
  const last = rows[0]?.finished_at ? new Date(rows[0].finished_at).getTime() : 0;
  const slot = expectedSlot(env, now);
  const stale = slot !== null && last < slot;
  // Kirim alert sekali per jadwal yang terlewat (watchdog berikutnya tidak mengulang).
  const firstCheck = slot !== null && now.getTime() - slot < 2 * 3600e3;
  const ageH = last ? ((now.getTime() - last) / 3600e3).toFixed(1) : "∞";
  const result = { stale, lastSuccess: rows[0]?.finished_at || null, expectedSlot: slot && new Date(slot).toISOString(), ageHours: ageH };

  if (test) {
    await telegram(env, `🧪 <b>Tes watchdog</b>\nSukses terakhir: ${result.lastSuccess || "belum ada"} (${ageH} jam lalu)\nStatus: ${stale ? "TERLAMBAT" : "aman"}`);
  } else if (stale && firstCheck) {
    await telegram(env, `⏰ <b>Gold Tracker</b>: job harga belum sukses sejak jadwal ${new Date(slot).toISOString().slice(11, 16)} UTC.\nSukses terakhir ${ageH} jam lalu. Cek GitHub › Actions › prices.`);
  }
  return result;
}

async function telegram(env, text) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_ADMIN_CHAT_ID) return;
  await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: env.TELEGRAM_ADMIN_CHAT_ID, text, parse_mode: "HTML", disable_web_page_preview: true }),
  });
}

const escapeHtml = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
const json = (o) => new Response(JSON.stringify(o, null, 2), { headers: { "Content-Type": "application/json" } });

