# Plan de Mejoras — Andén / renfe-enhora

**Fecha:** 2026-04-01
**Estado:** En progreso

---

## Co-autores

| Autor | Rol contractual | Participación |
| --- | --- | --- |
| Iker Ocio | El Desarrollador — desarrollo técnico, infraestructura, despliegue y mantenimiento | 50% |
| Jorge Buñuel | El Estratega de Datos — estrategia de datos, definición y gestión de la información, enfoque estratégico del producto | 50% |

*Contrato de Coautoría y Colaboración firmado en Vitoria, 1 de abril de 2026.*

### Decisiones acordadas

| # | Pregunta | Decisión |
| --- | --- | --- |
| F6 | ¿Formato de datos en crudo? | JSON mensual (un fichero por año-mes, ej. `raw/2026-04.json`) |
| F3 | ¿Fuente para mapeo de zonas? | Partir desde 0 usando las coordenadas lat/lon de `stations_geo.json` para inferir la CCAA |
| F4 | ¿IDA y VUELTA separados? | Sí, entradas separadas en el ranking |
| F7 | ¿Desacoplar procesado de deployment Vercel? | Sí — ver decisión de arquitectura abajo |

### Decisión de arquitectura: desacoplar pipeline de Vercel

**Problema:** con cron cada 5 min → 288 commits/día → 288 builds de Vercel/día.
El plan gratuito de Vercel (Hobby) permite 100 builds/día. Se excedería en 2.88×.

**Solución adoptada: dos crons separados.**

```text
*/5 * * * *   run_pipeline.sh   # procesa datos y escribe JSON en disco — sin git
0   * * * *   push_to_git.sh    # commit + push a GitHub — 1 vez por hora
```

- El pipeline corre cada 5 min y mantiene los JSON frescos en el VPS
- Vercel solo se despliega 24 veces/día (dentro del límite gratuito de 100/día)
- Los usuarios ven datos con hasta 60 min de antigüedad (igual que ahora con el cron horario)
- Para datos más frescos en el futuro: migrar JSON a Azure blob storage

---

## Resumen de cambios

| # | Feature | Dificultad | Estado | Área |
| --- | --- | --- | --- | --- |
| 1 | Recategorizar umbrales de retraso (5 min = en hora) | Fácil | ✓ Completado | Pipeline + Frontend |
| 2 | Tipo de tren: ranking de retrasos acumulados (cada tipo separado) | Media | Pendiente | Pipeline + Frontend |
| 3 | Zonas geográficas (dos niveles: Núcleos Cercanías + CCAA) | Media | Pendiente | Pipeline + Frontend |
| 4 | Peores conexiones: rutas completas con todas las paradas | Difícil | Pendiente | Pipeline + Frontend |
| 5 | Comparativa zonas: abandonadas vs bien servidas (narrativa automática) | Difícil | Pendiente | Pipeline + Frontend |
| 6 | Almacenamiento de datos en crudo para análisis futuros | Media | ✓ Completado | Pipeline |
| 7 | Cron cada 5 minutos | Fácil | ✓ Completado | Infra |
| 8 | Desacoplar pipeline de Vercel (run_pipeline.sh / push_to_git.sh) | Fácil | ✓ Completado | Infra |
| 9 | Sección equipo en sobre.astro | Fácil | ✓ Completado | Frontend |

**Alcance:** Cercanías + AVE/Larga Distancia en todos los features.

**Umbrales nuevos:** no se aplican retroactivamente. Los datos históricos mantienen el criterio antiguo.

---

## Feature 1 — Recategorizar umbrales de retraso

> Dificultad: Fácil — ✓ COMPLETADO

### Cambio de umbrales

| Estado | Umbral actual | Umbral nuevo |
| --- | --- | --- |
| `en_hora` | ≤ 60 s | ≤ 300 s (5 min) |
| `retraso_leve` | 61–300 s | 301–600 s (5–10 min) |
| `retraso_alto` | > 300 s | > 600 s (> 10 min) |
| `cancelado` | -1 | -1 (sin cambio) |

### Archivos a modificar

