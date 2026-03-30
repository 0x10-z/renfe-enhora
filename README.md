# Andén — Tablero de Llegadas Renfe Cercanías

Tablero en tiempo real de llegadas y retrasos de Renfe Cercanías (España).
Frontend estático en Astro + pipeline Python que combina GTFS estático con actualizaciones GTFS-RT.

---

## Arquitectura

```text
VPS (cron cada 5 min)          GitHub repo              Vercel
┌─────────────────────┐        ┌──────────────┐        ┌────────────┐
│  Python pipeline    │──push──▶ public/data/ │──build──▶ enhora.info  │
│  GTFS + GTFS-RT     │        │  *.json      │        │  (Astro)   │
└─────────────────────┘        └──────────────┘        └────────────┘
```

- **Pipeline** → descarga GTFS, fusiona con GTFS-RT, genera JSON por estación + estadísticas globales
- **Frontend** → páginas estáticas Astro, el JS carga los JSON y se refresca cada 60 s
- **Datos** → [Renfe Open Data](https://data.renfe.com/) · Licencia CC BY 4.0

---

## Estructura

```text
renfe-enhora/
├── scripts/
│   ├── config.py                  # URLs, rutas, umbrales
│   ├── ingestion/
│   │   ├── gtfs_static.py         # Descarga GTFS y caché 24h
│   │   └── gtfs_realtime.py       # GTFS-RT (JSON → protobuf fallback)
│   ├── processing/
│   │   ├── merger.py              # Fusión estático + tiempo real
│   │   └── stats.py               # Estadísticas globales
│   ├── output/
│   │   └── writer.py              # Escribe JSON en public/data/
│   └── main.py                    # Orquestador
├── public/data/
│   ├── stats.json                 # Estadísticas globales
│   └── stations/{stop_id}.json   # Llegadas por estación
├── src/
│   ├── layouts/Layout.astro
│   └── pages/
│       ├── index.astro            # Dashboard + lista de estaciones
│       └── estaciones.astro      # Tablero por estación (?id=…)
├── deploy.sh                      # Cron script: pipeline + git push
└── cron.example                   # Ejemplo de configuración crontab
```

---

## Fuentes de datos

| Feed | URL | Formato |
| ---- | --- | ------- |
| GTFS Estático (Cercanías) | `https://ssl.renfe.com/ftransit/Fichero_CER_FOMENTO/fomento_transit.zip` | ZIP/GTFS |
| GTFS-RT Trip Updates (JSON) | `https://gtfsrt.renfe.com/trip_updates.json` | JSON |
| GTFS-RT Trip Updates (PB) | `https://gtfsrt.renfe.com/trip_updates.pb` | Protobuf |

---

## Instalación (VPS)

```bash
git clone https://github.com/0x10-z/renfe-enhora.git
cd renfe-enhora
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Prueba manual (el timezone Europe/Madrid está hardcodeado en main.py)
python -m scripts.main

# Automatizar con cron (ver cron.example)
chmod +x deploy.sh
crontab -e   # añadir línea del cron.example
```

## Frontend (Vercel)

Conectar el repo en [vercel.com](https://vercel.com):

- Framework: **Astro**
- Build command: `npm run build`
- Output directory: `dist`

Vercel redeploya automáticamente cada vez que el pipeline hace push.

---

## Umbrales de retraso

| Estado | Color | Criterio |
| ------ | ----- | -------- |
| En hora | 🟢 Verde | ≤ 1 minuto |
| Retraso leve | 🟡 Amarillo | 2–5 minutos |
| Retraso alto | 🟠 Naranja | > 5 minutos |
| Cancelado | 🔴 Rojo | SKIPPED en GTFS-RT |
