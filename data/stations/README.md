# stations/

**Estructura:** `YYYY-MM-DD/{snapshot_id}.parquet` (un fichero por snapshot, en carpetas diarias)
**Grain:** 1 fila por estación × ejecución del pipeline
**Escritura:** cada ejecución crea un fichero nuevo — nunca sobreescribe datos anteriores

Versión agregada de `arrivals/` a nivel de estación. Más ligera para análisis de rendimiento por estación a lo largo del tiempo.

## Esquema

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `snapshot_id` | string | FK → `snapshots.snapshot_id` |
| `service` | string | `cercanias` o `ave-larga-distancia` |
| `stop_id` | string | ID de la estación |
| `stop_name` | string | Nombre de la estación |
| `ccaa` | string | Comunidad Autónoma |
| `nucleo` | string | Núcleo de cercanías o vacío |
| `total_arrivals` | int32 | Total de llegadas en el lookahead |
| `delayed_count` | int32 | Llegadas con retraso (leve + alto) |
| `cancelled_count` | int32 | Llegadas canceladas |
| `avg_delay_min` | float32 | Retraso medio de las llegadas retrasadas |
| `max_delay_min` | float32 | Retraso máximo registrado |

## Ejemplo de consulta

```python
import pyarrow.parquet as pq
import pandas as pd
import glob

# Leer todo un día
dataset = pq.ParquetDataset("data/stations/2026-04-10/")
df = dataset.read().to_pandas()

# Leer varios días
df = pd.concat([
    pd.read_parquet(f)
    for f in sorted(glob.glob("data/stations/2026-04-*/*.parquet"))
])

# Estaciones con más retraso medio histórico
ranking = (
    df[df["total_arrivals"] > 0]
    .assign(delayed_pct=lambda d: d["delayed_count"] / d["total_arrivals"])
    .groupby(["stop_id", "stop_name"])["delayed_pct"]
    .mean()
    .sort_values(ascending=False)
    .head(20)
)
```
