import { state } from "./store";
import { esc, timeAgo } from "./utils";

// Maps pipeline train_type strings → CSS badge class suffix
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

let _byTypeData: Record<string, any[]> | null = null;
let _generatedAt = "";

export async function openTrainTypeDetail(typeName: string) {
  const modal = document.getElementById("tt-detail-modal")!;
  const title = document.getElementById("tt-detail-title")!;
  const badge = document.getElementById("tt-detail-badge")!;
  const meta  = document.getElementById("tt-detail-meta")!;
  const body  = document.getElementById("tt-detail-body")!;
  const empty = document.getElementById("tt-detail-empty")!;
  const chips = document.getElementById("tt-detail-chips")!;

  title.textContent = typeName;
  badge.textContent = typeName;
  badge.className   = `tt-badge tt-${TYPE_CLASS[typeName] ?? "reg"}`;
  meta.textContent  = "Cargando…";
  body.innerHTML    = Array(4).fill(`<tr class="skeleton-modal"><td colspan="6"><div class="skeleton-cell"></div></td></tr>`).join("");
  empty.style.display = "none";
  chips.innerHTML   = "";
  modal.style.display = "flex";
  document.body.style.overflow = "hidden";

  if (!_byTypeData) {
    try {
      const res = await fetch(`/data/${state.activeSvc}/by_type_arrivals.json?t=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      _byTypeData  = json.by_type ?? {};
      _generatedAt = json.generated_at ?? "";
    } catch {
      body.innerHTML = "";
      meta.textContent = "Error al cargar los datos.";
      return;
    }
  }

  renderTypeDetail(typeName);
}

export function closeTrainTypeDetail() {
  document.getElementById("tt-detail-modal")!.style.display = "none";
  document.body.style.overflow = "";
}

// Invalidate cached data when the service tab changes
export function invalidateTypeDetailCache() {
  _byTypeData = null;
  _generatedAt = "";
}

function renderTypeDetail(typeName: string) {
  const arrivals: any[] = _byTypeData?.[typeName] ?? [];
  const body   = document.getElementById("tt-detail-body")!;
  const meta   = document.getElementById("tt-detail-meta")!;
  const empty  = document.getElementById("tt-detail-empty")!;
  const chips  = document.getElementById("tt-detail-chips")!;
  const upd    = document.getElementById("tt-detail-updated")!;

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
  const chipsList: string[] = [
    `<span class="chip chip-yellow">${arrivals.length} con retraso</span>`,
    maxDelay > 0 ? `<span class="chip chip-red">+${maxDelay}m máx</span>` : "",
    cancelled > 0 ? `<span class="chip chip-gray">${cancelled} cancelado${cancelled !== 1 ? "s" : ""}</span>` : "",
  ];
  chips.innerHTML = chipsList.filter(Boolean).join("");

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

  const estTime = a.estimated_time
    ? `<span class="time-cell ${timeClass[a.status] ?? ""}">${esc(a.estimated_time)}</span>`
    : `<span class="time-cell time-cancel">—</span>`;

  const delayStr   = a.delay_min != null && a.delay_min > 0 ? `+${a.delay_min}m` : "—";
  const delayClass = a.status === "retraso_alto" ? "delay-alto" : a.status === "retraso_leve" ? "delay-leve" : "";
  const rowClass   = a.status === "cancelado" ? "cancelled-row" : "";

  return `<tr class="${rowClass}">
    <td><div>${trayecto}</div></td>
    <td><span class="station-name-cell">${esc(a.stop_name ?? "—")}</span></td>
    <td><span class="time-cell">${esc(a.scheduled_time ?? "—")}</span></td>
    <td>${estTime}</td>
    <td><span class="delay-cell ${delayClass}">${delayStr}</span></td>
    <td><span class="badge badge-${a.status ?? "retraso_leve"}">● ${esc(statusLabel[a.status] ?? a.status)}</span></td>
  </tr>`;
}
