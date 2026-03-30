# Pipeline de datos

El pipeline es un proceso Python que se ejecuta cada hora en un servidor VPS vía cron. Su función es descargar los datos de Renfe (horarios estáticos + actualizaciones en tiempo real), procesarlos y escribir los JSON que luego consume la web.

## Ejecución

```bash
# Desde la raíz del repositorio, con el venv activado
python -m scripts.main                    # todos los servicios
python -m scripts.main cercanias          # solo cercanías
python -m scripts.main ave-larga-distancia # solo AVE/LD

# El script de despliegue completo (git pull → pipeline → git push)
./deploy.sh
```

El script cron configurado en el VPS:

```
0 * * * * /ruta/deploy.sh >> /ruta/logs/cron.log 2>&1
```

## Estructura de módulos

```
scripts/
├── main.py              # Orquestador: itera servicios y llama a cada etapa
├── config.py            # Definición de servicios, URLs, umbrales
├── ingestion/
│   ├── gtfs_static.py   # Descarga y caché local del ZIP GTFS estático (24h)
│   └── gtfs_realtime.py # Obtiene actualizaciones RT (JSON primario, protobuf fallback)
├── processing/
│   ├── merger.py        # Lógica principal: fusiona estático+RT, clasifica retrasos
│   ├── stats.py         # Agrega métricas globales
│   └── insights.py      # Genera insights en lenguaje natural (A–I)
└── output/
    └── writer.py        # Escribe los JSON en public/data/{servicio}/
```

## Flujo por servicio

```
gtfs_static.py   → directorio con stops.txt, trips.txt, stop_times.txt, calendar*.txt
gtfs_realtime.py → dict {trip_id: {stop_id: delay_seconds}}  (-1 = cancelado)
merger.py        → StationData = {stop_id: {name, arrivals: [...]}}
stats.py         → dict con métricas globales
writer.py        → escribe stats.json, stations/{id}.json, history.json
insights.py      → lista de {id, text, severity}
writer.py        → escribe insights.json
```

## Clasificación de retrasos

Definida en `config.py`, aplicada en `merger.py`:

| Estado | Condición |
|--------|-----------|
| `en_hora` | delay ≤ 60s |
| `retraso_leve` | 61s – 300s |
| `retraso_alto` | > 300s |
| `cancelado` | delay == -1 (señal especial del feed RT) |

La ventana de predicción es de **60 minutos desde el momento de la ejecución**. Solo se incluyen llegadas dentro de esa ventana.

## Servicios configurados

| ID | Label | GTFS estático | GTFS-RT |
|----|-------|---------------|---------|
| `cercanias` | Cercanías | `ssl.renfe.com/ftransit/...` | `gtfsrt.renfe.com/trip_updates.json` (+ `.pb` fallback) |
| `ave-larga-distancia` | Alta Velocidad / Larga y Media Distancia | `ssl.renfe.com/gtransit/...` | `gtfsrt.renfe.com/trip_updates_LD.json` |

El orden de `ALL_SERVICES` en `config.py` determina la prioridad de visualización en el frontend.

## Caché GTFS estático

Los ZIPs se descargan en `.cache/gtfs/{subdir}/` y se reusan durante 24h. La verificación SSL está desactivada intencionalmente para los endpoints de Renfe (problema conocido del servidor de Renfe).

## Insights (A–I)

`insights.py` genera hasta 9 insights. Los primeros 3 son siempre del snapshot actual; los 6 restantes requieren ≥8 registros históricos:

| ID | Descripción | Requiere historial |
|----|-------------|-------------------|
| A | Hora con más retrasos acumulados ahora | No |
| B | Tren con mayor retraso (≥15min para aparecer) | No |
| C | Estación más afectada (ratio ≥30%, ≥2 retrasos) | No |
| D | Día de la semana históricamente peor | Sí |
| E | Hoy vs. media histórica del mismo día | Sí |
| F | Franja horaria tranquila (retrasos <8% de media) | Sí |
| G | Tendencia esta semana vs. la anterior | Sí |
| H | Peor semana del último mes | Sí |
| I | Anomalía: hoy duplica la media o es excepcionalmente puntual | Sí |

Severidades: `ok` · `info` · `warn` · `bad`

## Timezone

El pipeline fuerza `TZ=Europe/Madrid` al arrancar (`main.py`), independientemente de la configuración del VPS, para que los horarios GTFS se interpreten siempre en hora española.
