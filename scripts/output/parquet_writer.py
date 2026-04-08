"""
Parquet writer — appends pipeline snapshots to columnar storage.

One call to `append_snapshot()` per service per pipeline run writes to four tables:

  data/snapshots/snapshots.parquet       — 1 row per run (global aggregates)
  data/arrivals/YYYY-MM.parquet          — 1 row per train arrival per run (full grain)
  data/stations/YYYY-MM.parquet          — 1 row per station per run (station aggregates)
  data/by_type/history.parquet           — 1 row per train-type per run
  data/by_ccaa/history.parquet           — 1 row per CCAA per run

All files are append-only. Schema is enforced on each write so columns stay consistent.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict
from zoneinfo import ZoneInfo

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger(__name__)

_TZ_MADRID = ZoneInfo("Europe/Madrid")

# Root of the parquet store, relative to repo root
_DATA_ROOT = Path(__file__).parent.parent.parent / "data"

# ── schemas ──────────────────────────────────────────────────────────────────

SCHEMA_SNAPSHOTS = pa.schema([
    pa.field("snapshot_id",      pa.string()),
    pa.field("service",          pa.string()),
    pa.field("ts",               pa.string()),   # ISO datetime
    pa.field("date",             pa.string()),   # YYYY-MM-DD
    pa.field("hour",             pa.int8()),
    pa.field("total",            pa.int32()),
    pa.field("delayed",          pa.int32()),
    pa.field("cancelled",        pa.int32()),
    pa.field("on_time",          pa.int32()),
    pa.field("avg_delay_min",    pa.float32()),
    pa.field("max_delay_min",    pa.float32()),
    pa.field("p50",              pa.float32()),
    pa.field("p75",              pa.float32()),
    pa.field("p90",              pa.float32()),
    pa.field("p95",              pa.float32()),
    pa.field("unique_trips",     pa.int32()),
    pa.field("stations_count",   pa.int32()),
])

SCHEMA_ARRIVALS = pa.schema([
    pa.field("snapshot_id",      pa.string()),
    pa.field("service",          pa.string()),
    pa.field("trip_id",          pa.string()),
    pa.field("route_id",         pa.string()),
    pa.field("train_name",       pa.string()),
    pa.field("train_type",       pa.string()),
    pa.field("stop_id",          pa.string()),
    pa.field("stop_name",        pa.string()),
    pa.field("ccaa",             pa.string()),
    pa.field("nucleo",           pa.string()),
    pa.field("headsign",         pa.string()),
    pa.field("origin",           pa.string()),
    pa.field("scheduled_time",   pa.string()),
    pa.field("estimated_time",   pa.string()),
    pa.field("delay_min",        pa.float32()),
    pa.field("status",           pa.string()),
])

SCHEMA_STATIONS = pa.schema([
    pa.field("snapshot_id",      pa.string()),
    pa.field("service",          pa.string()),
    pa.field("stop_id",          pa.string()),
    pa.field("stop_name",        pa.string()),
    pa.field("ccaa",             pa.string()),
    pa.field("nucleo",           pa.string()),
    pa.field("total_arrivals",   pa.int32()),
    pa.field("delayed_count",    pa.int32()),
    pa.field("cancelled_count",  pa.int32()),
    pa.field("avg_delay_min",    pa.float32()),
    pa.field("max_delay_min",    pa.float32()),
])

SCHEMA_BY_TYPE = pa.schema([
    pa.field("snapshot_id",      pa.string()),
    pa.field("service",          pa.string()),
    pa.field("train_type",       pa.string()),
    pa.field("total",            pa.int32()),
    pa.field("delayed",          pa.int32()),
    pa.field("cancelled",        pa.int32()),
    pa.field("delayed_pct",      pa.float32()),
    pa.field("avg_delay_min",    pa.float32()),
    pa.field("max_delay_min",    pa.float32()),
])

SCHEMA_BY_CCAA = pa.schema([
    pa.field("snapshot_id",      pa.string()),
    pa.field("service",          pa.string()),
    pa.field("ccaa",             pa.string()),
    pa.field("total",            pa.int32()),
    pa.field("delayed",          pa.int32()),
    pa.field("delayed_pct",      pa.float32()),
    pa.field("avg_delay_min",    pa.float32()),
    pa.field("max_delay_min",    pa.float32()),
    pa.field("stations_count",   pa.int32()),
])

# ── helpers ───────────────────────────────────────────────────────────────────

def _append(path: Path, table: pa.Table) -> None:
    """Append a PyArrow table to a parquet file, creating it if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = pq.read_table(path)
            combined = pa.concat_tables([existing, table])
        except Exception as exc:
            log.warning("Corrupt parquet file %s (%s) — recreating from scratch", path, exc)
            path.unlink()
            combined = table
    else:
        combined = table
    pq.write_table(combined, path, compression="zstd")


def _month_path(folder: str, now: datetime) -> Path:
    return _DATA_ROOT / folder / f"{now.strftime('%Y-%m')}.parquet"


# ── public API ─────────────────────────────────────────────────────────────────

