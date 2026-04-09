# Plan de Mejoras — Andén / renfe-enhora

**Fecha inicio:** 2026-04-01
**Última actualización:** 2026-04-09 (F5 completado — todos los features terminados)
**Estado:** ✓ Completado (15/15 features)

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
| F3 | ¿Fuente para mapeo de zonas? | Coordenadas lat/lon de `stations_geo.json` + haversine a centroides de núcleos |
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
| 2 | Tipo de tren: ranking + drilldown modal (click en gráfico) | Media | ✓ Completado | Pipeline + Frontend |
| 3 | Zonas geográficas: CCAA + núcleos, mapa coropleta, modal de detalle | Media | ✓ Completado | Pipeline + Frontend |
| 4 | Peores conexiones: rutas completas con todas las paradas | Difícil | ✓ Completado | Pipeline + Frontend |
| 5 | Comparativa zonas: abandonadas vs bien servidas (narrativa automática) | Difícil | ✓ Completado | Pipeline + Frontend |
| 6 | Almacenamiento histórico en Parquet (snapshots, arrivals, stations, by_type, by_ccaa) | Media | ✓ Completado | Pipeline |
| 7 | Cron cada 5 minutos | Fácil | ✓ Completado | Infra |
| 8 | Desacoplar pipeline de Vercel (run_pipeline.sh / push_to_git.sh) | Fácil | ✓ Completado | Infra |
| 9 | Sección equipo en sobre.astro | Fácil | ✓ Completado | Frontend |
| 10 | Imágenes reales de trenes por tipo (WebP desde Wikimedia Commons) | Fácil | ✓ Completado | Frontend |
| 11 | Histórico por estación: gráfico de tendencia en página de detalle | Media | ✓ Completado | Frontend |
| 12 | Ranking de rutas/líneas con más retrasos | Media | ✓ Completado | Pipeline + Frontend |
| 13 | SEO / OpenGraph: meta tags dinámicos por servicio | Fácil | ✓ Completado | Frontend |
| 14 | Tendencias históricas: weekday vs weekend + evolución por tipo de tren | Media | ✓ Completado | Frontend |
| 15 | Alertas por umbral: insight cuando una zona/línea supera su media histórica | Media | ✓ Completado | Pipeline + Frontend |

**Alcance:** Cercanías + AVE/Larga Distancia en todos los features.

**Umbrales nuevos:** no se aplican retroactivamente. Los datos históricos mantienen el criterio antiguo.

---

## Feature 1 — Recategorizar umbrales de retraso

> Dificultad: Fácil — ✓ COMPLETADO

### Cambio de umbrales

| Estado | Umbral anterior | Umbral nuevo |
| --- | --- | --- |
| `en_hora` | ≤ 60 s | ≤ 300 s (5 min) |
| `retraso_leve` | 61–300 s | 301–600 s (5–10 min) |
| `retraso_alto` | > 300 s | > 600 s (> 10 min) |
| `cancelado` | -1 | -1 (sin cambio) |

### Archivos modificados

- `scripts/config.py` — constantes `DELAY_THRESHOLDS` ✅
- `scripts/processing/merger.py` — ya lee de config ✅
- `src/components/StationBoard.astro` — badges "5-10 min" y "+10 min" ✅
- `src/pages/sobre.astro` — umbrales y descripción actualizados ✅

---

## Feature 2 — Tipo de tren: categorización y ranking de retrasos

> Dificultad: Media — ✓ COMPLETADO

### Lo implementado

- Pipeline: campo `train_type` en cada arrival; `by_train_type` en `stats.json` con `total`, `delayed`, `cancelled`, `avg_delay_min`, `max_delay_min`, `delayed_pct`, `rank_worst`
- Pipeline: `by_type_arrivals.json` — lista de retrasos por tipo, máx 200, ordenados por delay desc
- Frontend: gráfico de barras horizontales ECharts con narrativa automática
- Frontend: imágenes reales de trenes por subtipo (WebP, Wikimedia Commons)
- Frontend: modal drilldown al hacer click en el gráfico (`TrainTypeDetailModal`)
- Frontend: componente `DrilldownModal.astro` reutilizable

