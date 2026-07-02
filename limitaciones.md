# Plataforma Inteligente de Apoyo a la Planificación Urbana
## Especificaciones para el Entrenamiento del Modelo de Inteligencia Artificial

**Versión:** 1.0  
**Proyecto:** Plataforma Inteligente de Apoyo a la Planificación Urbana mediante Inteligencia Artificial y Sistemas de Información Geográfica (SIG)  
**Caso de estudio:** Ciudad de Sucre - Bolivia

---

# 1. Objetivo del Modelo

Desarrollar un modelo de Inteligencia Artificial capaz de analizar información geoespacial, demográfica, topográfica, sanitaria y normativa para apoyar la toma de decisiones relacionadas con la planificación urbana.

Inicialmente, el modelo estará especializado en recomendar ubicaciones estratégicas para la construcción de hospitales de segundo nivel, considerando las restricciones establecidas por la normativa municipal y sanitaria vigente.

La arquitectura del modelo deberá ser escalable para incorporar posteriormente otros tipos de equipamientos urbanos, tales como:

- Centros de Salud
- Escuelas
- Universidades
- Mercados
- Estaciones de Bomberos
- Comisarías
- Parques Urbanos
- Terminales de Transporte
- Nuevas Avenidas
- Equipamientos Municipales

---

# 2. Rol del Modelo

El modelo NO reemplaza el criterio técnico de urbanistas o autoridades.

Su función consiste en actuar como un **Sistema Inteligente de Apoyo a la Toma de Decisiones (Decision Support System - DSS)** proporcionando recomendaciones fundamentadas mediante análisis espacial, estadístico y predictivo.

Debe responder preguntas como:

- ¿Hacia dónde crecerá la ciudad?
- ¿Qué sectores tendrán mayor demanda hospitalaria?
- ¿Qué terrenos cumplen con la normativa urbana?
- ¿Cuál es el mejor lugar para construir un hospital?
- ¿Qué restricciones existen en un determinado terreno?
- ¿Cómo afecta una nueva avenida a la cobertura hospitalaria?

---

# 3. Dominio del Conocimiento

El modelo deberá comprender conceptos relacionados con:

## Urbanismo

- Planificación Urbana
- Ordenamiento Territorial
- Zonificación
- Expansión Urbana
- Catastro
- Uso del Suelo
- Equipamiento Urbano
- Infraestructura Urbana

---

## Sistemas de Información Geográfica

Debe comprender:

- Cartografía
- Capas GIS
- Shapefile
- GeoJSON
- Raster
- Vector
- Buffer
- Overlay
- Intersección
- Isocronas
- HotSpot
- Kernel Density
- Moran's I
- Modelos Digitales de Elevación

---

## Salud

Debe conocer:

- Redes Integradas de Salud
- Hospitales
- Cobertura Hospitalaria
- Nivel Hospitalario
- Radio de Influencia
- Capacidad Resolutiva
- Número de Camas
- Especialidades
- Demanda Hospitalaria

---

## Inteligencia Artificial

Conceptos mínimos

- Machine Learning
- Predicción
- Clasificación
- Clustering
- Regresión
- Explicabilidad
- Sistemas Expertos
- Modelos Predictivos

---

# 4. Contexto Territorial

Todo el conocimiento estará orientado inicialmente al municipio de **Sucre (Bolivia)**.

El modelo deberá comprender las características del territorio.

## Componentes

- Distritos
- Barrios
- Manzanas
- Parcelas
- Catastro
- Red vial
- Topografía
- Hidrología
- Equipamientos urbanos
- Cobertura vegetal
- Expansión urbana

---

# 5. Componentes del Dataset

## 5.1 Información Territorial

Variables

- Latitud
- Longitud
- Altitud
- Pendiente
- Curvas de nivel
- Modelo Digital de Elevación
- Orientación
- Tipo de Suelo
- Geología
- Geotecnia
- Cobertura Vegetal

Objetivo

Determinar la factibilidad física del terreno.

---

## 5.2 Información Demográfica

Variables

- Población
- Densidad
- Crecimiento
- Proyección
- Migración
- Edad Promedio
- Índice de Dependencia
- Urbanización

Objetivo

Predecir futuras demandas de infraestructura.

---

## 5.3 Información Urbana

Variables

- Distrito
- Barrio
- Zonificación
- Uso del Suelo
- Área Urbana
- Área de Expansión
- Área de Reserva
- Equipamientos Existentes
- Catastro

---

## 5.4 Información Vial

Variables

- Avenida Principal
- Avenida Secundaria
- Calle Colectora
- Calle Local
- Transporte Público
- Tiempo de Viaje
- Distancia
- Accesibilidad

---

## 5.5 Información Hospitalaria

Variables

- Hospital más cercano
- Nivel Hospitalario
- Número de Camas
- Especialidades
- Cobertura
- Tiempo de Respuesta
- Capacidad Resolutiva
- Radio de Influencia

---

## 5.6 Información Ambiental

Variables

- Áreas Verdes
- Áreas Protegidas
- Ríos
- Quebradas
- Inundaciones
- Deslizamientos
- Contaminación
- Calidad del Aire

