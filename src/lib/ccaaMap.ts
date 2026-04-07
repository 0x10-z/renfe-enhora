/**
 * Choropleth map for CCAA (Comunidades Autónomas) using Leaflet + GeoJSON.
 * Embedded inside the zones section — separate from the main stations map.
 */
import type * as L from "leaflet";
import type { openCcaaDetail as OpenCcaaDetailFn } from "./ccaaDetailModal";

let _openCcaaDetail: typeof OpenCcaaDetailFn | null = null;

export function setCcaaClickHandler(fn: typeof OpenCcaaDetailFn) {
  _openCcaaDetail = fn;
}

type LeafletType = typeof L;

let _L: LeafletType | null = null;
let _mapInstance: L.Map | null = null;
let _geoLayer: L.GeoJSON | null = null;
let _geojson: any = null;

async function getLeaflet(): Promise<LeafletType> {
  if (!_L) {
    await import("leaflet/dist/leaflet.css");
    _L = (await import("leaflet")).default as unknown as LeafletType;
  }
  return _L;
}

// GeoJSON NAME_1 → pipeline CCAA name
const NAME_MAP: Record<string, string> = {
  "Ceuta y Melilla": "Ceuta",
  "Cataluña":        "Cataluña",
  // rest are identical
};
function normalizeName(geojsonName: string): string {
  return NAME_MAP[geojsonName] ?? geojsonName;
}

function delayColor(pct: number): string {
  if (pct >= 0.30) return "#dc2626";
  if (pct >= 0.20) return "#ea580c";
  if (pct >= 0.10) return "#d97706";
  if (pct >= 0.03) return "#65a30d";
  return "#16a34a";
}

export async function renderCcaaChoropleth(ccaaData: any[]): Promise<void> {
  const L = await getLeaflet();
  const container = document.getElementById("ccaa-map-container") as HTMLElement | null;
  if (!container) return;

  // Build lookup: normalized_name → zone stats
  const lookup: Record<string, any> = {};
  for (const z of ccaaData) {
    lookup[z.name] = z;
  }

  // Load GeoJSON once
  if (!_geojson) {
    try {
      const res = await fetch("/data/spain-ccaa.geojson");
      if (!res.ok) return;
      _geojson = await res.json();
    } catch {
      return;
    }
  }

  // Init map once
  if (!_mapInstance) {
    _mapInstance = L.map(container, {
      center: [40.2, -3.6],
      zoom: 5,
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: false,
      dragging: true,
      doubleClickZoom: true,
    });
    // No tile layer — clean choropleth look
  }

  // Remove previous layer
  if (_geoLayer) {
    _geoLayer.remove();
    _geoLayer = null;
  }

  _geoLayer = (L as any).geoJSON(_geojson, {
    style: (feature: any) => {
      const name = normalizeName(feature.properties.NAME_1 ?? "");
      const z = lookup[name];
      const pct = z ? z.delayed_pct : 0;
      const hasData = !!z;
      return {
        fillColor:   hasData ? delayColor(pct) : "#94a3b8",
        fillOpacity: hasData ? 0.78 : 0.25,
        color:       "var(--bg-card, #1e293b)",
        weight:      1.2,
        opacity:     0.9,
      };
    },
    onEachFeature: (feature: any, layer: any) => {
      const name = normalizeName(feature.properties.NAME_1 ?? "");
      const z = lookup[name];
      if (z) {
        const pct = Math.round(z.delayed_pct * 100);
        const avg = z.avg_delay_min > 0 ? `<br/>Retraso medio: <b>${z.avg_delay_min.toFixed(1)} min</b>` : "";
        layer.bindTooltip(
          `<b>${z.name}</b><br/>${pct}% con retrasos${avg}<br/><span style="color:#94a3b8;font-size:0.8em">${z.total} trenes · ${z.stations_count} estaciones</span>`,
          { sticky: true, direction: "top" }
        );
      } else {
        layer.bindTooltip(`<b>${name}</b><br/><span style="color:#94a3b8">Sin datos</span>`, { sticky: true });
      }

      layer.on("mouseover", () => {
        layer.setStyle({ fillOpacity: 0.95, weight: 2.2 });
        layer.bringToFront();
      });
      layer.on("mouseout", () => {
        (_geoLayer as any)?.resetStyle(layer);
      });
      if (z) {
        layer.on("click", () => _openCcaaDetail?.(z.name));
        layer.getElement?.()?.style.setProperty("cursor", "pointer");
      }
    },
  }).addTo(_mapInstance);

  // Fit to Spain mainland bounds
  _mapInstance.fitBounds([[35.9, -9.3], [43.8, 4.3]], { padding: [8, 8] });

  // Pointer cursor on interactive regions
  container.style.cursor = "default";
  (_geoLayer as any)?.eachLayer((l: any) => {
    const el = l.getElement?.();
    if (el) el.style.cursor = "pointer";
  });
}

export function destroyCcaaMap(): void {
  if (_mapInstance) {
    _mapInstance.remove();
    _mapInstance = null;
    _geoLayer = null;
  }
}