### Tipos identificados

| Código GTFS | Tipo mostrado |
| --- | --- |
| AVE | AVE |
| AV2, AVLO | AVLO |
| ALVIA | Alvia |
| AVANT | Avant |
| MD | Media Distancia |
| LD | Larga Distancia |
| RG / REG | Regional |
| C1–C10+ | Cercanías |
| (sin prefijo conocido) | Otros |

---

## Feature 3 — Zonas geográficas (dos niveles)

> Dificultad: Media — ✓ COMPLETADO

### Lo implementado

**Pipeline:**

- `scripts/data/zones_map.json` — 1.602 estaciones → `{ccaa, nucleo}`, generado con haversine desde `stations_geo.json`
- `scripts/config_zones.py` — `get_ccaa(stop_id)`, `get_nucleo(stop_id)`
- `stats.json` — nuevos campos `by_ccaa` y `by_nucleo` con totales, retrasos, percentiles y `rank_worst`
- `zones.json` — snapshot actual por CCAA y núcleo
- `by_ccaa_arrivals.json` — lista de retrasos por CCAA, máx 200, para el modal

**Frontend:**

- Layout 2 columnas: mapa coropleta Leaflet (izquierda) + gráfico barras ECharts (derecha)
- Mapa: cada CCAA coloreada por `delayed_pct`, tooltip interactivo, leyenda
- Barras: misma escala de color, ordenadas de mayor a menor retraso
- Click en mapa o en barra → `CcaaDetailModal` con tabla de retrasos (tren, tipo, estación, horarios)
- `DrilldownModal.astro`: componente base reutilizable con props
- `spain-ccaa.geojson` (335 KB, softlinegeodb/GADM, licencia ODbL)
- Atribución cartográfica en `sobre.astro`

### Pendiente de F3

- [ ] Filtrar estaciones del dashboard principal al hacer click en una zona (ver F5)
- [x] Histórico por CCAA — disponible en `data/by_ccaa/history.parquet` (F6 ✓)

---

## Feature 4 — Peores conexiones: rutas completas

> Dificultad: Difícil — ✓ COMPLETADO (depende de: F3 ✓, F6 ✓)

### Lo implementado

| Pieza | Estado |
| --- | --- |
| `scripts/processing/routes.py` — geo estática + `compute_route_chronic_stats` desde Parquet | ✅ |
| `writer.py` → `routes_geo.json` con `stats` (snapshot) + `chronic_stats` (histórico) | ✅ |
| `by_route_arrivals.json` — arrivals por ruta (snapshot actual) | ✅ (F12) |
| `src/pages/rutas.astro` — ranking, mapa, filtros, link ↗ a detalle | ✅ |
| `src/pages/rutas/[service]/[route_id].astro` — página detalle con mapa + paradas + stats | ✅ |
| Bloque top-3 en `index.astro` | ✅ |

### Objetivo

Identificar las líneas con peor rendimiento **crónico** (no solo en la captura actual), extraer su recorrido completo con todas las paradas en orden, y mostrar el impacto parada a parada.

### Definición de "ruta"

En GTFS: `route_id` agrupa todos los `trip_id` de una misma línea (ej: C-1 Madrid, AVE Madrid–Sevilla). La secuencia canónica de paradas = el trip más largo de esa ruta.

### Fuente de datos históricos (Parquet)

El análisis crónico usa `data/arrivals/YYYY-MM.parquet` (una fila por arrival con `trip_id`, `train_name`, `route_id`, `delay_seconds`, `stop_id`, `ts`). Ejemplo:

```python
import pandas as pd, glob
dfs = [pd.read_parquet(f) for f in glob.glob("data/arrivals/*.parquet")]
arrivals = pd.concat(dfs)
route_stats = (
    arrivals.groupby(["service", "route_id", "train_name"])
    .agg(avg_delay_min=("delay_seconds", lambda x: x[x>0].mean()/60),
         delayed_pct=("delay_seconds", lambda x: (x > 300).mean()),
         n_trips=("trip_id", "nunique"))
    .reset_index()
    .sort_values("delayed_pct", ascending=False)
)
```

