import json
import os

MAIN_HIGHWAYS = {"motorway", "trunk", "primary", "secondary", "tertiary",
                 "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}
ALL_DRIVABLE = MAIN_HIGHWAYS | {"residential", "living_street", "unclassified", "service"}

SUCRE_BBOX = {
    "min_lon": -65.36, "max_lon": -65.16,
    "min_lat": -19.12, "max_lat": -18.96
}

def extract_roads(input_path: str, output_main_path: str, output_all_path: str = None):
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    main_roads = []
    all_roads = []

    for feat in features:
        props = feat.get("properties", {})
        highway = props.get("highway")
        if not highway:
            continue
        geom = feat.get("geometry")
        if not geom or geom.get("type") not in ("LineString",):
            continue

        coords = geom.get("coordinates", [])
        if not coords:
            continue

        def in_bbox(c):
            return (SUCRE_BBOX["min_lon"] <= c[0] <= SUCRE_BBOX["max_lon"]
                    and SUCRE_BBOX["min_lat"] <= c[1] <= SUCRE_BBOX["max_lat"])

        if not all(in_bbox(c) for c in coords):
            coords = [c for c in coords if in_bbox(c)]
            if len(coords) < 2:
                continue

        name = props.get("name", "")
        road_feature = {
            "type": "Feature",
            "properties": {
                "highway": highway,
                "name": name,
                "oneway": props.get("oneway", "no"),
                "surface": props.get("surface", ""),
                "maxspeed": props.get("maxspeed", ""),
                "width": props.get("width", ""),
                "lanes": props.get("lanes", "")
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }

        if highway in ALL_DRIVABLE:
            all_roads.append(road_feature)
        if highway in MAIN_HIGHWAYS:
            main_roads.append(road_feature)

    main_fc = {
        "type": "FeatureCollection",
        "name": "vias_principales_sucre_osm",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": main_roads
    }

    os.makedirs(os.path.dirname(output_main_path), exist_ok=True)
    with open(output_main_path, "w", encoding="utf-8") as f:
        json.dump(main_fc, f, ensure_ascii=False)
    print(f"Vías principales: {len(main_roads)} guardadas en {output_main_path}")

    if output_all_path:
        all_fc = {
            "type": "FeatureCollection",
            "name": "vias_completas_sucre_osm",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": all_roads
        }
        with open(output_all_path, "w", encoding="utf-8") as f:
            json.dump(all_fc, f, ensure_ascii=False)
        print(f"Vías totales (todas las transitables): {len(all_roads)} guardadas en {output_all_path}")

if __name__ == "__main__":
    extract_roads(
        input_path="/tmp/sucre_full.geojson",
        output_main_path="geojson/vias_sucre.geojson",
        output_all_path="geojson/vias_completas.geojson"
    )
