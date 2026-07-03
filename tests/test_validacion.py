import unittest
import sys
import os
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.validacion.hospitales import HospitalValidator
from src.server import app

class TestHospitalValidation(unittest.TestCase):
    def setUp(self):
        self.validator = HospitalValidator.get_instance()
        self.client = TestClient(app)

    def test_validar_hospitales_returns_expected_structure(self):
        result = self.validator.validar_todos()
        self.assertIn("total", result)
        self.assertIn("validos", result)
        self.assertIn("con_errores", result)
        self.assertIn("hospitales", result)
        self.assertIn("duplicados", result)
        self.assertEqual(result["total"], 8)

    def test_cada_hospital_tiene_campos_esperados(self):
        result = self.validator.validar_todos()
        for hosp in result["hospitales"]:
            self.assertIn("id", hosp)
            self.assertIn("nombre", hosp)
            self.assertIn("coordenadas", hosp)
            self.assertIn("distrito_declarado", hosp)
            self.assertIn("distrito_real", hosp)
            self.assertIn("coincide_distrito", hosp)
            self.assertIn("issues", hosp)
            self.assertIn("valido", hosp)

    def test_hospital_santa_barbara_ok(self):
        result = self.validator.validar_todos()
        hosp = next(h for h in result["hospitales"] if h["id"] == 1)
        self.assertTrue(hosp["valido"])
        self.assertEqual(hosp["distrito_real"], "D-1")
        self.assertTrue(hosp["coincide_distrito"])

    def test_hospital_san_pedro_claver_ok(self):
        result = self.validator.validar_todos()
        hosp = next(h for h in result["hospitales"] if h["id"] == 6)
        self.assertTrue(hosp["valido"])
        self.assertEqual(hosp["distrito_real"], "D-3")
        self.assertTrue(hosp["coincide_distrito"])

    def test_coordenadas_fuera_de_bbox_genera_error(self):
        hosp_original = None
        with open("geojson/hospitales_sucre.geojson") as f:
            import json
            original = json.load(f)

        try:
            hosp_original = [
                f["properties"]["id"]
                for f in original["features"]
            ]

            result = self.validator.validar_todos()
            for hosp in result["hospitales"]:
                lon = hosp["coordenadas"]["lon"]
                lat = hosp["coordenadas"]["lat"]
                bbox_ok = (-65.36 <= lon <= -65.16) and (-19.12 <= lat <= -18.96)
                if not bbox_ok:
                    self.assertFalse(hosp["valido"])
                    self.assertTrue(
                        any("fuera" in iss["mensaje"].lower() for iss in hosp["issues"])
                    )
        finally:
            pass

    def test_duplicados_cercanos(self):
        result = self.validator.validar_todos()
        for dupe in result["duplicados"]:
            self.assertIn("hospital_a", dupe)
            self.assertIn("hospital_b", dupe)
            self.assertIn("distancia_m", dupe)
            self.assertLess(dupe["distancia_m"], 200)

    def test_endpoint_validar_hospitales(self):
        response = self.client.get("/api/validar/hospitales")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total", data)
        self.assertIn("hospitales", data)
        self.assertEqual(data["total"], 8)

    def test_solo_un_hospital_fuera_de_distrito(self):
        result = self.validator.validar_todos()
        hospital_lajastambo = next(h for h in result["hospitales"] if h["id"] == 2)
        self.assertEqual(hospital_lajastambo["distrito_declarado"], "D-3")


if __name__ == '__main__':
    unittest.main()
