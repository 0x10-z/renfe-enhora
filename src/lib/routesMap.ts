/**
 * Leaflet map logic for the /rutas page.
 * Draws route polylines colored by delay %, handles selection.
 * Communicates with the page via a "route:selected" CustomEvent.
 */
import type * as L from "leaflet";

type LeafletType = typeof L;

let _L: LeafletType | null = null;
let _map: L.Map | null = null;
let _routeLayer: L.LayerGroup | null = null;
let _routesData: RouteGeo[] | null = null;
let _selectedRouteId: string | null = null;
// Visual polylines (for styling)
let _visualLines: Map<string, L.Polyline> = new Map();

export interface RouteStop {
  stop_id: string;
  name: string;
  lat: number;
  lon: number;
}

export interface RouteStats {
  total: number;
  delayed: number;
  cancelled: number;
  delayed_pct: number;
  avg_delay_min: number;
  max_delay_min: number;
}

export interface RouteGeo {
  route_id: string;
  route_short_name: string;
  route_long_name: string;
  route_color: string;
  stops: RouteStop[];
  shape: [number, number][];
  stats: RouteStats;
}

/** Derive a human-readable "Origin → Destination" label for a route. */
export function getDisplayName(r: RouteGeo): string {
  // Prefer GTFS long_name when it's meaningful (not equal to short_name)
  if (r.route_long_name && r.route_long_name.trim() !== r.route_short_name.trim()) {
    return r.route_long_name.trim();
  }
  // Derive from first/last stop
  if (r.stops.length >= 2) {
    const origin = r.stops[0].name;
    const dest   = r.stops[r.stops.length - 1].name;
    return `${origin} → ${dest}`;
  }
  return r.route_short_name;
}

async function getLeaflet(): Promise<LeafletType> {
  if (!_L) {
    await import("leaflet/dist/leaflet.css");
    _L = (await import("leaflet")).default as unknown as LeafletType;
  }
  return _L;
}

export function delayColor(pct: number, total: number): string {
  if (total === 0) return "#c8cfd8";
  if (pct >= 0.5) return "#dc2626";
  if (pct >= 0.3) return "#c2410c";
  if (pct >= 0.1) return "#b45309";
  if (pct > 0)    return "#65a30d";
  return "#059669";
}

function visualWeight(pct: number, selected: boolean): number {
  const base = pct >= 0.3 ? 4 : pct >= 0.1 ? 3 : 2.5;
  return selected ? base + 2 : base;
}

export async function initRoutesMap(containerId = "routes-map"): Promise<void> {
  const L = await getLeaflet();
  const container = document.getElementById(containerId);
  if (!container || _map) return;

  _map = L.map(container, {
    center: [40.2, -3.5],
    zoom: 6,
    zoomControl: true,
    attributionControl: true,
  });

  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution:
      '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(_map);

  _routeLayer = L.layerGroup().addTo(_map);
}

export async function loadRoutesData(service: string): Promise<RouteGeo[]> {
  const res = await fetch(`/data/${service}/routes_geo.json`);
  if (!res.ok) throw new Error(`routes_geo.json not found for ${service}`);
  const json = await res.json();
  _routesData = json.routes as RouteGeo[];
  return _routesData;
}

export async function renderRoutePolylines(routes: RouteGeo[]): Promise<void> {
  const L = await getLeaflet();
  if (!_routeLayer || !_map) return;

  _routeLayer.clearLayers();
  _visualLines.clear();
  _selectedRouteId = null;

  for (const route of routes) {
    const pts = route.shape as [number, number][];
    if (!pts || pts.length < 2) continue;

    const color   = delayColor(route.stats.delayed_pct, route.stats.total);
    const weight  = visualWeight(route.stats.delayed_pct, false);
    const opacity = route.stats.total === 0 ? 0.35 : 0.8;
    const displayName = getDisplayName(route);
    const pctStr = route.stats.total > 0
      ? `${Math.round(route.stats.delayed_pct * 100)}% retraso`
      : "Sin tráfico ahora";

    // Visual line (non-interactive — just for display)
    const visual = L.polyline(pts, {
      color, weight, opacity,
      interactive: false,
    });
    visual.addTo(_routeLayer!);
    _visualLines.set(route.route_id, visual);

    // Invisible thick hit area — wide enough to click easily
    const hit = L.polyline(pts, {
      weight:  18,
      opacity: 0,
      interactive: true,
    });
    hit.bindTooltip(
      `<b>${route.route_short_name}</b><br>${displayName}<br><span style="color:${color}">${pctStr}</span>`,
      { sticky: true, className: "route-tooltip" }
    );
    hit.on("click", () => selectRoute(route.route_id));
    hit.addTo(_routeLayer!);
  }
}

export async function selectRoute(routeId: string): Promise<void> {
  const L = await getLeaflet();
  const routes = _routesData;
  if (!routes) return;

  const route = routes.find(r => r.route_id === routeId);
  if (!route) return;

  // Reset previous visual line style
  if (_selectedRouteId) {
    const prev = routes.find(r => r.route_id === _selectedRouteId);
    if (prev) {
      const vl = _visualLines.get(_selectedRouteId);
      if (vl) {
        vl.setStyle({
          color:   delayColor(prev.stats.delayed_pct, prev.stats.total),
          weight:  visualWeight(prev.stats.delayed_pct, false),
          opacity: prev.stats.total === 0 ? 0.35 : 0.8,
        });
      }
    }
  }

  // Highlight selected visual line
  _selectedRouteId = routeId;
  const vl = _visualLines.get(routeId);
  if (vl) {
    vl.setStyle({
      color:   delayColor(route.stats.delayed_pct, route.stats.total),
      weight:  visualWeight(route.stats.delayed_pct, true),
      opacity: 1,
    });
    vl.bringToFront();
  }

  // Fit map to route bounds
  if (_map && route.shape && route.shape.length > 1) {
    _map.fitBounds(L.latLngBounds(route.shape as [number, number][]), {
      padding: [40, 40],
      maxZoom: 12,
    });
  }

  // Render stop markers on map
  _renderStopMarkers(route, L);

  // Dispatch event so the page can show the detail panel
  document.dispatchEvent(new CustomEvent("route:selected", { detail: route }));
}

function _renderStopMarkers(route: RouteGeo, L: LeafletType): void {
  if (!_routeLayer) return;

  // Clear previous stop markers
  _routeLayer.eachLayer((layer: any) => {
    if (layer._isStopMarker) _routeLayer!.removeLayer(layer);
  });

  for (let i = 0; i < route.stops.length; i++) {
    const stop = route.stops[i];
    const isTerminal = i === 0 || i === route.stops.length - 1;

    const marker = L.circleMarker([stop.lat, stop.lon], {
      radius:      isTerminal ? 7 : 4,
      color:       "#fff",
      weight:      isTerminal ? 2 : 1.5,
      fillColor:   isTerminal ? "#0d9488" : "#6b7280",
      fillOpacity: 1,
      interactive: true,
    });
    marker.bindTooltip(stop.name, { sticky: true, className: "route-tooltip" });
    (marker as any)._isStopMarker = true;
    marker.addTo(_routeLayer!);
  }
}

export function getRoutesData(): RouteGeo[] | null {
  return _routesData;
}

export function destroyRoutesMap(): void {
  if (_map) {
    _map.remove();
    _map = null;
    _routeLayer = null;
    _visualLines.clear();
    _routesData = null;
    _selectedRouteId = null;
  }
}
