# arrivals/

**Ficheros:** `YYYY-MM.parquet` (uno por mes)
**Grain:** 1 fila por tren × estación × ejecución del pipeline
**Append:** sí — cada ejecución añade todas las llegadas del lookahead de 60 min

Esta es la tabla más granular: contiene **todos** los trenes en todas las estaciones en cada snapshot. Permite reconstruir exactamente qué estaba pasando en la red en cualquier momento histórico.

## Esquema

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `snapshot_id` | string | FK → `snapshots.snapshot_id` |
| `service` | string | `cercanias` o `ave-larga-distancia` |
| `trip_id` | string | ID del viaje GTFS |
| `route_id` | string | ID de la ruta GTFS |
| `train_name` | string | Nombre comercial del tren (C1, AVE, etc.) |
| `train_type` | string | Categoría: AVE, Cercanías, Alvia, etc. |
| `stop_id` | string | ID de la estación (parada GTFS) |
| `stop_name` | string | Nombre legible de la estación |
| `ccaa` | string | Comunidad Autónoma de la estación |
| `nucleo` | string | Núcleo de cercanías (madrid, barcelona…) o vacío |
| `headsign` | string | Destino final del tren |
| `origin` | string | Origen del tren |
| `scheduled_time` | string | Hora programada `HH:MM` |
| `estimated_time` | string | Hora estimada `HH:MM` (vacío si cancelado) |
| `delay_min` | float32 | Retraso en minutos (0.0 si en hora) |
| `status` | string | `en_hora`, `retraso_leve`, `retraso_alto`, `cancelado` |

## Tamaño estimado

~4.000 filas por ejecución × 24 ejecuciones/día × 30 días = ~2.9M filas/mes
Con compresión zstd: **~15-25 MB por fichero mensual**.

## Ejemplo de consulta

```python
import pandas as pd

df = pd.read_parquet("data/arrivals/2026-04.parquet")

# Top 10 trenes con más retraso acumulado en abril
top_delayed = (
    df[df["delay_min"] > 0]
    .groupby("train_name")["delay_min"]
    .agg(["sum", "count", "mean"])
    .sort_values("sum", ascending=False)
    .head(10)
)

# Retraso medio por hora del día en Madrid
madrid = df[df["ccaa"] == "Comunidad de Madrid"].copy()
madrid["hour"] = madrid["snapshot_id"].str[-5:-3].astype(int)
madrid.groupby("hour")["delay_min"].mean()
```
