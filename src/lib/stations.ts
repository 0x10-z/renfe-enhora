import { state } from "./store";
import { esc } from "./utils";

export const PAGE_SIZE = 40;

export function stationHTML(s: any): string {
  const noTraffic = (s.arrivals_count ?? 0) === 0;
  const ratio   = !noTraffic ? (s.delayed_count ?? 0) / s.arrivals_count : 0;
  const dotCls  = noTraffic
    ? "dot-grey"
    : (s.delayed_count ?? 0) === 0
      ? "dot-green"
      : ratio > 0.3 ? "dot-red" : "dot-yellow";
  const sub = noTraffic
    ? `<span class="station-arrivals">sin tráfico</span>`
    : (s.delayed_count ?? 0) > 0
      ? `<span class="station-delayed">${s.delayed_count} retraso${s.delayed_count !== 1 ? "s" : ""}</span>`
      : `<span class="station-arrivals">${s.arrivals_count} llegadas</span>`;
  return `<button type="button" class="station-card" data-id="${esc(s.id)}" data-name="${esc(s.name)}">
    <span class="station-dot ${dotCls}"></span>
    <span class="station-name">${esc(s.name)}</span>
    ${sub}
    <span class="station-arrow">›</span>
  </button>`;
}

export function renderStations(stations: any[]) {
  const list    = document.getElementById("stations-list")!;
  const countEl = document.getElementById("station-count")!;
  const noData  = document.getElementById("no-data")!;

  state.scrollObserver?.disconnect();
  state.scrollObserver = null;

  if (!stations.length) {
    list.innerHTML = "";
    noData.style.display = "block";
    countEl.textContent = "0";
    return;
  }

  noData.style.display = "none";
  countEl.textContent = `${stations.length}`;
  state.displayedCount = Math.min(PAGE_SIZE, stations.length);
  list.innerHTML = stations.slice(0, state.displayedCount).map(stationHTML).join("");

  if (state.displayedCount < stations.length) {
    const sentinel = document.createElement("div");
    sentinel.id = "load-sentinel";
    sentinel.className = "load-sentinel";
    list.appendChild(sentinel);

    state.scrollObserver = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      const next = Math.min(state.displayedCount + PAGE_SIZE, stations.length);
      const frag = stations.slice(state.displayedCount, next).map(stationHTML).join("");
      sentinel.insertAdjacentHTML("beforebegin", frag);
      state.displayedCount = next;
      if (state.displayedCount >= stations.length) {
        state.scrollObserver!.disconnect();
        state.scrollObserver = null;
        sentinel.remove();
      }
    }, { rootMargin: "200px" });

    state.scrollObserver.observe(sentinel);
  }
}

export function filterAndRender() {
  const q = (document.getElementById("station-search") as HTMLInputElement)
    ?.value.trim().toLowerCase() ?? "";
  state.filteredStations = q
    ? state.allStations.filter(s => s.name.toLowerCase().includes(q))
    : state.allStations;
  renderStations(state.filteredStations);
}

export function showNoData() {
  document.getElementById("stations-list")!.innerHTML = "";
  document.getElementById("no-data")!.style.display = "block";
}
