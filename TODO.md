# TODO de funcionalidades

## Objetivo

Planificar la evolución del sistema para soporte de decisiones urbanas y sanitarias en Sucre, con foco inicial en cobertura hospitalaria, expansión urbana y validación geoespacial.

## Fase 1: Funcionalidades prioritarias

- [x] Mostrar radio de alcance de llegada a hospitales de 3er nivel.
- [x] Incorporar hospitales de 2do nivel dentro del análisis de cobertura.
- [ ] Calcular cobertura usando distancia real sobre red vial (rutas/isócronas) y no solo radio circular.
- [x] Visualizar áreas cubiertas y áreas descubiertas por hospital (capas conmutables).
- [x] Validar y corregir coordenadas de hospitales para ubicarlos con precisión (coordenadas reales).
- [x] Normalizar sistema de coordenadas en toda la plataforma (UTM 20S interno / WGS84 externo).
- [x] Detectar hospitales duplicados, mal georreferenciados o fuera de su distrito esperado (script de validación).

## Fase 2: Expansión urbana

- [x] Estimar áreas probables de expansión de la ciudad según topografía (fuera de distritos).
- [x] Clasificar zonas aptas y no recomendadas (restringidas) para crecimiento urbano (pendiente <15% vs >=15% o ríos).
- [x] Cruzar expansión urbana con pendiente, altitud y riesgo hidráulico (corredores Quirpinchaca).
- [ ] Generar mapa de crecimiento futuro por escenarios (simulación predictiva conmutativa).
- [x] Priorizar sectores de expansión compatibles con infraestructura existente (modelo MCDA / ML RandomForest).

## Fase 3: Análisis sanitario y territorial

- [x] Calcular déficit hospitalario por distrito o zona (relación de camas por habitante vs meta OMS).
- [x] Identificar vacíos de cobertura entre hospitales de 2do y 3er nivel (capas de áreas descubiertas).
- [ ] Estimar saturación futura de hospitales según crecimiento poblacional.
- [ ] Medir accesibilidad sanitaria por tiempo de viaje real.
- [x] Sugerir ubicación de nuevos hospitales o refuerzo de los existentes (evaluador espacial / MCDA).

## Fase 4: Calidad de datos y validación espacial

- [x] Revisar coherencia entre distrito, barrio y coordenadas de cada hospital.
- [x] Validar si un punto hospitalario cae sobre una zona físicamente o normativamente incompatible (ej. centro histórico).
- [x] Identificar inconsistencias entre capas GeoJSON y atributos tabulares.
- [x] Incorporar mensajes de advertencia cuando falten datos críticos (issues de validación en popup y API).

## Fase 5: Análisis avanzado

- [ ] Agregar simulación de escenarios de crecimiento urbano.
- [ ] Permitir comparar varias ubicaciones candidatas en paralelo.
- [ ] Incorporar análisis de especialidades hospitalarias.
- [ ] Evaluar impacto de nuevas vías sobre tiempos de acceso.
- [ ] Crear ranking de hospitales por centralidad y cobertura.

## Fase 6: Producto y visualización

- [x] Mejorar el dashboard con capas conmutables por temática (toggles de Toolbar superior).
- [x] Añadir panel de indicadores para cobertura, expansión y riesgo (KPIs laterales).
- [ ] Crear leyenda clara para hospitales de 1er, 2do y 3er nivel.
- [x] Agregar exportación de resultados a PDF (Reporte Técnico Automatizado) y GeoJSON.
- [ ] Guardar resultados de análisis para consultas posteriores.

## Dependencias técnicas sugeridas

- [x] Definir qué capa será la fuente oficial de hospitales (geojson/hospitales_sucre.geojson).
- [x] Confirmar si la red vial actual permite cálculo de rutas o solo aproximación geométrica (actualmente proximidad lineal).
- [x] Revisar si existe base topográfica suficiente para modelar expansión urbana (geojson/topografia_sucre.geojson).
- [x] Establecer criterios de validación de coordenadas para hospitales.
- [x] Verificar si el cálculo de cobertura se hará con red vial, distancia euclidiana o ambos (euclidiana inicial).

## Prioridad recomendada para el desarrollo restante

1. **Ruteo y Distancia Real (Fase 1/3):** Implementar isócronas basadas en la red de vías actual en lugar de círculos geométricos.
2. **Comparador en Paralelo (Fase 5):** Permitir al usuario seleccionar y comparar dos terrenos candidatos lado a lado en el dashboard.
3. **Escenarios de Crecimiento (Fase 2/5):** Incorporar un slider temporal para simular el avance de la mancha urbana a 5, 10 y 20 años.
4. **Leyenda de Hospitales y Niveles (Fase 6):** Refinar los marcadores del mapa con colores o formas distintas por nivel y añadir una leyenda estática en la esquina inferior izquierda.
