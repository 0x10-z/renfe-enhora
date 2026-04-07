import { state } from "./store";
import { esc, timeAgo } from "./utils";

// Maps pipeline train_type → CSS badge class suffix
const TYPE_CLASS: Record<string, string> = {
  "AVE":             "ave",
  "AVLO":            "avlo",
  "Alvia":           "alvia",
  "Avant":           "avant",
  "Media Distancia": "md",
  "Regional":        "reg",
  "Larga Distancia": "ld",
  "Cercanías":       "c",
};

let _byCcaaData: Record<string, any[]> | null = null;
let _generatedAt = "";

export async function openCcaaDetail(ccaaName: string) {
  const modal = document.getElementById("ccaa-detail-modal")!;
  const title = document.getElementById("ccaa-detail-title")!;
  const meta  = document.getElementById("ccaa-detail-meta")!;
  const body  = document.getElementById("ccaa-detail-body")!;
  const empty = document.getElementById("ccaa-detail-empty")!;
  const chips = document.getElementById("ccaa-detail-chips")!;

  title.textContent = ccaaName;
  meta.textContent  = "Cargando…";
  body.innerHTML    = Array(4).fill(`<tr class="skeleton-modal"><td colspan="7"><div class="skeleton-cell"></div></td></tr>`).join("");
  empty.style.display = "none";
  chips.innerHTML   = "";
  modal.style.display = "flex";
  document.body.style.overflow = "hidden";

  if (!_byCcaaData) {
    try {
      const res = await fetch(`/data/${state.activeSvc}/by_ccaa_arrivals.json?t=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      _byCcaaData  = json.by_ccaa ?? {};
      _generatedAt = json.generated_at ?? "";
    } catch {
      body.innerHTML = "";
      meta.textContent = "Error al cargar los datos.";
      return;
    }
  }

  renderDetail(ccaaName);
}

export function closeCcaaDetail() {
  document.getElementById("ccaa-detail-modal")!.style.display = "none";
  document.body.style.overflow = "";
}

export function invalidateCcaaDetailCache() {
  _byCcaaData = null;
  _generatedAt = "";
}

function renderDetail(ccaaName: string) {
  const arrivals: any[] = _byCcaaData?.[ccaaName] ?? [];
  const body  = document.getElementById("ccaa-detail-body")!;
  const meta  = document.getElementById("ccaa-detail-meta")!;
  const empty = document.getElementById("ccaa-detail-empty")!;
  const chips = document.getElementById("ccaa-detail-chips")!;
  const upd   = document.getElementById("ccaa-detail-updated")!;

  upd.textContent = _generatedAt ? `Actualizado ${timeAgo(_generatedAt)}` : "";

  if (!arrivals.length) {
    body.innerHTML = "";
    empty.style.display = "flex";
    meta.textContent = "Sin retrasos en la última captura";
    return;
  }

  meta.textContent = `${arrivals.length} servicio${arrivals.length !== 1 ? "s" : ""} con retraso`;
  empty.style.display = "none";

  const maxDelay  = Math.max(...arrivals.map(a => a.delay_min ?? 0));
  const cancelled = arrivals.filter(a => a.status === "cancelado").length;
  chips.innerHTML = [
    `<span class="chip chip-yellow">${arrivals.length} con retraso</span>`,
    maxDelay > 0 ? `<span class="chip chip-red">+${maxDelay}m máx</span>` : "",
    cancelled > 0 ? `<span class="chip chip-gray">${cancelled} cancelado${cancelled !== 1 ? "s" : ""}</span>` : "",
  ].filter(Boolean).join("");

  body.innerHTML = arrivals.map(rowHTML).join("");
}

function rowHTML(a: any): string {
  const statusLabel: Record<string, string> = {
    retraso_leve: "Leve", retraso_alto: "Alto", cancelado: "Cancelado",
  };
  const timeClass: Record<string, string> = {
    retraso_leve: "time-leve", retraso_alto: "time-alto", cancelado: "time-cancel",
  };

  const routeTag = a.train_name ? `<span class="route-tag">${esc(a.train_name)}</span>` : "";
  const destText = a.headsign || "—";
  const fromLine = a.origin && a.origin !== destText
    ? `<div class="origin-from"><span class="route-sep">desde</span> ${esc(a.origin)}</div>`
    : "";
  const trayecto = `<div class="origin-main">${routeTag}${esc(destText)}</div>${fromLine}`;

  const typeClass = TYPE_CLASS[a.train_type] ?? "reg";
  const typeBadge = `<span class="tt-badge tt-${typeClass}" style="font-size:0.68rem;padding:1px 6px">${esc(a.train_type ?? "—")}</span>`;

  const estTime = a.estimated_time
    ? `<span class="time-cell ${timeClass[a.status] ?? ""}">${esc(a.estimated_time)}</span>`
    : `<span class="time-cell time-cancel">—</span>`;

  const delayStr   = a.delay_min != null && a.delay_min > 0 ? `+${a.delay_min}m` : "—";
  const delayClass = a.status === "retraso_alto" ? "delay-alto" : a.status === "retraso_leve" ? "delay-leve" : "";
  const rowClass   = a.status === "cancelado" ? "cancelled-row" : "";

  return `<tr class="${rowClass}">
    <td><div>${trayecto}</div></td>
    <td>${typeBadge}</td>
    <td><span class="station-name-cell">${esc(a.stop_name ?? "—")}</span></td>
    <td><span class="time-cell">${esc(a.scheduled_time ?? "—")}</span></td>
    <td>${estTime}</td>
    <td><span class="delay-cell ${delayClass}">${delayStr}</span></td>
    <td><span class="badge badge-${a.status ?? "retraso_leve"}">● ${esc(statusLabel[a.status] ?? a.status)}</span></td>
  </tr>`;
}
