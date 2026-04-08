"""
Build enriched route geographic data: stop sequences with lat/lon, shape polylines,
and per-snapshot delay stats.

Design: static geo data (stops, shapes) is expensive to compute from stop_times.txt
(1.9 M rows for cercanías), so it is cached in .cache/routes_static/{service}.json
and only rebuilt when the GTFS static feed is refreshed (every 24 h).
Per-snapshot delay stats are always computed fresh from station_data.
"""
import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

log = logging.getLogger(__name__)

_DOWNSAMPLE_MAX = 70  # max shape points per route


# ── GTFS helpers ──────────────────────────────────────────────────────────────

def _gtfs_reader(f):
    reader = csv.DictReader(f)
    if reader.fieldnames:
        reader.fieldnames = [k.strip() for k in reader.fieldnames]
    for row in reader:
        yield {k.strip(): (v.strip() if v else "") for k, v in row.items()}


def _load_stops_geo(gtfs_dir: Path) -> Dict[str, dict]:
    """Returns {stop_id: {name, lat, lon}}."""
    stops: Dict[str, dict] = {}
    with open(gtfs_dir / "stops.txt", encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            try:
                lat = float(row.get("stop_lat") or 0)
                lon = float(row.get("stop_lon") or 0)
                stops[row["stop_id"]] = {
                    "name": row["stop_name"],
                    "lat": lat,
                    "lon": lon,
                }
            except (ValueError, KeyError):
                pass
    return stops


def _load_routes_meta(gtfs_dir: Path) -> Dict[str, dict]:
    """Returns {route_id: {short, long, color}}."""
    routes: Dict[str, dict] = {}
    with open(gtfs_dir / "routes.txt", encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            routes[row["route_id"]] = {
                "short": row.get("route_short_name", "").strip(),
                "long":  row.get("route_long_name",  "").strip(),
                "color": row.get("route_color", "").strip(),
            }
    return routes


def _load_trips_meta(gtfs_dir: Path) -> Tuple[Dict[str, dict], Dict[str, str]]:
    """
    Returns:
        trips  — {trip_id: {route_id, shape_id}}
        route_rep — {route_id: trip_id}  one representative trip per route
    """
    trips: Dict[str, dict] = {}
    route_rep: Dict[str, str] = {}
    with open(gtfs_dir / "trips.txt", encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            tid = row["trip_id"]
            rid = row["route_id"]
            trips[tid] = {
                "route_id":  rid,
                "shape_id":  row.get("shape_id", "").strip(),
            }
            if rid not in route_rep:
                route_rep[rid] = tid
    return trips, route_rep


def _load_stop_sequences(
    gtfs_dir: Path, target_trips: Set[str]
) -> Dict[str, List[Tuple[int, str]]]:
    """
    Stream stop_times.txt, collecting (sequence, stop_id) pairs only for
    target_trips.  Returns {trip_id: [(seq, stop_id), ...]}.
    """
    trip_stops: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    with open(gtfs_dir / "stop_times.txt", encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            tid = row["trip_id"]
            if tid not in target_trips:
                continue
            try:
                seq = int(row.get("stop_sequence") or 0)
                trip_stops[tid].append((seq, row["stop_id"]))
            except ValueError:
                pass
    return dict(trip_stops)


def _downsample(points: list, max_pts: int = _DOWNSAMPLE_MAX) -> list:
    if len(points) <= max_pts:
        return points
    step = len(points) / max_pts
    return [points[int(i * step)] for i in range(max_pts)]


def _load_shapes(
    gtfs_dir: Path, target_shape_ids: Set[str]
) -> Dict[str, List[List[float]]]:
    """Returns {shape_id: [[lat, lon], ...]} (downsampled)."""
    shapes_file = gtfs_dir / "shapes.txt"
    if not shapes_file.exists() or not target_shape_ids:
        return {}

    raw: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    with open(shapes_file, encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            sid = row.get("shape_id", "")
            if sid not in target_shape_ids:
                continue
            try:
                seq = int(row.get("shape_pt_sequence") or 0)
                lat = float(row["shape_pt_lat"])
                lon = float(row["shape_pt_lon"])
                raw[sid].append((seq, lat, lon))
            except (ValueError, KeyError):
                pass

    result: Dict[str, List[List[float]]] = {}
    for sid, pts in raw.items():
        coords = [[p[1], p[2]] for p in sorted(pts)]
        result[sid] = _downsample(coords)
    return result


# ── Static geo builder (cached 24 h) ─────────────────────────────────────────

def build_routes_static(gtfs_dir: Path) -> List[dict]:
    """
    Build route list with stop sequences and shape polylines from GTFS.
    This is the expensive part — called once per GTFS refresh.
    Returns list of dicts (no delay stats yet).
    """
    log.info(f"[routes] Building static geo from {gtfs_dir}")
    stops_geo    = _load_stops_geo(gtfs_dir)
    routes_meta  = _load_routes_meta(gtfs_dir)
    trips_meta, route_rep = _load_trips_meta(gtfs_dir)

    target_trips = set(route_rep.values())
    log.info(f"[routes] Loading stop sequences for {len(target_trips)} representative trips …")
    trip_stop_seqs = _load_stop_sequences(gtfs_dir, target_trips)
    log.info(f"[routes] Stop sequences loaded for {len(trip_stop_seqs)} trips")

    # Collect shape_ids for representative trips
    target_shape_ids = {
        trips_meta[tid]["shape_id"]
        for tid in target_trips
        if trips_meta.get(tid, {}).get("shape_id")
    }
    shapes = _load_shapes(gtfs_dir, target_shape_ids)
    log.info(f"[routes] Loaded {len(shapes)} shapes")

    result: List[dict] = []
    for route_id, meta in routes_meta.items():
        rep_tid = route_rep.get(route_id)
        if not rep_tid:
            continue

        trip     = trips_meta.get(rep_tid, {})
        shape_id = trip.get("shape_id", "")

        # Build ordered stop list
        stop_seq = trip_stop_seqs.get(rep_tid, [])
        stops_list = []
        for (seq, stop_id) in sorted(stop_seq):
            sg = stops_geo.get(stop_id, {})
            lat = sg.get("lat", 0)
            lon = sg.get("lon", 0)
            if lat and lon:
                stops_list.append({
                    "stop_id": stop_id,
                    "name":    sg.get("name", stop_id),
                    "lat":     lat,
                    "lon":     lon,
                })

        # Shape polyline (prefer shapes.txt; fallback to stop coordinates)
        shape_pts: Optional[List[List[float]]] = shapes.get(shape_id) if shape_id else None
        if not shape_pts and stops_list:
            shape_pts = [[s["lat"], s["lon"]] for s in stops_list]

        if not stops_list and not shape_pts:
            continue

        result.append({
            "route_id":         route_id,
            "route_short_name": meta["short"],
            "route_long_name":  meta["long"],
            "route_color":      meta["color"],
            "stops":            stops_list,
            "shape":            shape_pts or [],
        })

    log.info(f"[routes] Static geo built — {len(result)} routes")
    return result


# ── Per-snapshot stats ────────────────────────────────────────────────────────

def compute_route_stats(station_data: dict) -> Dict[str, dict]:
    """
    Aggregate delay stats per route_id from the current station_data snapshot.
    Returns {route_id: {total, delayed, cancelled, delayed_pct, avg_delay_min, max_delay_min}}.
    """
    accum: Dict[str, dict] = defaultdict(
        lambda: {"total": 0, "delayed": 0, "cancelled": 0, "delay_values": []}
    )

    for _stop_id, data in station_data.items():
        for arr in data.get("arrivals", []):
            route_id = arr.get("route_id", "")
            if not route_id:
                continue
            status    = arr.get("status", "")
            delay_min = arr.get("delay_min") or 0

            accum[route_id]["total"] += 1
            if status in ("retraso_leve", "retraso_alto"):
                accum[route_id]["delayed"] += 1
            elif status == "cancelado":
                accum[route_id]["cancelled"] += 1
            if delay_min > 0:
                accum[route_id]["delay_values"].append(float(delay_min))

    result: Dict[str, dict] = {}
    for route_id, d in accum.items():
        total    = d["total"]
        delayed  = d["delayed"]
        cancelled = d["cancelled"]
        dvals    = d["delay_values"]
        result[route_id] = {
            "total":         total,
            "delayed":       delayed,
            "cancelled":     cancelled,
            "delayed_pct":   round((delayed + cancelled) / total, 4) if total else 0.0,
            "avg_delay_min": round(sum(dvals) / len(dvals), 1) if dvals else 0.0,
            "max_delay_min": round(max(dvals), 1) if dvals else 0.0,
        }
    return result
