# Plan de Mejoras UX — enhora.info

**Fecha:** 2026-04-08
**Autor del análisis:** Claude Sonnet 4.6 (experto UX)
**Estado:** ✓ Completado — todos los sprints terminados (16/16 mejoras implementadas)
**Nota:** Este documento integra la UX de las features pendientes en [plan-mejoras-2026.md](plan-mejoras-2026.md) — concretamente **F5** (Comparativa zonas) y **F15** (Alertas por umbral histórico). El diseño UX de esas features está planificado aquí antes de que se implementen.

---

## Principio rector

> **El dato sin contexto no comunica. La web debe hablarle a quien no sabe nada de trenes ni de datos.**

Un periodista, un jubilado, un estudiante que coge el Cercanías cada día — ninguno debería necesitar saber qué es GTFS, qué significa "delayed_pct" ni qué son "snapshots" para entender si su tren llega tarde. La información existe. El trabajo del UX es traducirla a lenguaje humano.

---

## Diagnóstico: problemas actuales por área

### 🔴 Críticos (dañan la comprensión)

| ID | Problema | Dónde |
|----|----------|-------|
| P1 | El titular "Tablero de Llegadas" es lenguaje técnico/institucional | Header principal |
| P2 | Los 5 stat cards muestran números sin responder la pregunta real: "¿van bien o mal los trenes?" | Homepage |
| P3 | Los insights se identifican con letras (A–I) que no significan nada para nadie | Sección Observaciones |
| P4 | "chronic_n_snapshots: 2" aparece literalmente en páginas de detalle de ruta | /rutas/[id] |
| P5 | Tres pestañas (Análisis / Estaciones / Mapa) fragmentan la experiencia sin jerarquía clara | Homepage |
| P6 | Los gráficos no tienen subtítulo explicando **qué muestran** ni **por qué importan** | Todos los gráficos |
| P7 | "Metodología" en la nav aleja al usuario medio (suena a paper académico) | Navegación global |

### 🟡 Importantes (dificultan la navegación)

| ID | Problema | Dónde |
|----|----------|-------|
| P8 | La búsqueda de estaciones está escondida detrás de una pestaña — no es el punto de entrada natural | Homepage |
| P9 | 6 botones de rango temporal en el gráfico histórico (7d, 30d, 90d, Todo, Por hora, Mapa de calor) — demasiadas opciones a la vez | Gráfico histórico |
| P10 | El mapa de rutas no orienta al usuario: ¿qué hago aquí? ¿qué busco? | /rutas |
| P11 | Los modales se apilan en capas (hasta 7 tipos distintos) — difícil orientarse | Toda la web |
| P12 | "Sin tráfico en la ventana actual" como estado vacío es frío y técnico | Páginas de ruta/estación |
| P13 | La leyenda de colores del mapa de CCAA usa porcentajes (<3%, 3-10%...) sin contexto de si eso es mucho o poco | Sección CCAA |

### 🟢 Mejorables (pulirían la experiencia)

| ID | Problema | Dónde |
|----|----------|-------|
| P14 | Mobile: los grids de 5 y 2 columnas colapsan pero sin una jerarquía clara para móvil | Responsive |
| P15 | El footer es invisible (0.72rem, texto muted) — la atribución y el "¿quiénes somos?" están enterrados | Footer |
| P16 | No hay estado de primera visita — el usuario que llega sin contexto no sabe dónde empezar | Homepage |
| P17 | Los colores de estado (verde/amarillo/rojo) no son accesibles para daltónicos | Global |
| P18 | "Paradas analizadas" como métrica — una parada puede tener 0 trenes; confunde con "estaciones activas" | Stat card |

---

## Resumen de mejoras propuestas

