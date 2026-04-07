"""
One-off script to generate scripts/data/zones_map.json.

Reads public/data/stations_geo.json and assigns each station:
  - ccaa: comunidad autónoma (derived from provincia)
  - nucleo: nearest Cercanías hub (if within 80 km), else None

Run from repo root:
    python -m scripts.data.generate_zones_map
"""
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
GEO_FILE  = REPO_ROOT / "public" / "data" / "stations_geo.json"
OUT_FILE  = Path(__file__).parent / "zones_map.json"

# ── Provincia → CCAA ──────────────────────────────────────────────────────────
PROV_TO_CCAA: dict[str, str] = {
    "Álava":               "País Vasco",
    "Araba/Álava":         "País Vasco",
    "Albacete":            "Castilla-La Mancha",
    "Alicante":            "Comunidad Valenciana",
    "Alicante/Alacant":    "Comunidad Valenciana",
    "Almería":             "Andalucía",
    "Asturias":            "Principado de Asturias",
    "Ávila":               "Castilla y León",
    "Badajoz":             "Extremadura",
    "Barcelona":           "Cataluña",
    "Bizkaia":             "País Vasco",
    "Burgos":              "Castilla y León",
    "Cáceres":             "Extremadura",
    "Cádiz":               "Andalucía",
    "Cantabria":           "Cantabria",
    "Castellón":           "Comunidad Valenciana",
    "Castellón/Castelló":  "Comunidad Valenciana",
    "Ciudad Real":         "Castilla-La Mancha",
    "Córdoba":             "Andalucía",
    "Coruña, A":           "Galicia",
    "Cuenca":              "Castilla-La Mancha",
    "Ceuta":               "Ceuta",
    "Gipuzkoa":            "País Vasco",
    "Girona":              "Cataluña",
    "Granada":             "Andalucía",
    "Guadalajara":         "Castilla-La Mancha",
    "Huelva":              "Andalucía",
    "Huesca":              "Aragón",
    "Jaén":                "Andalucía",
    "León":                "Castilla y León",
    "Lleida":              "Cataluña",
    "Lugo":                "Galicia",
    "Madrid":              "Comunidad de Madrid",
    "Málaga":              "Andalucía",
    "Murcia":              "Región de Murcia",
    "Navarra":             "Comunidad Foral de Navarra",
    "Ourense":             "Galicia",
    "Palencia":            "Castilla y León",
    "Pontevedra":          "Galicia",
    "Rioja, La":           "La Rioja",
    "Salamanca":           "Castilla y León",
    "Segovia":             "Castilla y León",
    "Sevilla":             "Andalucía",
    "Soria":               "Castilla y León",
    "Tarragona":           "Cataluña",
    "Teruel":              "Aragón",
    "Toledo":              "Castilla-La Mancha",
    "Valencia":            "Comunidad Valenciana",
    "Valencia/València":   "Comunidad Valenciana",
    "Valladolid":          "Castilla y León",
    "Zamora":              "Castilla y León",
    "Zaragoza":            "Aragón",
}

# ── Cercanías hubs with approximate centroid coords ───────────────────────────
# Radius within which a station is considered part of the hub (km)
HUB_RADIUS_KM = 80

NUCLEOS: list[dict] = [
    {"id": "madrid",         "name": "Núcleo Madrid",         "lat": 40.4168,  "lng": -3.7038},
    {"id": "barcelona",      "name": "Núcleo Barcelona",      "lat": 41.3851,  "lng":  2.1734},
    {"id": "valencia",       "name": "Núcleo Valencia",       "lat": 39.4699,  "lng": -0.3763},
    {"id": "sevilla",        "name": "Núcleo Sevilla",        "lat": 37.3886,  "lng": -5.9823},
    {"id": "bilbao",         "name": "Núcleo Bilbao",         "lat": 43.2627,  "lng": -2.9253},
    {"id": "asturias",       "name": "Núcleo Asturias",       "lat": 43.3614,  "lng": -5.8593},
    {"id": "murcia",         "name": "Núcleo Murcia-Alicante","lat": 38.0,     "lng": -1.13},
    {"id": "zaragoza",       "name": "Núcleo Zaragoza",       "lat": 41.6488,  "lng": -0.8891},
    {"id": "san_sebastian",  "name": "Núcleo San Sebastián",  "lat": 43.3183,  "lng": -1.9812},
    {"id": "santander",      "name": "Núcleo Santander",      "lat": 43.4623,  "lng": -3.8099},
    {"id": "cadiz",          "name": "Núcleo Cádiz-Málaga",   "lat": 36.9,     "lng": -5.6},
    {"id": "almeria",        "name": "Núcleo Almería",        "lat": 36.8399,  "lng": -2.4597},
]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def nearest_nucleo(lat: float, lng: float) -> str | None:
    best_id, best_dist = None, float("inf")
    for hub in NUCLEOS:
        d = haversine_km(lat, lng, hub["lat"], hub["lng"])
        if d < best_dist:
            best_dist = d
            best_id = hub["id"]
    return best_id if best_dist <= HUB_RADIUS_KM else None


def main() -> None:
    geo = json.loads(GEO_FILE.read_text(encoding="utf-8"))

    zones: dict[str, dict] = {}
    unknown_prov: set[str] = set()

    for stop_id, station in geo.items():
        prov = (station.get("provincia") or "").strip()
        lat  = station.get("lat")
        lng  = station.get("lng")

        ccaa = PROV_TO_CCAA.get(prov)
        if not ccaa:
            ccaa = "Desconocida"
            if prov and prov != "Desconocido":
                unknown_prov.add(prov)

        nucleo = nearest_nucleo(lat, lng) if lat and lng else None

        zones[stop_id] = {
            "ccaa":   ccaa,
            "nucleo": nucleo,
        }

    if unknown_prov:
        print(f"[WARN] Unmapped provinces: {sorted(unknown_prov)}")

    nucleos_count = sum(1 for v in zones.values() if v["nucleo"])
    ccaa_known    = sum(1 for v in zones.values() if v["ccaa"] != "Desconocida")
    print(f"Generated {len(zones)} entries: {ccaa_known} with CCAA, {nucleos_count} with nucleo")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(zones, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Written → {OUT_FILE}")


if __name__ == "__main__":
    main()
