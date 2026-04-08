"""Write JSON output files to public/data/{service}/."""
import json
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_TZ_MADRID = ZoneInfo("Europe/Madrid")
from typing import Dict

from scripts.config import ServiceConfig

log = logging.getLogger(__name__)

StationData = Dict[str, dict]


def write_all(station_data: StationData, stats: dict, service: ServiceConfig) -> None:
    """
    Write one JSON per station into public/data/{service}/stations/{stop_id}.json
    and the global public/data/{service}/stats.json.
    """
    service.data_dir.mkdir(parents=True, exist_ok=True)
    service.stations_dir.mkdir(parents=True, exist_ok=True)

    now_madrid = datetime.now(_TZ_MADRID)
    generated_at = now_madrid.isoformat(timespec="seconds")
    stations_list = []

    for stop_id, data in station_data.items():
        payload = {
            "station_id": stop_id,
            "name": data["name"],
            "generated_at": generated_at,
            "arrivals": data["arrivals"],
        }
        dest = service.stations_dir / f"{stop_id}.json"
        dest.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        delayed = [a for a in data["arrivals"] if a.get("status") in ("retraso_leve", "retraso_alto")]
        max_delay = max((a.get("delay_min") or 0 for a in data["arrivals"]), default=0)
        stations_list.append(
            {
                "id": stop_id,
                "name": data["name"],
                "arrivals_count": len(data["arrivals"]),
                "delayed_count": len(delayed),
                "max_delay_min": max_delay,
            }
        )

    log.info(f"[{service.label}] Wrote {len(station_data)} station files to {service.stations_dir}")

    stats_payload = {
        "generated_at": generated_at,
        "stats": stats,
        "stations": sorted(stations_list, key=lambda x: x["name"]),
    }
    stats_path = service.data_dir / "stats.json"
    stats_path.write_text(
        json.dumps(stats_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info(f"[{service.label}] Wrote {stats_path}")


def write_history(stats: dict, service: ServiceConfig) -> None:
    """
    Append a snapshot of today's stats to public/data/{service}/history.json.
    Each record is one pipeline run. Records older than HISTORY_RETENTION_DAYS are pruned.
    """
    history_path = service.data_dir / "history.json"

    records: list = []
    if history_path.exists():
        try:
            records = json.loads(history_path.read_text(encoding="utf-8")).get("records", [])
        except Exception:
            records = []

    # Append new snapshot
    percs = stats.get("delay_percentiles", {})
    # Compact by_train_type for history: {label: [total, delayed, avg_min]}
    by_type_compact = {
        tt: [v["total"], v["delayed"], v["avg_delay_min"]]
        for tt, v in stats.get("by_train_type", {}).items()
    }
    records.append({
        "ts":      datetime.now(_TZ_MADRID).strftime("%Y-%m-%dT%H:%M"),
        "date":    datetime.now(_TZ_MADRID).strftime("%Y-%m-%d"),
        "total":   stats.get("total_trains", 0),
        "trips":   stats.get("unique_trips", 0),
        "delayed": stats.get("delayed", 0),
        "avg_min": stats.get("avg_delay_min", 0.0),
        "max_min": stats.get("max_delay_min", 0),
        "p50":     percs.get("p50", 0),
        "p75":     percs.get("p75", 0),
        "p90":     percs.get("p90", 0),
        "by_type": by_type_compact,
    })

    history_path.write_text(
        json.dumps({"records": records}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    log.info(f"[{service.label}] History updated — {len(records)} snapshots")


def write_station_history(station_data: StationData, service: ServiceConfig) -> None:
    """
    Append a per-station snapshot to public/data/{service}/station-history/YYYY-MM-DD.json.
    Only active stations (arrivals > 0) are stored, with compact keys to keep files small.
    Files older than STATION_HISTORY_RETENTION_DAYS are pruned automatically.
    """
    from scripts.config import STATION_HISTORY_RETENTION_DAYS

    history_dir = service.station_history_dir
    history_dir.mkdir(parents=True, exist_ok=True)

    now_madrid = datetime.now(_TZ_MADRID)
    date_str = now_madrid.strftime("%Y-%m-%d")
    time_str = now_madrid.strftime("%H:%M")
    day_path = history_dir / f"{date_str}.json"

    snapshots: list = []
    if day_path.exists():
        try:
            snapshots = json.loads(day_path.read_text(encoding="utf-8")).get("snapshots", [])
        except Exception:
            snapshots = []

    active_stations = []
    for stop_id, data in station_data.items():
        arrivals = data.get("arrivals", [])
        if not arrivals:
            continue
        delayed = sum(1 for a in arrivals if a.get("status") in ("retraso_leve", "retraso_alto"))
        max_delay = max((a.get("delay_min") or 0 for a in arrivals), default=0)
        active_stations.append({
            "id": stop_id,
            "t": len(arrivals),
            "d": delayed,
            "mx": round(float(max_delay), 1),
        })

    snapshots.append({"ts": time_str, "st": active_stations})

    day_path.write_text(
        json.dumps({"date": date_str, "snapshots": snapshots}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    # Prune files older than retention window
    cutoff = (now_madrid - timedelta(days=STATION_HISTORY_RETENTION_DAYS)).date()
    for old_file in history_dir.glob("*.json"):
        try:
            if datetime.strptime(old_file.stem, "%Y-%m-%d").date() < cutoff:
                old_file.unlink()
                log.info(f"[{service.label}] Pruned old station-history: {old_file.name}")
        except ValueError:
            pass

    log.info(f"[{service.label}] Station history updated — {len(active_stations)} active stations at {time_str}")


def write_raw_events(station_data: StationData, service: ServiceConfig) -> None:
    """
    Append delayed/cancelled arrivals to public/data/{service}/raw/YYYY-MM.json (NDJSON).
    Only stores arrivals with delay_min > 0 or status = cancelado.
    Files are kept on VPS only — excluded from git via .gitignore.
    """
    raw_dir = service.data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    now_madrid = datetime.now(_TZ_MADRID)
    ts = now_madrid.strftime("%Y-%m-%dT%H:%M")
    raw_path = raw_dir / f"{now_madrid.strftime('%Y-%m')}.json"

    events = []
    for stop_id, data in station_data.items():
        for arr in data.get("arrivals", []):
            status = arr.get("status")
            delay_min = arr.get("delay_min") or 0
            if delay_min <= 0 and status != "cancelado":
                continue
            events.append({
                "ts":         ts,
                "trip_id":    arr.get("trip_id", ""),
                "route_id":   arr.get("route_id", ""),
                "train_type": arr.get("train_type", "Otros"),
                "stop_id":    stop_id,
                "stop_name":  data["name"],
                "delay_min":  delay_min,
                "status":     status,
            })

    if not events:
        return

    lines = "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n"
    with open(raw_path, "a", encoding="utf-8") as f:
        f.write(lines)

    log.info(f"[{service.label}] Raw events appended — {len(events)} events → {raw_path.name}")


def write_by_type_arrivals(station_data: StationData, service: ServiceConfig) -> None:
    """
    Write per-train-type arrival lists to public/data/{service}/by_type_arrivals.json.
    Includes only arrivals with delay > 0 or status=cancelado, enriched with stop info,
    sorted by delay descending. Capped at 200 entries per type to keep the file small.
    """
    from collections import defaultdict
    MAX_PER_TYPE = 200

    by_type: Dict[str, list] = defaultdict(list)

    for stop_id, data in station_data.items():
        stop_name = data["name"]
        for arr in data.get("arrivals", []):
            status = arr.get("status")
            delay_min = arr.get("delay_min") or 0
            if delay_min <= 0 and status != "cancelado":
                continue
            train_type = arr.get("train_type") or "Otros"
            by_type[train_type].append({
                "train_name":     arr.get("train_name", ""),
                "headsign":       arr.get("headsign", ""),
                "origin":         arr.get("origin", ""),
                "stop_id":        stop_id,
                "stop_name":      stop_name,
                "scheduled_time": arr.get("scheduled_time", ""),
                "estimated_time": arr.get("estimated_time"),
                "delay_min":      delay_min,
                "status":         status,
            })

    # Sort each type by delay desc, cap at MAX_PER_TYPE
    result = {
        t: sorted(arrivals, key=lambda x: -(x["delay_min"] or 0))[:MAX_PER_TYPE]
        for t, arrivals in by_type.items()
    }

    path = service.data_dir / "by_type_arrivals.json"
    path.write_text(
        json.dumps({
            "generated_at": datetime.now(_TZ_MADRID).isoformat(timespec="seconds"),
            "by_type": result,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"[{service.label}] Wrote by_type_arrivals — {sum(len(v) for v in result.values())} entries across {len(result)} types")


def write_by_ccaa_arrivals(station_data: StationData, service: ServiceConfig) -> None:
    """
    Write per-CCAA arrival lists to public/data/{service}/by_ccaa_arrivals.json.
    Includes only arrivals with delay > 0 or status=cancelado, capped at 200 per CCAA.
    """
    from collections import defaultdict
    from scripts.config_zones import get_ccaa
    MAX_PER_CCAA = 200

    by_ccaa: Dict[str, list] = defaultdict(list)

    for stop_id, data in station_data.items():
        stop_name = data["name"]
        ccaa = get_ccaa(stop_id)
        for arr in data.get("arrivals", []):
            status = arr.get("status")
            delay_min = arr.get("delay_min") or 0
            if delay_min <= 0 and status != "cancelado":
                continue
            by_ccaa[ccaa].append({
                "train_name":     arr.get("train_name", ""),
                "train_type":     arr.get("train_type") or "Otros",
                "headsign":       arr.get("headsign", ""),
                "origin":         arr.get("origin", ""),
                "stop_id":        stop_id,
                "stop_name":      stop_name,
                "scheduled_time": arr.get("scheduled_time", ""),
                "estimated_time": arr.get("estimated_time"),
                "delay_min":      delay_min,
                "status":         status,
            })

    result = {
        ccaa: sorted(arrivals, key=lambda x: -(x["delay_min"] or 0))[:MAX_PER_CCAA]
        for ccaa, arrivals in by_ccaa.items()
    }

    path = service.data_dir / "by_ccaa_arrivals.json"
    path.write_text(
        json.dumps({
            "generated_at": datetime.now(_TZ_MADRID).isoformat(timespec="seconds"),
            "by_ccaa": result,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"[{service.label}] Wrote by_ccaa_arrivals — {sum(len(v) for v in result.values())} entries across {len(result)} ccaa")


def write_zones(stats: dict, service: ServiceConfig) -> None:
    """Write public/data/{service}/zones.json with per-CCAA and per-nucleo stats."""
    path = service.data_dir / "zones.json"
    path.write_text(
        json.dumps({
            "generated_at": datetime.now(_TZ_MADRID).isoformat(timespec="seconds"),
            "ccaa":   stats.get("by_ccaa", []),
            "nucleos": stats.get("by_nucleo", []),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(
        f"[{service.label}] Wrote zones.json — "
        f"{len(stats.get('by_ccaa', []))} CCAA, {len(stats.get('by_nucleo', []))} nucleos"
    )


def write_by_route_arrivals(station_data: StationData, service: ServiceConfig) -> None:
    """
    Write per-route (train_name) arrival stats to public/data/{service}/by_route_arrivals.json.
    Groups all arrivals by train_name, computes stats (total, delayed, cancelled, delayed_pct,
    avg_delay_min, max_delay_min), and keeps up to 50 delayed/cancelled arrivals per route.
    Routes are sorted by delayed_pct descending.
    """
    from collections import defaultdict
    MAX_PER_ROUTE = 50

    # Accumulators: route_key → dict with list fields
    route_all: Dict[str, list] = defaultdict(list)      # all arrivals for stats
    route_delayed: Dict[str, list] = defaultdict(list)  # only delayed/cancelled for display
    route_type: Dict[str, str] = {}                     # train_name → train_type

    for stop_id, data in station_data.items():
        stop_name = data["name"]
        for arr in data.get("arrivals", []):
            train_name = arr.get("train_name", "").strip()
            if not train_name:
                continue
            train_type = arr.get("train_type") or "Otros"
            route_all[train_name].append(arr)
            if train_name not in route_type:
                route_type[train_name] = train_type

            status = arr.get("status")
            delay_min = arr.get("delay_min") or 0
            if delay_min > 0 or status == "cancelado":
                route_delayed[train_name].append({
                    "train_name":     train_name,
                    "headsign":       arr.get("headsign", ""),
                    "origin":         arr.get("origin", ""),
                    "stop_id":        stop_id,
                    "stop_name":      stop_name,
                    "scheduled_time": arr.get("scheduled_time", ""),
                    "estimated_time": arr.get("estimated_time"),
                    "delay_min":      delay_min,
                    "status":         status,
                })

    routes = []
    for train_name, arrivals in route_all.items():
        total = len(arrivals)
        delayed = sum(
            1 for a in arrivals
            if a.get("status") in ("retraso_leve", "retraso_alto")
        )
        cancelled = sum(1 for a in arrivals if a.get("status") == "cancelado")
        delayed_pct = round((delayed + cancelled) / total, 4) if total else 0.0
        delay_values = [a.get("delay_min") or 0 for a in arrivals if (a.get("delay_min") or 0) > 0]
        avg_delay_min = round(sum(delay_values) / len(delay_values), 1) if delay_values else 0.0
        max_delay_min = round(float(max(delay_values)), 1) if delay_values else 0.0

        sorted_arrivals = sorted(
            route_delayed.get(train_name, []),
            key=lambda x: -(x["delay_min"] or 0)
        )[:MAX_PER_ROUTE]

        routes.append({
            "train_name":    train_name,
            "train_type":    route_type.get(train_name, "Otros"),
            "total":         total,
            "delayed":       delayed,
            "cancelled":     cancelled,
            "delayed_pct":   delayed_pct,
            "avg_delay_min": avg_delay_min,
            "max_delay_min": max_delay_min,
            "arrivals":      sorted_arrivals,
        })

    routes.sort(key=lambda r: -r["delayed_pct"])

    path = service.data_dir / "by_route_arrivals.json"
    path.write_text(
        json.dumps({
            "generated_at": datetime.now(_TZ_MADRID).isoformat(timespec="seconds"),
            "routes": routes,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(
        f"[{service.label}] Wrote by_route_arrivals — {len(routes)} routes"
    )


def write_routes_geo(gtfs_dir, station_data: StationData, service: ServiceConfig) -> None:
    """
    Write public/data/{service}/routes_geo.json with route stop sequences,
    shape polylines, and current-snapshot delay stats.

    Static geo data (stop sequences + shapes) is cached in
    .cache/routes_static/{service.name}.json and only rebuilt when the GTFS
    static feed is newer than the cache (i.e. once per 24 h).
    Delay stats are always recomputed from station_data.
    """
    from scripts.processing.routes import build_routes_static, compute_route_stats, compute_route_chronic_stats
    from scripts.config import CACHE_DIR, BASE_DIR

    cache_dir = CACHE_DIR / "routes_static"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{service.name}.json"

    # Rebuild static geo only when GTFS stops.txt is newer than cache
    gtfs_stops = gtfs_dir / "stops.txt"
    need_rebuild = (
        not cache_path.exists()
        or not gtfs_stops.exists()
        or gtfs_stops.stat().st_mtime > cache_path.stat().st_mtime
    )

    if need_rebuild:
        log.info(f"[{service.label}] Rebuilding routes static geo (GTFS refreshed)")
        static_routes = build_routes_static(gtfs_dir)
        cache_path.write_text(
            json.dumps(static_routes, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        log.info(f"[{service.label}] Routes static geo cached — {len(static_routes)} routes")
    else:
        static_routes = json.loads(cache_path.read_text(encoding="utf-8"))
        log.info(f"[{service.label}] Routes static geo loaded from cache — {len(static_routes)} routes")

    # Always update stats from current snapshot
    route_stats = compute_route_stats(station_data)
    _empty_stats = {
        "total": 0, "delayed": 0, "cancelled": 0,
        "delayed_pct": 0.0, "avg_delay_min": 0.0, "max_delay_min": 0.0,
    }
    chronic_stats = compute_route_chronic_stats(service.name, BASE_DIR / "data")
    _empty_chronic = {"chronic_avg_delay_min": 0.0, "chronic_delayed_pct": 0.0, "chronic_n_snapshots": 0}
    for r in static_routes:
        r["stats"] = route_stats.get(r["route_id"], dict(_empty_stats))
        r["chronic_stats"] = chronic_stats.get(r["route_id"], dict(_empty_chronic))

    # Sort by delayed_pct desc, then by total desc
    static_routes.sort(key=lambda r: (-r["stats"]["delayed_pct"], -r["stats"]["total"]))

    path = service.data_dir / "routes_geo.json"
    path.write_text(
        json.dumps({
            "generated_at": datetime.now(_TZ_MADRID).isoformat(timespec="seconds"),
            "routes": static_routes,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(
        f"[{service.label}] Wrote routes_geo.json — "
        f"{len(static_routes)} routes, "
        f"{sum(1 for r in static_routes if r['stats']['total'] > 0)} active"
    )


def write_insights(insights: list, service: ServiceConfig) -> None:
    """Write computed insights to public/data/{service}/insights.json."""
    path = service.data_dir / "insights.json"
    path.write_text(
        json.dumps({
            "generated_at": datetime.now(_TZ_MADRID).strftime("%Y-%m-%dT%H:%M"),
            "insights": insights,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"[{service.label}] Wrote {len(insights)} insights")
