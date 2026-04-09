"""
Merge GTFS static schedule with GTFS-RT updates to produce per-station arrivals.

One streaming pass through stop_times.txt:
  - collects arrivals in the next LOOKAHEAD_MINUTES window
  - tracks the first stop of each trip (origin)
Then enriches each arrival with RT delay and classifies its status.
"""
import csv
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from scripts.config import (
    DELAY_LEVE_MAX_SEC,
    LOOKAHEAD_MINUTES,
    ON_TIME_THRESHOLD_SEC,
    TRAIN_TYPE_PREFIXES,
)
from scripts.ingestion.gtfs_realtime import TripUpdates

log = logging.getLogger(__name__)

# {stop_id: {"name": str, "arrivals": [Arrival dict]}}
StationData = Dict[str, dict]


def build_station_arrivals(
    gtfs_dir: Path,
    rt_updates: TripUpdates,
    now: Optional[datetime] = None,
    on_time_threshold_sec: int = ON_TIME_THRESHOLD_SEC,
    delay_leve_max_sec: int = DELAY_LEVE_MAX_SEC,
) -> StationData:
    """Build per-station arrivals for the next LOOKAHEAD_MINUTES window."""
    if now is None:
        now = datetime.now()

    service_date = now.date()
    lookahead = now + timedelta(minutes=LOOKAHEAD_MINUTES)

    log.info(
        f"Window: {now:%H:%M} → {lookahead:%H:%M} on {service_date}"
    )

    stops = _load_stops(gtfs_dir)
    active_svc = _get_active_services(gtfs_dir, service_date)

    if not active_svc:
        log.warning("No active services for today — falling back to all services")

    trips = _load_trips(gtfs_dir, active_svc)
    routes = _load_routes(gtfs_dir)
    log.info(f"Active trips: {len(trips)}")

    # Single pass through stop_times.txt
    arrivals_by_stop: Dict[str, List[dict]] = defaultdict(list)
    trip_first: Dict[str, tuple] = {}  # {trip_id: (min_seq, stop_id)}
    trip_last:  Dict[str, tuple] = {}  # {trip_id: (max_seq, stop_id)}
    all_active_stops: Set[str] = set()  # all stops that appear in active trips

    stop_times_path = gtfs_dir / "stop_times.txt"
    with open(stop_times_path, encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            trip_id = row["trip_id"]
            if trip_id not in trips:
                continue

            stop_id = row["stop_id"]
            all_active_stops.add(stop_id)
            seq = int(row.get("stop_sequence") or 0)

            # Track origin (first stop) and destination (last stop)
            prev = trip_first.get(trip_id)
            if prev is None or seq < prev[0]:
                trip_first[trip_id] = (seq, stop_id)
            last = trip_last.get(trip_id)
            if last is None or seq > last[0]:
                trip_last[trip_id] = (seq, stop_id)

            # Check if this stop is in the lookahead window
            time_str = (row.get("arrival_time") or row.get("departure_time") or "").strip()
            if not time_str:
                continue

            scheduled = _parse_gtfs_time(time_str, service_date)
            if not (now <= scheduled <= lookahead):
                continue

            arrivals_by_stop[stop_id].append(
                {"trip_id": trip_id, "seq": seq, "scheduled": scheduled}
            )

    log.info(f"Stops with arrivals in window: {len(arrivals_by_stop)} / {len(all_active_stops)} active")

    # Build origin and destination name lookups
    trip_origins = {
        tid: stops.get(sid, {}).get("name", sid)
        for tid, (_, sid) in trip_first.items()
    }
    trip_destinations = {
        tid: stops.get(sid, {}).get("name", sid)
        for tid, (_, sid) in trip_last.items()
    }

    # Enrich and classify each arrival
    station_data: StationData = {}

    for stop_id, raw in arrivals_by_stop.items():
        stop_name = stops.get(stop_id, {}).get("name", f"Parada {stop_id}")
        enriched = []

        for a in sorted(raw, key=lambda x: x["scheduled"]):
            trip = trips[a["trip_id"]]
            trip_rt = rt_updates.get(a["trip_id"], {})
            delay_sec = trip_rt.get(stop_id, trip_rt.get("*", 0))

            if delay_sec == -1:
                status = "cancelado"
                estimated_str = None
                delay_min = None
            else:
                estimated = a["scheduled"] + timedelta(seconds=delay_sec)
                delay_min = round(delay_sec / 60, 1)
                estimated_str = estimated.strftime("%H:%M")

                if delay_sec <= on_time_threshold_sec:
                    status = "en_hora"
                elif delay_sec <= delay_leve_max_sec:
                    status = "retraso_leve"
                else:
                    status = "retraso_alto"

            route_short = routes.get(trip["route_id"], "")
            trip_short = trip.get("trip_short_name", "")
            if route_short and trip_short:
                train_name = f"{route_short} {trip_short}"
            else:
                train_name = route_short or trip_short

            enriched.append(
                {
                    "trip_id": a["trip_id"],
                    "route_id": trip["route_id"],
                    "train_name": train_name,
                    "train_type": _classify_train_type(trip_short, route_short),
                    "headsign": trip["headsign"] or trip_destinations.get(a["trip_id"], ""),
                    "origin": trip_origins.get(a["trip_id"], ""),
                    "scheduled_time": a["scheduled"].strftime("%H:%M"),
                    "estimated_time": estimated_str,
                    "delay_min": delay_min,
                    "status": status,
                }
            )

        # Deduplicate: same train number + scheduled time + headsign
        seen: set = set()
        deduped = []
        for a in enriched:
            key = (a["train_name"], a["scheduled_time"], a["headsign"])
            if key not in seen:
                seen.add(key)
                deduped.append(a)

        station_data[stop_id] = {"name": stop_name, "arrivals": deduped}

    # Include all active stops that had no arrivals in the window
    for stop_id in all_active_stops:
        if stop_id not in station_data:
            stop_name = stops.get(stop_id, {}).get("name", f"Parada {stop_id}")
            station_data[stop_id] = {"name": stop_name, "arrivals": []}

    return station_data


# ── GTFS loaders ───────────────────────────────────────────────────────────────

def _gtfs_reader(f):
    """
    Wrapper around csv.DictReader that strips whitespace from all field names
    and values. Renfe GTFS files use fixed-width padding (trailing spaces).
    """
    reader = csv.DictReader(f)
    if reader.fieldnames:
        reader.fieldnames = [k.strip() for k in reader.fieldnames]
    for row in reader:
        yield {k.strip(): (v.strip() if v else v) for k, v in row.items()}


def _load_stops(gtfs_dir: Path) -> Dict[str, dict]:
    stops: Dict[str, dict] = {}
    with open(gtfs_dir / "stops.txt", encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            stops[row["stop_id"]] = {"name": row["stop_name"]}
    return stops


def _get_active_services(gtfs_dir: Path, service_date: date) -> Optional[Set[str]]:
    """Return set of service_ids active on service_date (calendar + exceptions)."""
    active: Set[str] = set()
    weekday = service_date.strftime("%A").lower()  # "monday", "tuesday" …
    date_str = service_date.strftime("%Y%m%d")

    cal = gtfs_dir / "calendar.txt"
    if cal.exists():
        with open(cal, encoding="utf-8-sig") as f:
            for row in _gtfs_reader(f):
                if (
                    row.get(weekday) == "1"
                    and row["start_date"] <= date_str <= row["end_date"]
                ):
                    active.add(row["service_id"])

    cal_dates = gtfs_dir / "calendar_dates.txt"
    if cal_dates.exists():
        with open(cal_dates, encoding="utf-8-sig") as f:
            for row in _gtfs_reader(f):
                if row["date"] != date_str:
                    continue
                if row["exception_type"] == "1":
                    active.add(row["service_id"])
                elif row["exception_type"] == "2":
                    active.discard(row["service_id"])

    return active or None


def _load_trips(
    gtfs_dir: Path, active_svc: Optional[Set[str]]
) -> Dict[str, dict]:
    trips: Dict[str, dict] = {}
    with open(gtfs_dir / "trips.txt", encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            if active_svc and row["service_id"] not in active_svc:
                continue
            trips[row["trip_id"]] = {
                "route_id": row.get("route_id", ""),
                "headsign": row.get("trip_headsign", "").strip(),
                "trip_short_name": row.get("trip_short_name", "").strip(),
                "service_id": row.get("service_id", ""),
            }
    return trips


def _load_routes(gtfs_dir: Path) -> Dict[str, str]:
    """Return {route_id: route_short_name} for all routes."""
    routes: Dict[str, str] = {}
    routes_path = gtfs_dir / "routes.txt"
    if not routes_path.exists():
        return routes
    with open(routes_path, encoding="utf-8-sig") as f:
        for row in _gtfs_reader(f):
            short = row.get("route_short_name", "").strip()
            if short:
                routes[row["route_id"].strip()] = short
    return routes


def _classify_train_type(trip_short_name: str, route_short_name: str) -> str:
    """Return a human-readable train type label for a given trip.

    Tries trip_short_name first, then route_short_name.
    In Renfe GTFS, trip_short_name is often just a numeric code (e.g. "13905")
    while route_short_name carries the type prefix (e.g. "MD", "AVE").
    """
    for candidate in [trip_short_name, route_short_name]:
        name = (candidate or "").strip().upper()
        if not name:
            continue
        for prefix, label in TRAIN_TYPE_PREFIXES:
            if name.startswith(prefix):
                return label
        # Cercanías lines: C1, C2, … C10, etc.
        if len(name) >= 2 and name[0] == "C" and name[1].isdigit():
            return "Cercanías"
    return "Otros"


def _parse_gtfs_time(time_str: str, service_date: date) -> datetime:
    """
    Parse a GTFS time string into a datetime.
    GTFS times can exceed 24:00:00 for overnight services (e.g. "25:30:00").
    """
    h, m, s = (int(x) for x in time_str.split(":"))
    extra_days = h // 24
    return datetime.combine(service_date, time(h % 24, m, s)) + timedelta(
        days=extra_days
    )