---

# 6. Restricciones Normativas

El modelo debe considerar la normativa urbana antes de generar cualquier recomendación.

## Restricciones de Uso del Suelo

No podrá recomendar terrenos donde:

- El uso del suelo sea incompatible.
- Existan restricciones ambientales.
- Existan restricciones patrimoniales.
- Existan actividades industriales incompatibles.

---

## Restricciones Topográficas

Evitar:

- Pendientes elevadas.
- Suelos inestables.
- Riesgo geológico.
- Zonas inundables.
- Deslizamientos.

---

## Restricciones de Infraestructura

El terreno deberá contar con:

- Agua Potable.
- Alcantarillado.
- Energía Eléctrica.
- Telecomunicaciones.
- Drenaje.

---

## Restricciones Sanitarias

Debe evaluar:

- Cobertura existente.
- Déficit hospitalario.
- Radio de influencia.
- Capacidad hospitalaria.
- Demanda futura.

---

# 7. Parámetros de Evaluación

Cada terreno será evaluado mediante un sistema multicriterio.

Ejemplo de ponderación

| Criterio | Peso |
|----------|------|
| Crecimiento poblacional | 25 % |
| Accesibilidad | 20 % |
| Cobertura Hospitalaria | 15 % |
| Infraestructura | 15 % |
| Uso del Suelo | 10 % |
| Topografía | 10 % |
| Riesgos | 5 % |

---

# 8. Variable Objetivo

El modelo deberá generar un:

## Índice de Aptitud Territorial (IAT)

Escala

0 - 100

Interpretación

90 - 100
Excelente

80 - 89
Muy Bueno

70 - 79
Adecuado

60 - 69
Aceptable

0 - 59
No recomendable

---

# 9. Algoritmos Sugeridos

Predicción

- Random Forest
- XGBoost
- LightGBM
- Gradient Boosting

Clasificación

- Árboles de Decisión
- SVM

Agrupamiento

- KMeans
- DBSCAN

Series Temporales

- Prophet
- LSTM

Análisis Espacial

- Moran's I
- Kernel Density
- Hot Spot Analysis

---

# 10. Explicabilidad del Modelo

Toda recomendación deberá incluir una justificación.

Ejemplo

```

Terreno Recomendado

Distrito: 4

Índice de Aptitud: 94

Justificación

• Alto crecimiento poblacional.
• Baja cobertura hospitalaria.
• Pendiente menor al 8%.
• Uso del suelo compatible.
• Cercanía a avenida principal.
• Disponibilidad de infraestructura básica.
• Riesgo ambiental bajo.

```

No se aceptarán respuestas del tipo:

"Porque el modelo lo predijo."

---

# 11. Salidas Esperadas

La plataforma deberá generar:

- Ranking de terrenos.
- Índice de Aptitud Territorial.
- Justificación técnica.
- Mapa de crecimiento urbano.
- Mapa de expansión urbana.
- Mapa de densidad poblacional.
- Mapa de accesibilidad.
- Mapa de cobertura hospitalaria.
- Mapa de riesgos.
- Mapa de restricciones.
- Dashboard de indicadores.
- Reportes PDF.

---

# 12. Escalabilidad

La arquitectura debe permitir incorporar nuevos módulos.

Ejemplos

- Planificación Vial
- Gestión Ambiental
- Educación
- Seguridad Ciudadana
- Cambio Climático
- Gestión del Riesgo
- Smart City
- Gemelo Digital (Digital Twin)

---

# 13. Visión del Proyecto

La plataforma no será únicamente un recomendador de terrenos.

Será un **Gemelo Digital Territorial** capaz de integrar información geográfica, normativa, demográfica, sanitaria y ambiental para simular escenarios de crecimiento urbano y apoyar la planificación estratégica del municipio.

El objetivo final es proporcionar una herramienta basada en evidencia que permita optimizar la inversión pública, mejorar la cobertura de servicios y promover un desarrollo urbano sostenible mediante el uso de Inteligencia Artificial y Sistemas de Información Geográfica.

---

# 14. Principios del Modelo

El modelo deberá cumplir los siguientes principios:

- Explicabilidad de las decisiones.
- Transparencia en la evaluación.
- Escalabilidad.
- Modularidad.
- Reproducibilidad.
- Basado en evidencia.
- Cumplimiento de normativa.
- Integración GIS.
- Soporte a la toma de decisiones.
- Predicción basada en datos.
- Optimización del territorio.
- Actualización continua mediante nuevos datasets.

---

# 15. Futuras Integraciones

- Catastro Municipal.
- Plan Municipal de Ordenamiento Territorial (PMOT).
- Plan de Uso del Suelo (PLUS).
- Modelos Digitales de Elevación.
- Imágenes Satelitales.
- Datos del INE.
- OpenStreetMap.
- GeoBolivia.
- IDE Municipales.
- Sensores IoT (Smart City).
- Datos en tiempo real de movilidad.
- Información climática.
- Modelos de expansión urbana mediante visión artificial.