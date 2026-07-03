import json
from collections import defaultdict
from src.preprocessing.generate_mock_data import DISTRICT_PROFILES

BEDS_PER_1000 = 2.0
PROJECTION_YEARS = [5, 10, 15, 20]

class DeficitAnalyzer:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        with open("geojson/hospitales_sucre.geojson", encoding="utf-8") as f:
            self.hospitales = json.load(f)

    def get_deficit(self) -> dict:
        beds_by_district = defaultdict(int)
        hospitals_by_district = defaultdict(list)
        total_beds = 0
        total_hospitals = 0
        nivel_counts = defaultdict(int)

        for feat in self.hospitales.get("features", []):
            props = feat["properties"]
            distrito = props.get("distrito", "")
            camas = props.get("camas", 0)
            nivel = props.get("nivel", 0)
            nombre = props.get("nombre", "Sin nombre")

            beds_by_district[distrito] += camas
            hospitals_by_district[distrito].append({
                "nombre": nombre, "camas": camas, "nivel": nivel
            })
            total_beds += camas
            total_hospitals += 1
            nivel_counts[nivel] += 1

        total_population = sum(
            p["poblacion_estimada"] for p in DISTRICT_PROFILES.values()
        )
        ratio_actual = round(total_beds / total_population * 1000, 2) if total_population else 0

        distritos = []
        total_deficit = 0
        for cod, profile in DISTRICT_PROFILES.items():
            pop = profile["poblacion_estimada"]
            crecimiento = profile["crecimiento_anual"]
            camas_actuales = beds_by_district.get(cod, 0)

            camas_recomendadas = max(1, round(pop * BEDS_PER_1000 / 1000))
            deficit = camas_recomendadas - camas_actuales

            proyecciones = {}
            for years in PROJECTION_YEARS:
                pop_futura = int(pop * (1 + crecimiento) ** years)
                camas_necesarias = max(1, round(pop_futura * BEDS_PER_1000 / 1000))
                deficit_futuro = camas_necesarias - camas_actuales
                proyecciones[f"{years}_años"] = {
                    "poblacion_proyectada": pop_futura,
                    "camas_necesarias": camas_necesarias,
                    "deficit_proyectado": max(0, deficit_futuro)
                }

            distritos.append({
                "codigo": cod,
                "nombre": profile["nombre"],
                "poblacion": pop,
                "crecimiento_anual": crecimiento,
                "camas_actuales": camas_actuales,
                "camas_recomendadas": camas_recomendadas,
                "deficit_actual": max(0, deficit),
                "superavit_actual": max(0, -deficit),
                "ratio_camas_1000": round(camas_actuales / pop * 1000, 2) if pop else 0,
                "hospitales": hospitals_by_district.get(cod, []),
                "proyecciones": proyecciones
            })
            total_deficit += max(0, deficit)

        return {
            "resumen": {
                "total_hospitales": total_hospitals,
                "total_camas": total_beds,
                "poblacion_total": total_population,
                "ratio_camas_1000_actual": ratio_actual,
                "ratio_recomendado": BEDS_PER_1000,
                "deficit_total_actual": total_deficit,
                "hospitales_3er_nivel": nivel_counts.get(3, 0),
                "hospitales_2do_nivel": nivel_counts.get(2, 0),
                "hospitales_1er_nivel": nivel_counts.get(1, 0)
            },
            "distritos": distritos
        }
