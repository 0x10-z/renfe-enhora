"""Fetch and parse Renfe GTFS-RT trip updates."""
import logging
from typing import Dict

import requests
import urllib3

from scripts.config import REQUEST_TIMEOUT, ServiceConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
log = logging.getLogger(__name__)

# {trip_id: {stop_id: delay_seconds}}  (-1 means cancelled/skipped)
TripUpdates = Dict[str, Dict[str, int]]


def fetch_trip_updates(service: ServiceConfig) -> TripUpdates:
    """
    Fetch realtime trip updates for the given service.
    Returns empty dict when no RT feed is configured or on total failure.
    """
    if not service.gtfs_rt_json_url and not service.gtfs_rt_pb_url:
        log.info(f"[{service.label}] No RT feed configured — using scheduled data only")
        return {}

    if service.gtfs_rt_json_url:
        try:
            data = _fetch_json(service.gtfs_rt_json_url)
            log.info(f"[{service.label}] RT trip updates (JSON): {len(data)} trips")
            return data
        except Exception as e:
            log.warning(f"[{service.label}] JSON endpoint failed ({e}), trying protobuf…")

    if service.gtfs_rt_pb_url:
        try:
            data = _fetch_protobuf(service.gtfs_rt_pb_url)
            log.info(f"[{service.label}] RT trip updates (protobuf): {len(data)} trips")
            return data
        except Exception as e:
            log.error(f"[{service.label}] Both RT endpoints failed: {e} — using scheduled data only")

    return {}


# ── JSON parser ────────────────────────────────────────────────────────────────

def _fetch_json(url: str) -> TripUpdates:
    resp = requests.get(url, timeout=REQUEST_TIMEOUT, verify=False)
    resp.raise_for_status()
    return _parse_json(resp.json())


def _parse_json(data: dict) -> TripUpdates:
    # Renfe RT JSON uses camelCase keys; support both camelCase and snake_case
    def get(d: dict, *keys):
        for k in keys:
            if k in d:
                return d[k]
        return None

    updates: TripUpdates = {}

    for entity in data.get("entity", []):
        tu = get(entity, "tripUpdate", "trip_update")
        if not tu:
            continue

        trip = get(tu, "trip") or {}
        trip_id = get(trip, "tripId", "trip_id") or ""
        if not trip_id:
            continue

        stop_updates = get(tu, "stopTimeUpdate", "stop_time_update") or []

        if stop_updates:
            updates[trip_id] = {}
            for stu in stop_updates:
                stop_id = get(stu, "stopId", "stop_id") or ""
                if not stop_id:
                    continue

                rel = get(stu, "scheduleRelationship", "schedule_relationship") or "SCHEDULED"
                if rel in ("SKIPPED", "NO_DATA"):
                    updates[trip_id][stop_id] = -1
                    continue

                arrival = get(stu, "arrival") or {}
                departure = get(stu, "departure") or {}
                delay = arrival.get("delay") or departure.get("delay") or 0
                updates[trip_id][stop_id] = int(delay)
        else:
            # Trip-level delay only (e.g. Renfe LD feed) — apply to all stops
            trip_delay = get(tu, "delay") or 0
            if trip_delay:
                updates[trip_id] = {"*": int(trip_delay)}

    return updates


# ── Protobuf parser (fallback) ─────────────────────────────────────────────────

def _fetch_protobuf(url: str) -> TripUpdates:
    from google.transit import gtfs_realtime_pb2  # optional dep

    resp = requests.get(url, timeout=REQUEST_TIMEOUT, verify=False)
    resp.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)

    updates: TripUpdates = {}
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        trip_id = entity.trip_update.trip.trip_id
        updates[trip_id] = {}

        for stu in entity.trip_update.stop_time_update:
            cancelled = (
                stu.schedule_relationship
                == gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SKIPPED
            )
            if cancelled:
                updates[trip_id][stu.stop_id] = -1
                continue

            if stu.HasField("arrival"):
                delay = stu.arrival.delay
            elif stu.HasField("departure"):
                delay = stu.departure.delay
            else:
                delay = 0

            updates[trip_id][stu.stop_id] = delay

    return updates
