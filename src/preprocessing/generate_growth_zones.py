import json
import os
import sys
import math
from shapely.geometry import shape, mapping, LineString, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

# Add parent directory of 'src' to python path to resolve package imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.spatial.elevation import ElevationModel

def get_fast_elevation(x: float, y: float, tree, contours, k: int = 3) -> float:
    point = Point(x, y)
    # Query contours within 600 meters buffer
    near_indices = tree.query(point.buffer(600.0))
    
    # If no contours found, expand buffer to 2500m
    if len(near_indices) == 0:
        near_indices = tree.query(point.buffer(2500.0))
        
    # If still none, fall back to all contours
    if len(near_indices) == 0:
        near_indices = list(range(len(contours)))
        
    distances = []
    for idx in near_indices:
        geom, elev = contours[idx]
        dist = geom.distance(point)
        distances.append((dist, elev))
        
    distances.sort(key=lambda item: item[0])
    nearest = distances[:k]
    
    if nearest[0][0] < 1.0:
        return nearest[0][1]
        
    weights_sum = 0.0
    weighted_elev_sum = 0.0
    for dist, elev in nearest:
        w = 1.0 / (dist ** 2 + 1e-9)
        weights_sum += w
        weighted_elev_sum += elev * w
        
    return weighted_elev_sum / weights_sum

def get_fast_slope(x: float, y: float, tree, contours, step: float = 15.0) -> float:
    z_e = get_fast_elevation(x + step, y, tree, contours)
    z_w = get_fast_elevation(x - step, y, tree, contours)
    z_n = get_fast_elevation(x, y + step, tree, contours)
    z_s = get_fast_elevation(x, y - step, tree, contours)
    
    dz_dx = (z_e - z_w) / (2.0 * step)
    dz_dy = (z_n - z_s) / (2.0 * step)
    
    slope_magnitude = math.sqrt(dz_dx**2 + dz_dy**2)
    return slope_magnitude * 100.0

