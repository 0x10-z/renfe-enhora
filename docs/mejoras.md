Mejoras de datos / pipeline

F4 – Histórico por estación: la page de detalle de estación (/cercanias/[id]) ahora muestra solo el tiempo real. Se podría añadir un gráfico de tendencia histórica con station-history/YYYY-MM-DD.json (que ya se genera)
F5 – Ranking de rutas con más retrasos: agrupar por route_id en el merger y exponer un top-10 de rutas más problemáticas
Alertas / umbral: detectar en insights.py si una línea o zona supera un umbral histórico y marcarla como alerta
Mejoras de frontend

Mapa de calor por CCAA/núcleo: la sección de zonas que acabamos de hacer muestra tarjetas, pero podría complementarse con el mapa geográfico que ya existe
Página de tendencias: una vista dedicada con los gráficos históricos más ricos (por tipo de tren, comparativa días semana vs fin de semana)
PWA / notificaciones push: permitir suscribirse a alertas de una línea concreta
Quick wins (bajo esfuerzo, alto valor)

Fotos de trenes pendientes: quedan ~7 .fake (cercanias/s440, s450, s463, s599; md/s450, s598; regional/s598) — yo los puedo descargar igual que el resto
SEO / OpenGraph: añadir meta tags dinámicos por servicio para que se comparta bien
Sort/filtro en la tabla de zonas: poder ordenar por % retraso, por total de trenes, etc.
¿Cuál te llama más? O si tienes algo en mente que no está aquí, cuéntame.
