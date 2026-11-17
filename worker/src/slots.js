/** Jadwal terakhir (UTC) yang seharusnya sudah selesai, dengan masa tenggang. */
export function expectedSlot(env, now) {
  const grace = Number(env.GRACE_MIN || 45) * 60e3;
  const slots = (env.PRICE_SLOTS_UTC || "2:15,6:15,10:15,14:15").split(",").map((s) => s.trim().split(":").map(Number));
  let best = null;
  for (let d = 0; d <= 1; d++) {
    for (const [h, m] of slots) {
      const t = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - d, h, m);
      if (t + grace <= now.getTime() && (best === null || t > best)) best = t;
    }
  }
  return best;
}

