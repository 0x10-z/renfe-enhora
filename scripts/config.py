"""Configuration constants for the Renfe pipeline."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / ".cache" / "gtfs"

# Processing thresholds (shared across all services)
LOOKAHEAD_MINUTES = 60
ON_TIME_THRESHOLD_SEC = 5 * 60   # <= 5 min  → en_hora
DELAY_LEVE_MAX_SEC = 10 * 60     # <= 10 min → retraso_leve
                                  # >  10 min → retraso_alto

# HTTP
REQUEST_TIMEOUT = 30
GTFS_CACHE_HOURS = 24

# Station history retention
STATION_HISTORY_RETENTION_DAYS = 30

# Raw events retention (months kept on VPS — no auto-rotation yet)
RAW_RETENTION_DAYS = 90

# Train type classification: ordered list of (prefix, label).
# Checked against trip_short_name (uppercased), first match wins.
# Cercanías (C1–C10+) is handled separately by the classifier.
TRAIN_TYPE_PREFIXES: list[tuple[str, str]] = [
    ("AVLO",  "AVLO"),
    ("AV2",   "AVLO"),
    ("AVE",   "AVE"),
    ("ALVIA", "Alvia"),
    ("AVANT", "Avant"),
    ("MD",    "Media Distancia"),
    ("LD",    "Larga Distancia"),
    ("REG",   "Regional"),
    ("RG",    "Regional"),
]


@dataclass(frozen=True)
class ServiceConfig:
    name: str             # slug — used in folder names and URLs
    label: str            # human-readable label shown in the frontend
    gtfs_url: str
    gtfs_rt_json_url: Optional[str]
    gtfs_rt_pb_url: Optional[str]
    cache_subdir: str     # subfolder inside CACHE_DIR

    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "public" / "data" / self.name

    @property
    def stations_dir(self) -> Path:
        return self.data_dir / "stations"

    @property
    def station_history_dir(self) -> Path:
        return self.data_dir / "station-history"


CERCANIAS = ServiceConfig(
    name="cercanias",
    label="Cercanías",
    gtfs_url="https://ssl.renfe.com/ftransit/Fichero_CER_FOMENTO/fomento_transit.zip",
    gtfs_rt_json_url="https://gtfsrt.renfe.com/trip_updates.json",
    gtfs_rt_pb_url="https://gtfsrt.renfe.com/trip_updates.pb",
    cache_subdir="gtfs_cercanias",
)

AV_LD = ServiceConfig(
    name="ave-larga-distancia",
    label="Alta Velocidad / Larga y Media Distancia",
    # Combined feed: AVE + Larga Distancia + Media Distancia
    gtfs_url="https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip",
    gtfs_rt_json_url="https://gtfsrt.renfe.com/trip_updates_LD.json",
    gtfs_rt_pb_url=None,
    cache_subdir="gtfs_ave_ld",
)

# Order determines display priority in the frontend
ALL_SERVICES = [AV_LD, CERCANIAS]

# Backward-compatible aliases (used by merger.py — not per-service)
DATA_DIR = CERCANIAS.data_dir
STATIONS_DIR = CERCANIAS.stations_dir