- `scripts/config.py` — constantes `DELAY_THRESHOLDS` (único punto de verdad) ✅
- `scripts/processing/merger.py` — ya lee de config, sin valores hardcodeados ✅
- `scripts/processing/insights.py` — umbrales B (≥15 min) y C (30%) son independientes, sin cambios ✅
- `src/components/StationBoard.astro` — badges actualizados a "5-10 min" y "+10 min" ✅
- `src/pages/index.astro` — sin leyenda de umbrales, no aplica ✅
- `src/pages/sobre.astro` — umbrales y descripción de limitaciones actualizados ✅

### Decisión sobre histórico

Los `history.json` existentes NO se recalculan. Los datos anteriores al cambio reflejan el umbral antiguo. Se añade un campo `schema_version: 2` a `stats.json` y `history.json` para que el frontend pueda distinguir la época si fuera necesario en el futuro.

**Partición de history.json:** sí, se particionará por año-mes para evitar crecimiento indefinido.

- Formato: `public/data/{service}/history/YYYY-MM.json` (un fichero por mes)
- El fichero del mes actual se va completando con cada ejecución del cron
- El frontend carga los últimos N meses según lo que necesite mostrar (ej. 3 meses para el gráfico de tendencia)
- Con cron cada 5 min: ~288 registros/día × 30 días = ~8.640 registros/mes, ~1.7 MB/mes — manejable por fichero

---

## Feature 2 — Tipo de tren: categorización y ranking de retrasos

> Dificultad: Media

### Objetivo

Identificar qué tipo de tren acumula más retrasos de forma sistemática. Cada subtipo es independiente — no se agrupan AVE + ALVIA + AVANT.

### Tipos a identificar

Fuente: campos `trip_short_name` / `route_short_name` del GTFS estático.

| Código GTFS | Tipo mostrado |
| --- | --- |
| AVE | AVE |
| AV2, AVLO | AVE low-cost (AVLO) |
| ALVIA | Alvia |
| AVANT | Avant |
| MD | Media Distancia |
| LD | Larga Distancia |
| RG / REG | Regional |
| C1–C10+ | Cercanías (línea específica) |
| (sin prefijo conocido) | Otros |

### Cambios en pipeline

1. `scripts/config.py` — añadir `TRAIN_TYPE_PREFIXES: dict[str, str]` (código → etiqueta)
2. `scripts/processing/merger.py` — añadir campo `train_type` a cada arrival
3. `scripts/processing/stats.py` — nuevo bloque `by_train_type`:

```python
by_train_type = {
    "AVE": {
        "total": 120,
        "delayed": 34,
        "cancelled": 2,
        "avg_delay_min": 8.3,
        "max_delay_min": 47.0,
        "delayed_pct": 0.28,
        "rank_worst": 3
    },
}
```

4. `scripts/output/writer.py` — incluir `by_train_type` en `stats.json`
5. `history/YYYY-MM.json` — añadir `by_train_type` a cada registro histórico

**Sobre guardar stats con dimensión temporal:** `stats.json` es un snapshot del momento actual (sin fecha propia más allá de `generated_at`) — no pierde información porque la dimensión temporal vive en `history/YYYY-MM.json`. Cada registro histórico incluirá `by_train_type`, lo que permite trazar la evolución de cada tipo de tren a lo largo del tiempo sin duplicar datos.

### Ranking de retrasos acumulados

- Métrica principal: `avg_delay_min` ponderado por volumen (`total` trenes)
- Métrica secundaria: `delayed_pct` (% de trenes con retraso)
- El campo `rank_worst` (1 = peor) se calcula al escribir `stats.json`

### Cambios en frontend

- Sección nueva "Por tipo de tren" en `pages/index.astro`: gráfico de barras horizontales (ECharts) ordenado de peor a mejor, tipo → avg_delay_min, tooltip con total trenes / % retrasados / retraso máximo
- Badge `train_type` en `StationBoard.astro`
- Narrativa automática: *"El tipo de tren con más retrasos acumulados este periodo es [X], con una media de [Y] min y un [Z]% de servicios afectados"*

---

## Feature 3 — Zonas geográficas (dos niveles)

> Dificultad: Media

### Objetivo

Asignar cada estación a dos niveles de zona para comparar territorios: núcleo operativo y comunidad autónoma.

### Definición de zonas

