"""Compute global statistics across all station arrivals."""
import logging
from typing import Dict, Optional

log = logging.getLogger(__name__)

StationData = Dict[str, dict]


def compute_stats(station_data: StationData) -> dict:
    """
    Aggregate all arrivals into a single stats dict.
    Returns the payload that goes into stats.json → "stats".
    """
    total = on_time = delayed = cancelled = 0
    delays: list = []

    station_counts: Dict[str, dict] = {}
    station_delays: Dict[str, list] = {}
    max_delay_entry: Optional[dict] = None  # {stop_id, name, delay_min, train_name}

    for stop_id, data in station_data.items():
        arrivals = data["arrivals"]
        station_counts[stop_id] = {"name": data["name"], "count": len(arrivals)}
        station_delays[stop_id] = []

        for arr in arrivals:
            total += 1
            status = arr["status"]

            if status == "cancelado":
                cancelled += 1
            elif status == "en_hora":
                on_time += 1
            else:
                delayed += 1
                if arr["delay_min"] is not None:
                    delays.append(arr["delay_min"])
                    station_delays[stop_id].append(arr["delay_min"])
                    if max_delay_entry is None or arr["delay_min"] > max_delay_entry["delay_min"]:
                        max_delay_entry = {
                            "stop_id": stop_id,
                            "station_name": data["name"],
                            "delay_min": arr["delay_min"],
                            "train_name": arr.get("train_name") or arr.get("route_id", ""),
                        }

    avg_delay = round(sum(delays) / len(delays), 1) if delays else 0.0
    max_delay = round(max(delays), 1) if delays else 0

    busiest = _top(station_counts, key=lambda v: v["count"])
    worst = _top(
        {
            sid: {"name": data["name"], "avg_delay": round(sum(d) / len(d), 1)}
            for sid, data in station_data.items()
            if (d := station_delays.get(sid))
        },
        key=lambda v: v["avg_delay"],
    )

    stats = {
        "total_trains": total,
        "on_time": on_time,
        "delayed": delayed,
        "cancelled": cancelled,
        "avg_delay_min": avg_delay,
        "max_delay_min": max_delay,
        "max_delay_station": max_delay_entry,
        "stations_count": len(station_data),
        "busiest_station": _with_id(busiest) if busiest else None,
        "worst_delay_station": _with_id(worst) if worst else None,
    }

    log.info(
        f"Stats — total: {total}, on_time: {on_time}, delayed: {delayed}, "
        f"avg: {avg_delay}m, max: {max_delay}m"
    )
    return stats


def _top(d: dict, key) -> Optional[tuple]:
    if not d:
        return None
    return max(d.items(), key=lambda item: key(item[1]))


def _with_id(item: Optional[tuple]) -> Optional[dict]:
    if item is None:
        return None
    stop_id, data = item
    return {"id": stop_id, **data}
