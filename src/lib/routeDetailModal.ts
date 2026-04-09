import { state } from "./store";
import { esc, timeAgo, fmtDelay } from "./utils";

interface RouteEntry {
  train_name:    string;
  train_type:    string;
  total:         number;
  delayed:       number;
  cancelled:     number;
  delayed_pct:   number;
  avg_delay_min: number;
  max_delay_min: number;
  arrivals:      any[];
}

let _byRouteData: RouteEntry[] | null = null;
let _byTrayectoData: any[] | null = null;
let _generatedAt = "";

export async function openRouteDetail(trainName: string, nucleo?: string) {
  const modal = document.getElementById("route-detail-modal")!;
  const title = document.getElementById("route-detail-title")!;
  const meta  = document.getElementById("route-detail-meta")!;
  const body  = document.getElementById("route-detail-body")!;
  const empty = document.getElementById("route-detail-empty")!;
  const chips = document.getElementById("route-detail-chips")!;

  title.textContent = trainName;
  meta.textContent  = "Cargando…";
  body.innerHTML    = Array(4).fill(`<tr class="skeleton-modal"><td colspan="6"><div class="skeleton-cell"></div></td></tr>`).join("");
  empty.style.display = "none";
  chips.innerHTML   = "";
  modal.style.display = "flex";
  document.body.style.overflow = "hidden";

  if (!_byRouteData) {
    try {
      const res = await fetch(`/data/${state.activeSvc}/by_route_arrivals.json?t=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      _byRouteData  = json.routes ?? [];
      _generatedAt = json.generated_at ?? "";
    } catch {
      body.innerHTML = "";
      meta.textContent = "Error al cargar los datos.";
      return;
    }
  }

  renderRouteDetail(trainName, nucleo);
}

export function closeRouteDetail() {
  document.getElementById("route-detail-modal")!.style.display = "none";
  document.body.style.overflow = "";
}

export function invalidateRouteDetailCache() {
  _byRouteData = null;
  _byTrayectoData = null;
  _generatedAt = "";
}

export async function openTrayectoDetail(trainType: string, headsign: string) {
  const modal = document.getElementById("route-detail-modal")!;
  const title = document.getElementById("route-detail-title")!;
  const meta  = document.getElementById("route-detail-meta")!;
  const body  = document.getElementById("route-detail-body")!;
  const empty = document.getElementById("route-detail-empty")!;
  const chips = document.getElementById("route-detail-chips")!;

  title.textContent = `${trainType} → ${headsign}`;
  meta.textContent  = "Cargando…";
  body.innerHTML    = Array(4).fill(`<tr class="skeleton-modal"><td colspan="6"><div class="skeleton-cell"></div></td></tr>`).join("");
  empty.style.display = "none";
  chips.innerHTML   = "";
  modal.style.display = "flex";
  document.body.style.overflow = "hidden";

  if (!_byTrayectoData) {
    try {
      const res = await fetch(`/data/${state.activeSvc}/by_trayecto.json?t=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      _byTrayectoData = json.trayectos ?? [];
      _generatedAt    = json.generated_at ?? "";
    } catch {
      body.innerHTML = "";
      meta.textContent = "Error al cargar los datos.";
      return;
    }
  }

  const trayecto = _byTrayectoData.find(t => t.train_type === trainType && t.headsign === headsign);
  const arrivals: any[] = trayecto?.arrivals ?? [];
  const upd = document.getElementById("route-detail-updated")!;
  upd.textContent = _generatedAt ? `Actualizado ${timeAgo(_generatedAt)}` : "";

  if (!arrivals.length) {
    body.innerHTML = "";
    empty.style.display = "flex";
    meta.textContent = "Sin retrasos en la última captura";
    return;
  }

  const maxDelay  = Math.max(...arrivals.map((a: any) => a.delay_min ?? 0));
  const cancelled = arrivals.filter((a: any) => a.status === "cancelado").length;
  meta.textContent = `${arrivals.length} servicio${arrivals.length !== 1 ? "s" : ""} con retraso`;
  empty.style.display = "none";
  chips.innerHTML = [
    `<span class="chip chip-yellow">${arrivals.length} con retraso</span>`,
    maxDelay > 0 ? `<span class="chip chip-red">${fmtDelay(maxDelay)} máx</span>` : "",
    cancelled > 0 ? `<span class="chip chip-gray">${cancelled} cancelado${cancelled !== 1 ? "s" : ""}</span>` : "",
  ].filter(Boolean).join("");

  body.innerHTML = arrivals.map(rowHTML).join("");
}

function renderRouteDetail(trainName: string, nucleo?: string) {
  const route = _byRouteData?.find(r =>
    r.train_name === trainName && (nucleo === undefined || (r as any).nucleo === nucleo || !(r as any).nucleo)
  );
  const arrivals: any[] = route?.arrivals ?? [];

  const body   = document.getElementById("route-detail-body")!;
  const meta   = document.getElementById("route-detail-meta")!;
  const empty  = document.getElementById("route-detail-empty")!;
  const chips  = document.getElementById("route-detail-chips")!;
  const upd    = document.getElementById("route-detail-updated")!;

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
    maxDelay > 0 ? `<span class="chip chip-red">${fmtDelay(maxDelay)} máx</span>` : "",
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

  const delayStr   = a.delay_min != null && a.delay_min > 0 ? fmtDelay(a.delay_min) : "—";
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
