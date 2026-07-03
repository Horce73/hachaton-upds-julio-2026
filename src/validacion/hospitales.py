import json
from shapely.geometry import shape, Point
from src.spatial.projection import reproject_geojson, to_utm

SUCRE_BBOX = {
    "min_lon": -65.36,
    "max_lon": -65.16,
    "min_lat": -19.12,
    "max_lat": -18.96
}

class HospitalValidator:
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

        self.district_polys = []
        for feature in self.distritos_utm.get("features", []):
            geom = shape(feature["geometry"])
            cod = feature["properties"]["COD"]
            name = feature["properties"]["Distritos"]
            self.district_polys.append((geom, cod, name))

    def validar_todos(self) -> dict:
        resultados = []
        utm_features = self.hospitales_utm.get("features", [])
        wgs84_features = self.hospitales_wgs84.get("features", [])

        for i, (feat_utm, feat_wgs84) in enumerate(zip(utm_features, wgs84_features)):
            props = feat_wgs84["properties"]
            coords_wgs84 = feat_wgs84["geometry"]["coordinates"]
            punto_utm = shape(feat_utm["geometry"])

            hospital_id = props.get("id", i + 1)
            nombre = props.get("nombre", f"Hospital #{hospital_id}")
            declared_district = props.get("distrito", "")

            issues = []

            actual_district_cod = None
            actual_district_name = None
            for geom, cod, name in self.district_polys:
                if geom.contains(punto_utm) or geom.intersects(punto_utm):
                    actual_district_cod = cod
                    actual_district_name = name
                    break

            if actual_district_cod is None:
                issues.append({
                    "tipo": "error",
                    "mensaje": f"El hospital '{nombre}' no se encuentra dentro de ningún distrito urbano de Sucre."
                })
            elif actual_district_cod != declared_district:
                issues.append({
                    "tipo": "error",
                    "mensaje": f"El hospital '{nombre}' declara pertenecer al {declared_district} pero su ubicación real cae en {actual_district_cod} ({actual_district_name})."
                })

            lon, lat = coords_wgs84
            if not (SUCRE_BBOX["min_lon"] <= lon <= SUCRE_BBOX["max_lon"]):
                issues.append({
                    "tipo": "error",
                    "mensaje": f"Longitud {lon} fuera del bounding box de Sucre."
                })
            if not (SUCRE_BBOX["min_lat"] <= lat <= SUCRE_BBOX["max_lat"]):
                issues.append({
                    "tipo": "error",
                    "mensaje": f"Latitud {lat} fuera del bounding box de Sucre."
                })

            if not nombre.strip():
                issues.append({
                    "tipo": "warning",
                    "mensaje": "El hospital no tiene nombre asignado."
                })

            if not props.get("nivel"):
                issues.append({
                    "tipo": "warning",
                    "mensaje": f"El hospital '{nombre}' no tiene nivel definido."
                })

            resultados.append({
                "id": hospital_id,
                "nombre": nombre,
                "coordenadas": {"lon": lon, "lat": lat},
                "distrito_declarado": declared_district,
                "distrito_real": actual_district_cod,
                "distrito_real_nombre": actual_district_name,
                "coincide_distrito": actual_district_cod == declared_district if actual_district_cod else False,
                "issues": issues,
                "valido": len([iss for iss in issues if iss["tipo"] == "error"]) == 0
            })

        dupes = self._detectar_duplicados(utm_features, wgs84_features)

        return {
            "total": len(resultados),
            "validos": sum(1 for r in resultados if r["valido"]),
            "con_errores": sum(1 for r in resultados if not r["valido"]),
            "hospitales": resultados,
            "duplicados": dupes
        }

    def _detectar_duplicados(self, utm_features: list, wgs84_features: list) -> list:
        duplicados = []
        puntos = []
        for feat_utm, feat_wgs84 in zip(utm_features, wgs84_features):
            props = feat_wgs84["properties"]
            coords = feat_wgs84["geometry"]["coordinates"]
            punto = shape(feat_utm["geometry"])
            puntos.append({
                "id": props.get("id"),
                "nombre": props.get("nombre", ""),
                "punto_utm": punto,
                "coords_wgs84": coords
            })

        for i in range(len(puntos)):
            for j in range(i + 1, len(puntos)):
                dist = puntos[i]["punto_utm"].distance(puntos[j]["punto_utm"])
                if dist < 200:
                    duplicados.append({
                        "hospital_a": {"id": puntos[i]["id"], "nombre": puntos[i]["nombre"]},
                        "hospital_b": {"id": puntos[j]["id"], "nombre": puntos[j]["nombre"]},
                        "distancia_m": round(dist, 1)
                    })

        return duplicados