### Datos GTFS necesarios (ya cacheados)

`routes.txt` + `trips.txt` + `stop_times.txt` + `stops.txt`

### Cambios en pipeline

1. `scripts/processing/routes.py` (nuevo módulo):
   - Carga `routes.txt`, `trips.txt`, `stop_times.txt` del GTFS cacheado
   - Lee `data/arrivals/*.parquet` para calcular métricas crónicas (no solo snapshot actual)
   - Calcula: `avg_delay_min`, `delayed_pct`, `cancellation_rate`, `worst_stop_id` sobre N meses
   - Asigna zona (nucleo + ccaa) desde `config_zones`
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
      "display_name": "C-1 Príncipe Pío – Alcobendas",
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
        "worst_stop": {"stop_id": "71012", "name": "...", "avg_delay_min": 9.1}
      },
      "rank_worst": 1
    }
  ]
}
```

### Cambios en frontend

1. Nueva página `src/pages/rutas.astro`: ranking de rutas peor servidas, filtro por zona / tipo de tren
2. Nueva página `src/pages/rutas/[route_id].astro`: diagrama lineal de paradas con gradiente de color
3. Sección "rutas más afectadas" en `pages/index.astro` (top 3, enlace a página completa)

### Complejidad técnica

- `stop_times.txt` puede tener cientos de miles de filas — filtrar por `trip_id` activos
- Rutas bidireccionales: mantener IDA/VUELTA separados (decisión F4 ya tomada)
- Rutas nocturnas: `arrival_time > 24:00:00` ya manejado en el merger

---

## Feature 5 — Comparativa zonas: abandonadas vs bien servidas

> Dificultad: Difícil — ✓ COMPLETADO (depende de: F3 ✓, F6 ✓)

### Lo implementado

**Pipeline (`scripts/processing/zones_analysis.py`):**

- `compute_zone_trends(service_name, data_root)` — nuevo módulo, puro PyArrow (sin pandas/scipy)
- Lee `data/by_ccaa/history.parquet`, filtra por servicio, agrupa por CCAA, toma últimos 30 registros
- Regresión lineal OLS en Python puro para calcular pendiente de `delayed_pct`
- Clasifica cada CCAA en `zona_critica`, `zona_deterioro`, `zona_estable`, `zona_referencia`
- Genera narrativa automática por zona con contexto vs media nacional
- Media nacional = media ponderada de todas las CCAA (igual peso por región)

**`writer.py` — `write_zones()` actualizado:**

- Llama a `compute_zone_trends()` y fusiona los campos `label`, `trend`, `narrative`, `historical_avg_pct`, `national_avg_pct`, `n_records` en cada entrada CCAA de `zones.json`
- Degradación elegante: si no hay Parquet, los campos se rellenan con valores neutros

**Frontend (`src/pages/zonas.astro`):**

- Nueva página `/zonas` con tabs Cercanías / AVE
- Narrativa hero: frase automática del peor y mejor zona
- Dos columnas: top 5 peores / top 5 mejores con flechas de tendencia
- Tabla completa ordenable por % hoy, media histórica o nombre
- Badges de zona (`zona_critica` → rojo, `zona_referencia` → verde)
- Badges de tendencia (↑ empeorando / ↓ mejorando / → estable)
- Degradación elegante si no hay datos históricos

**`index.astro`:** CTA "Ver análisis completo por comunidad →" al final de la sección CCAA

**`Layout.astro`:** "Zonas" añadido a la navegación global

### Criterios de clasificación

| Etiqueta | Criterio |
| --- | --- |
| `zona_critica` | hist_avg ≥ 2× media nacional AND trend = "worsening" |
| `zona_deterioro` | hist_avg > media nacional AND trend = "worsening" |
| `zona_estable` | resto de casos |
| `zona_referencia` | hist_avg < 0.7× media nacional |

---

## Feature 6 — Almacenamiento histórico en Parquet

> Dificultad: Media — ✓ COMPLETADO

- `data/snapshots/snapshots.parquet` — 1 fila por ejecución, métricas globales
- `data/arrivals/YYYY-MM.parquet` — todos los arrivals (completo, no solo retrasados)
- `data/stations/YYYY-MM.parquet` — resumen por estación por snapshot
- `data/by_type/history.parquet` — histórico por tipo de tren
- `data/by_ccaa/history.parquet` — histórico por CCAA
- Compresión zstd, ~15-25 MB/mes para arrivals
- Incluido en git. README de esquema en cada carpeta.
- `scripts/output/parquet_writer.py` — writer con schemas tipados
- `push_to_git.sh` actualizado para incluir `data/` en commit y diff

---

## Feature 7 — Cron cada 5 minutos

> Dificultad: Fácil — ✓ COMPLETADO

`cron.example` actualizado a `*/5 * * * *`.

---

## Feature 8 — Desacoplar pipeline de Vercel

> Dificultad: Fácil — ✓ COMPLETADO

Creados `run_pipeline.sh` (cron `*/5`) y `push_to_git.sh` (cron `0 *`).

---

## Feature 9 — Sección de equipo en sobre.astro

> Dificultad: Fácil — ✓ COMPLETADO

Sección `08 · Equipo` en `sobre.astro` con tarjetas para Iker Ocio y Jorge Buñuel.

---

## Feature 10 — Imágenes reales de trenes

> Dificultad: Fácil — ✓ COMPLETADO

- Imágenes WebP descargadas de Wikimedia Commons (CC BY-SA / CC0) para AVE, AVLO, Alvia, Avant, MD, Regional, LD, Cercanías
- Organizadas en `public/trenes/{tipo}/s{serie}.webp`
- Pendiente: ~7 `.fake` (cercanias/s440, s450, s463, s599; md/s450, s598; regional/s598)

---

## Feature 11 — Histórico por estación

> Dificultad: Media — ✓ COMPLETADO

- Gráfico de barras ECharts en `StationBoard.astro` mostrando `% retrasos` últimos 7 días
- Lee `station-history/YYYY-MM-DD.json` (7 ficheros en paralelo con `Promise.all`)
- Color por umbral: verde <10%, naranja 10-30%, rojo ≥30%
- Se muestra solo si hay datos disponibles
- Sin cambios en pipeline

---

## Feature 12 — Ranking de rutas/líneas con más retrasos

> Dificultad: Media — ✓ COMPLETADO (versión simplificada de F4)

### Lo implementado

- Pipeline: `by_route_arrivals.json` — todas las rutas agrupadas por `train_name`, ordenadas por `delayed_pct` desc
- `scripts/output/writer.py` — `write_by_route_arrivals()` llamada desde `main.py`
- Frontend: sección `#route-section` en `index.astro` con tabla top-10 y botón "Ver todas"
- `RouteDetailModal.astro` — wrapper de `DrilldownModal.astro` con 6 columnas (tren, origen, destino, estado, retraso, vía)
- `src/lib/routeDetailModal.ts` — lazy fetch de `by_route_arrivals.json`, openRouteDetail, closeRouteDetail
- `src/lib/chart.ts` — `renderRouteRanking()` con ECharts barras horizontales
- Reutiliza toda la infraestructura de `by_type_arrivals` y `DrilldownModal`

