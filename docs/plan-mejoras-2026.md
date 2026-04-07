# Plan de Mejoras — Andén / renfe-enhora

**Fecha inicio:** 2026-04-01
**Última actualización:** 2026-04-07
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
| 4 | Peores conexiones: rutas completas con todas las paradas | Difícil | Pendiente | Pipeline + Frontend |
| 5 | Comparativa zonas: abandonadas vs bien servidas (narrativa automática) | Difícil | Pendiente | Pipeline + Frontend |
| 6 | Almacenamiento de datos en crudo para análisis futuros | Media | ✓ Completado | Pipeline |
| 7 | Cron cada 5 minutos | Fácil | ✓ Completado | Infra |
| 8 | Desacoplar pipeline de Vercel (run_pipeline.sh / push_to_git.sh) | Fácil | ✓ Completado | Infra |
| 9 | Sección equipo en sobre.astro | Fácil | ✓ Completado | Frontend |
| 10 | Imágenes reales de trenes por tipo (WebP desde Wikimedia Commons) | Fácil | ✓ Completado | Frontend |
| 11 | Histórico por estación: gráfico de tendencia en página de detalle | Media | Pendiente | Frontend |
| 12 | Ranking de rutas/líneas con más retrasos | Media | Pendiente | Pipeline + Frontend |
| 13 | SEO / OpenGraph: meta tags dinámicos por servicio | Fácil | Pendiente | Frontend |
| 14 | Página de tendencias históricas (semana vs fin de semana, por tipo de tren) | Media | Pendiente | Frontend |
| 15 | Alertas por umbral: insight cuando una zona/línea supera su media histórica | Media | Pendiente | Pipeline |

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
- [ ] Añadir `by_ccaa` y `by_nucleo` al histórico (`history.json`) para poder trazar tendencias por zona

---

## Feature 4 — Peores conexiones: rutas completas

> Dificultad: Difícil — **PENDIENTE** (depende de: F3 ✓)

### Objetivo

Identificar las líneas con peor rendimiento crónico, extraer su recorrido completo con todas las paradas en orden, y mostrar el impacto parada a parada.

### Definición de "ruta"

En GTFS: `route_id` agrupa todos los `trip_id` de una misma línea (ej: C-1 Madrid, AVE Madrid–Sevilla). La secuencia canónica de paradas = el trip más largo de esa ruta.

### Datos GTFS necesarios (ya cacheados)

`routes.txt` + `trips.txt` + `stop_times.txt` + `stops.txt`

### Cambios en pipeline

1. `scripts/processing/routes.py` (nuevo módulo):
   - Carga `routes.txt`, `trips.txt`, `stop_times.txt` del GTFS cacheado
   - Cruza con delays RT del pipeline actual
   - Calcula: `avg_delay_min`, `delayed_pct`, `cancellation_rate`, `worst_stop_id`
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

> Dificultad: Difícil — **PENDIENTE** (depende de: F3 ✓, F4 pendiente)

### Objetivo

Mostrar de forma visual y objetiva qué zonas están sistemáticamente mal atendidas vs bien atendidas, con narrativa generada automáticamente desde los datos.

### Criterios de clasificación

| Etiqueta | Criterios |
| --- | --- |
| `zona_critica` | avg_delay > 2× media nacional AND trend = "worsening" |
| `zona_deterioro` | avg_delay > media nacional AND trend = "worsening" |
| `zona_estable` | avg_delay ≈ media nacional (±20%) |
| `zona_referencia` | avg_delay < 0.7× media nacional AND trend = "stable" o "improving" |

El campo `trend` usa regresión lineal sobre los últimos N registros históricos por zona.

### Narrativa automática (ejemplos)

- *"La Región de Murcia acumula un retraso medio de 11.4 min, 3.2× la media nacional, y la tendencia es creciente."*
- *"El Núcleo de Madrid es el mejor servido: retraso medio de 2.1 min, 88% en hora."*

### Cambios en pipeline

- `scripts/processing/insights.py` — nuevos tipos de insight (J–N) para zonas
- `zones.json` — añadir campos `label` y `narrative` por zona
- `history.json` — añadir `by_nucleo` y `by_ccaa` a cada registro histórico

### Cambios en frontend

1. Página `src/pages/zonas.astro`: mapa de calor, tabla de ranking, sección "más afectadas" vs "mejor servidas", gráfico de tendencia histórica por zona (ECharts multi-line)
2. `pages/index.astro` — bloque resumen: *"X zonas en estado crítico"* con enlace

---

## Feature 6 — Almacenamiento de datos en crudo

> Dificultad: Media — ✓ COMPLETADO

