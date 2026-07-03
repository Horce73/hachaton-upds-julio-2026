import unittest
import sys
import os

# Include src directory in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.spatial.projection import to_wgs84, to_utm, reproject_geojson

class TestProjection(unittest.TestCase):
    def test_coordinate_conversion(self):
        # Lat/Lon for Plaza 25 de Mayo (Sucre, Bolivia)
        lon_target, lat_target = -65.2594, -19.0476
        
        # Convert to UTM Zone 20S
        x, y = to_utm(lon_target, lat_target)
        
        # Convert back to WGS84
        lon_back, lat_back = to_wgs84(x, y)
        
        # Validate values are extremely close (sub-millimeter precision)
        self.assertAlmostEqual(lon_target, lon_back, places=5)
        self.assertAlmostEqual(lat_target, lat_back, places=5)

    def test_geojson_reprojection(self):
        # Mock Feature Collection in UTM 20S (meters)
        geojson_utm = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:EPSG::32720"}
            },
            "features": [
                {
                    "type": "Feature",
                    "properties": {"id": 101},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [262093.4935178175, 7892286.269371505]
                    }
                }
            ]
        }
        
        # Reproject to WGS84 (Lat/Lon)
        geojson_wgs = reproject_geojson(geojson_utm, to_crs="epsg:4326", from_crs="epsg:32720")
        
        coords = geojson_wgs["features"][0]["geometry"]["coordinates"]
        
        # Expected coordinates: longitude approx -65.260586, latitude approx -19.048388
        self.assertAlmostEqual(coords[0], -65.260586, places=5)
        self.assertAlmostEqual(coords[1], -19.048388, places=5)
        
        # Verify CRS metadata update
        self.assertIn("CRS84", geojson_wgs["crs"]["properties"]["name"])

if __name__ == '__main__':
    unittest.main()
