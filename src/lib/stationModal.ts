import { state } from "./store";
import { esc, timeAgo } from "./utils";
import { getTrainType, getTrainImage, TRAIN_TYPE_LABELS } from "../utils/trains";

export function openModal(stationId: string, name: string, fromInsight = false) {
  state.stationFromInsight = fromInsight;
  state.modalStationId = stationId;
  const backBtn = document.getElementById("modal-back")!;
  backBtn.style.display = fromInsight ? "flex" : "none";

  document.getElementById("modal-name")!.textContent = name;
  document.getElementById("modal-meta")!.textContent = "Cargando llegadas…";
  document.getElementById("modal-chips")!.innerHTML = "";
  document.getElementById("modal-dot")!.className = "station-dot-lg";
  document.getElementById("modal-arrivals-body")!.innerHTML =
    Array(5).fill(`<tr class="skeleton-modal"><td colspan="5"><div class="skeleton-cell"></div></td></tr>`).join("");
  document.getElementById("modal-no-arrivals")!.style.display = "none";
  document.getElementById("modal-error")!.style.display = "none";
  document.getElementById("modal-updated")!.textContent = "";
  document.getElementById("modal-train-preview")!.style.display = "none";
  document.getElementById("station-modal")!.style.display = "flex";
  document.body.style.overflow = "hidden";
  fetchModalStation(stationId);
}

export function closeModal() {
  document.getElementById("station-modal")!.style.display = "none";
  closeTrainViewer();
  if (!state.stationFromInsight) document.body.style.overflow = "";
  state.stationFromInsight = false;
  document.getElementById("modal-train-preview")!.style.display = "none";
}