- `public/data/{service}/raw/YYYY-MM.json` — NDJSON mensual, append-only
- Solo arrivals con `delay_min > 0` o `status = cancelado`
- Excluido de git (`.gitignore`), solo en VPS
- Habilita: análisis de patrones por hora/día, detección de incidentes, exportación CSV

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

> Dificultad: Media — **PENDIENTE**

### Objetivo

La página de detalle de estación (`/cercanias/[id]`, `/ave-larga-distancia/[id]`) actualmente muestra solo el tiempo real del momento actual. Los datos históricos diarios ya se generan en `station-history/YYYY-MM-DD.json` — solo falta exponerlos en el frontend.

### Propuesta

- Gráfico de línea (ECharts) en la página de detalle mostrando `% retrasos` y `max_delay` de los últimos 7 días
- Datos disponibles: `station-history/YYYY-MM-DD.json` → `snapshots[].st[{id, t, d, mx}]`
- Sin cambios en pipeline — los datos ya están

---

## Feature 12 — Ranking de rutas/líneas con más retrasos

> Dificultad: Media — **PENDIENTE** (versión simplificada de F4)

### Diferencia con F4

F4 extrae el recorrido completo parada a parada. Esta versión simplificada solo necesita agrupar por `route_id` los arrivals actuales y calcular `avg_delay_min` y `delayed_pct` por ruta — sin recorrido completo ni histórico.

### Propuesta

- Pipeline: `by_route_arrivals.json` — top 50 rutas con más delay en la captura actual
- Frontend: tabla en la sección analytics con top 10, click → `DrilldownModal` con retrasos de esa ruta
- Coste: bajo, reutiliza infraestructura existente de `by_type_arrivals` y `DrilldownModal`

---

## Feature 13 — SEO / OpenGraph

> Dificultad: Fácil — **PENDIENTE**

- Meta tags `og:title`, `og:description`, `og:image` en `Layout.astro`
- Imagen de preview estática por servicio (screenshot del dashboard)
- `<meta name="description">` descriptivo en `index.astro` y `sobre.astro`
- URL canónica

---

## Feature 14 — Página de tendencias históricas

> Dificultad: Media — **PENDIENTE**

### Propuesta

Página `src/pages/tendencias.astro` o sección desplegable en el dashboard con:

- Comparativa laborable vs fin de semana (ya calculable desde `history.json` con el campo `date`)
- Evolución por tipo de tren a lo largo del tiempo (`by_type` está en `history.json`)
- Heatmap hora × día de la semana (ya implementado en la vista de heatmap del gráfico principal, ampliar)
- Sin cambios en pipeline — todos los datos necesarios ya están en `history.json`

---

## Feature 15 — Alertas por umbral histórico

> Dificultad: Media — **PENDIENTE**

### Propuesta

En `scripts/processing/insights.py`, añadir un nuevo tipo de insight (tipo "alerta") cuando:

- Una CCAA o núcleo supera 1.5× su propia media histórica (últimos 30 días)
- Una línea (`route_id`) supera 2× su media histórica

Se mostraría con `severity: "high"` en el panel de insights, destacado visualmente.

---

## Dependencias entre features

```text
[1]  Umbrales          → base para todos                  ✓ completado
[2]  Tipo de tren      → necesario para [4] y [5]         ✓ completado
[3]  Zonas             → necesario para [4] y [5]         ✓ completado
[4]  Rutas completas   → necesario para [5]               pendiente
[5]  Comparativa       → depende de [2] + [3] + [4]       pendiente
[6]  Datos en crudo    → independiente                    ✓ completado
[7]  Cron 5min         → independiente                    ✓ completado
[8]  Desacoplar Vercel → independiente                    ✓ completado
[9]  Equipo sobre.astro → independiente                   ✓ completado
[10] Imágenes trenes   → independiente                    ✓ completado
[11] Histórico estación → independiente (datos ya existen) pendiente
[12] Ranking rutas     → versión light de [4]             pendiente
[13] SEO / OpenGraph   → independiente                    pendiente
[14] Tendencias        → independiente (datos ya existen) pendiente
[15] Alertas umbral    → depende de [3] (zonas)           pendiente
```

## Orden de implementación sugerido

```text
Sprint 3 — Quick wins (1–2 días)
  ├── [13] SEO / OpenGraph — impacto de visibilidad inmediato
  ├── [11] Histórico estación — datos listos, solo frontend
  └── [14] Tendencias históricas — datos listos, solo frontend

Sprint 4 — Análisis de rutas (3–5 días)
  ├── [12] Ranking rutas simplificado — reutiliza infraestructura existente
  └── [4]  Rutas completas — routes.py + routes.json + página /rutas

Sprint 5 — Narrativa avanzada (3–5 días)
  ├── [15] Alertas por umbral
  └── [5]  Comparativa zonas — insights.py + zonas.astro
```
