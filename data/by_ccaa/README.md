# by_ccaa/

**Fichero:** `history.parquet`
**Grain:** 1 fila por Comunidad Autónoma × ejecución del pipeline
**Append:** sí — fichero único acumulativo

Histórico de rendimiento por CCAA. Permite ver qué comunidades tienen peor puntualidad a lo largo del tiempo.

## Esquema

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `snapshot_id` | string | FK → `snapshots.snapshot_id` |
| `service` | string | `cercanias` o `ave-larga-distancia` |
| `ccaa` | string | Nombre de la Comunidad Autónoma |
| `total` | int32 | Total de paradas en el lookahead |
| `delayed` | int32 | Paradas con retraso |
| `delayed_pct` | float32 | Fracción de paradas retrasadas (0–1) |
| `avg_delay_min` | float32 | Retraso medio en minutos |
| `max_delay_min` | float32 | Retraso máximo en minutos |
| `stations_count` | int32 | Estaciones activas en esa CCAA |

## Ejemplo de consulta

```python
import pandas as pd

df = pd.read_parquet("data/by_ccaa/history.parquet")

# Ranking de CCAA por % de retraso histórico en cercanías
ranking = (
    df[df["service"] == "cercanias"]
    .groupby("ccaa")["delayed_pct"]
    .mean()
    .sort_values(ascending=False)
)
```