| # | Mejora | Impacto | Dificultad | Estado |
|---|--------|---------|------------|--------|
| U1 | Hero status: frase humana como titular del estado actual | Alto | Fácil | ✓ Sprint B |
| U2 | Renombrar secciones y navegación con lenguaje natural | Alto | Fácil | ✓ Sprint A |
| U3 | Subtítulos explicativos en cada gráfico (dinámicos por vista) | Alto | Fácil | ✓ Sprint A+C |
| U4 | Insight cards: eliminar etiquetas A-I, rediseñar como alertas narrativas | Alto | Fácil | ✓ Sprint B |
| U5 | Búsqueda de estación como acción principal visible desde el hero | Alto | Media | ✗ Descartado |
| U6 | Simplificar gráfico histórico: 4 opciones con nombres descriptivos | Medio | Fácil | ✓ Sprint C |
| U7 | Limpiar páginas de detalle de ruta: lenguaje humano, sin jerga técnica | Alto | Fácil | ✓ Sprint B |
| U8 | Página /rutas: añadir contexto de entrada (¿qué es esto y para qué sirve?) | Medio | Fácil | ✓ Sprint A |
| U9 | Estados vacíos empáticos y útiles | Medio | Fácil | ✓ Sprint A |
| U10 | Leyenda CCAA con contexto cualitativo (bien / regular / mal) | Medio | Fácil | ✓ Sprint B |
| U11 | Footer visible con sección "Sobre el proyecto" | Bajo | Fácil | ✓ Sprint C |
| U12 | Primer viaje: banner de bienvenida descartable (localStorage) | Medio | Media | ✓ Sprint C |
| U13 | Accesibilidad: iconos junto a colores en badges de estado | Medio | Media | ✓ Sprint E |
| U14 | Mobile: scroll horizontal en stat cards, límite de insights con "Ver más" | Alto | Difícil | ✓ Sprint E |
| U15 | **[F15]** Alertas de umbral: integrarlas como el tipo de insight más urgente y visible | Alto | Fácil | ✓ Sprint D |
| U16 | **[F5]** Página "Zonas": narrativa automática de abandono/buen servicio con lenguaje periodístico | Alto | Media | ✓ Sprint D |

---

## U1 — Hero status: una frase que dice todo

> Impacto: Alto — Dificultad: Fácil

### Problema

El usuario entra y ve cinco números: "561 paradas analizadas", "134 con retraso", "17.6 min media"… Tiene que hacer la operación mental él mismo. Nadie quiere hacer eso.

### Propuesta

Sustituir (o complementar) los 5 stat cards por **una frase de estado al inicio**, generada automáticamente desde los mismos datos:

```
╔══════════════════════════════════════════════════════════╗
║  🟡  Hoy los trenes AVE llegan tarde en el 24% de los casos  ║
║      Media de retraso: 17 minutos · Peor ruta: Alvia Madrid–Bilbao  ║
╚══════════════════════════════════════════════════════════╝
```

Estados posibles:
- 🟢 **< 10% retraso** → "Los trenes van bien ahora mismo"
- 🟡 **10–25%** → "Hay retrasos moderados en [servicio]"
- 🔴 **> 25%** → "Atención: muchos trenes llegan tarde hoy"

### Implementación

- Calcular `hero_status` en el frontend desde `stats.json` (ya disponible)
- Tres plantillas de texto, un componente `HeroStatus.astro`
- Los 5 stat cards se mantienen debajo como detalle secundario

---

## U2 — Renombrar con lenguaje natural

> Impacto: Alto — Dificultad: Fácil

### Cambios de texto propuestos