---

## Feature 13 — SEO / OpenGraph

> Dificultad: Fácil — ✓ COMPLETADO

- `Layout.astro` acepta props `ogImage`, `ogUrl`, `ogType`
- Meta tags `og:title`, `og:description`, `og:image`, `og:url`, `og:locale`, `og:site_name`
- Twitter Card: `summary_large_image`
- `<link rel="canonical">` con URL configurable
- Description por defecto descriptiva con keywords

---

## Feature 14 — Tendencias históricas

> Dificultad: Media — ✓ COMPLETADO

- Sección `#tendencias-section` en `index.astro`, visible cuando hay ≥7 registros históricos
- `renderWeekdayStats(records)` — tarjetas laborables vs fin de semana (% retraso + media)
- `renderTrainTypeHistory(records)` — gráfico multi-línea ECharts con evolución por tipo de tren (últimos 60 días)
- Sin cambios en pipeline — datos tomados de `history.json`

---

## Feature 15 — Alertas por umbral histórico

> Dificultad: Media — ✓ COMPLETADO

### Lo implementado

**Pipeline (`scripts/processing/insights.py`):**

- Nueva función `_insight_J`: detecta anomalías por tipo de tren comparando `delayed_pct` actual contra la media histórica extraída del campo `by_type` de `history.json`
- Umbral: ratio ≥ 1.5×, delayed_pct actual ≥ 20%, ≥ 8 snapshots históricos con datos para ese tipo, media histórica ≥ 5%
- Requiere ≥ 20 registros globales en history para activarse (evita falsos positivos con poco historial)
- Los insights con `severity: "high"` se ordenan siempre los primeros antes de escribir el JSON

