/* Gold Tracker — PoC Fase 1
 * Membuktikan: login undangan (magic link), cek masa akses via has_access(),
 * data harga terbaca hanya oleh user aktif (RLS), log job hanya untuk admin.
 */
const cfg = window.GT_CONFIG;
const sb = supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const wib = (t) => (t ? new Date(t).toLocaleString("id-ID", { timeZone: "Asia/Jakarta", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "-");
const fmt = (p, cur) => (cur === "USD" ? "$" + Number(p).toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "Rp " + Math.round(p).toLocaleString("id-ID"));
const show = (el, cls, text) => { el.className = "msg " + cls; el.textContent = text; el.style.display = "block"; };

if (cfg.SUPABASE_URL.includes("GANTI")) {
  show($("#login-msg"), "bad", "config.js belum diisi (SUPABASE_URL & SUPABASE_ANON_KEY). Lihat panduan Fase 1 langkah G.");
}

$("#btn-login").onclick = async () => {
  const email = $("#email").value.trim().toLowerCase();
  if (!email) return;
  $("#btn-login").disabled = true;
  const { error } = await sb.auth.signInWithOtp({
    email,
    options: { shouldCreateUser: false, emailRedirectTo: location.origin + location.pathname },
  });
  $("#btn-login").disabled = false;
  if (error) {
    const notInvited = /signups not allowed|not found|otp_disabled/i.test(error.message);
    show($("#login-msg"), "bad", notInvited ? "Email ini belum diundang admin." : "Gagal: " + error.message);
  } else {
    show($("#login-msg"), "ok", "Link masuk sudah dikirim. Buka email lalu klik link-nya (cek folder spam).");
  }
};
$("#email").addEventListener("keydown", (e) => e.key === "Enter" && $("#btn-login").click());
$("#btn-out").onclick = async () => { await sb.auth.signOut(); location.reload(); };

sb.auth.onAuthStateChange((_evt, session) => render(session));
sb.auth.getSession().then(({ data }) => render(data.session));

let rendered = null;
async function render(session) {
  if (!session) { $("#v-login").classList.remove("hidden"); $("#v-app").classList.add("hidden"); $("#btn-out").classList.add("hidden"); return; }
  if (rendered === session.access_token) return;
  rendered = session.access_token;
  $("#v-login").classList.add("hidden"); $("#v-app").classList.remove("hidden"); $("#btn-out").classList.remove("hidden");

  const [{ data: prof, error: pe }, { data: access }] = await Promise.all([
    sb.from("profiles").select("*").eq("user_id", session.user.id).maybeSingle(),
    sb.rpc("has_access"),
  ]);
  if (pe || !prof) { show($("#access-msg"), "bad", "Profil tidak ditemukan. Hubungi admin."); return; }

  $("#hello").textContent = `Halo, ${prof.display_name || prof.email}`;
  $("#me").innerHTML = `
    <div class="kpi"><small>Email</small><b style="font-size:14px">${esc(prof.email)}</b></div>
    <div class="kpi"><small>Role</small><b>${esc(prof.role)}</b></div>
    <div class="kpi"><small>Status</small><b>${esc(prof.status)}</b></div>
    <div class="kpi"><small>Berlaku s/d</small><b style="font-size:15px">${prof.access_end ? wib(prof.access_end) : "Unlimited"}</b></div>`;

  if (!access) {
    show($("#access-msg"), "bad", prof.status !== "active"
      ? `Akun berstatus "${prof.status}". Hubungi admin.`
      : `Masa akses berakhir pada ${wib(prof.access_end)}. Hubungi admin untuk perpanjangan.`);
    $("#c-prices").classList.add("hidden"); $("#c-jobs").classList.add("hidden");
    return;
  }
  show($("#access-msg"), "ok", "Akses aktif ✓");
  $("#c-prices").classList.remove("hidden");
  loadPrices();
  if (prof.role === "admin") { $("#c-jobs").classList.remove("hidden"); loadJobs(); }
}

async function loadPrices() {
  const { data, error } = await sb.from("price_snapshots")
    .select("instrument,price_type,price,currency,source,observed_at,quality_status")
    .order("observed_at", { ascending: false }).limit(40);
  if (error) { $("#prices").innerHTML = `<tr><td colspan="6">${esc(error.message)}</td></tr>`; return; }
  const latest = {};
  data.forEach((r) => { const k = r.instrument + "|" + r.price_type; if (!latest[k]) latest[k] = r; });
  const label = { "XAU_USD|spot": "Emas dunia /oz", "USD_IDR|rate": "Kurs USD/IDR", "SPOT_IDR_G|spot": "Spot /gram", "antam|sell": "Antam jual /g", "antam|buyback": "Antam buyback /g" };
  $("#kpis").innerHTML = Object.entries(latest).map(([k, r]) =>
    `<div class="kpi"><small>${esc(label[k] || k)}</small><b>${r.instrument === "USD_IDR" ? Number(r.price).toLocaleString("id-ID") : fmt(r.price, r.currency)}</b><small>${wib(r.observed_at)}</small></div>`).join("")
    || '<div class="sub">Belum ada data. Jalankan workflow "prices" di GitHub.</div>';
  const q = { ok: "b-ok", needs_review: "b-rev", manual: "b-man" };
  $("#prices").innerHTML = data.map((r) => `<tr><td>${wib(r.observed_at)}</td><td>${esc(r.instrument)}</td><td>${esc(r.price_type)}</td>
    <td>${r.instrument === "USD_IDR" ? Number(r.price).toLocaleString("id-ID") : fmt(r.price, r.currency)}</td><td>${esc(r.source)}</td>
    <td><span class="badge ${q[r.quality_status] || ""}">${esc(r.quality_status)}</span></td></tr>`).join("");
}

async function loadJobs() {
  const { data, error } = await sb.from("job_runs").select("*").order("started_at", { ascending: false }).limit(15);
  if (error) { $("#jobs").innerHTML = `<tr><td colspan="6">${esc(error.message)}</td></tr>`; return; }
  const c = { success: "b-ok", partial: "b-rev", failed: "b-fail", skipped: "b-man", running: "b-man" };
  $("#jobs").innerHTML = data.map((j) => `<tr><td>${wib(j.started_at)}</td><td>${esc(j.job)}</td><td>${esc(j.trigger)}</td>
    <td><span class="badge ${c[j.status]}">${esc(j.status)}</span></td><td>${j.rows_written}</td>
    <td class="sub">${esc(Object.keys(j.detail?.errors || {}).join(", ") || "-")}</td></tr>`).join("");
}
