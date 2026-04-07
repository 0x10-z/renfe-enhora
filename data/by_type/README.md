# by_type/

**Fichero:** `history.parquet`
**Grain:** 1 fila por tipo de tren × ejecución del pipeline
**Append:** sí — fichero único acumulativo

Histórico de rendimiento por categoría de tren (AVE, Alvia, Cercanías, etc.).

## Esquema

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `snapshot_id` | string | FK → `snapshots.snapshot_id` |
| `service` | string | `cercanias` o `ave-larga-distancia` |
| `train_type` | string | Categoría: AVE, AVLO, Alvia, Avant, Media Distancia, Regional, Larga Distancia, Cercanías, Otros |
| `total` | int32 | Total de paradas en el lookahead |
| `delayed` | int32 | Paradas con retraso |
| `cancelled` | int32 | Paradas canceladas |
| `delayed_pct` | float32 | Fracción de paradas retrasadas (0–1) |
| `avg_delay_min` | float32 | Retraso medio en minutos |
| `max_delay_min` | float32 | Retraso máximo en minutos |

## Ejemplo de consulta

```python
import pandas as pd

df = pd.read_parquet("data/by_type/history.parquet")

# Evolución mensual del % de retraso por tipo
df["month"] = df["snapshot_id"].str[df["snapshot_id"].str.find("_")+1:].str[:7]
monthly = df.groupby(["month", "train_type"])["delayed_pct"].mean().unstack()
```