**Frontend:**

- `insightModal.ts`: nueva etiqueta "Anomalía" con icono de rayo (`⚡` SVG) para `severity: "high"`
- `index.astro`: clase `.insight-high` con borde rojo 2px, fondo rojizo y halo de sombra — visualmente diferenciado del resto

### Decisión de implementación

Se usa `history.json` (campo `by_type: {tt: [total, delayed, avg_min]}`) en lugar de los Parquet, porque `history.json` ya contiene datos compactos por tipo de tren en cada snapshot y no requiere dependencia de pandas. Más robusto y sin overhead.

### Pendiente (posibles extensiones)

- Alertas por CCAA (requeriría añadir `by_ccaa` compacto a `history.json` — hoy no se guarda)
- Alertas por línea/ruta individual (requeriría Parquet de `arrivals`)

---

## Dependencias entre features

```text
[1]  Umbrales          → base para todos                  ✓ completado
[2]  Tipo de tren      → necesario para [4] y [5]         ✓ completado
[3]  Zonas             → necesario para [4] y [5]         ✓ completado
[4]  Rutas completas   → necesario para [5]               ✓ completado
[5]  Comparativa       → depende de [2] + [3] + [4] + [6] ✓ completado
[6]  Parquet histórico → necesario para [4], [5] y [15]   ✓ completado
[7]  Cron 5min         → independiente                    ✓ completado
[8]  Desacoplar Vercel → independiente                    ✓ completado
[9]  Equipo sobre.astro → independiente                   ✓ completado
[10] Imágenes trenes   → independiente                    ✓ completado
[11] Histórico estación → independiente (datos ya existen) ✓ completado
[12] Ranking rutas     → versión light de [4]             ✓ completado
[13] SEO / OpenGraph   → independiente                    ✓ completado
[14] Tendencias        → independiente (datos ya existen) ✓ completado
[15] Alertas umbral    → depende de [3] + [6]             ✓ completado
```

## Orden de implementación sugerido

```text
Sprint 3 — Quick wins ✓ COMPLETADO
  ├── [13] SEO / OpenGraph ✓
  ├── [11] Histórico estación ✓
  ├── [14] Tendencias históricas ✓
  └── [12] Ranking rutas simplificado ✓

Sprint 4 — Rutas completas ✓ COMPLETADO
  ├── [4a] Métricas crónicas en routes.py desde data/arrivals/*.parquet ✓
  └── [4b] src/pages/rutas/[service]/[route_id].astro — diagrama de paradas + mapa ✓

Sprint 5 — Narrativa avanzada (3–5 días)
  ├── [15] Alertas por umbral ✓ COMPLETADO (usa by_type en history.json)
  └── [5]  Comparativa zonas ✓ COMPLETADO (zones_analysis.py + zonas.astro + nav + CTA)
```
