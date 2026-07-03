# Plataforma Inteligente de Apoyo a la Planificación Urbana

Sistema de apoyo a la toma de decisiones para planificación urbana con Inteligencia Artificial y Sistemas de Información Geográfica (SIG), orientado inicialmente al municipio de Sucre, Bolivia.

## Resumen del proyecto

La aplicación evalúa terrenos y zonas urbanas para apoyar la selección de ubicaciones estratégicas, con foco inicial en hospitales de segundo nivel. El sistema combina análisis multicriterio, capas geoespaciales, reglas normativas y una capa de predicción para entregar un Índice de Aptitud Territorial e indicadores explicables.

La solución no reemplaza el criterio técnico de urbanistas, autoridades o especialistas. Su función es servir como un sistema de apoyo a la decisión, con resultados trazables y basados en evidencia.

## Estado actual del repositorio

El repositorio ya incluye un backend con FastAPI, un dashboard web con Leaflet y un conjunto de capas geoespaciales en GeoJSON para Sucre. También contiene módulos para preprocesamiento, análisis espacial, modelo multicriterio y entrenamiento de modelos.

### Estructura principal

- src/server.py: API principal y exportación de reportes PDF.
- src/models/mcda.py: evaluación multicriterio y cálculo del IAT.
- src/models/train.py: entrenamiento de modelos de ML.
- src/preprocessing/: generación de datos sintéticos, zonas de crecimiento y dataset de entrenamiento.
- src/spatial/: utilidades de proyección y análisis topográfico.
- dashboard/: interfaz web interactiva.
- data/: dataset de entrenamiento.
- geojson/: distritos, hospitales, vías, topografía, terrenos candidatos y zonas restringidas.
- tests/: pruebas para elevación, MCDA, ML, proyección y servidor.

## Cómo continuar el desarrollo en VS Code

1. Instala las dependencias del proyecto.
2. Ejecuta el backend desde la carpeta raíz con uvicorn src.server:app --reload.
3. Abre la interfaz en http://127.0.0.1:8000/ o http://127.0.0.1:8000/dashboard.
4. Trabaja sobre las capas GeoJSON y los módulos de src/ para ampliar la lógica de evaluación.
5. Usa la carpeta tests/ para validar cambios sobre ML, proyección, MCDA y endpoints.

## API disponible hoy

El backend expone estas rutas principales:

- GET /api/distritos
- GET /api/hospitales
- GET /api/vias
- GET /api/topografia
- GET /api/zonas/crecimiento
- GET /api/zonas/restringidas
- GET /api/terrenos
- POST /api/evaluar
- POST /api/reporte/pdf

## Limitaciones actuales

Estas son las limitaciones más importantes a tener en cuenta para seguir desarrollando:

- El alcance está centrado en Sucre, Bolivia, y no está generalizado para otros municipios.
- La primera versión está orientada a hospitales de segundo nivel, no a cualquier tipo de equipamiento urbano.
- Varias capas dependen de archivos GeoJSON estáticos; no hay conexión en tiempo real con catastro, tráfico, clima ni sensores.
- Parte de la evaluación usa perfiles sintéticos o datos generados para completar variables faltantes.
- La predicción de ML depende de modelos entrenados localmente y de archivos .pkl que pueden no existir aún.
- La validación espacial está acotada a un bounding box de Sucre y a reglas predefinidas.
- No hay autenticación, permisos ni persistencia de usuarios.
- El dashboard es funcional, pero todavía actúa más como visor técnico que como producto final endurecido.

## Resumen funcional

El sistema debe permitir evaluar compatibilidad del suelo, accesibilidad vial, cobertura hospitalaria, riesgos topográficos y restricciones normativas para priorizar terrenos con mejor aptitud. La salida esperada incluye ranking, justificación técnica, mapas temáticos, dashboard e informes PDF.

## Visión del proyecto

La plataforma está pensada para evolucionar hacia un gemelo digital territorial capaz de integrar información geográfica, normativa, demográfica, sanitaria y ambiental para simular escenarios de crecimiento urbano y apoyar la planificación estratégica.

## Estado del documento

Este README ya funciona como resumen operativo para retomar el trabajo en VS Code sin tener que revisar toda la documentación conceptual previa.