| Actual | Propuesto | Razón |
|--------|-----------|-------|
| "Tablero de Llegadas" | "¿Cómo van los trenes hoy?" | Pregunta directa que responde la página |
| "Renfe España · Próximos 60 minutos" | "Datos actualizados cada hora · próxima hora de servicio" | Aclara la ventana temporal |
| "Metodología" (nav) | "¿Cómo funciona?" | Invita en lugar de intimidar |
| "Observaciones" (sección insights) | "Lo que dicen los datos" | Natural, no académico |
| "Paradas analizadas" (stat card) | "Estaciones con trenes ahora" | Más concreto |
| "Trenes en ruta" | "Trenes en circulación" | Más coloquial |
| "Sin tráfico en la ventana actual" | "Sin trenes previstos en la próxima hora" | Humano |
| "Sin datos históricos aún" | "Acumulando datos históricos…" | Da sensación de progreso |
| "chronic_n_snapshots" (visible en ruta) | "Basado en [N] registros históricos" | Traducir siempre la jerga |
| "Por comunidad autónoma" | "¿Dónde hay más retrasos?" | Pregunta que el usuario se hace |
| "Por tipo de tren" | "¿Qué tren va peor?" | Ídem |
| "Por línea / servicio" | "Las rutas con más retrasos" | Directo al grano |

---

## U3 — Subtítulos explicativos en cada gráfico

> Impacto: Alto — Dificultad: Fácil

### Problema

Cada gráfico tiene un título pero ninguno explica:
1. **Qué muestra** el eje Y o la codificación de color
2. **Qué debería buscar** el usuario (¿una barra alta es mala o buena?)
3. **Qué hace** la interacción disponible

### Propuesta: anatomía estándar de cada gráfico

```
┌─ Título del gráfico ────────────────────────────── [?] ─┐
│  Subtítulo de una línea: qué muestra y qué significa     │
│                                                          │
│  [El gráfico]                                            │
│                                                          │
│  Nota pie: "Barras más altas = más retrasos ese día"     │
└──────────────────────────────────────────────────────────┘
```

### Subtítulos propuestos por gráfico

| Gráfico | Subtítulo propuesto |
|---------|---------------------|
| Histórico de retrasos | "Porcentaje de trenes que llegaron tarde en cada captura horaria. Cuanto más alta la barra, peor fue ese momento." |
| Por tipo de tren | "Cada barra es un tipo de tren. Las barras más largas indican que ese tipo llegó tarde con más frecuencia hoy." |
| Mapa CCAA | "Cada región coloreada según cuántos trenes llegaron tarde. Rojo = peor servicio, verde = mejor servicio." |
| Tendencias históricas | "Comparativa entre días laborables y fin de semana. Te muestra si los retrasos son peores según el día." |
| Evolución por tipo | "Cómo han evolucionado los retrasos de cada tipo de tren en los últimos meses." |
| Histórico estación | "Los últimos 7 días en esta estación. Una barra alta un día concreto indica que fue una jornada mala." |

---

## U4 — Insight cards: narrativa sin etiquetas técnicas

> Impacto: Alto — Dificultad: Fácil

### Problema

Las tarjetas de insights se identifican con letras (A, B, C... hasta I) que no aportan nada al usuario. Además, los textos son correctos pero no tienen jerarquía visual que distinga urgencia.

### Propuesta

Eliminar las etiquetas de letra. En su lugar:

```
┌──────────────────────────────────────────────────┐
│ 🔴  ATENCIÓN                                     │
│ El AVE Madrid–Sevilla acumula hoy un retraso      │
│ medio de 23 minutos, el peor en 30 días.          │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ 🟡  TENDENCIA                                    │
│ Los viernes suelen ser el peor día para las       │
│ Cercanías de Madrid: 18% más de retrasos          │
│ que el resto de la semana.                        │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ 🟢  DATO CURIOSO                                 │
│ El AVE Madrid–Barcelona es el tren más puntual    │
│ del sistema: 96% de llegadas en hora este mes.    │
└──────────────────────────────────────────────────┘
```

Tipos de insight con icono y color:
- 🔴 `alerta` — algo está claramente mal hoy
- 🟡 `tendencia` — patrón temporal detectado
- 🟢 `positivo` — algo que funciona bien
- 🔵 `contexto` — dato histórico de fondo
- ⚪ `info` — dato neutro sin urgencia

