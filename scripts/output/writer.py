"""Write JSON output files to public/data/{service}/."""
import json
import logging
from datetime import datetime
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

    generated_at = datetime.now().isoformat(timespec="seconds")
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
    records.append({
        "ts":      datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "date":    datetime.now().strftime("%Y-%m-%d"),
        "total":   stats.get("total_trains", 0),
        "delayed": stats.get("delayed", 0),
        "avg_min": stats.get("avg_delay_min", 0.0),
        "max_min": stats.get("max_delay_min", 0),
    })

    history_path.write_text(
        json.dumps({"records": records}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    log.info(f"[{service.label}] History updated — {len(records)} snapshots")


def write_insights(insights: list, service: ServiceConfig) -> None:
    """Write computed insights to public/data/{service}/insights.json."""
    path = service.data_dir / "insights.json"
    path.write_text(
        json.dumps({
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "insights": insights,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"[{service.label}] Wrote {len(insights)} insights")
