# arrivals/

**Estructura:** `YYYY-MM-DD/{snapshot_id}.parquet` (un fichero por snapshot, en carpetas diarias)
**Grain:** 1 fila por tren × estación × ejecución del pipeline
**Escritura:** cada ejecución crea un fichero nuevo — nunca sobreescribe datos anteriores

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

~4.000 filas por snapshot × 24 snapshots/día = ~100K filas/día por servicio.
Cada fichero de snapshot: **~200-500 KB** (zstd). Carpeta diaria: ~5-12 MB.

## Ejemplo de consulta

```python
import pyarrow.parquet as pq
import pandas as pd

# Leer todo un día
dataset = pq.ParquetDataset("data/arrivals/2026-04-10/")
df = dataset.read().to_pandas()

# Leer varios días con pandas
import glob
df = pd.concat([
    pd.read_parquet(f)
    for f in sorted(glob.glob("data/arrivals/2026-04-*/*.parquet"))
])

# Top 10 trenes con más retraso acumulado
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