Cambio en `insights.json`: añadir campo `type` con uno de estos valores. El frontend renderiza el icono y el color según el tipo.

---

## U5 — Búsqueda de estación como acción principal

> Impacto: Alto — Dificultad: Media

### Problema

La búsqueda de estaciones está en la segunda pestaña ("Estaciones"), invisible por defecto. Sin embargo, **la pregunta más frecuente del usuario es "¿cómo va mi estación?"**.

### Propuesta

Añadir la búsqueda de estación **directamente en el hero**, antes de los gráficos:

```
╔══════════════════════════════════════════════════════╗
║  🟡 Hoy los trenes AVE llevan 17 min de retraso      ║
║                                                      ║
║  [🔍 Busca tu estación...              ] [Buscar]    ║
║       Ej: Madrid Atocha, Vitoria, Valencia           ║
╚══════════════════════════════════════════════════════╝
```

La búsqueda lleva directamente a la página de estación (`/cercanias/{id}` o `/ave-larga-distancia/{id}`).

Detrás, los gráficos y el análisis para quien quiera más contexto.

### Jerarquía de contenido resultante

1. **Hero**: estado actual + búsqueda de estación
2. **Gráficos**: análisis temporal, por tipo, por zona
3. **Estaciones**: grid navegable (igual que ahora, en pestaña o scroll)

---

## U6 — Simplificar el gráfico histórico

> Impacto: Medio — Dificultad: Fácil

### Problema

6 opciones de visualización (7d, 30d, 90d, Todo, Por hora, Mapa de calor) para un solo gráfico es demasiado. La mayoría de usuarios no sabrá qué hace "Por hora" ni "Mapa de calor" sin probarlos.

### Propuesta

Reducir a **3 opciones** con nombres descriptivos:

| Actual | Propuesto | Vista |
|--------|-----------|-------|
| 7d | Última semana | Barras diarias |
| 30d | Último mes | Barras diarias |
| Por hora | Horario típico | Barras por hora del día |

- "90d", "Todo" → mover a sección "Análisis avanzado" o eliminar
- "Mapa de calor" → promoverlo como visualización propia con su propia sección y explicación

El mapa de calor es el más potente visualmente pero también el más confuso sin contexto. Merece su propia sección con un título como: **"¿A qué horas hay más retrasos?"**

---

## U7 — Página de detalle de ruta: lenguaje humano

> Impacto: Alto — Dificultad: Fácil

### Problema actual (página `/rutas/[service]/[route_id]`)

```
HISTÓRICO
0%          4.0 min          2
con retraso  media histórica  snapshots
```

"2 snapshots" no dice nada. El usuario no sabe si 2 snapshots son muchos o pocos ni qué es un snapshot.

### Propuesta

```
HISTÓRICO  (últimos 2 registros)
0%               4.0 min
sin retrasos     de media por llegada
```

- Sustituir "snapshots" por "registros" y moverlo al título de la card
- Añadir aviso cuando hay pocos datos: "⚠ Pocos datos aún — el histórico mejorará con el tiempo"
- Cuando hay suficientes datos (>20 registros): mostrar una comparativa "vs. media nacional"

### Escala de fiabilidad del histórico

| Registros | Mensaje |
|-----------|---------|
| < 5 | "⚠ Datos insuficientes para el histórico" |
| 5–20 | "Basado en [N] registros — datos en acumulación" |
| 20–100 | "Basado en [N] registros · [X] días de datos" |
| > 100 | "Basado en [N] registros · histórico consolidado" |

---

## U8 — Página /rutas: contexto de entrada

> Impacto: Medio — Dificultad: Fácil

### Problema

El usuario llega a `/rutas` y ve una lista + un mapa. No sabe qué se supone que debe hacer ni por qué importa.

### Propuesta: añadir una frase de contexto bajo el título

**Actual:**
```
Rutas
Selecciona una ruta para ver su trayecto y todas sus paradas
```

