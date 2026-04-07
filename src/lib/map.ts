import type * as L from "leaflet";
import { state } from "./store";
import { fmtDelay } from "./utils";

type LeafletType = typeof L;

let _L: LeafletType | null = null;

async function getLeaflet(): Promise<LeafletType> {
  if (!_L) {
    await import("leaflet/dist/leaflet.css");
    _L = (await import("leaflet")).default as unknown as LeafletType;
  }
  return _L;
}

export async function initMap(): Promise<void> {
  const L = await getLeaflet();
  const container = document.getElementById("map-container") as HTMLElement;
  if (!container || state.mapInstance) return;

  state.mapInstance = L.map(container, {
    center: [40.2, -3.5],
    zoom: 6,
    zoomControl: true,
    attributionControl: true,
  });

  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(state.mapInstance as L.Map);

  state.mapLayer = L.layerGroup().addTo(state.mapInstance as L.Map);
}

export async function destroyMap(): Promise<void> {
  if (state.mapInstance) {
    (state.mapInstance as L.Map).remove();
    state.mapInstance = null;
    state.mapLayer = null;
  }
}

export async function loadGeoIfNeeded(): Promise<void> {
  if (state.mapGeo) return;
  try {
    const res = await fetch("/data/stations_geo.json");
    if (!res.ok) return;
    state.mapGeo = await res.json();
  } catch {
    // geo not yet generated — map will show empty
  }
}

export async function renderMapMarkers(): Promise<void> {
  const L = await getLeaflet();
  const layer = state.mapLayer as L.LayerGroup | null;
  if (!layer) return;

  layer.clearLayers();

  const geo = state.mapGeo;
  if (!geo) {
    showMapMessage("Ejecuta scripts/fetch_stations_geo.py para generar los datos de coordenadas.");
    return;
  }

  hideMapMessage();

  const stations: any[] = state.allStations;
  const mode: "scatter" | "heat" = state.mapMode;
  let rendered = 0;
  for (const st of stations) {
    const g = geo[st.id];
    if (!g) continue;

    const ratio = st.arrivals_count > 0 ? st.delayed_count / st.arrivals_count : 0;
    const color = ratio > 0.5 ? "#dc2626" : ratio > 0.2 ? "#b45309" : "#059669";
    const pct = st.arrivals_count > 0 ? Math.round(ratio * 100) : 0;
    const label = `<b>${st.name}</b><br/>${pct}% de retrasos · ${st.arrivals_count} paradas<br/>${st.delayed_count} retrasadas · Máx. ${fmtDelay(st.max_delay_min, false)}`;

    if (mode === "scatter") {
      const radius = Math.max(5, Math.min(18, 5 + Math.sqrt(st.arrivals_count) * 1.2));
      (L as any).circleMarker([g.lat, g.lng], {
        radius,
        fillColor: color,
        color: "#fff",
        weight: 1,
        opacity: 1,
        fillOpacity: st.arrivals_count === 0 ? 0.15 : 0.75,
      })
        .bindTooltip(label, { direction: "top", sticky: true })
        .addTo(layer);
    } else {
      // heatmap: size = volume of delayed trains, color+opacity = ratio severity
      const r = Math.max(7, Math.min(36, 6 + Math.sqrt(st.delayed_count) * 6));
      const opacity = Math.max(0.1, ratio) * 0.7;
      (L as any).circleMarker([g.lat, g.lng], {
        radius: r,
        fillColor: color,
        color: "transparent",
        weight: 0,
        fillOpacity: opacity,
      })
        .bindTooltip(label, { direction: "top", sticky: true })
        .addTo(layer);
    }
    rendered++;
  }

  if (rendered === 0 && stations.length > 0) {
    showMapMessage("No se encontraron coordenadas para las estaciones activas. Verifica stations_geo.json.");
  }
}

function showMapMessage(msg: string) {
  const el = document.getElementById("map-message");
  if (el) { el.textContent = msg; el.style.display = "flex"; }
}

function hideMapMessage() {
  const el = document.getElementById("map-message");
  if (el) el.style.display = "none";
}
