"""
Compute zone trend labels and narratives from data/by_ccaa/history.parquet.
Uses pure Python + PyArrow (no pandas/scipy dependency).
"""
import logging
from collections import defaultdict
from pathlib import Path

log = logging.getLogger(__name__)

# Trend thresholds (OLS slope on delayed_pct per snapshot)
SLOPE_WORSENING = 0.002    # +0.2 pp per snapshot
SLOPE_IMPROVING = -0.002   # -0.2 pp per snapshot

# Zone classification ratios relative to national avg
RATIO_CRITICA    = 2.0
RATIO_REFERENCIA = 0.7
MIN_RECORDS      = 5       # need at least this many snapshots per CCAA


def compute_zone_trends(service_name: str, data_root: Path) -> dict:
    """
    Returns {ccaa: {label, trend, narrative, historical_avg_pct, national_avg_pct, n_records}}.
    Falls back to {} on any error.
    """
    parquet_path = data_root / "by_ccaa" / "history.parquet"
    if not parquet_path.exists():
        log.debug("by_ccaa/history.parquet not found — skipping zone trends")
        return {}

    try:
        import pyarrow.parquet as pq
        table = pq.read_table(parquet_path)
    except Exception as exc:
        log.warning("Could not read by_ccaa parquet (%s) — skipping zone trends", exc)
        return {}

    rows = table.to_pydict()
    n_rows = len(rows.get("ccaa", []))
    if n_rows == 0:
        return {}

    # Group by CCAA, filtering by service
    by_ccaa: dict[str, list] = defaultdict(list)
    services = rows.get("service", [""] * n_rows)
    for i in range(n_rows):
        if services[i] and services[i] != service_name:
            continue
        ccaa = rows["ccaa"][i]
        if not ccaa or ccaa == "Desconocida":
            continue
        by_ccaa[ccaa].append({
            "snapshot_id":   rows["snapshot_id"][i],
            "delayed_pct":   float(rows["delayed_pct"][i] or 0),
            "avg_delay_min": float(rows["avg_delay_min"][i] or 0),
        })

    # Sort each CCAA by snapshot_id, keep last 30
    for ccaa in by_ccaa:
        by_ccaa[ccaa].sort(key=lambda r: r["snapshot_id"])
        by_ccaa[ccaa] = by_ccaa[ccaa][-30:]

    if not by_ccaa:
        return {}

    # National average: mean of each CCAA's own historical avg (equal weight per region)
    ccaa_avgs = [
        sum(r["delayed_pct"] for r in records) / len(records)
        for records in by_ccaa.values()
        if len(records) >= MIN_RECORDS
    ]
    national_avg = sum(ccaa_avgs) / len(ccaa_avgs) if ccaa_avgs else 0.10

    result = {}
    for ccaa, records in by_ccaa.items():
        n = len(records)
        if n < MIN_RECORDS:
            continue

        pcts = [r["delayed_pct"] for r in records]
        hist_avg = sum(pcts) / n
        slope = _ols_slope(pcts)

        if slope > SLOPE_WORSENING:
            trend = "worsening"
        elif slope < SLOPE_IMPROVING:
            trend = "improving"
        else:
            trend = "stable"

        ratio = hist_avg / national_avg if national_avg > 0 else 1.0

        if ratio >= RATIO_CRITICA and trend == "worsening":
            label = "zona_critica"
        elif ratio > 1.0 and trend == "worsening":
            label = "zona_deterioro"
        elif ratio < RATIO_REFERENCIA:
            label = "zona_referencia"
        else:
            label = "zona_estable"

        result[ccaa] = {
            "label":              label,
            "trend":              trend,
            "narrative":          _narrative(ccaa, hist_avg, national_avg, label, trend, n),
            "historical_avg_pct": round(hist_avg, 4),
            "national_avg_pct":   round(national_avg, 4),
            "n_records":          n,
        }

    log.info(
        "Zone trends (%s): %d CCAA classified, national_avg=%.1f%%",
        service_name, len(result), national_avg * 100,
    )
    return result


def _ols_slope(values: list) -> float:
    """OLS slope over x = 0, 1, ..., n-1."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den if den else 0.0


def _narrative(ccaa: str, hist_avg: float, national_avg: float,
               label: str, trend: str, n: int) -> str:
    pct = round(hist_avg * 100, 1)
    nat = round(national_avg * 100, 1)
    trend_es = {"worsening": "empeorando", "improving": "mejorando", "stable": "estable"}[trend]

    if label == "zona_critica":
        mult = round(hist_avg / national_avg, 1) if national_avg > 0 else 0
        return (
            f"Situación crítica: el {pct}% de los trenes llegan tarde, "
            f"{mult}× la media nacional ({nat}%), y la tendencia sigue empeorando."
        )
    if label == "zona_deterioro":
        return (
            f"Situación preocupante: {pct}% de retrasos, por encima de la media "
            f"({nat}%), con tendencia al alza. Basado en {n} registros."
        )
    if label == "zona_referencia":
        return (
            f"Referencia de puntualidad: solo el {pct}% de retrasos, "
            f"de los mejor atendidos del país. Tendencia: {trend_es}."
        )
    return (
        f"Servicio normal: {pct}% de retrasos, en línea con la media nacional ({nat}%). "
        f"Tendencia: {trend_es}."
    )