**Propuesto:**
```
Rutas con más retrasos
Las líneas ordenadas de peor a mejor puntualidad, basándose en
las últimas horas de servicio. Haz clic en una ruta para ver
el trayecto completo y el estado de cada parada.
```

Además, añadir una fila de **3 stats destacados** al inicio:
```
[Ruta más retrasada hoy]  [% medio del servicio]  [Rutas sin incidencias]
  ALVIA Madrid–Bilbao        24% con retraso           48 rutas en hora
```

---

## U9 — Estados vacíos empáticos

> Impacto: Medio — Dificultad: Fácil

### Propuesta por pantalla

| Pantalla | Estado vacío actual | Estado vacío propuesto |
|----------|---------------------|------------------------|
| Estación sin trenes | "Sin llegadas en los próximos 60 minutos" | "No hay trenes previstos en la próxima hora en esta estación. Puede que esté fuera del horario de servicio." |
| Ruta sin tráfico | "Sin tráfico en la ventana actual" | "Esta ruta no tiene trenes en circulación ahora mismo. Puede que sea de noche o fin de servicio." |
| Histórico vacío | "Sin datos históricos aún" | "Aún no tenemos histórico para esta ruta. Los datos se acumulan con cada actualización." |
| Sin resultados de búsqueda | (skeleton infinito) | "No hemos encontrado ninguna estación con ese nombre. Prueba con el municipio o con el nombre completo." |
| Error de carga | "No hay datos disponibles" | "No hemos podido cargar los datos. Intenta recargar la página en unos segundos." + botón Reintentar |

---

## U10 — Leyenda del mapa CCAA con contexto cualitativo

> Impacto: Medio — Dificultad: Fácil

### Problema

La leyenda actual:
```
<3%  ·  3-10%  ·  10-20%  ·  20-30%  ·  >30%  ·  Sin datos
```

¿Es malo un 10%? ¿Es normal un 20%? El usuario no tiene referencia.

### Propuesta: añadir etiquetas cualitativas

```
🟢 Servicio bueno    < 10% de trenes con retraso
🟡 Retrasos leves   10 – 20%
🟠 Retrasos notables  20 – 30%
🔴 Servicio deficiente  > 30%
⬜ Sin datos disponibles
```

Y debajo del mapa, una frase dinámica:
> "La media nacional hoy es del 18%. Las regiones en naranja y rojo están por encima de esa media."

---

## U11 — Footer visible y útil

> Impacto: Bajo — Dificultad: Fácil

### Problema

El footer actual es casi invisible: texto de 0.72rem en color muted. Para una web independiente y sin ánimo de lucro, la transparencia sobre quién hay detrás es importante para generar confianza.

### Propuesta

Añadir una sección de cierre con 3 columnas antes del footer actual:

```
┌─────────────────┬─────────────────┬─────────────────┐
│  Sobre enhora   │  Datos          │  Proyecto       │
│  ─────────────  │  ─────────────  │  ─────────────  │
│  ¿Qué es esto?  │  Fuente: Renfe  │  Código abierto │
│  El equipo      │  GTFS oficial   │  GitHub         │
│  ¿Cómo funciona?│  Actualización  │  Contacto       │
│                 │  cada hora      │                 │
└─────────────────┴─────────────────┴─────────────────┘
```

---

## U12 — Banner de primera visita (descartable)

> Impacto: Medio — Dificultad: Media

### Propuesta

La primera vez que un usuario visita la web (localStorage `enhora_visited` no existe), mostrar un banner no intrusivo en la parte inferior:

```
╔═══════════════════════════════════════════════════════════╗
║  👋 Bienvenido a enhora.info                               ║
║  Este tablero muestra en tiempo real cuántos trenes de     ║
║  Renfe llegan tarde. Todos los datos son oficiales y       ║
║  se actualizan cada hora.   [Entendido] [¿Cómo funciona?] ║
╚═══════════════════════════════════════════════════════════╝
```

