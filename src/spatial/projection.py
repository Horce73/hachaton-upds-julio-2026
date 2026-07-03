from pyproj import Transformer

# Create standard transformers
# always_xy=True ensures the coordinate order is always (longitude/x, latitude/y) or (Easting, Northing)
# instead of the default pyproj order which matches standard axis order (lat, lon)
_to_wgs84_transformer = Transformer.from_crs("epsg:32720", "epsg:4326", always_xy=True)
_to_utm_transformer = Transformer.from_crs("epsg:4326", "epsg:32720", always_xy=True)

def to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """
    Transforms UTM Zone 20S coordinates (Easting, Northing) to WGS84 coordinates (Longitude, Latitude).
    """
    lon, lat = _to_wgs84_transformer.transform(easting, northing)
    return lon, lat

def to_utm(longitude: float, latitude: float) -> tuple[float, float]:
    """
    Transforms WGS84 coordinates (Longitude, Latitude) to UTM Zone 20S coordinates (Easting, Northing).
    """
    x, y = _to_utm_transformer.transform(longitude, latitude)
    return x, y

def reproject_coordinates(coords, transformer) -> list:
    """
    Recursively traverses coordinates lists to reproject them.
    Supports Point, LineString, Polygon, MultiPolygon formats.
    """
    if not isinstance(coords, list):
        return coords
    
    # If it is a coordinate pair [x, y]
    if len(coords) == 2 and not isinstance(coords[0], list):
        x, y = coords
        tx, ty = transformer.transform(x, y)
        return [tx, ty]
    
    # Otherwise recurse into nested lists
    return [reproject_coordinates(sub, transformer) for sub in coords]

def reproject_geojson(geojson: dict, to_crs: str = "epsg:4326", from_crs: str = "epsg:32720") -> dict:
    """
    Reprojects an entire GeoJSON dict (FeatureCollection, Feature, or Geometry) from from_crs to to_crs.
    """
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    reprojected = geojson.copy()
    
    if geojson.get("type") == "FeatureCollection":
        features = []
        for feature in geojson.get("features", []):
            new_feature = feature.copy()
            if "geometry" in feature and feature["geometry"]:
                geom = feature["geometry"].copy()
                geom["coordinates"] = reproject_coordinates(geom["coordinates"], transformer)
                new_feature["geometry"] = geom
            features.append(new_feature)
        reprojected["features"] = features
        # Update CRS metadata if present
        if "crs" in reprojected:
            reprojected["crs"] = {
                "type": "name",
                "properties": {
                    "name": f"urn:ogc:def:crs:OGC:1.3:CRS84" if to_crs.lower() == "epsg:4326" else f"urn:ogc:def:crs:EPSG::{to_crs.split(':')[-1]}"
                }
            }
            
    elif geojson.get("type") == "Feature":
        if "geometry" in reprojected and reprojected["geometry"]:
            geom = reprojected["geometry"].copy()
            geom["coordinates"] = reprojected_coordinates(geom["coordinates"], transformer)
            reprojected["geometry"] = geom
            
    elif "coordinates" in geojson:
        reprojected["coordinates"] = reproject_coordinates(geojson["coordinates"], transformer)
        
    return reprojected