**Nivel 1 — Núcleos de Cercanías Renfe** (para servicio Cercanías):
Madrid, Barcelona, Valencia, Sevilla, Bilbao, Asturias, Murcia, Zaragoza, San Sebastián, Santander, Cádiz, Málaga, Almería.

**Nivel 2 — Comunidad Autónoma** (para AVE/LD y como segundo nivel en Cercanías):
Las 17 CCAA + Ceuta + Melilla.

### Fuente de datos para el mapeo

- `public/data/stations_geo.json` tiene coordenadas lat/lon de cada estación
- Estrategia: tabla manual `stop_id → {nucleo, ccaa}` generada una sola vez desde las coordenadas + revisión manual
- Razón: más fiable que reverse geocoding continuo; las estaciones de Renfe son un conjunto finito y estable

### Archivos nuevos y modificados

1. `scripts/data/zones_map.json` (nuevo, generado una vez):

```json
{
  "71000": {"nucleo": "Madrid",    "ccaa": "Comunidad de Madrid"},
  "79300": {"nucleo": "Barcelona", "ccaa": "Cataluña"}
}
```

2. `scripts/config_zones.py` (nuevo) — carga `zones_map.json`, expone `get_zone(stop_id)`
3. `scripts/processing/stats.py` — añadir `by_nucleo` y `by_ccaa` en stats
4. `scripts/output/writer.py` — escribir `public/data/{service}/zones.json`

### Formato zones.json

```json
{
  "generated_at": "...",
  "nucleos": [
    {
      "id": "madrid",
      "name": "Núcleo Madrid",
      "stations_count": 94,
      "avg_delay_min": 2.1,
      "delayed_pct": 0.12,
      "cancellation_rate": 0.01,
      "trend": "stable",
      "rank_worst": 8
    }
  ],
  "ccaa": [
    {
      "id": "murcia",
      "name": "Región de Murcia",
      "avg_delay_min": 11.4,
      "delayed_pct": 0.47,
      "cancellation_rate": 0.08,
      "trend": "worsening",
      "rank_worst": 1
    }
  ]
}
```

### Cambios en frontend

- Mapa SVG de España coloreado por `avg_delay_min` o `delayed_pct` (escala verde→rojo)
- Panel de ranking lateral: top 5 peores / top 5 mejores zonas
- Click en zona → filtra estaciones del dashboard principal

---

## Feature 4 — Peores conexiones: rutas completas

> Dificultad: Difícil

### Objetivo

Identificar las líneas con peor rendimiento crónico, extraer su recorrido completo con todas las paradas en orden, y mostrar el impacto parada a parada.

### Definición de "ruta"

En GTFS: `route_id` agrupa todos los `trip_id` de una misma línea (ej: C-1 Madrid, AVE Madrid–Sevilla). La secuencia canónica de paradas = el trip más largo de esa ruta (mayor número de paradas).

### Datos GTFS necesarios (ya cacheados)

`routes.txt` + `trips.txt` + `stop_times.txt` + `stops.txt`

### Cambios en pipeline

1. `scripts/processing/routes.py` (nuevo módulo):
   - Carga `routes.txt`, `trips.txt`, `stop_times.txt` del GTFS cacheado
   - Consolida trips bidireccionales (misma `route_id`, headsigns opuestos → una ruta con sentidos IDA/VUELTA)
   - Cruza con delays RT del pipeline actual
   - Calcula: `avg_delay_min`, `delayed_pct`, `cancellation_rate`, `worst_stop_id`, `best_stop_id`
   - Asigna `zone` (nucleo + ccaa) desde Feature 3
   - Genera `rank_worst` global y por zona
2. `scripts/output/writer.py` — nuevo archivo `public/data/{service}/routes.json`

### Formato routes.json

```json
{
  "generated_at": "...",
  "routes": [
    {
      "route_id": "C1_IDA",
      "route_name": "C-1",
      "display_name": "C-1 Príncipe Pío – Recoletos – Alcobendas",
      "train_type": "Cercanías",
      "zone_nucleo": "Madrid",
      "zone_ccaa": "Comunidad de Madrid",
      "stops_sequence": [
        {"stop_id": "71001", "name": "Príncipe Pío", "avg_delay_min": 0.4},
        {"stop_id": "71002", "name": "Recoletos",    "avg_delay_min": 1.1}
      ],
      "stats": {
        "avg_delay_min": 4.2,
        "delayed_pct": 0.31,
        "cancellation_rate": 0.03,
        "worst_stop": {"stop_id": "71012", "name": "...", "avg_delay_min": 9.1},
        "best_stop":  {"stop_id": "71001", "name": "...", "avg_delay_min": 0.4}
      },
      "rank_worst": 1,
      "rank_worst_in_zone": 1
    }
  ]
}
```

