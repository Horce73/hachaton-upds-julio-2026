import json
import math
from shapely.geometry import shape, Point
from src.spatial.projection import reproject_geojson, to_utm
from src.spatial.elevation import ElevationModel
from src.preprocessing.generate_mock_data import DISTRICT_PROFILES

class MCDAModel:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Load and project layers to UTM 20S for spatial calculations
        with open("geojson/distritos_sucre.geojson") as f:
            dist_wgs84 = json.load(f)
        self.distritos_utm = reproject_geojson(dist_wgs84, to_crs="epsg:32720", from_crs="epsg:32720") # Already UTM 20S
        
        with open("geojson/hospitales_sucre.geojson") as f:
            hosp_wgs84 = json.load(f)
        self.hospitales_utm = reproject_geojson(hosp_wgs84, to_crs="epsg:32720", from_crs="epsg:4326")
        
        with open("geojson/vias_sucre.geojson") as f:
            vias_wgs84 = json.load(f)
        self.vias_utm = reproject_geojson(vias_wgs84, to_crs="epsg:32720", from_crs="epsg:4326")
        
        # Geometries lists
        self.district_geoms = []
        for feature in self.distritos_utm.get("features", []):
            geom = shape(feature["geometry"])
            cod = feature["properties"]["COD"]
            name = feature["properties"]["Distritos"]
            self.district_geoms.append((geom, cod, name))
            
        self.hospital_geoms = [shape(f["geometry"]) for f in self.hospitales_utm.get("features", [])]
        self.vias_geoms = [shape(f["geometry"]) for f in self.vias_utm.get("features", [])]
        
        self.elevation_model = ElevationModel.get_instance()

    def evaluate_parcel(self, geojson_geometry: dict, properties: dict) -> dict:
        """
        Evaluates a parcel geometry against criteria and restrictions to compute its IAT.
        Inputs:
            geojson_geometry: dict representation of WGS84 geometry (Polygon or Point).
            properties: dict containing attributes (agua, electricidad, alcantarillado, uso_suelo, etc.)
        """
        # Reproject parcel geometry to UTM 20S
        parcel_utm_geom = reproject_geojson(geojson_geometry, to_crs="epsg:32720", from_crs="epsg:4326")
        sh_geom = shape(parcel_utm_geom)
        
        # Calculate centroid in UTM
        centroid = sh_geom.centroid
        cx, cy = centroid.x, centroid.y
        
        # 1. Determine District
        district_cod = "D-Desconocido"
        district_name = "Fuera de jurisdicción urbana"
        for geom, cod, name in self.district_geoms:
            if geom.contains(centroid) or geom.intersects(sh_geom):
                district_cod = cod
                district_name = name
                break
                
        profile = DISTRICT_PROFILES.get(district_cod, {
            "nombre": district_name,
            "poblacion_estimada": 0,
            "crecimiento_anual": 0.0,
            "densidad_hab_km2": 0,
            "camas_actuales": 0,
            "servicios_basicos_pct": 0.5,
            "compatibilidad_uso": "Desconocida"
        })
        
        # 2. Topography & Elevation
        elev = self.elevation_model.get_elevation(cx, cy)
        slope = self.elevation_model.get_slope(cx, cy)
        
        # 3. Size/Area Check
        # If geometry is Polygon, compute area from shape. Otherwise use properties 'area_m2' or default 10,000
        area_m2 = sh_geom.area if sh_geom.geom_type in ["Polygon", "MultiPolygon"] else float(properties.get("area_m2", 10000))
        
        # 4. Restriction evaluations
        restrictions = []
        
        # R1: Slope Restriction (> 15% is unstable for hospital construction)
        if slope > 15.0:
            restrictions.append(f"Restricción Topográfica: Pendiente excesiva del {slope:.1f}% (límite máximo: 15%).")
            
        # R2: Incompatible Land Use
        uso_suelo = properties.get("uso_suelo", "No definido")
        if properties.get("patrimonial", False) or "patrimonial" in uso_suelo.lower() or district_cod == "D-1":
            restrictions.append("Restricción Normativa: Terreno ubicado en zona patrimonial (Distrito 1) incompatible con equipamiento hospitalario mayor.")
        if properties.get("industrial_incompatible", False) or "industrial pesada" in uso_suelo.lower():
            restrictions.append("Restricción Normativa: Zonificación industrial incompatible.")
            
        # R3: River Buffer Restriction (simulated flooding hazard, within 50m of river/creek)
        is_near_river = properties.get("cerca_rio", False)
        if is_near_river:
            restrictions.append("Restricción de Riesgo: Terreno ubicado dentro de zona de influencia de quebrada/río (riesgo de inundación).")
            
        # R4: Size Restriction (hospital of second level requires at least 5,000 m2)
        if area_m2 < 5000:
            restrictions.append(f"Restricción de Superficie: Área insuficiente de {area_m2:.0f} m² (mínimo requerido: 5,000 m²).")

        # 5. Multi-Criteria Scoring (0-100 per criteria)
        scores = {}
        
        # C1: Crecimiento Poblacional (25%)
        # Scale: 5% growth -> 100 points. 0% growth -> 0 points.
        growth_rate = profile["crecimiento_anual"]
        scores["crecimiento"] = min(100.0, max(0.0, growth_rate * 2000.0))
        
        # C2: Accesibilidad Vial (20%)
        # Distance to nearest main road
        if self.vias_geoms:
            dist_vias = min(geom.distance(centroid) for geom in self.vias_geoms)
        else:
            dist_vias = 1000.0
            
        # Score scales from 100 (< 100m) down to 0 (> 1500m)
        if dist_vias <= 100.0:
            scores["accesibilidad"] = 100.0
        elif dist_vias >= 1500.0:
            scores["accesibilidad"] = 0.0
        else:
            scores["accesibilidad"] = 100.0 - (dist_vias - 100.0) * (100.0 / 1400.0)
            
        # C3: Cobertura Hospitalaria (15%)
        # Distance to nearest existing hospital (we want to place it in underserved areas, far from other hospitals)
        if self.hospital_geoms:
            dist_hosp = min(geom.distance(centroid) for geom in self.hospital_geoms)
        else:
            dist_hosp = 5000.0
            
        # Score scales: < 500m -> 0 points (over-saturated), > 3000m -> 100 points (highly underserved)
        if dist_hosp <= 500.0:
            scores["cobertura"] = 0.0
        elif dist_hosp >= 3000.0:
            scores["cobertura"] = 100.0
        else:
            scores["cobertura"] = (dist_hosp - 500.0) * (100.0 / 2500.0)
            
        # C4: Infraestructura Básica (15%)
        # Based on services availability properties
        servicios = [
            properties.get("agua", True),
            properties.get("electricidad", True),
            properties.get("alcantarillado", True)
        ]
        scores["infraestructura"] = (sum(1 for s in servicios if s) / 3.0) * 100.0
        
        # C5: Uso del Suelo (10%)
        if "expansión" in uso_suelo.lower() or "reserva" in uso_suelo.lower() or "mixto" in uso_suelo.lower():
            scores["uso_suelo"] = 100.0
        elif "residencial" in uso_suelo.lower():
            scores["uso_suelo"] = 80.0
        else:
            scores["uso_suelo"] = 50.0
            
        # C6: Topografía / Pendiente (10%)
        # Slope < 4% -> 100 points. Slope >= 15% -> 0 points.
        if slope <= 4.0:
            scores["topografia"] = 100.0
        elif slope >= 15.0:
            scores["topografia"] = 0.0
        else:
            scores["topografia"] = 100.0 - (slope - 4.0) * (100.0 / 11.0)
            
        # C7: Riesgos (5%)
        scores["riesgos"] = 0.0 if is_near_river else 100.0
        
        # 6. Weightings configuration (from .md files)
        weights = {
            "crecimiento": 0.25,
            "accesibilidad": 0.20,
            "cobertura": 0.15,
            "infraestructura": 0.15,
            "uso_suelo": 0.10,
            "topografia": 0.10,
            "riesgos": 0.05
        }
        
        # Calculate IAT
        iat = sum(scores[key] * weights[key] for key in weights)
        
        # If any major restriction is present, the final IAT is overridden to 0 (No recomendable)
        apto = len(restrictions) == 0
        final_iat = iat if apto else 0.0
        
        # 7. Generate Explainable Justification text
        explicacion = self._generate_justification(final_iat, scores, slope, area_m2, district_cod, profile, restrictions, dist_vias, dist_hosp)
        
        return {
            "apto": apto,
            "restricciones": restrictions,
            "criterios": {k: round(v, 1) for k, v in scores.items()},
            "iat": round(final_iat, 1),
            "original_iat": round(iat, 1), # IAT before restriction overrides
            "elevacion_m": round(elev, 1),
            "pendiente_pct": round(slope, 1),
            "area_m2": round(area_m2, 1),
            "distrito_cod": district_cod,
            "distrito_nombre": district_name,
            "distancia_vias_m": round(dist_vias, 1),
            "distancia_hosp_m": round(dist_hosp, 1),
            "explicacion": explicacion
        }

    def _generate_justification(self, iat: float, scores: dict, slope: float, area_m2: float, district_cod: str, profile: dict, restrictions: list, dist_vias: float, dist_hosp: float) -> str:
        """Generates a text-based explanation detailing why the parcel scored what it did."""
        if restrictions:
            return "Terreno NO RECOMENDABLE debido a las siguientes restricciones críticas:\n" + "\n".join([f"- {r}" for r in restrictions])
            
        # Success description
        qualitative = "Excelente" if iat >= 90 else "Muy Bueno" if iat >= 80 else "Adecuado" if iat >= 70 else "Aceptable"
        
        points = []
        
        # Topography
        if slope < 5.0:
            points.append(f"Topografía ideal con una pendiente muy suave del {slope:.1f}%.")
        elif slope < 10.0:
            points.append(f"Topografía estable con pendiente del {slope:.1f}%.")
        else:
            points.append(f"Topografía con pendiente moderada del {slope:.1f}%, requiere movimientos menores de tierra.")
            
        # Growth and Deficit
        if scores["crecimiento"] >= 75.0:
            points.append(f"Ubicado en el {profile['nombre']} con una altísima tasa de crecimiento urbano ({profile['crecimiento_anual']*100:.1f}% anual).")
            
        # Coverage
        if dist_hosp > 2000.0:
            points.append(f"Excelente emplazamiento para mitigar el déficit de cobertura hospitalaria, a {dist_hosp/1000.0:.1f} km del hospital más cercano.")
        else:
            points.append(f"Cercanía a red de salud existente ({dist_hosp:.0f} m), lo que facilita la derivación de pacientes pero reduce la cobertura de áreas desatendidas.")
            
        # Accessibility
        if dist_vias < 200.0:
            points.append(f"Conectividad vial óptima, a solo {dist_vias:.0f} metros de avenidas principales.")
            
        # Services
        services_score = scores["infraestructura"]
        if services_score == 100.0:
            points.append("Acceso completo a servicios básicos (agua potable, energía eléctrica y alcantarillado).")
        elif services_score >= 50.0:
            points.append("Acceso parcial a servicios básicos, requiere extensiones menores de servicios de alcantarillado o red.")
            
        justificacion = f"Terreno clasificado como {qualitative.upper()} (Índice de Aptitud: {iat:.1f}/100).\n\n"
        justificacion += "Justificación Técnica:\n" + "\n".join([f"- {p}" for p in points])
        
        return justificacion
