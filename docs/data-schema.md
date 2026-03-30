# Esquema de datos JSON

El pipeline escribe los siguientes ficheros en `public/data/{servicio}/`. Son el contrato entre el pipeline Python y el frontend Astro.

## `stats.json`

Métricas globales del snapshot actual + lista de todas las estaciones.

```json
{
  "generated_at": "2026-03-30T09:00:17",
  "stats": {
    "total_trains": 3725,
    "on_time": 3706,
    "delayed": 17,
    "cancelled": 2,
    "avg_delay_min": 2.8,
    "max_delay_min": 6.0,
    "stations_count": 900,
    "busiest_station": {
      "id": "18000",
      "name": "Madrid-Atocha Cercanías",
      "count": 65
    },
    "worst_delay_station": {
      "id": "71502",
      "name": "Nombre estación",
      "avg_delay": 6.0
    }
  },
  "stations": [
    {
      "id": "18000",
      "name": "Madrid-Atocha Cercanías",
      "arrivals_count": 65,
      "delayed_count": 1,
      "max_delay_min": 3.0
    }
  ]
}
```

## `history.json`

Serie temporal append-only. Se añade un registro por cada ejecución del pipeline.

```json
{
  "records": [
    {
      "ts":      "2026-03-30T09:00",
      "date":    "2026-03-30",
      "total":   3725,
      "delayed": 17,
      "avg_min": 2.8,
      "max_min": 6.0
    }
  ]
}
```

## `insights.json`

Lista de insights generados. Puede tener entre 0 y 9 entradas según los datos disponibles.

```json
{
  "generated_at": "2026-03-30T09:00",
  "insights": [
    {
      "id":       "A",
      "text":     "A las 07h se están acumulando los retrasos — 14 trenes afectados",
      "severity": "warn"
    }
  ]
}
```

Valores de `severity`: `ok` · `info` · `warn` · `bad`

IDs posibles: `A` `B` `C` `D` `E` `F` `G` `H` `I` (ver [pipeline.md](pipeline.md#insights-ai))

## `stations/{stop_id}.json`

Llegadas previstas en los próximos 60 minutos para una estación concreta.

```json
{
  "station_id":   "18000",
  "name":         "Madrid-Atocha Cercanías",
  "generated_at": "2026-03-30T09:00:17",
  "arrivals": [
    {
      "trip_id":        "1085L76384C5",
      "route_id":       "10T0017C5",
      "headsign":       "",
      "origin":         "Móstoles-El Soto",
      "scheduled_time": "09:01",
      "estimated_time": "09:01",
      "delay_min":      0.0,
      "status":         "en_hora"
    }
  ]
}
```

Valores de `status`: `en_hora` · `retraso_leve` · `retraso_alto` · `cancelado`

`scheduled_time` y `estimated_time` son strings `HH:MM` en hora de Madrid. Pueden superar `23:59` (p. ej. `25:10`) en servicios nocturnos GTFS; el frontend debe contemplarlo.