### Cambios en frontend

1. Nueva página `src/pages/rutas.astro`: ranking de rutas peor servidas, filtro por zona / tipo de tren
2. Nueva página `src/pages/rutas/[route_id].astro`: diagrama lineal de paradas con gradiente de color (delay bajo→alto), comparativa con la mejor ruta de la misma zona/tipo, narrativa automática
3. Sección "rutas más afectadas" en `pages/index.astro` (top 3, con enlace a página completa)

### Complejidad técnica

- `stop_times.txt` puede tener cientos de miles de filas en AVE/LD — usar pandas con chunking o filtrar por `trip_id` activos
- Las rutas nocturnas tienen `arrival_time > 24:00:00` — ya manejado en el merger actual
- Rutas bidireccionales: consolidar por `route_id` o mantener dos entradas IDA/VUELTA (decisión pendiente Jorge)

---

## Feature 5 — Comparativa zonas: abandonadas vs bien servidas

> Dificultad: Difícil — Depende de: Feature 3 (zonas) + Feature 4 (rutas)

### Objetivo

Mostrar de forma visual y objetiva qué zonas están sistemáticamente mal atendidas vs bien atendidas, con narrativa generada automáticamente desde los datos.

### Criterios de clasificación automática

| Etiqueta | Criterios |
| --- | --- |
| `zona_critica` | avg_delay > 2× media nacional AND trend = "worsening" |
| `zona_deterioro` | avg_delay > media nacional AND trend = "worsening" |
| `zona_estable` | avg_delay ≈ media nacional (±20%) |
| `zona_referencia` | avg_delay < 0.7× media nacional AND trend = "stable" o "improving" |

El cálculo de `trend` usa los últimos N registros del `history.json` por zona (regresión lineal simple sobre `avg_delay_min`).

### Narrativa automática

Generada en `insights.py`, ejemplos:

- `zona_critica`: *"La Región de Murcia acumula un retraso medio de 11.4 min, 3.2× la media nacional (3.5 min), y la tendencia es creciente en las últimas 2 semanas."*
- `zona_referencia`: *"El Núcleo de Madrid es el mejor servido: retraso medio de 2.1 min, con el 88% de los trenes llegando a tiempo."*
- Comparativa: *"La línea C-1 de Madrid tarda de media 1.8 min. La línea MD-114 de Murcia acumula 12.3 min — 6.8× más."*

### Cambios en pipeline

- `scripts/processing/insights.py` — nuevos tipos de insight (J–N) para zonas
- `zones.json` (Feature 3) — añadir campos `label` y `narrative` por zona
- `history/YYYY-MM.json` — añadir `by_nucleo` y `by_ccaa` a cada registro histórico

### Cambios en frontend

1. Página `src/pages/zonas.astro`: mapa de calor (Feature 3), tabla de ranking completo con badge de estado, sección "más afectadas" vs "mejor servidas" side-by-side, gráfico de tendencia histórica por zona (ECharts multi-line)
2. `pages/index.astro` — bloque de resumen: *"X zonas en estado crítico"* con enlace

---

## Feature 6 — Almacenamiento de datos en crudo

> Dificultad: Media

### Contexto y recomendación

Actualmente el pipeline solo persiste datos **agregados** (`history.json`, `stats.json`). Esto impide análisis futuros como patrones por hora/día, evolución de tipo de tren en el tiempo, o detección de incidentes.

**Recomendación: almacenar eventos de retraso individuales en formato NDJSON rolling.**

### Propuesta de implementación

Archivo: `public/data/{service}/raw/YYYY-MM.json`

