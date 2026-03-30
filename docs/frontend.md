# Frontend (Astro)

La web es un sitio estático generado con Astro que actúa como panel de analítica e infografía de los retrasos de Renfe. No hay servidor en runtime: todo se genera en tiempo de build a partir de los JSON pre-calculados por el pipeline Python.

## Comandos

```bash
npm run dev       # Servidor de desarrollo en localhost:3000 (hot reload)
npm run build     # Genera el sitio estático en dist/
npm run preview   # Previsualiza el build
```

## Estructura de páginas

```
src/
├── layouts/
│   └── Layout.astro              # Shell HTML global, CSS de tema y tipografía
├── pages/
│   ├── index.astro               # Dashboard principal (~1000 líneas)
│   ├── sobre.astro               # Página metodología/about
│   ├── cercanias/[id].astro      # Página de detalle de estación (Cercanías)
│   └── ave-larga-distancia/
│       └── [id].astro            # Página de detalle de estación (AVE/LD)
└── components/
    └── StationBoard.astro        # Tabla de llegadas reutilizable
```

## Página principal (`index.astro`)

Contiene toda la lógica del dashboard en un único fichero. Las secciones principales son:

1. **Tabs de servicio** — alterna entre Cercanías y AVE/LD; recarga los datos correspondientes
2. **Tarjetas de estadísticas** — total de trenes, % puntualidad, retrasos, cancelaciones, retraso medio
3. **Gráfico de histórico** — serie temporal renderizada con ECharts (datos de `history.json`)
4. **Insights** — lista de insights con badges de severidad (verde/amarillo/rojo)
5. **Buscador de estaciones** — filtra la lista de estaciones; enlaza a páginas de detalle

Los datos se cargan vía `fetch()` al montar la página, apuntando a los JSON en `/data/{servicio}/stats.json`, `/data/{servicio}/history.json` e `/data/{servicio}/insights.json`.

## Páginas de detalle de estación

Las rutas `cercanias/[id]` y `ave-larga-distancia/[id]` son páginas dinámicas de Astro que en el build generan un HTML por cada `stop_id`. Usan `StationBoard.astro` para mostrar la tabla de llegadas.

`StationBoard.astro` carga `/data/{servicio}/stations/{stop_id}.json` y muestra:
- Hora programada y estimada
- Badge de estado (`en_hora` / `retraso_leve` / `retraso_alto` / `cancelado`)
- Origen del tren
- Timestamp de última actualización

## Dependencias clave

- **Astro 4.16** — generador de sitio estático (output: `static`)
- **ECharts 6** — gráfico de histórico en la página principal
- Sin frameworks JS adicionales (Astro vanilla)

## Configuración de build

`astro.config.mjs` usa `output: 'static'` con un directorio de assets personalizado. El sitio se despliega en Vercel, que detecta el push a GitHub y lanza el build automáticamente.

## Relación con el pipeline

El frontend **solo lee** los JSON generados por el pipeline. No escribe ni transforma datos. El directorio `public/data/` es el contrato entre ambas partes:

```
public/data/
├── cercanias/
│   ├── stats.json
│   ├── history.json
│   ├── insights.json
│   └── stations/{stop_id}.json
└── ave-larga-distancia/
    ├── stats.json
    ├── history.json
    ├── insights.json
    └── stations/{stop_id}.json
```

Si el pipeline falla una iteración, el frontend muestra los datos de la última ejecución correcta (los JSON no se borran entre runs, solo se sobreescriben).
