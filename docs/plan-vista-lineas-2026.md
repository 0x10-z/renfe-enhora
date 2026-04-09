# Plan: Vista por línea (cercanías) y por trayecto (AVE/LD)

## Contexto y motivación

retrasosrenfe.com muestra un resumen por línea que es más accionable para el viajero:
- C5 Madrid: 73 trenes con incidencias · 20 min media · 59 min máximo
- El usuario entiende inmediatamente si su línea o trayecto está afectado

Nosotros actualmente mostramos el ranking compacto top-3 de rutas con más % de retraso,
pero la unidad son **paradas** (cada tren × cada estación = 1 fila), no **trenes**.
Esto hace que el número parezca pequeño y sea difícil de interpretar.

**Terminología usada en este plan:**

- **Línea** — identidad fija con nombre propio (C1, C5, R4…). Aplica a cercanías.
- **Trayecto** — combinación de tipo de servicio + destino (AVE → Barcelona, Alvia → Vigo…). Aplica a AVE/LD donde los trenes tienen nombres numéricos sin identidad propia.

---

## Análisis: ¿qué hacen ellos vs nosotros?

| Aspecto | retrasosrenfe.com | enhora.info (actual) |
|---------|-------------------|----------------------|
| Unidad | Trenes (viajes) con retraso | Paradas con retraso |
| Agrupación | Por línea + ciudad separados | Por nombre de línea (C1 agrupa Madrid+Sevilla+Málaga) |
| Ventana temporal | Todos los trenes activos del momento | Próximos 60 minutos |
| Histórico | No visible | Sí (heatmap, tendencias, insights) |
| Granularidad estación | No | Sí (detalle por parada) |

**Problema nuestro detectado:** el C1 de Madrid, Sevilla, Málaga y Bilbao aparece como
una sola entrada "C1" con stops mezclados. retrasosrenfe los separa por ciudad/núcleo.
Esto requiere separar por `nucleo` en el pipeline.

---

## Mi opinión: ¿uno o dos modos?

**Recomendación: mantener ambos, con el modo línea como vista principal.**

El motivo es que sirven para preguntas distintas:

- **"¿Está mi línea mal ahora?"** → modo por línea (lo que falta y es más útil)
- **"¿Qué estación concreta está peor?"** → modo actual por paradas (lo que ya tenemos)

No son competidores sino capas de detalle. El flujo natural sería:
> Vista líneas → ves que C5 está mal → haces clic → ves las paradas afectadas

Esto también da más valor frente a retrasosrenfe: ellos tienen el resumen,
nosotros tenemos el resumen + el drill-down + el histórico.

**¿Por qué no dejar solo uno?**
- Solo el modo línea: perdemos la granularidad de estación que ya tenemos y que ningún otro sitio ofrece
- Solo el modo paradas: seguimos siendo difíciles de leer para el viajero casual

---

## Cambios necesarios

### Pipeline

**P1 — Separar rutas por núcleo en `by_route_arrivals.json`**
- Actualmente: una entrada `{train_name: "C1", ...}` agrupa todos los C1 del país
- Objetivo: `{train_name: "C1", nucleo: "madrid", ...}` separado por ciudad
- Fichero: `scripts/output/writer.py` → `write_by_route_arrivals()`
- También en `scripts/processing/routes.py` para las crónicas históricas

**P2 — Añadir `unique_trips_delayed` a `by_route_arrivals.json`**
- Actualmente: `delayed` cuenta paradas retrasadas
- Añadir: `unique_trips` (viajes totales en ventana) y `unique_trips_delayed` (viajes con ≥1 parada retrasada)
- Esto da el número comparable al "Con incidencias" de retrasosrenfe

### Frontend

#### F1 — Sección "Estado de líneas / trayectos" en index.astro

- Cercanías: tabla/grid por núcleo (Madrid, Barcelona, Sevilla…) con sus líneas
  - Por línea: badge de color + nombre, trenes con incidencias, retraso medio, retraso máximo
- AVE/LD: lista de trayectos afectados (solo los que tienen retraso activo)
  - Por trayecto: tipo (AVE/AVLO/Alvia…) + destino, trenes afectados, retraso medio, retraso máximo
  - Si no hay retrasos: "Todos los trayectos circulan con normalidad"
- Badge de color según severidad (verde/amarillo/rojo) en ambos casos
- Click → abre el route detail modal existente

#### F2 — Modo toggle: "Por línea/trayecto" / "Por estación"

- Toggle en la sección de estaciones/rutas del index
- "Por línea/trayecto" muestra la tabla nueva (F1)
- "Por estación" muestra el buscador+mapa actual
- Persistir preferencia en localStorage

#### F3 — Separar C1 Madrid de C1 Sevilla en la UI (cercanías)

- Mostrar ciudad/núcleo junto al nombre de línea
- Evitar la confusión actual donde "C1" mezcla varias ciudades

---

## Prioridad sugerida

1. **P2** (unique_trips_delayed) — cambio de pipeline, pequeño, alto impacto
2. **P1** (separar por núcleo) — necesario para que la vista tenga sentido
3. **F1** (sección estado de líneas) — el cambio visual principal
4. **F2** (toggle) — mejora UX, no bloquea F1
5. **F3** (separar ciudades en UI) — depende de P1

---

---

## AVE / Larga Distancia

Aplica el mismo concepto pero con diferencias importantes:

**Similitudes:**

- El viajero quiere saber "¿está el AVE a Barcelona retrasado?" igual que el de cercanías
- Ya tenemos `train_name` (AVE 03142) + `headsign` (destino) en `by_route_arrivals.json`
- `unique_trips_delayed` tiene el mismo sentido: ¿cuántos trenes hacia ese destino van tarde?

**Diferencias clave:**

- 280+ rutas activas en AVE vs 35 en cercanías — no se puede mostrar tabla de 280 filas
- Los nombres son numéricos (AVE 03142), no líneas con identidad propia (C5)
- La agrupación natural no es por núcleo/ciudad sino por **tipo de servicio + destino**
  - Ej: "AVE → Barcelona" (3 trenes, 1 con retraso 12 min)
  - Ej: "AVLO → Sevilla" (2 trenes, 0 retrasos)

**Estrategia para AVE:**

- Mostrar solo trenes con retraso activo (no tabla completa)
- Agrupar por `headsign` (destino final) + `train_type` (AVE/AVLO/Alvia…)
- Ordenar por retraso máximo descendente
- Si no hay retrasos: mensaje "Todos los servicios circulan con normalidad"

**Pipeline adicional necesario para AVE:**

- P3 — Agrupar `by_route_arrivals` por destino (`headsign`) en lugar de por `train_name` numérico
- Añadir `unique_trips` y `unique_trips_delayed` también aquí

---

## Estado

- [x] P1 — Separar rutas cercanías por núcleo en pipeline (`by_route_arrivals.json` ahora incluye `nucleo`)
- [x] P2 — Añadir unique_trips / unique_trips_delayed (cercanías + AVE)
- [x] P3 — Nuevo fichero `by_trayecto.json` con agrupación por (train_type, headsign)
- [x] F1 — Sección "Estado de líneas / Trayectos afectados" en index.astro
- [x] F3 — Cercanías agrupadas por núcleo (Madrid, Barcelona, Sevilla…) en la UI
- [ ] F2 — Toggle por línea/trayecto / por estación (pendiente)