- Un fichero por mes (ej. `raw/2026-04.json`), append-only dentro del mes
- Estructura: objeto con clave `records` → array de eventos
- Solo almacena arrivals con `delay_min > 0` o `status = cancelado`
- Se mantienen todos los meses en el VPS; no hay rotación automática (el coste es bajo)
- **No se sube a GitHub** — se almacena solo en el VPS (añadir a `.gitignore`)

Ventajas del fichero mensual frente al diario:

- Menos ficheros en disco (12/año vs 365/año)
- Cada fichero contiene contexto temporal suficiente para análisis de tendencias mensuales
- Fácil de exportar o archivar mes a mes

Esquema por línea:

```json
{"ts":"2026-04-01T10:05","trip_id":"AVE-1234","route_id":"R001","train_type":"AVE","stop_id":"71000","stop_name":"Madrid-Atocha","delay_min":8.5,"status":"retraso_alto","zone_nucleo":"Madrid","zone_ccaa":"Comunidad de Madrid"}
```

### Estimación de volumen

Con cron cada 5 min y filtrando solo trenes retrasados:

- ~7 MB/día (estimación conservadora)
- ~210 MB/mes con retención de 90 días
- Manejable en cualquier VPS de gama media

### Archivos a modificar

1. `scripts/output/writer.py` — añadir `write_raw_events(arrivals, service)` con append al NDJSON del día
2. `scripts/config.py` — `RAW_RETENTION_DAYS = 90`
3. `.gitignore` — añadir `public/data/*/raw/`

### Qué habilita en el futuro

- Análisis de patrones por hora del día y día de la semana
- Tendencias por tipo de tren con granularidad diaria
- Detección automática de incidentes (spike > 2σ)
- Exportación a CSV para análisis externos

---

## Feature 7 — Cron cada 5 minutos

> Dificultad: Fácil — ✓ COMPLETADO

`cron.example` actualizado a `*/5 * * * *`.

## Feature 8 — Desacoplar pipeline de Vercel

> Dificultad: Fácil — ✓ COMPLETADO

Creados `run_pipeline.sh` (cron `*/5`) y `push_to_git.sh` (cron `0 *`). Ambos con bit ejecutable guardado en git. `cron.example` actualizado con los dos crons y documentación de setup.

## Feature 9 — Sección de equipo en sobre.astro

> Dificultad: Fácil — ✓ COMPLETADO

Añadida sección `07 · Equipo` en `sobre.astro` con tarjetas para Iker Ocio (El Desarrollador) y Jorge Buñuel (El Estratega de Datos), basada en los roles del contrato de coautoría.

### Impacto en otros features

- `history/YYYY-MM.json` crecerá ~288 registros/día (particionado por mes — ver Feature 1)
- El deployment en Vercel se desacopla del cron: pipeline cada 5 min, push a git cada hora (ver decisión de arquitectura)
- Los datos en crudo (Feature 6) dependen directamente de esta frecuencia

---

## Dependencias entre features

```text
[1] Umbrales          → base para todos los demás        (completado ✓)
[2] Tipo de tren      → necesario para [4] y [5]         (pendiente)
[3] Zonas             → necesario para [4] y [5]         (pendiente)
[4] Rutas             → necesario para [5]               (pendiente)
[5] Comparativa       → depende de [2] + [3] + [4]       (pendiente)
[6] Datos en crudo    → independiente                    (completado ✓)
[7] Cron 5min         → completado ✓
[8] Desacoplar Vercel → completado ✓
[9] Equipo sobre.astro → completado ✓
```

## Orden de implementación recomendado

```text
Sprint 1 — Base de datos (1–2 días)
  ├── [1] Umbrales de retraso (config.py + merger.py + frontend badges)
  └── [6] Datos en crudo (writer.py + .gitignore)

Sprint 2 — Enriquecimiento (3–5 días)
  ├── [2] Tipo de tren (config + merger + stats + frontend gráfico)
  └── [3] Zonas — generar zones_map.json + config_zones.py + stats por zona

Sprint 3 — Análisis avanzado (5–7 días)
  ├── [4] Rutas completas — routes.py + routes.json + página /rutas
  └── [5] Comparativa zonas — insights.py + zonas.astro + narrativa

Sprint 4 — Pulido frontend (2–3 días)
  └── Mapa SVG España, gráficos de tendencia, páginas de detalle de ruta
```
