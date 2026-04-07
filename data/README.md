# data/

Almacenamiento columnar histórico del pipeline de Renfe Enhora.

Cada ejecución del pipeline (`python -m scripts.main`) añade filas a estos ficheros Parquet sin borrar datos anteriores. Son la **fuente de verdad histórica** del proyecto.

Los JSONs en `public/data/` son artefactos generados a partir de estos datos para servir al frontend estático de Vercel. No son la fuente de verdad.

## Tablas

| Carpeta | Fichero | Grain | Tamaño estimado |
|---------|---------|-------|-----------------|
| `snapshots/` | `snapshots.parquet` | 1 fila por ejecución | < 1 MB/año |
| `arrivals/` | `YYYY-MM.parquet` | 1 fila por tren × estación × ejecución | ~15-25 MB/mes |
| `stations/` | `YYYY-MM.parquet` | 1 fila por estación × ejecución | ~3-5 MB/mes |
| `by_type/` | `history.parquet` | 1 fila por tipo de tren × ejecución | < 1 MB/año |
| `by_ccaa/` | `history.parquet` | 1 fila por CCAA × ejecución | < 1 MB/año |

## Cómo leer

```python
import pandas as pd

df = pd.read_parquet("data/arrivals/2026-04.parquet")
df.head()
```

## Cómo se generan

El módulo `scripts/output/parquet_writer.py` expone `append_snapshot()`, que es llamado desde `scripts/main.py` al final de cada ejecución del pipeline.

## Compresión

Los ficheros usan compresión **zstd** internamente (gestionada por pyarrow). No es necesario comprimir manualmente.