export async function fetchModalStation(stationId: string) {
  try {
    const res = await fetch(`/data/${state.activeSvc}/stations/${encodeURIComponent(stationId)}.json?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    renderModal(await res.json());
  } catch {
    document.getElementById("modal-arrivals-body")!.innerHTML = "";
    document.getElementById("modal-error")!.style.display = "flex";
  }
}

export function renderModal(data: any) {
  const arrivals: any[] = data.arrivals ?? [];
  state.modalStationName = data.name ?? "";

  document.getElementById("modal-meta")!.textContent = arrivals.length
    ? `${arrivals.length} llegada${arrivals.length !== 1 ? "s" : ""} · próximos 60 min`
    : "Sin llegadas próximas";
  document.getElementById("modal-updated")!.textContent = `Actualizado ${timeAgo(data.generated_at)}`;
  const pageLink = document.getElementById("modal-page-link") as HTMLAnchorElement;
  pageLink.href = `/${state.activeSvc}/${state.modalStationId}`;

  const delayed   = arrivals.filter(a => ["retraso_leve","retraso_alto"].includes(a.status));
  const cancelled = arrivals.filter(a => a.status === "cancelado");
  const maxDelay  = Math.max(0, ...arrivals.map(a => a.delay_min ?? 0));
  const dot = document.getElementById("modal-dot")!;

  if (arrivals.some(a => a.status === "retraso_alto")) {
    dot.className = "station-dot-lg has-high-delays";
  } else if (delayed.length > 0) {
    dot.className = "station-dot-lg has-delays";
  } else {
    dot.className = "station-dot-lg";
  }

  const onTime = arrivals.filter(a => a.status === "en_hora").length;
  const chips: string[] = [];
  if (onTime)           chips.push(`<span class="chip chip-green">${onTime} en hora</span>`);
  if (delayed.length)   chips.push(`<span class="chip chip-yellow">${delayed.length} retraso${delayed.length !== 1 ? "s" : ""}</span>`);
  if (maxDelay > 0)     chips.push(`<span class="chip chip-red">+${maxDelay}m máx</span>`);
  if (cancelled.length) chips.push(`<span class="chip chip-gray">${cancelled.length} cancelado${cancelled.length !== 1 ? "s" : ""}</span>`);
  document.getElementById("modal-chips")!.innerHTML = chips.join("");

  const body = document.getElementById("modal-arrivals-body")!;
  if (!arrivals.length) {
    body.innerHTML = "";
    document.getElementById("modal-no-arrivals")!.style.display = "flex";
    document.getElementById("modal-train-preview")!.style.display = "none";
    return;
  }
  body.innerHTML = arrivals.map(modalRowHTML).join("");
  attachModalTrainPreview(arrivals);
}

export function modalRowHTML(a: any): string {
  const statusLabel: Record<string, string> = {
    en_hora: "En hora", retraso_leve: "Leve", retraso_alto: "Alto", cancelado: "Cancelado",
  };
  const timeClass: Record<string, string> = {
    en_hora: "time-on-time", retraso_leve: "time-leve", retraso_alto: "time-alto", cancelado: "time-cancel",
  };
  const routeTag = (a.train_name || a.route_id) ? `<span class="route-tag">${esc(a.train_name || a.route_id)}</span>` : "";
  const destText = a.headsign || a.origin || "—";
  const fromLine = a.origin && a.origin !== state.modalStationName && a.origin !== destText
    ? `<div class="origin-from"><span class="route-sep">desde</span> ${esc(a.origin)}</div>`
    : "";
  const origin = `<div class="origin-main">${routeTag}${esc(destText)}</div>${fromLine}`;
  const dest   = "";
  const estTime = a.estimated_time
    ? `<span class="time-cell ${timeClass[a.status] ?? ""}">${esc(a.estimated_time)}</span>`
    : `<span class="time-cell time-cancel">—</span>`;
  const delayStr   = a.delay_min != null && a.delay_min > 0 ? `+${a.delay_min}m` : "—";
  const delayClass = a.status === "retraso_alto" ? "delay-alto" : a.status === "retraso_leve" ? "delay-leve" : "";
  const rowClass   = a.status === "cancelado" ? "cancelled-row" : "";
  const trainAttr = a.train_name ? `data-train-name="${esc(a.train_name)}"` : "";
  return `<tr class="${rowClass}" ${trainAttr}>
    <td><div>${origin}${dest}</div></td>
    <td><span class="time-cell">${esc(a.scheduled_time ?? "—")}</span></td>
    <td>${estTime}</td>
    <td><span class="delay-cell ${delayClass}">${delayStr}</span></td>
    <td><span class="badge badge-${a.status ?? "en_hora"}">● ${esc(statusLabel[a.status] ?? a.status)}</span></td>
  </tr>`;
}

export function attachModalTrainPreview(arrivals: any[]) {
  const preview = document.getElementById("modal-train-preview") as HTMLElement;
  preview.style.display = "flex";

  const first = arrivals.find((a) => a.train_name) ?? arrivals[0];
  setModalTrainPreview(first?.train_name, first);

  document.querySelectorAll<HTMLTableRowElement>("#modal-arrivals-body tr").forEach((row, i) => {
    const arrival = arrivals[i];
    row.addEventListener("mouseenter", () => setModalTrainPreview(row.dataset.trainName, arrival));
    row.addEventListener("click", () => {
      setModalTrainPreview(row.dataset.trainName, arrival);
      openTrainViewer();
    });
  });
}

export function setModalTrainPreview(trainName?: string, arrival?: any) {
  const type = getTrainType(trainName);
  const image = document.getElementById("modal-train-preview-image") as HTMLImageElement;
  const label = document.getElementById("modal-train-preview-type") as HTMLElement;
  const name = document.getElementById("modal-train-preview-name") as HTMLElement;
  state.modalSelectedTrainName = trainName ?? "";
  state.modalSelectedArrival = arrival ?? null;
  image.src = getTrainImage(trainName);
  label.textContent = TRAIN_TYPE_LABELS[type] ?? "Tren";
  name.textContent = `Servicio detectado: ${trainName ?? "-"}`;
}

export function openTrainViewer() {
  const a = state.modalSelectedArrival;
  const type = getTrainType(state.modalSelectedTrainName);

  (document.getElementById("train-viewer-image") as HTMLImageElement).src = getTrainImage(state.modalSelectedTrainName);
  (document.getElementById("train-viewer-title") as HTMLElement).textContent = TRAIN_TYPE_LABELS[type] ?? "Serie aproximada";
  (document.getElementById("train-viewer-train-name") as HTMLElement).textContent = `Servicio: ${state.modalSelectedTrainName || "—"}`;

  // Badge
  const badge = document.getElementById("train-viewer-badge") as HTMLElement;
  const statusLabel: Record<string, string> = { en_hora: "En hora", retraso_leve: "Leve", retraso_alto: "Alto", cancelado: "Cancelado" };
  badge.className = `badge badge-${a?.status ?? "en_hora"}`;
  badge.textContent = `● ${statusLabel[a?.status] ?? "—"}`;

  // Route: origin → [current station] → dest
  const routeEl = document.getElementById("train-viewer-route") as HTMLElement;
  const origin = a?.origin || "";
  const dest = a?.headsign || "";
  const current = state.modalStationName;
  const arrows = routeEl.querySelectorAll<HTMLElement>(".train-viewer-arrow");
  const currentEl = document.getElementById("train-viewer-current") as HTMLElement;

  if (origin || dest) {
    (document.getElementById("train-viewer-origin") as HTMLElement).textContent = origin || "—";
    currentEl.textContent = current;
    (document.getElementById("train-viewer-dest") as HTMLElement).textContent = dest || "—";
    // Hide arrows if extremes are missing or same as current
    arrows[0].style.display = origin && origin !== current ? "" : "none";
    arrows[1].style.display = dest && dest !== current ? "" : "none";
    routeEl.style.display = "flex";
  } else {
    routeEl.style.display = "none";
  }

  // Times
  const timesEl = document.getElementById("train-viewer-times") as HTMLElement;
  if (a?.scheduled_time) {
    const timeClass: Record<string, string> = { en_hora: "time-on-time", retraso_leve: "time-leve", retraso_alto: "time-alto", cancelado: "time-cancel" };
    (document.getElementById("train-viewer-scheduled") as HTMLElement).textContent = a.scheduled_time;
    const estEl = document.getElementById("train-viewer-estimated") as HTMLElement;
    estEl.textContent = a.estimated_time ?? "—";
    estEl.className = `train-viewer-time-val ${timeClass[a.status] ?? ""}`;
    const delayEl = document.getElementById("train-viewer-delay") as HTMLElement;
    delayEl.textContent = a.delay_min != null && a.delay_min > 0 ? `+${a.delay_min}m` : "—";
    delayEl.className = `train-viewer-time-val ${a.status === "retraso_alto" ? "delay-alto" : a.status === "retraso_leve" ? "delay-leve" : ""}`;
    timesEl.style.display = "flex";
  } else {
    timesEl.style.display = "none";
  }

  (document.getElementById("train-viewer-modal") as HTMLElement).style.display = "flex";
}

export function closeTrainViewer() {
  (document.getElementById("train-viewer-modal") as HTMLElement).style.display = "none";
}