- Se cierra al hacer clic en "Entendido" y no vuelve a aparecer
- "¿Cómo funciona?" lleva a `/sobre`
- No bloquea el contenido (posición fixed bottom, no modal)

---

## U13 — Accesibilidad: iconos junto a colores

> Impacto: Medio — Dificultad: Media

### Problema

Todo el sistema de estados depende del color (verde/amarillo/rojo). Para personas con daltonismo deuteranope (el más común: ~8% de los hombres), el verde y el rojo son indistinguibles.

### Propuesta

Añadir un icono a cada estado de color en los lugares clave:

| Estado | Color actual | Propuesto |
|--------|-------------|-----------|
| En hora | Verde | ✓ En hora |
| Retraso leve | Amarillo | ⚠ 5–10 min |
| Retraso alto | Rojo | ✕ +10 min |
| Cancelado | Rojo oscuro | ✕ Cancelado |

Los iconos ya existen en algunos lugares (StationBoard tiene badges de texto). Se trata de aplicarlos consistentemente en mapas, gráficos y leyendas.

---

## U14 — Mobile: jerarquía de contenido para pantallas pequeñas

> Impacto: Alto — Dificultad: Difícil

### Problema

La homepage tiene un grid de 5 stat cards, una sección de 3 pestañas, y dentro de cada pestaña más grids. En móvil, todo colapsa a una columna, pero el orden de los elementos no se reordena — el usuario tiene que hacer mucho scroll para llegar a la búsqueda de estación.

### Propuesta de orden en móvil

```
1. Hero status (frase del estado actual)
2. [🔍 Busca tu estación]  ← MÁS IMPORTANTE EN MÓVIL
3. Stat cards (horizontal scroll, 2 visibles a la vez)
4. Insights (máximo 3, "Ver más" para el resto)
5. Gráfico histórico (solo "Última semana" por defecto)
6. Por tipo de tren (gráfico reducido)
7. Mapa (oculto por defecto en móvil, botón "Ver mapa")
8. Por comunidad (oculto por defecto, botón "Ver por región")
```

En escritorio: la experiencia actual es adecuada.

---

---

## U15 — Alertas de umbral: el insight más urgente [vinculado a F15]

> Impacto: Alto — Dificultad: Fácil (depende de que F15 esté implementado en el pipeline)

### Contexto (F15)

F15 añadirá al pipeline la detección automática de anomalías: cuando una CCAA, tipo de tren o línea supera 1.5–2× su propia media histórica, genera un insight con `severity: "high"`.

### Problema de UX si no se diseña bien

Si las alertas llegan como un insight más entre los 8–9 que ya hay, se pierden. Una alerta de que el AVE lleva hoy el triple de retraso de su media histórica merece **visibilidad prioritaria**, no estar en la posición 5 de una lista.

### Propuesta UX para las alertas (U15)

**1. Posición:** Las alertas `severity: "high"` van siempre **primeras** en la sección de insights, separadas visualmente del resto.

**2. Diseño diferenciado:**

```
╔══════════════════════════════════════════════════════╗
║  🚨  ANOMALÍA DETECTADA                              ║
║                                                      ║
║  Los trenes AVE llevan HOY un 3.2× más de retraso   ║
║  que su media de los últimos 30 días.                ║
║                                                      ║
║  Media habitual: 4 min · Hoy: 13 min                 ║
║  [Ver rutas AVE afectadas →]                         ║
╚══════════════════════════════════════════════════════╝
```

- Fondo ligeramente rojo/anaranjado para distinguirlo del fondo blanco
- Botón de acción que lleva a la sección de tipo de tren o CCAA afectada
- Si no hay alertas: **no mostrar nada** (no "Todo en orden" — el silencio es suficiente)

**3. Cuándo NO mostrar alertas:**

