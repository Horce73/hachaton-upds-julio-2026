import unittest
import json
import sys
import os

# Include src directory in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.mcda import MCDAModel

class TestMCDA(unittest.TestCase):
    def test_mcda_evaluation(self):
        mcda = MCDAModel.get_instance()
        
        # Load the mock terrains we generated
        with open("geojson/terrenos_candidatos.geojson") as f:
            parcels_geojson = json.load(f)
            
        evaluated_results = []
        for feature in parcels_geojson["features"]:
            geom = feature["geometry"]
            props = feature["properties"]
            res = mcda.evaluate_parcel(geom, props)
            evaluated_results.append((props["id"], props["nombre"], res))
            print(f"\n[Test MCDA] Evaluado: {props['nombre']} (ID: {props['id']})")
            print(f" -> Apto: {res['apto']}, IAT: {res['iat']}, Original IAT: {res['original_iat']}")
            print(f" -> Distrito: {res['distrito_cod']}, Pendiente: {res['pendiente_pct']:.1f}%")
            if res["restricciones"]:
                print(f" -> Restricciones: {res['restricciones']}")
        
        # Validate Parcel 6 (Norte - Excelente Aptitud) is suitable
        p6 = next(r for r in evaluated_results if r[0] == 6)[2]
        self.assertTrue(p6["apto"])
        self.assertTrue(p6["iat"] >= 80.0) # Should be a very good candidate
        
        # Validate Parcel 4 (Recoleta - D-1) is restricted due to patrimonial heritage / central location
        p4 = next(r for r in evaluated_results if r[0] == 4)[2]
        self.assertFalse(p4["apto"])
        self.assertEqual(p4["iat"], 0.0)
        self.assertTrue(any("patrimonial" in r.lower() for r in p4["restricciones"]))
        
        # Validate Parcel 5 (Río Quirpinchaca) is restricted due to flood risk
        p5 = next(r for r in evaluated_results if r[0] == 5)[2]
        self.assertFalse(p5["apto"])
        self.assertEqual(p5["iat"], 0.0)
        self.assertTrue(any("riesgo" in r.lower() or "influencia" in r.lower() for r in p5["restricciones"]))

if __name__ == '__main__':
    unittest.main()
