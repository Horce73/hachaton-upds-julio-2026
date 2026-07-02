# Plataforma Inteligente de Apoyo a la Planificación Urbana

Sistema de apoyo a la toma de decisiones para planificación urbana con Inteligencia Artificial y Sistemas de Información Geográfica (SIG), orientado inicialmente al municipio de Sucre, Bolivia.

## Propósito

El proyecto busca analizar información territorial, demográfica, urbana, vial, hospitalaria, ambiental y normativa para recomendar ubicaciones estratégicas para equipamientos urbanos. La primera versión estará enfocada en la selección de terrenos para hospitales de segundo nivel.

La solución no reemplaza el criterio técnico de urbanistas, autoridades o especialistas. Su función es actuar como un sistema inteligente de apoyo a la toma de decisiones con recomendaciones explicables y basadas en evidencia.

## Alcance Inicial

La primera versión del sistema debe cubrir:

- Evaluación de terrenos para hospitales de segundo nivel.
- Análisis de restricciones normativas, topográficas, ambientales e infraestructurales.
- Cálculo de un Índice de Aptitud Territorial (IAT).
- Generación de ranking de terrenos y justificación técnica.
- Visualización geoespacial de indicadores y restricciones.

## Objetivos Funcionales

El proyecto debe permitir:

- Identificar sectores con mayor demanda hospitalaria.
- Evaluar compatibilidad de uso del suelo.
- Medir accesibilidad vial y tiempos de respuesta.
- Analizar cobertura hospitalaria existente.
- Detectar restricciones físicas, ambientales y normativas.
- Producir recomendaciones explicables para toma de decisiones.

## Contexto Territorial

El sistema debe estar diseñado para Sucre, Bolivia, y comprender como mínimo:

- Distritos, barrios, manzanas y parcelas.
- Catastro y zonificación urbana.
- Red vial y transporte público.
- Topografía, hidrología y cobertura vegetal.
- Expansión urbana y áreas de reserva.
- Equipamientos urbanos existentes.

## Tipos de Datos Requeridos

### Información Territorial

- Latitud, longitud y altitud.
- Pendiente, curvas de nivel y modelo digital de elevación.
- Orientación, tipo de suelo, geología y geotecnia.
- Cobertura vegetal.

### Información Demográfica

- Población y densidad.
- Crecimiento y proyección.
- Migración, edad promedio e índice de dependencia.
- Urbanización.

### Información Urbana

- Distrito y barrio.
- Zonificación y uso del suelo.
- Área urbana, expansión y reserva.
- Equipamientos existentes.
- Catastro.

### Información Vial

- Jerarquía vial.
- Transporte público.
- Tiempo de viaje, distancia y accesibilidad.

### Información Hospitalaria

- Hospital más cercano.
- Nivel hospitalario.
- Número de camas.
- Especialidades.
- Cobertura, capacidad resolutiva y radio de influencia.

### Información Ambiental

- Áreas verdes y protegidas.
- Ríos y quebradas.
- Inundaciones y deslizamientos.
- Contaminación y calidad del aire.

## Restricciones que Debe Respetar el Modelo

El sistema no debe recomendar terrenos con:

- Uso del suelo incompatible.
- Restricciones ambientales.
- Restricciones patrimoniales.
- Actividades industriales incompatibles.
- Pendientes elevadas o suelos inestables.
- Riesgo geológico, inundaciones o deslizamientos.
- Falta de servicios básicos o infraestructura esencial.

Además, debe evaluar cobertura hospitalaria existente, déficit hospitalario, radio de influencia, capacidad hospitalaria y demanda futura.

## Índice de Aptitud Territorial (IAT)

Cada terreno debe recibir una puntuación de 0 a 100.

### Interpretación

- 90 a 100: Excelente.
- 80 a 89: Muy bueno.
- 70 a 79: Adecuado.
- 60 a 69: Aceptable.
- 0 a 59: No recomendable.

### Criterios de Evaluación

El sistema multicriterio debe considerar, como referencia inicial:

- Crecimiento poblacional: 25 %
- Accesibilidad: 20 %
- Cobertura hospitalaria: 15 %
- Infraestructura: 15 %
- Uso del suelo: 10 %
- Topografía: 10 %
- Riesgos: 5 %

## Modelos y Técnicas Sugeridas

### Predicción

- Random Forest
- XGBoost
- LightGBM
- Gradient Boosting

### Clasificación

- Árboles de Decisión
- SVM

### Agrupamiento

- KMeans
- DBSCAN

### Series Temporales

- Prophet
- LSTM

### Análisis Espacial

- Moran's I
- Kernel Density
- Hot Spot Analysis

## Requisitos de Explicabilidad

Toda recomendación debe incluir justificación técnica. La salida no puede limitarse a una predicción sin contexto.

Ejemplo esperado:

```text
Terreno recomendado
Distrito: 4
Índice de aptitud: 94

Justificación:
- Alto crecimiento poblacional.
- Baja cobertura hospitalaria.
- Pendiente menor al 8 %.
- Uso del suelo compatible.
- Cercanía a avenida principal.
- Disponibilidad de infraestructura básica.
- Riesgo ambiental bajo.
```

## Salidas Esperadas

La plataforma debe generar:

- Ranking de terrenos.
- Índice de Aptitud Territorial.
- Justificación técnica.
- Mapas de crecimiento urbano, expansión urbana y densidad poblacional.
- Mapas de accesibilidad, cobertura hospitalaria, riesgos y restricciones.
- Dashboard de indicadores.
- Reportes PDF.

## Arquitectura y Escalabilidad

La arquitectura debe ser modular y escalable para incorporar nuevos componentes como:

- Planificación vial.
- Gestión ambiental.
- Educación.
- Seguridad ciudadana.
- Cambio climático.
- Gestión del riesgo.
- Smart City.
- Gemelo Digital Territorial.

## Visión del Proyecto

La solución debe evolucionar de un recomendador de terrenos a un gemelo digital territorial capaz de integrar información geográfica, normativa, demográfica, sanitaria y ambiental para simular escenarios de crecimiento urbano y apoyar la planificación estratégica.

## Principios del Sistema

- Explicabilidad.
- Transparencia.
- Escalabilidad.
- Modularidad.
- Reproducibilidad.
- Basado en evidencia.
- Cumplimiento normativo.
- Integración GIS.
- Soporte a la toma de decisiones.
- Predicción basada en datos.
- Optimización territorial.
- Actualización continua con nuevos datasets.

## Integraciones Futuras

El proyecto debe estar preparado para integrar:

- Catastro municipal.
- PMOT y PLUS.
- Modelos digitales de elevación.
- Imágenes satelitales.
- Datos del INE.
- OpenStreetMap.
- GeoBolivia.
- IDE municipales.
- Sensores IoT.
- Datos de movilidad en tiempo real.
- Información climática.
- Modelos de expansión urbana por visión artificial.

## Recomendación de Estructura del Proyecto

Una estructura inicial sugerida es:

```text
.
├── data/
├── notebooks/
├── src/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── spatial/
│   ├── models/
│   ├── evaluation/
│   └── visualization/
├── reports/
├── dashboards/
└── docs/
```

## Estado del Documento

Este README resume las especificaciones base del proyecto y debe servir como referencia inicial para diseño, desarrollo y validación del sistema.