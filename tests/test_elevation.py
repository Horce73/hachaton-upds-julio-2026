import unittest
import sys
import os

# Include src directory in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.spatial.elevation import ElevationModel
from src.spatial.projection import to_utm

class TestElevation(unittest.TestCase):
    def test_elevation_and_slope(self):
        # Initialize the model with the actual GeoJSON file
        model = ElevationModel.get_instance("geojson/topografia_sucre.geojson")
        
        # Test coordinate in Sucre: Plaza 25 de Mayo (-65.2594, -19.0476)
        x, y = to_utm(-65.2594, -19.0476)
        
        # Interpolate elevation
        elevation = model.get_elevation(x, y)
        print(f"\n[Test] Elevación interpolada en Plaza Central: {elevation:.2f} metros")
        
        # Validate elevation is within reasonable bounds for Sucre (2500m - 3000m for central city)
        self.assertTrue(2500.0 < elevation < 3000.0)
        
        # Calculate slope percentage
        slope = model.get_slope(x, y)
        print(f"[Test] Pendiente aproximada en Plaza Central: {slope:.2f}%")
        
        # The central square of Sucre is relatively flat, slope should be low (e.g. < 10%)
        self.assertTrue(0.0 <= slope < 15.0)

if __name__ == '__main__':
    unittest.main()
