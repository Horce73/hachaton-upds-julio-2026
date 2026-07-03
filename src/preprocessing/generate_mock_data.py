import json
import os

TOTAL_POPULATION_SUCRE = 296746

# Define demographic and planning profiles for the 5 urban districts of Sucre.
# The population is distributed proportionally to the area of each district
# extracted from geojson/distritos_sucre.geojson.
DISTRICT_BASE_DATA = {
    "D-1": {
        "nombre": "Distrito 1 (Central/Histórico)",
        "crecimiento_anual": 0.005,       # 0.5% (Low growth, consolidated)
        "densidad_hab_km2": 12053,
        "camas_actuales": 340,            # High because of main hospitals (Santa Barbara)
        "servicios_basicos_pct": 0.99,    # 99% coverage
        "compatibilidad_uso": "Zonificación Patrimonial/Residencial Central"
    },
    "D-2": {
        "nombre": "Distrito 2 (Zonas de Consolidación)",
        "crecimiento_anual": 0.018,       # 1.8% (Medium growth)
        "densidad_hab_km2": 7200,
        "camas_actuales": 100,            # Medium (San Pedro Claver)
        "servicios_basicos_pct": 0.92,
        "compatibilidad_uso": "Zonificación Residencial/Comercial Mixto"
    },
    "D-3": {
        "nombre": "Distrito 3 (Expansión Norte/Industrial)",
        "crecimiento_anual": 0.045,       # 4.5% (High growth)
        "densidad_hab_km2": 4100,
        "camas_actuales": 120,            # Medium (Lajastambo)
        "servicios_basicos_pct": 0.81,
        "compatibilidad_uso": "Zonificación Industrial/Residencial de Expansión"
    },
    "D-4": {
        "nombre": "Distrito 4 (Expansión Oeste)",
        "crecimiento_anual": 0.032,       # 3.2% (Medium-high growth)
        "densidad_hab_km2": 3200,
        "camas_actuales": 0,              # No second/third level hospitals
        "servicios_basicos_pct": 0.78,
        "compatibilidad_uso": "Zonificación Residencial/Agrícola de Reserva"
    },
    "D-5": {
        "nombre": "Distrito 5 (Expansión Sur/Cochabambita)",
        "crecimiento_anual": 0.050,       # 5.0% (Critical expansion)
        "densidad_hab_km2": 2800,
        "camas_actuales": 30,             # Critically low coverage
        "servicios_basicos_pct": 0.72,
        "compatibilidad_uso": "Zonificación Residencial Semiurbana/Expansión"
    }
}

DISTRICT_GEOJSON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "geojson", "distritos_sucre.geojson")
)


def build_district_profiles() -> dict:
    with open(DISTRICT_GEOJSON_PATH, encoding="utf-8") as f:
        district_geojson = json.load(f)

    district_areas = {}
    for feature in district_geojson.get("features", []):
        props = feature.get("properties", {})
        cod = props.get("COD")
        area_km2 = props.get("Area_km2")
        if cod and area_km2 is not None:
            district_areas[cod] = float(area_km2)

    total_area = sum(district_areas.values())
    if total_area <= 0:
        raise ValueError("No se pudieron obtener las áreas de los distritos para distribuir la población")

    allocations = []
    for cod, base_profile in DISTRICT_BASE_DATA.items():
        raw_population = TOTAL_POPULATION_SUCRE * district_areas.get(cod, 0.0) / total_area
        integer_population = int(raw_population)
        allocations.append({
            "cod": cod,
            "raw_population": raw_population,
            "population": integer_population,
            "fraction": raw_population - integer_population,
            "profile": base_profile,
        })

    assigned_population = sum(item["population"] for item in allocations)
    remaining = TOTAL_POPULATION_SUCRE - assigned_population
    if remaining > 0:
        allocations.sort(key=lambda item: (-item["fraction"], item["cod"]))
        for index in range(remaining):
            allocations[index]["population"] += 1

    return {
        item["cod"]: {
            **item["profile"],
            "poblacion_estimada": item["population"],
        }
        for item in sorted(allocations, key=lambda item: item["cod"])
    }


DISTRICT_PROFILES = build_district_profiles()

def generate_hospitals():
    """Generates the geojson file for existing hospitals."""
    geojson = {
        "type": "FeatureCollection",
        "name": "hospitales_existentes_sucre",
        "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": 1,
                    "nombre": "Hospital Santa Bárbara",
                    "nivel": 3,
                    "camas": 250,
                    "distrito": "D-1",
                    "tipo": "Público General"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-65.26164, -19.04478]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 2,
                    "nombre": "Hospital de Tercer Nivel (Lajastambo)",
                    "nivel": 3,
                    "camas": 200,
                    "distrito": "D-3",
                    "tipo": "Público General"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-65.29500, -19.01300]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 3,
                    "nombre": "Hospital Jaime Mendoza",
                    "nivel": 3,
                    "camas": 180,
                    "distrito": "D-1",
                    "tipo": "Seguridad Social (CNS)"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-65.25940, -19.04846]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 4,
                    "nombre": "Instituto de Gastroenterología Boliviano-Japonés",
                    "nivel": 3,
                    "camas": 100,
                    "distrito": "D-1",
                    "tipo": "Público Especializado"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-65.25400, -19.04400]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 5,
                    "nombre": "Hospital Gíneco-Obstétrico Jaime Sánchez",
                    "nivel": 3,
                    "camas": 90,
                    "distrito": "D-1",
                    "tipo": "Público Especializado"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-65.2558, -19.0515]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 6,
                    "nombre": "Hospital San Pedro Claver",
                    "nivel": 2,
                    "camas": 100,
                    "distrito": "D-2",
                    "tipo": "Público General"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-65.2478, -19.0315]
                }
            }
        ]
    }
    return geojson