- Si hay < 20 registros históricos de esa entidad (dato insuficiente para comparar)
- Si el pipeline no ha corrido en las últimas 2 horas (dato obsoleto)

**4. Textos de alerta por tipo:**

| Tipo | Plantilla |
| --- | --- |
| CCAA | "La [CCAA] lleva hoy [X]× más retraso del habitual ([Y] min vs su media de [Z] min)" |
| Tipo de tren | "Los trenes [tipo] acumulan hoy [X]× su retraso habitual" |
| Línea | "La línea [nombre] tiene hoy el peor día en [N] semanas" |

---

## U16 — Página "Zonas": la narrativa del abandono [vinculado a F5]

> Impacto: Alto — Dificultad: Media (depende de que F5 esté implementado en el pipeline)

### Contexto (F5)

F5 añadirá al pipeline la clasificación de zonas (`zona_critica`, `zona_deterioro`, `zona_estable`, `zona_referencia`) basada en regresión lineal del histórico de retrasos por CCAA. La página propuesta en F5 es `zonas.astro` con mapa de calor, tabla de ranking y tendencias.

### El reto UX de esta feature

Es la feature con más potencial periodístico de todo el proyecto, y también la más fácil de hacer aburrida. Un ranking de comunidades con porcentajes puede quedarse en estadística fría. La clave es **humanizarlo**.

### Propuesta UX para la página Zonas (U16)

**Título de la página:**

```
¿Dónde están los trenes peor atendidos de España?
```

No "Comparativa zonas". No "Análisis por CCAA". Una pregunta que alguien se haría de verdad.

**Estructura de la página:**

```
┌─ Titular + frase narrativa ──────────────────────────────┐
│  "La Región de Murcia acumula el triple de retrasos      │
│  que la media nacional. La tendencia empeora."           │
└──────────────────────────────────────────────────────────┘

┌─ Dos columnas: peores vs mejores ────────────────────────┐
│  🔴 Zonas con más problemas  │  🟢 Zonas más puntuales   │
│  1. Murcia — 34%             │  1. País Vasco — 4%       │
│  2. Extremadura — 28%        │  2. Navarra — 6%          │
│  3. Castilla-La Mancha — 24% │  3. Madrid — 8%           │
└──────────────────────────────────────────────────────────┘

┌─ Mapa coropleta ─────────────────────────────────────────┐
│  [España coloreada, click en región = detalle]           │
└──────────────────────────────────────────────────────────┘

┌─ Tabla completa de tendencias ───────────────────────────┐
│  CCAA | % retraso | Tendencia | vs. media nacional       │
│  Murcia | 34% | 📈 Empeorando | +16 pp por encima       │
│  ...                                                     │
└──────────────────────────────────────────────────────────┘
```

**La tendencia es clave.** No es lo mismo tener un 20% de retrasos si llevas 3 meses mejorando que si llevas 6 meses empeorando. Mostrar el trend con flechas e iconos:

| Trend | Icono | Descripción |
| --- | --- | --- |
| `worsening` | 📈 Empeorando | La tendencia es al alza en los últimos 30 días |
| `stable` | ➡️ Estable | Sin cambio significativo |
| `improving` | 📉 Mejorando | La tendencia es a la baja |

**Etiquetas de zona en lenguaje natural:**

| Código F5 | Etiqueta UX mostrada |
| --- | --- |
| `zona_critica` | "Servicio deficiente" |
| `zona_deterioro` | "Situación preocupante" |
| `zona_estable` | "Servicio normal" |
| `zona_referencia` | "Referencia de puntualidad" |

**Narrativa automática por CCAA** (ampliando F5):

Cada CCAA tendrá al menos una frase automática en su card/fila. Ejemplos:

- *"La peor comunidad en puntualidad este mes. El tren a Murcia llega tarde 1 de cada 3 veces."*
- *"La única comunidad que ha mejorado más de 5 puntos en los últimos 30 días."*
- *"Rendimiento estable. Sin grandes cambios respecto al mes anterior."*