def append_snapshot(
    station_data: Dict[str, dict],
    stats: dict,
    service_name: str,
) -> None:
    """
    Write one snapshot worth of data across all five parquet tables.

    Parameters
    ----------
    station_data : dict  {stop_id: {"name": str, "arrivals": [...]}}
    stats        : dict  output of compute_stats()
    service_name : str   e.g. "cercanias" or "ave-larga-distancia"
    """
    from scripts.config_zones import get_ccaa, get_nucleo

    now = datetime.now(_TZ_MADRID)
    snapshot_id = f"{service_name}_{now.strftime('%Y-%m-%dT%H:%M')}"

    # ── snapshots ─────────────────────────────────────────────────────────────
    percs = stats.get("delay_percentiles", {})
    snap_row = {
        "snapshot_id":    [snapshot_id],
        "service":        [service_name],
        "ts":             [now.isoformat(timespec="seconds")],
        "date":           [now.strftime("%Y-%m-%d")],
        "hour":           [now.hour],
        "total":          [stats.get("total_trains", 0)],
        "delayed":        [stats.get("delayed", 0)],
        "cancelled":      [stats.get("cancelled", 0)],
        "on_time":        [stats.get("on_time", 0)],
        "avg_delay_min":  [float(stats.get("avg_delay_min", 0.0))],
        "max_delay_min":  [float(stats.get("max_delay_min", 0.0))],
        "p50":            [float(percs.get("p50", 0))],
        "p75":            [float(percs.get("p75", 0))],
        "p90":            [float(percs.get("p90", 0))],
        "p95":            [float(percs.get("p95", 0))],
        "unique_trips":   [stats.get("unique_trips", 0)],
        "stations_count": [stats.get("stations_count", 0)],
    }
    _append(
        _DATA_ROOT / "snapshots" / "snapshots.parquet",
        pa.Table.from_pydict(snap_row, schema=SCHEMA_SNAPSHOTS),
    )

    # ── arrivals ──────────────────────────────────────────────────────────────
    arrival_rows: list[dict] = []
    station_rows: list[dict] = []

    for stop_id, data in station_data.items():
        arrivals = data.get("arrivals", [])
        if not arrivals:
            continue

        stop_name = data["name"]
        ccaa  = get_ccaa(stop_id)
        nucleo = get_nucleo(stop_id) or ""

        delayed_count   = sum(1 for a in arrivals if a.get("status") in ("retraso_leve", "retraso_alto"))
        cancelled_count = sum(1 for a in arrivals if a.get("status") == "cancelado")
        delays          = [float(a.get("delay_min") or 0) for a in arrivals]
        avg_delay       = sum(delays) / len(delays) if delays else 0.0
        max_delay       = max(delays, default=0.0)

        station_rows.append({
            "snapshot_id":     snapshot_id,
            "service":         service_name,
            "stop_id":         stop_id,
            "stop_name":       stop_name,
            "ccaa":            ccaa,
            "nucleo":          nucleo,
            "total_arrivals":  len(arrivals),
            "delayed_count":   delayed_count,
            "cancelled_count": cancelled_count,
            "avg_delay_min":   round(avg_delay, 2),
            "max_delay_min":   round(max_delay, 2),
        })

        for arr in arrivals:
            arrival_rows.append({
                "snapshot_id":    snapshot_id,
                "service":        service_name,
                "trip_id":        arr.get("trip_id", ""),
                "route_id":       arr.get("route_id", ""),
                "train_name":     arr.get("train_name", ""),
                "train_type":     arr.get("train_type") or "Otros",
                "stop_id":        stop_id,
                "stop_name":      stop_name,
                "ccaa":           ccaa,
                "nucleo":         nucleo,
                "headsign":       arr.get("headsign", ""),
                "origin":         arr.get("origin", ""),
                "scheduled_time": arr.get("scheduled_time", ""),
                "estimated_time": arr.get("estimated_time", ""),
                "delay_min":      float(arr.get("delay_min") or 0),
                "status":         arr.get("status", ""),
            })

    if arrival_rows:
        _append(
            _month_path("arrivals", now),
            pa.Table.from_pylist(arrival_rows, schema=SCHEMA_ARRIVALS),
        )
    if station_rows:
        _append(
            _month_path("stations", now),
            pa.Table.from_pylist(station_rows, schema=SCHEMA_STATIONS),
        )

    # ── by_type ───────────────────────────────────────────────────────────────
    by_type_rows: list[dict] = []
    for tt, v in stats.get("by_train_type", {}).items():
        total = v.get("total", 0)
        delayed = v.get("delayed", 0)
        by_type_rows.append({
            "snapshot_id":   snapshot_id,
            "service":       service_name,
            "train_type":    tt,
            "total":         total,
            "delayed":       delayed,
            "cancelled":     v.get("cancelled", 0),
            "delayed_pct":   round(delayed / total, 4) if total else 0.0,
            "avg_delay_min": float(v.get("avg_delay_min", 0.0)),
            "max_delay_min": float(v.get("max_delay_min", 0.0)),
        })
    if by_type_rows:
        _append(
            _DATA_ROOT / "by_type" / "history.parquet",
            pa.Table.from_pylist(by_type_rows, schema=SCHEMA_BY_TYPE),
        )

    # ── by_ccaa ───────────────────────────────────────────────────────────────
    by_ccaa_rows: list[dict] = []
    for zone in stats.get("by_ccaa", []):
        total = zone.get("total", 0)
        delayed = zone.get("delayed", 0)
        by_ccaa_rows.append({
            "snapshot_id":   snapshot_id,
            "service":       service_name,
            "ccaa":          zone.get("name", ""),
            "total":         total,
            "delayed":       delayed,
            "delayed_pct":   round(zone.get("delayed_pct", 0.0), 4),
            "avg_delay_min": float(zone.get("avg_delay_min", 0.0)),
            "max_delay_min": float(zone.get("max_delay_min", 0.0)),
            "stations_count": zone.get("stations_count", 0),
        })
    if by_ccaa_rows:
        _append(
            _DATA_ROOT / "by_ccaa" / "history.parquet",
            pa.Table.from_pylist(by_ccaa_rows, schema=SCHEMA_BY_CCAA),
        )

    log.info(
        f"[{service_name}] Parquet written — snapshot {snapshot_id} | "
        f"{len(arrival_rows)} arrivals, {len(station_rows)} stations, "
        f"{len(by_type_rows)} types, {len(by_ccaa_rows)} ccaa"
    )