def generate_vias():
    """Generates geojson file for main road network."""
    geojson = {
        "type": "FeatureCollection",
        "name": "vias_principales_sucre",
        "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
        "features": [
            {
                "type": "Feature",
                "properties": { "id": 1, "nombre": "Avenida Circunvalación", "tipo": "Troncal" },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-65.2980, -19.0150],
                        [-65.2850, -19.0250],
                        [-65.2750, -19.0400],
                        [-65.2650, -19.0550],
                        [-65.2450, -19.0700]
                    ]
                }
            },
            {
                "type": "Feature",
                "properties": { "id": 2, "nombre": "Avenida Jaime Mendoza", "tipo": "Arteria" },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-65.2450, -19.0200],
                        [-65.2510, -19.0350],
                        [-65.2570, -19.0480],
                        [-65.2590, -19.0520],
                        [-65.2450, -19.0720]
                    ]
                }
            },
            {
                "type": "Feature",
                "properties": { "id": 3, "nombre": "Avenida Ostria Gutiérrez", "tipo": "Arteria" },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-65.2440, -19.0280],
                        [-65.2500, -19.0340],
                        [-65.2540, -19.0380]
                    ]
                }
            }
        ]
    }
    return geojson

def generate_parcels():
    """Generates geojson file for candidate parcels/terrenos."""
    geojson = {
        "type": "FeatureCollection",
        "name": "terrenos_candidatos_sucre",
        "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": 1,
                    "nombre": "Terreno Norte - Lajastambo",
                    "zona": "Lajastambo Alto (D-3)",
                    "agua": True, "electricidad": True, "alcantarillado": True,
                    "uso_suelo": "Residencial de Expansión",
                    "area_m2": 12500,
                    "patrimonial": False, "industrial_incompatible": False, "cerca_rio": False
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-65.2890, -19.0170],
                        [-65.2875, -19.0170],
                        [-65.2875, -19.0180],
                        [-65.2890, -19.0180],
                        [-65.2890, -19.0170]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 2,
                    "nombre": "Terreno Sur - cochabambita",
                    "zona": "Barrio Cochabambita (D-5)",
                    "agua": True, "electricidad": True, "alcantarillado": False,
                    "uso_suelo": "Expansión Urbana",
                    "area_m2": 15000,
                    "patrimonial": False, "industrial_incompatible": False, "cerca_rio": False
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-65.2390, -19.0690],
                        [-65.2370, -19.0690],
                        [-65.2370, -19.0700],
                        [-65.2390, -19.0700],
                        [-65.2390, -19.0690]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 3,
                    "nombre": "Terreno Oeste - Zona Pendiente",
                    "zona": "Cerro Sica Sica (D-4)",
                    "agua": True, "electricidad": True, "alcantarillado": True,
                    "uso_suelo": "Residencial",
                    "area_m2": 8200,
                    "patrimonial": False, "industrial_incompatible": False, "cerca_rio": False
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-65.2760, -19.0590],
                        [-65.2745, -19.0590],
                        [-65.2745, -19.0600],
                        [-65.2760, -19.0600],
                        [-65.2760, -19.0590]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 4,
                    "nombre": "Terreno Central - Recoleta",
                    "zona": "La Recoleta (D-1)",
                    "agua": True, "electricidad": True, "alcantarillado": True,
                    "uso_suelo": "Patrimonial Histórico",
                    "area_m2": 6000,
                    "patrimonial": True, "industrial_incompatible": False, "cerca_rio": False
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-65.2610, -19.0465],
                        [-65.2595, -19.0465],
                        [-65.2595, -19.0475],
                        [-65.2610, -19.0475],
                        [-65.2610, -19.0465]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 5,
                    "nombre": "Terreno Este - Zona Río Quirpinchaca",
                    "zona": "Cerca Río Quirpinchaca (D-2)",
                    "agua": True, "electricidad": True, "alcantarillado": True,
                    "uso_suelo": "Residencial Mixto",
                    "area_m2": 9500,
                    "patrimonial": False, "industrial_incompatible": False, "cerca_rio": True
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-65.2490, -19.0340],
                        [-65.2475, -19.0340],
                        [-65.2475, -19.0350],
                        [-65.2490, -19.0350],
                        [-65.2490, -19.0340]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": 6,
                    "nombre": "Terreno Norte - Excelente Aptitud",
                    "zona": "Barrio Lindo (D-3)",
                    "agua": True, "electricidad": True, "alcantarillado": True,
                    "uso_suelo": "Residencial de Expansión",
                    "area_m2": 18000,
                    "patrimonial": False, "industrial_incompatible": False, "cerca_rio": False
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-65.2860, -19.0210],
                        [-65.2840, -19.0210],
                        [-65.2840, -19.0225],
                        [-65.2860, -19.0225],
                        [-65.2860, -19.0210]
                    ]]
                }
            }
        ]
    }
    return geojson

def main():
    os.makedirs("geojson", exist_ok=True)
    
    # Save hospitals
    with open("geojson/hospitales_sucre.geojson", "w", encoding="utf-8") as f:
        json.dump(generate_hospitals(), f, ensure_ascii=False, indent=2)
    print("Generated: geojson/hospitales_sucre.geojson")
    
    # Save roads
    with open("geojson/vias_sucre.geojson", "w", encoding="utf-8") as f:
        json.dump(generate_vias(), f, ensure_ascii=False, indent=2)
    print("Generated: geojson/vias_sucre.geojson")
    
    # Save parcels
    with open("geojson/terrenos_candidatos.geojson", "w", encoding="utf-8") as f:
        json.dump(generate_parcels(), f, ensure_ascii=False, indent=2)
    print("Generated: geojson/terrenos_candidatos.geojson")

if __name__ == "__main__":
    main()