def main():
    print("Iniciando análisis geoespacial de alta resolución para la periferia de Sucre...")
    
    # Paths
    distritos_path = "geojson/distritos_sucre.geojson"
    
    if not os.path.exists(distritos_path):
        print(f"Error: No se encontró el archivo de distritos en {distritos_path}")
        sys.exit(1)
        
    with open(distritos_path, "r", encoding="utf-8") as f:
        distritos_data = json.load(f)
        
    # Parse district shapes
    districts = {}
    for feature in distritos_data["features"]:
        props = feature["properties"]
        cod = props.get("COD")
        geom = shape(feature["geometry"])
        districts[cod] = geom
        
    # Total consolidated urban boundaries (inside districts)
    total_districts = unary_union(list(districts.values()))
    
    # Extended Quirpinchaca River centerline in UTM 20S
    river_coords = [
        (254000, 7886000), 
        (257500, 7889500), 
        (258800, 7891200), 
        (260200, 7893000), 
        (261500, 7894500), 
        (262800, 7896500),
        (265000, 7899000)
    ]
    river_line = LineString(river_coords)
    
    # Initialize elevation model
    elevation_model = ElevationModel.get_instance()
    
    # Prepare spatial index for fast topography query
    print("Construyendo índice espacial R-Tree para curvas de nivel...")
    contours_list = elevation_model.contours
    contours_geoms = [geom for geom, elev in contours_list]
    tree = STRtree(contours_geoms)
    
    # Define extended bounding box (3km padding around Sucre's urban districts)
    min_x, max_x = 252500, 268500
    min_y, max_y = 7884500, 7901000
    envelope = box(min_x, min_y, max_x, max_y)
    
    # Grid cell size in meters
    step = 100
    
    # Defining scenarios and their respective slope limits
    scenarios = {
        "conservador": 10.0,
        "moderado": 15.0,
        "expansivo": 25.0
    }
    
    recommended_boxes = {scen: [] for scen in scenarios}
    restricted_boxes = {scen: [] for scen in scenarios}
    
    cols = list(range(min_x, max_x, step))
    rows = list(range(min_y, max_y, step))
    total_cells = len(cols) * len(rows)
    print(f"Evaluando {total_cells} celdas periféricas para 3 escenarios con paso de {step}m...")
    
    for i, x in enumerate(cols):
        for y in rows:
            # Cell center
            cx = x + step / 2
            cy = y + step / 2
            center_pt = Point(cx, cy)
            
            # Skip if inside consolidated districts
            if total_districts.contains(center_pt):
                continue
                
            cell_box = box(x, y, x + step, y + step)
            
            # Fast query using R-tree indexed functions
            slope = get_fast_slope(cx, cy, tree, contours_list)
            dist_to_river = river_line.distance(center_pt)
            
            for scen, limit in scenarios.items():
                if slope >= limit or dist_to_river <= 150.0:
                    restricted_boxes[scen].append(cell_box)
                else:
                    recommended_boxes[scen].append(cell_box)
                
        if (i + 1) % 20 == 0 or (i + 1) == len(cols):
            print(f"Progreso: {min(100, int((i + 1) / len(cols) * 100))}%...")
            
    print("Realizando unión espacial de celdas y exportación de archivos por escenario...")
    
    for scen, limit in scenarios.items():
        growth_final = unary_union(recommended_boxes[scen]) if recommended_boxes[scen] else Point(0,0).buffer(0)
        restricted_final = unary_union(restricted_boxes[scen]) if restricted_boxes[scen] else Point(0,0).buffer(0)
        
        # Clean boundaries: subtract district shapes again to prevent bleeding
        growth_final = growth_final.difference(total_districts)
        restricted_final = restricted_final.difference(total_districts)
        
        # Clip to envelope
        growth_final = growth_final.intersection(envelope)
        restricted_final = restricted_final.intersection(envelope)
        
        # Scenario descriptions
        if scen == "conservador":
            growth_desc = "Áreas recomendadas para la expansión urbana planificada en terrenos con pendientes muy suaves (< 10%) y sin riesgos hidráulicos."
            restricted_desc = "Áreas restringidas debido a pendientes de moderadas a empinadas (>= 10%) o cercanía al río Quirpinchaca (inundabilidad)."
        elif scen == "moderado":
            growth_desc = "Áreas recomendadas para el crecimiento ordenado y expansión en terrenos con pendientes estándar (< 15%) y sin riesgos hidráulicos."
            restricted_desc = "Áreas restringidas debido a pendientes pronunciadas (>= 15%) o cercanía al río Quirpinchaca (inundabilidad)."
        else: # expansivo
            growth_desc = "Escenario expansivo que tolera laderas con pendientes moderadas a pronunciadas de hasta el 25% para el crecimiento urbano."
            restricted_desc = "Áreas restringidas únicamente por pendientes críticas (>= 25%) o cercanía al río Quirpinchaca (inundabilidad)."
            
        # Save restricted GeoJSON
        scen_restricted_path = f"geojson/zonas_no_recomendadas_{scen}.geojson"
        restricted_geojson = {
            "type": "FeatureCollection",
            "name": f"zonas_no_recomendadas_{scen}",
            "crs": distritos_data["crs"],
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "id": 101,
                        "nombre": f"Periferia Restringida ({scen.capitalize()})",
                        "descripcion": restricted_desc
                    },
                    "geometry": mapping(restricted_final)
                }
            ]
        }
        with open(scen_restricted_path, "w", encoding="utf-8") as f:
            json.dump(restricted_geojson, f, indent=2)
            
        # Save growth GeoJSON
        scen_growth_path = f"geojson/zonas_crecimiento_{scen}.geojson"
        growth_geojson = {
            "type": "FeatureCollection",
            "name": f"zonas_crecimiento_{scen}",
            "crs": distritos_data["crs"],
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "id": 201,
                        "nombre": f"Periferia de Expansión ({scen.capitalize()})",
                        "descripcion": growth_desc
                    },
                    "geometry": mapping(growth_final)
                }
            ]
        }
        with open(scen_growth_path, "w", encoding="utf-8") as f:
            json.dump(growth_geojson, f, indent=2)
            
        # Legacy paths for backward compatibility (defaults to moderado)
        if scen == "moderado":
            with open("geojson/zonas_no_recomendadas.geojson", "w", encoding="utf-8") as f:
                json.dump(restricted_geojson, f, indent=2)
            with open("geojson/zonas_crecimiento.geojson", "w", encoding="utf-8") as f:
                json.dump(growth_geojson, f, indent=2)
                
    print("¡Proceso de generación espacial de todos los escenarios finalizado con éxito!")

if __name__ == "__main__":
    main()
