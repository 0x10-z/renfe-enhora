export function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!
  ));
}

export function timeAgo(iso: string): string {
  const date = new Date(iso);
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  const time = date.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
  if (diff < 5) return `${time} · ahora mismo`;
  if (diff < 60) return `${time} · hace ${diff}s`;
  if (diff < 3600) return `${time} · hace ${Math.floor(diff / 60)}m`;
  return `${time} · hace más de 1h`;
}

/**
 * Format a fractional-minute delay value as "Xm Ys".
 * e.g.  9.5  → "+9m 30s"
 *       15.0 → "+15m"
 *       0.5  → "+30s"
 * Pass withPlus=false to omit the leading "+".
 */
export function fmtDelay(minutes: number, withPlus = true): string {
  const prefix = withPlus ? "+" : "";
  const totalSecs = Math.round(minutes * 60);
  const m = Math.floor(totalSecs / 60);
  const s = totalSecs % 60;
  if (m === 0) return `${prefix}${s}s`;
  if (s === 0) return `${prefix}${m}m`;
  return `${prefix}${m}m ${s}s`;
}

export function setText(id: string, value: string) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

export function setValueWithUnit(id: string, value: string | number | null, unit: string) {
  const el = document.getElementById(id);
  if (!el) return;
  if (value == null || value === "—") {
    el.innerHTML = "—";
  } else {
    el.innerHTML = `${value}<span class="stat-unit">${unit}</span>`;
  }
}
