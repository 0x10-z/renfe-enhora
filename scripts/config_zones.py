"""
Zone lookup helpers.

Loads scripts/data/zones_map.json (generated once by generate_zones_map.py)
and exposes get_zone(stop_id) for use in the pipeline.
"""
import json
from pathlib import Path
from typing import Optional

_ZONES_FILE = Path(__file__).parent / "data" / "zones_map.json"

# {stop_id: {"ccaa": str, "nucleo": str | None}}
_ZONES: dict[str, dict] = {}


def _load() -> None:
    global _ZONES
    if _ZONES:
        return
    if not _ZONES_FILE.exists():
        return
    _ZONES = json.loads(_ZONES_FILE.read_text(encoding="utf-8"))


def get_zone(stop_id: str) -> dict:
    """Return {"ccaa": str, "nucleo": str | None} for a stop_id."""
    _load()
    return _ZONES.get(stop_id, {"ccaa": "Desconocida", "nucleo": None})


def get_ccaa(stop_id: str) -> str:
    return get_zone(stop_id)["ccaa"]


def get_nucleo(stop_id: str) -> Optional[str]:
    return get_zone(stop_id)["nucleo"]


# Human-readable names for núcleo IDs
NUCLEO_NAMES: dict[str, str] = {
    "madrid":        "Núcleo Madrid",
    "barcelona":     "Núcleo Barcelona",
    "valencia":      "Núcleo Valencia",
    "sevilla":       "Núcleo Sevilla",
    "bilbao":        "Núcleo Bilbao",
    "asturias":      "Núcleo Asturias",
    "murcia":        "Núcleo Murcia-Alicante",
    "zaragoza":      "Núcleo Zaragoza",
    "san_sebastian": "Núcleo San Sebastián",
    "santander":     "Núcleo Santander",
    "cadiz":         "Núcleo Cádiz-Málaga",
    "almeria":       "Núcleo Almería",
}
