"""Compute global statistics across all station arrivals."""
import logging
from typing import Dict, Optional

from scripts.config_zones import get_ccaa, get_nucleo, NUCLEO_NAMES

log = logging.getLogger(__name__)

StationData = Dict[str, dict]


def compute_stats(station_data: StationData) -> dict:
    """
    Aggregate all arrivals into a single stats dict.
    Returns the payload that goes into stats.json → "stats".
    """
    total = on_time = delayed = cancelled = 0
    delays: list = []
    unique_trip_ids: set = set()

    station_counts: Dict[str, dict] = {}
    station_delays: Dict[str, list] = {}
    max_delay_entry: Optional[dict] = None  # {stop_id, name, delay_min, train_name}
    by_train_type: Dict[str, dict] = {}  # {label: {total, delayed, cancelled, delays[]}}
    by_ccaa:   Dict[str, dict] = {}   # {ccaa_name:  {total, delayed, cancelled, delays[], stations:set}}
    by_nucleo: Dict[str, dict] = {}   # {nucleo_id:  {total, delayed, cancelled, delays[], stations:set}}

    for stop_id, data in station_data.items():
        arrivals = data["arrivals"]
        station_counts[stop_id] = {"name": data["name"], "count": len(arrivals)}
        station_delays[stop_id] = []

        # Zone lookup (once per station)
        ccaa   = get_ccaa(stop_id)
        nucleo = get_nucleo(stop_id)
        _zone_init(by_ccaa,   ccaa)
        if nucleo:
            _zone_init(by_nucleo, nucleo)

        for arr in arrivals:
            total += 1
            if arr.get("trip_id"):
                unique_trip_ids.add(arr["trip_id"])
            status = arr["status"]
            tt = arr.get("train_type", "Otros")
            if tt not in by_train_type:
                by_train_type[tt] = {"total": 0, "delayed": 0, "cancelled": 0, "delays": []}
            by_train_type[tt]["total"] += 1
            by_ccaa[ccaa]["total"] += 1
            by_ccaa[ccaa]["stations"].add(stop_id)
            if nucleo:
                by_nucleo[nucleo]["total"] += 1
                by_nucleo[nucleo]["stations"].add(stop_id)

            if status == "cancelado":
                cancelled += 1
                by_train_type[tt]["cancelled"] += 1
                by_ccaa[ccaa]["cancelled"] += 1
                if nucleo:
                    by_nucleo[nucleo]["cancelled"] += 1
            elif status == "en_hora":
                on_time += 1
            else:
                delayed += 1
                by_train_type[tt]["delayed"] += 1
                by_ccaa[ccaa]["delayed"] += 1
                if nucleo:
                    by_nucleo[nucleo]["delayed"] += 1
                if arr["delay_min"] is not None:
                    delays.append(arr["delay_min"])
                    station_delays[stop_id].append(arr["delay_min"])
                    by_train_type[tt]["delays"].append(arr["delay_min"])
                    by_ccaa[ccaa]["delays"].append(arr["delay_min"])
                    if nucleo:
                        by_nucleo[nucleo]["delays"].append(arr["delay_min"])
                    if max_delay_entry is None or arr["delay_min"] > max_delay_entry["delay_min"]:
                        max_delay_entry = {
                            "stop_id": stop_id,
                            "station_name": data["name"],
                            "delay_min": arr["delay_min"],
                            "train_name": arr.get("train_name") or arr.get("route_id", ""),
                        }

    avg_delay = round(sum(delays) / len(delays), 1) if delays else 0.0
    max_delay = round(max(delays), 1) if delays else 0
    percentiles = {
        "p50": _percentile(delays, 50),
        "p75": _percentile(delays, 75),
        "p90": _percentile(delays, 90),
        "p95": _percentile(delays, 95),
    } if delays else {"p50": 0, "p75": 0, "p90": 0, "p95": 0}

    busiest = _top(station_counts, key=lambda v: v["count"])
    worst = _top(
        {
            sid: {"name": data["name"], "avg_delay": round(sum(d) / len(d), 1)}
            for sid, data in station_data.items()
            if (d := station_delays.get(sid))
        },
        key=lambda v: v["avg_delay"],
    )

    # Build by_train_type summary and assign rank_worst (1 = worst avg delay)
    by_type_final = {}
    for tt, acc in by_train_type.items():
        tt_delays = acc["delays"]
        avg = round(sum(tt_delays) / len(tt_delays), 1) if tt_delays else 0.0
        mx  = round(max(tt_delays), 1) if tt_delays else 0.0
        denom = acc["total"] - acc["cancelled"]
        by_type_final[tt] = {
            "total":          acc["total"],
            "delayed":        acc["delayed"],
            "cancelled":      acc["cancelled"],
            "avg_delay_min":  avg,
            "max_delay_min":  mx,
            "delayed_pct":    round(acc["delayed"] / denom, 3) if denom > 0 else 0.0,
        }
    # rank_worst: 1 = highest avg_delay_min
    ranked = sorted(by_type_final.keys(), key=lambda t: by_type_final[t]["avg_delay_min"], reverse=True)
    for rank, tt in enumerate(ranked, start=1):
        by_type_final[tt]["rank_worst"] = rank

    # Build zone summaries (ccaa + nucleo)
    def _zone_summary(acc: dict, name_fn) -> list:
        items = []
        for key, a in acc.items():
            d = a["delays"]
            denom = a["total"] - a["cancelled"]
            items.append({
                "id":             key,
                "name":           name_fn(key),
                "stations_count": len(a["stations"]),
                "total":          a["total"],
                "delayed":        a["delayed"],
                "cancelled":      a["cancelled"],
                "avg_delay_min":  round(sum(d) / len(d), 1) if d else 0.0,
                "max_delay_min":  round(max(d), 1) if d else 0.0,
                "delayed_pct":    round(a["delayed"] / denom, 3) if denom > 0 else 0.0,
            })
        items.sort(key=lambda x: x["avg_delay_min"], reverse=True)
        for rank, item in enumerate(items, start=1):
            item["rank_worst"] = rank
        return items

    ccaa_list   = _zone_summary(by_ccaa,   lambda k: k)
    nucleo_list = _zone_summary(by_nucleo, lambda k: NUCLEO_NAMES.get(k, k))

    stats = {
        "total_trains": total,
        "unique_trips": len(unique_trip_ids),
        "on_time": on_time,
        "delayed": delayed,
        "cancelled": cancelled,
        "avg_delay_min": avg_delay,
        "max_delay_min": max_delay,
        "delay_percentiles": percentiles,
        "max_delay_station": max_delay_entry,
        "stations_count": len(station_data),
        "busiest_station": _with_id(busiest) if busiest else None,
        "worst_delay_station": _with_id(worst) if worst else None,
        "by_train_type": by_type_final,
        "by_ccaa":        ccaa_list,
        "by_nucleo":      nucleo_list,
    }

    log.info(
        f"Stats — total: {total}, on_time: {on_time}, delayed: {delayed}, "
        f"avg: {avg_delay}m, max: {max_delay}m"
    )
    return stats


def _zone_init(acc: dict, key: str) -> None:
    if key not in acc:
        acc[key] = {"total": 0, "delayed": 0, "cancelled": 0, "delays": [], "stations": set()}


def _percentile(data: list, p: float) -> float:
    s = sorted(data)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (idx - lo), 1)


def _top(d: dict, key) -> Optional[tuple]:
    if not d:
        return None
    return max(d.items(), key=lambda item: key(item[1]))


def _with_id(item: Optional[tuple]) -> Optional[dict]:
    if item is None:
        return None
    stop_id, data = item
    return {"id": stop_id, **data}
