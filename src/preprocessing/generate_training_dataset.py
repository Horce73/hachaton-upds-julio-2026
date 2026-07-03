import os
import sys
import json
import random
import csv
from shapely.geometry import shape, Point

# Include src directory in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.spatial.projection import to_wgs84
from src.models.mcda import MCDAModel
from src.preprocessing.generate_mock_data import DISTRICT_PROFILES

def main():
    print("Iniciando generación de dataset de entrenamiento...")
    
    # Load MCDA model instance
    mcda = MCDAModel.get_instance()
    
    # Get bounding box of all distritos in UTM 20S
    min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
    for geom, _, _ in mcda.district_geoms:
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        min_x = min(min_x, bounds[0])
        min_y = min(min_y, bounds[1])
        max_x = max(max_x, bounds[2])
        max_y = max(max_y, bounds[3])
        
    print(f"Límites UTM Sucre: X=[{min_x:.0f}, {max_x:.0f}], Y=[{min_y:.0f}, {max_y:.0f}]")
    
    # Number of training samples to collect
    n_samples = 5000
    samples = []
    
    # Seed for reproducibility
    random.seed(42)
    
    collected = 0
    attempts = 0
    
    land_uses = [
        "Residencial de Expansión", 
        "Residencial Consolidado", 
        "Mixto Comercial", 
        "Reserva Ecológica", 
        "Industrial"
    ]
    land_use_weights = [0.35, 0.35, 0.15, 0.08, 0.07]
    
    while collected < n_samples:
        attempts += 1
        if attempts > 100000 and collected == 0:
            print("Error: No se están encontrando puntos válidos dentro de los distritos.")
            break
            
        # 1. Sample random coordinate in UTM box
        x = random.uniform(min_x, max_x)
        y = random.uniform(min_y, max_y)
        pt = Point(x, y)
        
        # 2. Check if point is inside any district polygon
        inside = False
        district_cod = None
        district_profile = None
        for geom, cod, name in mcda.district_geoms:
            if geom.contains(pt):
                inside = True
                district_cod = cod
                district_profile = DISTRICT_PROFILES.get(cod)
                break
                
        if not inside:
            continue
            
        # Convert UTM to WGS84 for evaluate_parcel interface
        lon, lat = to_wgs84(x, y)
        
        # 3. Generate random parcel properties
        properties = {
            "agua": random.random() < 0.85,
            "electricidad": random.random() < 0.95,
            "alcantarillado": random.random() < 0.75,
            "uso_suelo": random.choices(land_uses, weights=land_use_weights, k=1)[0],
            "area_m2": random.uniform(3000.0, 20000.0),
            "patrimonial": random.random() < 0.08,
            "industrial_incompatible": random.random() < 0.05,
            "cerca_rio": random.random() < 0.12
        }
        
        # 4. Evaluate using the MCDA expert model
        geom_wgs84 = {"type": "Point", "coordinates": [lon, lat]}
        res = mcda.evaluate_parcel(geom_wgs84, properties)
        
        # Extract features and target values
        row = {
            "lon": lon,
            "lat": lat,
            "elevacion": res["elevacion_m"],
            "pendiente": res["pendiente_pct"],
            "distancia_hospital": res["distancia_hosp_m"],
            "distancia_via": res["distancia_vias_m"],
            "poblacion_distrito": district_profile["poblacion_estimada"] if district_profile else 0,
            "crecimiento_distrito": district_profile["crecimiento_anual"] if district_profile else 0.0,
            "agua": 1 if properties["agua"] else 0,
            "electricidad": 1 if properties["electricidad"] else 0,
            "alcantarillado": 1 if properties["alcantarillado"] else 0,
            "area_m2": properties["area_m2"],
            "patrimonial": 1 if properties["patrimonial"] or district_cod == "D-1" else 0,
            "industrial_incompatible": 1 if properties["industrial_incompatible"] or properties["uso_suelo"] == "Industrial" else 0,
            "cerca_rio": 1 if properties["cerca_rio"] else 0,
            "uso_suelo_compatible": 1 if "expansión" in properties["uso_suelo"].lower() or "reserva" in properties["uso_suelo"].lower() or "mixto" in properties["uso_suelo"].lower() else (0.8 if "residencial" in properties["uso_suelo"].lower() else 0.5),
            # Targets
            "iat": res["iat"],
            "apto": 1 if res["apto"] else 0
        }
        
        samples.append(row)
        collected += 1
        
        if collected % 1000 == 0:
            print(f"Muestreados: {collected}/{n_samples} puntos...")
            
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Save to CSV
    csv_file = "data/dataset_entrenamiento.csv"
    headers = list(samples[0].keys())
    
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(samples)
        
    print(f"¡Dataset de entrenamiento generado con éxito en {csv_file}!")
    print(f"Número total de intentos: {attempts}. Tasa de aceptación: {n_samples/attempts*100:.1f}%")

if __name__ == "__main__":
    main()