**Entrada desde la homepage:**

En la sección de CCAA del dashboard principal, añadir un CTA:

```
[Ver análisis completo de zonas →]
```

**Entrada desde la navbar:**

Valorar añadir "Zonas" a la navegación principal cuando F5 esté listo:

```
Tablero   Rutas   Zonas   ¿Cómo funciona?
```

---

## Dependencias entre mejoras

```
[U1]  Hero status        → base para [U5] y [U12]
[U2]  Renombrar          → independiente, puede hacerse primero
[U3]  Subtítulos         → independiente, alto impacto/bajo esfuerzo
[U4]  Insights           → necesita cambio en insights.json (campo type)
[U5]  Búsqueda hero      → depende de [U1] para la sección hero
[U6]  Simplificar chart  → independiente
[U7]  Detalle ruta       → independiente, solo frontend
[U8]  Contexto /rutas    → independiente
[U9]  Empty states       → independiente
[U10] Leyenda CCAA       → independiente
[U11] Footer             → independiente
[U12] Onboarding         → depende de [U2] para textos
[U13] Accesibilidad      → independiente, se puede hacer en paralelo
[U14] Mobile             → depende de [U1] y [U5] para el nuevo orden
[U15] Alertas umbral     → depende de F15 (pipeline) + [U4] (rediseño insights)
[U16] Página Zonas UX    → depende de F5 (pipeline) + [U2] (textos) + [U10] (leyenda)
```

## Orden de implementación sugerido

```
Sprint A — Quick wins de texto ✓ COMPLETADO
  ├── [U2]  Renombrar secciones y navegación
  ├── [U3]  Subtítulos en gráficos
  ├── [U9]  Estados vacíos empáticos
  └── [U8]  Contexto de entrada en /rutas

Sprint B — Componentes nuevos ✓ COMPLETADO
  ├── [U1]  Hero status dinámico
  ├── [U4]  Rediseño de insight cards (+ tipo "alerta" para F15)
  ├── [U7]  Detalle de ruta en lenguaje humano
  └── [U10] Leyenda CCAA cualitativa

Sprint C — Experiencia completa ✓ COMPLETADO
  ├── [U5]  Búsqueda en hero  ← descartado por decisión de diseño
  ├── [U6]  Simplificar gráfico histórico (4 botones con nombres descriptivos + subtitle dinámico)
  ├── [U11] Footer expandido (3 columnas)
  └── [U12] Banner primera visita (localStorage)

Sprint D — Features pendientes con UX diseñada ✓ COMPLETADO
  ├── [U15] Alertas umbral  ✓ severity "high", icono rayo, ordenadas primero, `.insight-high` CSS
  └── [U16] Página Zonas    ✓ /zonas con narrativa automática, top worst/best, tabla ordenable, tendencias

Sprint E — Calidad y accesibilidad ✓ COMPLETADO
  ├── [U13] Iconos junto a colores en badges (✓ ⚠ ✕)
  └── [U14] Mobile: scroll horizontal stat cards + "Ver más" en insights
```

---

## Métricas de éxito

Para saber si estas mejoras funcionan, medir:

| Métrica | Indicador | Objetivo |
|---------|-----------|---------|
| Tiempo hasta primera acción | ¿Cuánto tarda el usuario en hacer clic en algo? | < 10s |
| Tasa de búsqueda de estación | ¿Qué % de visitas busca una estación? | > 40% |
| Bounce rate | ¿Se va el usuario sin interactuar? | < 50% |
| Páginas por sesión | ¿Navega a detalle de ruta/estación? | > 1.8 |
| Tiempo en página | ¿Se queda a leer los datos? | > 45s |

Sin analytics instalados (privacidad), una proxy válida es observar el número de visitas a `/cercanias/[id]` y `/ave-larga-distancia/[id]` vs. visitas a `/` en los logs de Vercel.
