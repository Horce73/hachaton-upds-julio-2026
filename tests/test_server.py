import unittest
import sys
import os
from fastapi.testclient import TestClient

# Include src directory in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.server import app

class TestServer(unittest.TestCase):
    def setUp(self):
        # Create a test client for FastAPI
        self.client = TestClient(app)

    def test_get_distritos(self):
        response = self.client.get("/api/distritos")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertTrue(len(data["features"]) > 0)
        # Check if demographic enrichment properties are present
        feature = data["features"][0]
        self.assertIn("poblacion_estimada", feature["properties"])
        self.assertIn("crecimiento_anual", feature["properties"])

    def test_get_hospitales(self):
        response = self.client.get("/api/hospitales")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertTrue(len(data["features"]) > 0)

    def test_get_vias(self):
        response = self.client.get("/api/vias")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")

    def test_get_topografia(self):
        response = self.client.get("/api/topografia")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")

    def test_get_terrenos(self):
        response = self.client.get("/api/terrenos")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertTrue(len(data["features"]) > 0)
        # Ensure they are pre-evaluated
        props = data["features"][0]["properties"]
        self.assertIn("evaluacion", props)
        self.assertIn("iat", props)

    def test_evaluar_endpoint(self):
        # Test evaluation at Plaza 25 de Mayo (Sucre)
        payload = {
            "geometry": {
                "type": "Point",
                "coordinates": [-65.2594, -19.0476]
            },
            "properties": {
                "agua": True,
                "electricidad": True,
                "alcantarillado": True,
                "uso_suelo": "Residencial de Expansión",
                "area_m2": 12000.0,
                "patrimonial": False,
                "industrial_incompatible": False,
                "cerca_rio": False
            },
            "nombre": "Test Terreno Centro"
        }
        response = self.client.post("/api/evaluar", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn("iat", res)
        self.assertIn("apto", res)
        self.assertIn("explicacion", res)

    def test_evaluar_validation_bounds(self):
        # Test coordinate outside Sucre (e.g. La Paz or USA)
        payload = {
            "geometry": {
                "type": "Point",
                "coordinates": [-68.12, -16.50]  # La Paz coordinates
            },
            "properties": {},
            "nombre": "Fuera de Rango"
        }
        response = self.client.post("/api/evaluar", json=payload)
        # Should return 400 Bad Request due to coordinate validation
        self.assertEqual(response.status_code, 400)
        self.assertIn("fuera de los límites", response.json()["detail"])

    def test_get_zonas_crecimiento(self):
        response = self.client.get("/api/zonas/crecimiento")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertTrue(len(data["features"]) > 0)

    def test_get_zonas_restringidas(self):
        response = self.client.get("/api/zonas/restringidas")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertTrue(len(data["features"]) > 0)

    def test_get_zonas_crecimiento_scenarios(self):
        for scen in ["conservador", "moderado", "expansivo"]:
            response = self.client.get(f"/api/zonas/crecimiento?escenario={scen}")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["type"], "FeatureCollection")

    def test_get_zonas_restringidas_scenarios(self):
        for scen in ["conservador", "moderado", "expansivo"]:
            response = self.client.get(f"/api/zonas/restringidas?escenario={scen}")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["type"], "FeatureCollection")

    def test_get_zonas_invalid_scenario(self):
        response = self.client.get("/api/zonas/crecimiento?escenario=invalid")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/zonas/restringidas?escenario=invalid")
        self.assertEqual(response.status_code, 400)

    def test_update_camas_emergencia_success(self):
        payload = {"camas_emergencia_disponibles": 5}
        response = self.client.post("/api/hospitales/1/camas", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["camas_emergencia_disponibles"], 5)

    def test_update_camas_emergencia_exceed_total(self):
        payload = {"camas_emergencia_disponibles": 30}
        response = self.client.post("/api/hospitales/1/camas", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("no pueden exceder", response.json()["detail"])

    def test_update_camas_emergencia_invalid_id(self):
        payload = {"camas_emergencia_disponibles": 5}
        response = self.client.post("/api/hospitales/999/camas", json=payload)
        self.assertEqual(response.status_code, 404)

    def test_simulate_camas_emergencia(self):
        response = self.client.post("/api/hospitales/simular")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["updates"]) > 0)

if __name__ == '__main__':
    unittest.main()
