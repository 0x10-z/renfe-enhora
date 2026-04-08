"""Compute natural-language insights from current snapshot + history."""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

WEEKDAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def compute_insights(station_data: dict, stats: dict, history_path: Path) -> list:
    """
    Returns a list of insight dicts: {id, text, severity}
    severity: "ok" | "warn" | "bad" | "info"
    Only includes insights where there's enough data to be meaningful.
    """
    history = _load_history(history_path)
    now = datetime.now()
    insights = []

    # ── Current snapshot insights (always available) ────────────────────────
    _insight_A(station_data, insights)
    _insight_B(station_data, insights)
    _insight_C(station_data, insights)

    # ── Historical insights (need enough history) ────────────────────────────
    if len(history) >= 8:
        _insight_D(history, insights)
        _insight_E(history, stats, now, insights)
        _insight_F(history, insights)
        _insight_G(history, insights)
        _insight_H(history, insights)
        _insight_I(history, stats, now, insights)

    # ── Anomaly alerts (F15) — always last so we can sort them first ──────────
    if len(history) >= 20:
        _insight_J(history, stats, insights)

    # Alerts ("high") always surface first
    insights.sort(key=lambda x: 0 if x.get("severity") == "high" else 1)

    log.info(f"Computed {len(insights)} insights ({len(history)} history records available)")
    return insights


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_history(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("records", [])
    except Exception:
        return []


def _delay_pct(total: int, delayed: int) -> float:
    return round(delayed / total * 100, 1) if total > 0 else 0.0


def _append(insights: list, id_: str, text: str, severity: str, meta: dict | None = None) -> None:
    entry = {"id": id_, "text": text, "severity": severity}
    if meta:
        entry["meta"] = meta
    insights.append(entry)


# ── A: hora con más acumulación ahora ────────────────────────────────────────

def _insight_A(station_data: dict, insights: list) -> None:
    by_hour: dict[int, int] = {}
    for data in station_data.values():
        for arr in data.get("arrivals", []):
            if arr.get("status") not in ("retraso_leve", "retraso_alto"):
                continue
            try:
                hour = int(arr["scheduled_time"].split(":")[0])
            except (KeyError, ValueError, AttributeError):
                continue
            by_hour[hour] = by_hour.get(hour, 0) + 1

    if not by_hour:
        return

    peak_hour = max(by_hour, key=lambda h: by_hour[h])
    count = by_hour[peak_hour]
    if count < 3:
        return

    noun_s = "es" if count != 1 else ""
    adj_s  = "s"  if count != 1 else ""
    _append(insights, "A",
        f"A las {peak_hour:02d}h se están acumulando los retrasos — "
        f"{count} tren{noun_s} afectado{adj_s}",
        "warn",
        meta={"hour": peak_hour})


# ── B: tren con mayor retraso ahora ──────────────────────────────────────────

def _insight_B(station_data: dict, insights: list) -> None:
    best: dict | None = None
    for stop_id, data in station_data.items():
        for arr in data.get("arrivals", []):
            delay = arr.get("delay_min") or 0
            if delay <= 0:
                continue
            if best is None or delay > best["delay"]:
                best = {
                    "delay": delay,
                    "origin": arr.get("origin") or arr.get("headsign") or "origen desconocido",
                    "station": data.get("name", ""),
                    "station_id": stop_id,
                }

    if not best or best["delay"] < 15:
        return

    _append(insights, "B",
        f"El mayor retraso en este momento es de {best['delay']:.0f} minutos — "
        f"tren desde {best['origin']} con parada en {best['station']}",
        "bad" if best["delay"] >= 30 else "warn",
        meta={"station_id": best["station_id"], "station_name": best["station"]})


# ── C: estación más afectada ahora ───────────────────────────────────────────

def _insight_C(station_data: dict, insights: list) -> None:
    worst: dict | None = None
    worst_id: str | None = None
    for stop_id, data in station_data.items():
        arrivals = data.get("arrivals", [])
        if len(arrivals) < 3:
            continue
        delayed = sum(1 for a in arrivals if a.get("status") in ("retraso_leve", "retraso_alto"))
        if delayed < 2:
            continue
        ratio = delayed / len(arrivals)
        if ratio < 0.3:
            continue
        if worst is None or ratio > worst["ratio"]:
            worst = {
                "name": data["name"],
                "delayed": delayed,
                "total": len(arrivals),
                "ratio": ratio,
            }
            worst_id = stop_id

    if not worst:
        return

    _append(insights, "C",
        f"{worst['name']} es la estación más afectada ahora mismo: "
        f"{worst['delayed']} de {worst['total']} trenes con retraso",
        "bad" if worst["ratio"] > 0.5 else "warn",
        meta={"station_id": worst_id, "station_name": worst["name"]})


# ── D: día de la semana con más retrasos (histórico) ─────────────────────────

def _insight_D(history: list, insights: list) -> None:
    by_dow: dict[int, list] = {i: [] for i in range(7)}

    for r in history:
        try:
            date = datetime.strptime(r["date"], "%Y-%m-%d")
            pct = _delay_pct(r.get("total", 0), r.get("delayed", 0))
            by_dow[date.weekday()].append(pct)
        except (KeyError, ValueError):
            continue

    valid = {dow: vals for dow, vals in by_dow.items() if len(vals) >= 3}
    if len(valid) < 3:
        return

    avg_by_dow = {dow: sum(v) / len(v) for dow, v in valid.items()}
    worst_dow = max(avg_by_dow, key=lambda d: avg_by_dow[d])
    best_dow  = min(avg_by_dow, key=lambda d: avg_by_dow[d])

    _append(insights, "D",
        f"Históricamente los {WEEKDAYS_ES[worst_dow]} son el día con más retrasos "
        f"(media {avg_by_dow[worst_dow]:.0f}%); "
        f"los {WEEKDAYS_ES[best_dow]} son los más puntuales",
        "info")


# ── E: hoy vs media histórica para este día de la semana ─────────────────────

def _insight_E(history: list, stats: dict, now: datetime, insights: list) -> None:
    today_str = now.strftime("%Y-%m-%d")
    weekday = now.weekday()

    historical_pcts = []
    for r in history:
        if r.get("date") == today_str:
            continue
        try:
            date = datetime.strptime(r["date"], "%Y-%m-%d")
            if date.weekday() == weekday:
                historical_pcts.append(_delay_pct(r.get("total", 0), r.get("delayed", 0)))
        except (KeyError, ValueError):
            continue

    if len(historical_pcts) < 3:
        return

    hist_avg  = sum(historical_pcts) / len(historical_pcts)
    today_pct = _delay_pct(stats.get("total_trains", 0), stats.get("delayed", 0))

    if hist_avg < 1:
        return

    diff_pct = round((today_pct - hist_avg) / hist_avg * 100)
    if abs(diff_pct) < 15:
        return

    day = WEEKDAYS_ES[weekday]
    if diff_pct > 0:
        _append(insights, "E",
            f"Hoy hay un {diff_pct}% más retrasos de lo habitual para un {day} "
            f"(hoy {today_pct:.0f}% vs media histórica {hist_avg:.0f}%)",
            "bad" if diff_pct > 50 else "warn")
    else:
        _append(insights, "E",
            f"Hoy hay un {abs(diff_pct)}% menos retrasos de lo habitual para un {day} "
            f"(hoy {today_pct:.0f}% vs media histórica {hist_avg:.0f}%)",
            "ok")


# ── F: franja horaria tranquila ───────────────────────────────────────────────

def _insight_F(history: list, insights: list) -> None:
    by_hour: dict[int, list] = {i: [] for i in range(24)}

    for r in history:
        try:
            hour = int(r["ts"][11:13])
            pct  = _delay_pct(r.get("total", 0), r.get("delayed", 0))
            by_hour[hour].append(pct)
        except (KeyError, ValueError, TypeError):
            continue

    quiet = [
        h for h in range(24)
        if len(by_hour[h]) >= 3 and sum(by_hour[h]) / len(by_hour[h]) < 8
    ]
    if len(quiet) < 2:
        return

    # Find longest consecutive block
    blocks, block = [], [quiet[0]]
    for h in quiet[1:]:
        if h == block[-1] + 1:
            block.append(h)
        else:
            blocks.append(block)
            block = [h]
    blocks.append(block)

    longest = max(blocks, key=len)
    if len(longest) < 2:
        return

    _append(insights, "F",
        f"Entre las {longest[0]:02d}h y las {longest[-1]:02d}h los retrasos "
        f"son habitualmente bajos o inexistentes",
        "ok")


# ── G: tendencia esta semana vs anterior ─────────────────────────────────────

def _insight_G(history: list, insights: list) -> None:
    now = datetime.now()
    this_week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    last_week_start = (now - timedelta(days=now.weekday() + 7)).strftime("%Y-%m-%d")
    last_week_end   = (now - timedelta(days=now.weekday() + 1)).strftime("%Y-%m-%d")

    this_week_pcts, last_week_pcts = [], []
    for r in history:
        date = r.get("date", "")
        pct  = _delay_pct(r.get("total", 0), r.get("delayed", 0))
        if date >= this_week_start:
            this_week_pcts.append(pct)
        elif last_week_start <= date <= last_week_end:
            last_week_pcts.append(pct)

    if len(this_week_pcts) < 3 or len(last_week_pcts) < 3:
        return

    this_avg = sum(this_week_pcts) / len(this_week_pcts)
    last_avg = sum(last_week_pcts) / len(last_week_pcts)

    if last_avg < 1:
        return

    diff_pct = round((this_avg - last_avg) / last_avg * 100)
    if abs(diff_pct) < 10:
        return

    if diff_pct > 0:
        _append(insights, "G",
            f"Esta semana los retrasos están subiendo respecto a la anterior "
            f"(+{diff_pct}% · {this_avg:.0f}% vs {last_avg:.0f}%)",
            "warn")
    else:
        _append(insights, "G",
            f"Esta semana los retrasos están bajando respecto a la anterior "
            f"({diff_pct}% · {this_avg:.0f}% vs {last_avg:.0f}%)",
            "ok")


# ── H: peor semana del último mes ────────────────────────────────────────────

def _insight_H(history: list, insights: list) -> None:
    now = datetime.now()
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    current_week = (now - timedelta(days=now.weekday())).strftime("%d/%m")

    by_week: dict[str, list] = {}
    for r in history:
        date = r.get("date", "")
        if date < month_ago:
            continue
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            week_label = (dt - timedelta(days=dt.weekday())).strftime("%d/%m")
            by_week.setdefault(week_label, []).append(
                _delay_pct(r.get("total", 0), r.get("delayed", 0))
            )
        except (KeyError, ValueError):
            continue

    valid = {w: v for w, v in by_week.items() if len(v) >= 3 and w != current_week}
    if len(valid) < 2:
        return

    avg_by_week = {w: sum(v) / len(v) for w, v in valid.items()}
    worst_week  = max(avg_by_week, key=lambda w: avg_by_week[w])

    _append(insights, "H",
        f"La semana del {worst_week} fue la peor del último mes con un "
        f"{avg_by_week[worst_week]:.0f}% de trenes con retraso de media",
        "info")


# ── I: anomalía vs media del mismo día de la semana ─────────────────────────

def _insight_I(history: list, stats: dict, now: datetime, insights: list) -> None:
    today_str = now.strftime("%Y-%m-%d")
    weekday   = now.weekday()

    same_dow_pcts = []
    for r in history:
        if r.get("date") == today_str:
            continue
        try:
            date = datetime.strptime(r["date"], "%Y-%m-%d")
            if date.weekday() == weekday:
                same_dow_pcts.append(_delay_pct(r.get("total", 0), r.get("delayed", 0)))
        except (KeyError, ValueError):
            continue

    if len(same_dow_pcts) < 4:
        return

    hist_avg  = sum(same_dow_pcts) / len(same_dow_pcts)
    today_pct = _delay_pct(stats.get("total_trains", 0), stats.get("delayed", 0))

    if hist_avg < 2:
        return

    ratio = today_pct / hist_avg
    day   = WEEKDAYS_ES[weekday]

    if ratio >= 2.0:
        _append(insights, "I",
            f"Hoy es un {day} inusualmente malo — los retrasos duplican la media histórica "
            f"({today_pct:.0f}% hoy vs {hist_avg:.0f}% habitual)",
            "bad")
    elif ratio <= 0.3 and today_pct < 5:
        _append(insights, "I",
            f"Hoy es un {day} excepcionalmente puntual — muy por debajo de la media histórica "
            f"({today_pct:.0f}% hoy vs {hist_avg:.0f}% habitual)",
            "ok")


# ── J: anomalía por tipo de tren (F15) ───────────────────────────────────────

def _insight_J(history: list, stats: dict, insights: list) -> None:
    """
    Alert when a train type's current delayed_pct is ≥ 1.5× its historical mean.
    Requires ≥ 20 global history records AND ≥ 8 records with data for that type.
    Only fires when the current delayed_pct also exceeds 20% in absolute terms,
    to avoid false alarms on normally-punctual types with low base rates.
    """
    ANOMALY_RATIO   = 1.5   # current must be ≥ 1.5× historical mean
    ABS_THRESHOLD   = 0.20  # current must be ≥ 20% to be worth alerting
    MIN_TYPE_SAMPLES = 8    # need at least this many history snapshots for the type
    MIN_HIST_MEAN   = 0.05  # skip types that are normally < 5% delayed (noise)

    current_by_type = stats.get("by_train_type", {})

    for tt, curr in current_by_type.items():
        curr_pct = curr.get("delayed_pct", 0.0)
        if curr_pct < ABS_THRESHOLD:
            continue

        hist_pcts: list[float] = []
        for r in history:
            rec = r.get("by_type", {}).get(tt)
            if not rec:
                continue
            total, delayed, _ = rec
            if total < 5:
                continue
            hist_pcts.append(delayed / total)

        if len(hist_pcts) < MIN_TYPE_SAMPLES:
            continue

        hist_mean = sum(hist_pcts) / len(hist_pcts)
        if hist_mean < MIN_HIST_MEAN:
            continue

        ratio = curr_pct / hist_mean
        if ratio < ANOMALY_RATIO:
            continue

        ratio_str = f"{ratio:.1f}×"
        _append(insights, "J",
            f"Anomalía en trenes {tt}: los retrasos están a {ratio_str} su media histórica "
            f"({curr_pct*100:.0f}% hoy vs {hist_mean*100:.0f}% habitual). "
            f"Basado en {len(hist_pcts)} registros.",
            "high",
            meta={"train_type": tt})
