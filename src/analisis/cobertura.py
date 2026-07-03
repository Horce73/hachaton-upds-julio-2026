import json
from shapely.geometry import shape, mapping, Point
from shapely.ops import unary_union
from src.spatial.projection import reproject_geojson, to_wgs84
from src.analisis.routing import RoadNetwork

COVERAGE_CONFIG = {
    3: {"radius_m": 5000, "label": "Cobertura 3er Nivel (Red Vial)", "color": "#3B82F6"},
    2: {"radius_m": 3000, "label": "Cobertura 2do Nivel (Red Vial)", "color": "#FBBF24"},
    "default": {"radius_m": 1500, "label": "Cobertura Hospitalaria", "color": "#94A3B8"}
}

class CoverageAnalyzer:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        with open("geojson/distritos_sucre.geojson") as f:
            dist_utm = json.load(f)
        self.distritos_utm = reproject_geojson(dist_utm, to_crs="epsg:32720", from_crs="epsg:32720")

        with open("geojson/hospitales_sucre.geojson") as f:
            self.hospitales_wgs84 = json.load(f)

        hosp_utm = reproject_geojson(self.hospitales_wgs84, to_crs="epsg:32720", from_crs="epsg:4326")
        self.hospitales_utm = hosp_utm

        self.urban_boundary = unary_union([
            shape(f["geometry"]) for f in self.distritos_utm.get("features", [])
        ])

        self.road_network = None

    def get_coverage(self, use_network: bool = True) -> dict:
        return self._compute_coverage(use_network)

    def _compute_coverage(self, use_network: bool = True) -> dict:
        if use_network:
            if self.road_network is None:
                try:
                    self.road_network = RoadNetwork.get_instance()
                except Exception as e:
                    print(f"Advertencia: No se pudo cargar la red vial para routing: {e}")
                    use_network = False

        hosp_geom_utm = []
        for feat in self.hospitales_utm.get("features", []):
            props = feat["properties"]
            nivel = props.get("nivel", 0)
            geom = shape(feat["geometry"])
            hosp_geom_utm.append({"geom": geom, "nivel": nivel, "props": props})

        all_coverages = []
        nivel2_coverage = []
        nivel3_coverage = []

        for h in hosp_geom_utm:
            nivel = h["nivel"]
            config = COVERAGE_CONFIG.get(nivel, COVERAGE_CONFIG["default"])
            radius = config["radius_m"]

            if use_network and self.road_network:
                cx, cy = h["geom"].centroid.x, h["geom"].centroid.y
                coverage_geom = self.road_network.get_reachable_area(cx, cy, radius)
                if coverage_geom is None or coverage_geom.is_empty:
                    coverage_geom = h["geom"].buffer(radius)
            else:
                coverage_geom = h["geom"].buffer(radius)

            all_coverages.append(coverage_geom)
            if nivel == 2:
                nivel2_coverage.append(coverage_geom)
            elif nivel >= 3:
                nivel3_coverage.append(coverage_geom)

        covered_union = unary_union(all_coverages) if all_coverages else None
        nivel2_union = unary_union(nivel2_coverage) if nivel2_coverage else None
        nivel3_union = unary_union(nivel3_coverage) if nivel3_coverage else None

        uncovered = None
        if covered_union and not self.urban_boundary.is_empty:
            uncovered = self.urban_boundary.difference(covered_union)
        elif not self.urban_boundary.is_empty:
            uncovered = self.urban_boundary

        urban_covered = None
        if covered_union and not self.urban_boundary.is_empty:
            urban_covered = self.urban_boundary.intersection(covered_union)

        result = {
            "cobertura_total": self._geom_to_geojson_feature(covered_union, {
                "nombre": "Cobertura Hospitalaria Total",
                "descripcion": "Unión de todas las áreas de cobertura hospitalaria (2do y 3er nivel)"
            }),
            "cobertura_nivel2": self._geom_to_geojson_feature(nivel2_union, {
                "nombre": "Cobertura 2do Nivel",
                "descripcion": "Cobertura de hospitales de segundo nivel (3 km radio)"
            }),
            "cobertura_nivel3": self._geom_to_geojson_feature(nivel3_union, {
                "nombre": "Cobertura 3er Nivel",
                "descripcion": "Cobertura de hospitales de tercer nivel (5 km radio)"
            }),
            "areas_descubiertas": self._geom_to_geojson_feature(uncovered, {
                "nombre": "Áreas Descubiertas",
                "descripcion": "Zonas urbanas sin cobertura hospitalaria de 2do o 3er nivel"
            }),
            "cobertura_urbana": self._geom_to_geojson_feature(urban_covered, {
                "nombre": "Área Urbana Cubierta",
                "descripcion": "Porción del área urbana cubierta por la red hospitalaria"
            }),
            "metricas": self._compute_metrics(covered_union, nivel2_union, nivel3_union, uncovered, urban_covered)
        }

        return result

    def _geom_to_geojson_feature(self, geom, properties: dict):
        if geom is None or geom.is_empty:
            return None
        return {
            "type": "Feature",
            "properties": properties,
            "geometry": mapping(geom)
        }

    def _compute_metrics(self, covered_union, nivel2_union, nivel3_union, uncovered, urban_covered):
        urban_area_m2 = self.urban_boundary.area if self.urban_boundary and not self.urban_boundary.is_empty else 0
        covered_area_m2 = covered_union.area if covered_union and not covered_union.is_empty else 0
        uncovered_area_m2 = uncovered.area if uncovered and not uncovered.is_empty else 0
        nivel2_area_m2 = nivel2_union.area if nivel2_union and not nivel2_union.is_empty else 0
        nivel3_area_m2 = nivel3_union.area if nivel3_union and not nivel3_union.is_empty else 0
        urban_covered_area_m2 = urban_covered.area if urban_covered and not urban_covered.is_empty else 0

        return {
            "area_urbana_total_km2": round(urban_area_m2 / 1_000_000, 2),
            "area_cubierta_total_km2": round(covered_area_m2 / 1_000_000, 2),
            "area_descubierta_km2": round(uncovered_area_m2 / 1_000_000, 2),
            "area_cubierta_nivel2_km2": round(nivel2_area_m2 / 1_000_000, 2),
            "area_cubierta_nivel3_km2": round(nivel3_area_m2 / 1_000_000, 2),
            "area_urbana_cubierta_km2": round(urban_covered_area_m2 / 1_000_000, 2),
            "porcentaje_cobertura_urbana": round((urban_covered_area_m2 / urban_area_m2 * 100) if urban_area_m2 > 0 else 0, 1),
            "porcentaje_descubierto_urbano": round((uncovered_area_m2 / urban_area_m2 * 100) if urban_area_m2 > 0 else 0, 1),
            "total_hospitales": len(self.hospitales_utm.get("features", [])),
            "hospitales_nivel2": sum(1 for f in self.hospitales_utm["features"] if f["properties"].get("nivel") == 2),
            "hospitales_nivel3": sum(1 for f in self.hospitales_utm["features"] if f["properties"].get("nivel") >= 3),
        }
