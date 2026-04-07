"""
Main pipeline entry point.

Usage (from repo root):
    python -m scripts.main                   # all services
    python -m scripts.main cercanias         # single service
    python -m scripts.main media larga       # subset

Steps (per service):
    1. Download / use cached GTFS static data
    2. Fetch GTFS-RT trip updates (if available)
    3. Merge static + realtime -> per-station arrivals
    4. Compute global statistics
    5. Write JSON files to public/data/{service}/
"""
import logging
import os
import sys
import time
from datetime import datetime

# Hardcode Madrid timezone so the pipeline always interprets service dates
# and GTFS times correctly, regardless of VPS locale settings.
os.environ["TZ"] = "Europe/Madrid"
if hasattr(time, "tzset"):  # tzset is Linux/macOS only
    time.tzset()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False),
)
log = logging.getLogger("main")


def run_service(service) -> None:
    from scripts.ingestion.gtfs_static import get_gtfs_dir
    from scripts.ingestion.gtfs_realtime import fetch_trip_updates
    from scripts.processing.merger import build_station_arrivals
    from scripts.processing.stats import compute_stats
    from scripts.processing.insights import compute_insights
    from scripts.output.writer import write_all, write_by_ccaa_arrivals, write_by_route_arrivals, write_by_type_arrivals, write_history, write_insights, write_station_history, write_zones
    from scripts.output.parquet_writer import append_snapshot

    start = datetime.now()
    log.info(f"--- {service.label} start ---")

    gtfs_dir = get_gtfs_dir(service)
    rt_updates = fetch_trip_updates(service)
    station_data = build_station_arrivals(gtfs_dir, rt_updates)
    stats = compute_stats(station_data)
    write_all(station_data, stats, service)
    write_history(stats, service)
    write_station_history(station_data, service)
    write_by_type_arrivals(station_data, service)
    write_by_ccaa_arrivals(station_data, service)
    write_by_route_arrivals(station_data, service)
    write_zones(stats, service)
    insights = compute_insights(station_data, stats, service.data_dir / "history.json")
    write_insights(insights, service)
    append_snapshot(station_data, stats, service.name)

    elapsed = (datetime.now() - start).total_seconds()
    log.info(
        f"--- {service.label} done in {elapsed:.1f}s -- "
        f"{stats['stations_count']} estaciones, "
        f"{stats['total_trains']} trenes ---"
    )


def run() -> None:
    from scripts.config import ALL_SERVICES

    service_map = {s.name: s for s in ALL_SERVICES}

    # If service names passed as CLI args, run only those; otherwise run all
    requested = sys.argv[1:]
    if requested:
        services = []
        for name in requested:
            if name not in service_map:
                log.error(f"Unknown service '{name}'. Valid: {list(service_map)}")
                sys.exit(1)
            services.append(service_map[name])
    else:
        services = ALL_SERVICES

    overall_start = datetime.now()
    log.info(f"=== Renfe pipeline start -- services: {[s.name for s in services]} ===")

    errors = []
    for service in services:
        try:
            run_service(service)
        except Exception:
            log.exception(f"Pipeline failed for {service.label}")
            errors.append(service.name)

    elapsed = (datetime.now() - overall_start).total_seconds()
    if errors:
        log.error(f"=== Done in {elapsed:.1f}s -- FAILED: {errors} ===")
        sys.exit(1)
    else:
        log.info(f"=== All done in {elapsed:.1f}s ===")


if __name__ == "__main__":
    run()
