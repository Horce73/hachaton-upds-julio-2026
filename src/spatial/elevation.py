import json
import math
from shapely.geometry import shape, Point
from src.spatial.projection import reproject_geojson

class ElevationModel:
    _instance = None

    @classmethod
    def get_instance(cls, geojson_path: str = "geojson/topografia_sucre.geojson"):
        """
        Singleton access to prevent loading and reprojecting the contours repeatedly.
        """
        if cls._instance is None:
            cls._instance = cls(geojson_path)
        return cls._instance

    def __init__(self, geojson_path: str = "geojson/topografia_sucre.geojson"):
        # Load the WGS84 GeoJSON
        with open(geojson_path) as f:
            topo_wgs84 = json.load(f)
        
        # Reproject to UTM Zone 20S (meters) so elevation and horizontal coordinates match units
        self.topo_utm = reproject_geojson(topo_wgs84, to_crs="epsg:32720", from_crs="epsg:4326")
        
        # Parse features as Shapely geometries and cache their elevations
        self.contours = []
        for feature in self.topo_utm.get("features", []):
            geom = shape(feature["geometry"])
            elev = feature["properties"]["ELEV"]
            self.contours.append((geom, elev))
            
        if not self.contours:
            raise ValueError(f"No contour features found in {geojson_path}")

    def get_elevation(self, x: float, y: float, k: int = 3) -> float:
        """
        Interpolates the elevation at (x, y) in UTM 20S using Inverse Distance Weighting (IDW)
        to the k nearest contour lines.
        """
        point = Point(x, y)
        
        # Calculate distance to all contour lines
        distances = []
        for geom, elev in self.contours:
            dist = geom.distance(point)
            distances.append((dist, elev))
        
        # Sort by distance (ascending)
        distances.sort(key=lambda item: item[0])
        
        # Take k nearest
        nearest = distances[:k]
        
        # If the closest contour is extremely close (under 1 meter), return it directly
        if nearest[0][0] < 1.0:
            return nearest[0][1]
        
        # Apply Inverse Distance Weighting (IDW) with power = 2
        weights_sum = 0.0
        weighted_elev_sum = 0.0
        for dist, elev in nearest:
            # Avoid division by zero (already caught by exact match above, but for safety)
            w = 1.0 / (dist ** 2 + 1e-9)
            weights_sum += w
            weighted_elev_sum += elev * w
            
        return weighted_elev_sum / weights_sum

    def get_slope(self, x: float, y: float, step: float = 15.0) -> float:
        """
        Calculates the local slope percentage at (x, y) in UTM 20S using central finite differences.
        Uses a step size in meters.
        """
        # Fetch elevations at four cardinal directions
        z_e = self.get_elevation(x + step, y)
        z_w = self.get_elevation(x - step, y)
        z_n = self.get_elevation(x, y + step)
        z_s = self.get_elevation(x, y - step)
        
        # Central difference gradients
        dz_dx = (z_e - z_w) / (2.0 * step)
        dz_dy = (z_n - z_s) / (2.0 * step)
        
        # Calculate slope magnitude (rise/run)
        slope_magnitude = math.sqrt(dz_dx**2 + dz_dy**2)
        
        # Convert to percentage
        return slope_magnitude * 100.0
