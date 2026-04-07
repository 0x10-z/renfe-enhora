# snapshots/

**Fichero:** `snapshots.parquet`
**Grain:** 1 fila por ejecución del pipeline × servicio
**Append:** sí — nunca se sobreescribe

## Esquema

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `snapshot_id` | string | Clave primaria: `{service}_{YYYY-MM-DDTHH:MM}` |
| `service` | string | `cercanias` o `ave-larga-distancia` |
| `ts` | string | Timestamp ISO completo de la ejecución |
| `date` | string | Fecha `YYYY-MM-DD` |
| `hour` | int8 | Hora de la ejecución (0–23) |
| `total` | int32 | Total de paradas en el lookahead de 60 min |
| `delayed` | int32 | Paradas con retraso (leve + alto) |
| `cancelled` | int32 | Paradas canceladas |
| `on_time` | int32 | Paradas en hora |
| `avg_delay_min` | float32 | Retraso medio en minutos (solo retrasados) |
| `max_delay_min` | float32 | Retraso máximo en minutos |
| `p50` | float32 | Percentil 50 de retraso |
| `p75` | float32 | Percentil 75 de retraso |
| `p90` | float32 | Percentil 90 de retraso |
| `p95` | float32 | Percentil 95 de retraso |
| `unique_trips` | int32 | Viajes únicos en el lookahead |
| `stations_count` | int32 | Estaciones activas con al menos 1 llegada |

## Ejemplo de consulta

```python
import pandas as pd

df = pd.read_parquet("data/snapshots/snapshots.parquet")

# Evolución diaria del % de retrasos para cercanías
daily = (
    df[df["service"] == "cercanias"]
    .assign(delayed_pct=lambda d: d["delayed"] / d["total"] * 100)
    .groupby("date")["delayed_pct"]
    .mean()
)
```
