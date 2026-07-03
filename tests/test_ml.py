import unittest
import sys
import os
import pickle
from fastapi.testclient import TestClient

# Include src directory in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.server import app

class TestML(unittest.TestCase):
    def setUp(self):
        # Create a test client for FastAPI
        self.client = TestClient(app)
        
    def test_models_exist(self):
        # Verify that all trained ML files are created and stored in src/models
        reg_path = "src/models/model_regressor.pkl"
        clf_path = "src/models/model_classifier.pkl"
        features_path = "src/models/model_features.pkl"
        
        self.assertTrue(os.path.exists(reg_path), "Regressor model pickle file does not exist.")
        self.assertTrue(os.path.exists(clf_path), "Classifier model pickle file does not exist.")
        self.assertTrue(os.path.exists(features_path), "Features list pickle file does not exist.")

    def test_inference_raw(self):
        # Verify raw mathematical inference works
        reg_path = "src/models/model_regressor.pkl"
        clf_path = "src/models/model_classifier.pkl"
        features_path = "src/models/model_features.pkl"
        
        import pandas as pd
        with open(reg_path, "rb") as f:
            reg = pickle.load(f)
        with open(clf_path, "rb") as f:
            clf = pickle.load(f)
        with open(features_path, "rb") as f:
            features = pickle.load(f)
            
        # Sample features vector (e.g. flat flat terrain, next to hospital and main road, basic services available)
        sample_feature = [[
            2.0, 2800.0, 1000.0, 50.0, 50000.0, 0.02,
            1, 1, 1, 12000.0, 0, 0, 0, 1.0
        ]]
        
        df_sample = pd.DataFrame(sample_feature, columns=features)
        
        pred_iat = reg.predict(df_sample)[0]
        pred_apto = clf.predict(df_sample)[0]
        
        # Predicted IAT must be a score between 0 and 100
        self.assertTrue(0.0 <= pred_iat <= 100.0, f"Predicted IAT {pred_iat} is out of bounds.")
        # Predicted aptitud must be binary (0 or 1)
        self.assertIn(pred_apto, [0, 1])

    def test_api_evaluar_ml_fields(self):
        # Send a POST evaluation request to check that API includes predict_ml results
        payload = {
            "geometry": {
                "type": "Point",
                "coordinates": [-65.2594, -19.0476] # Center Plaza
            },
            "properties": {
                "agua": True,
                "electricidad": True,
                "alcantarillado": True,
                "uso_suelo": "Residencial de Expansión",
                "area_m2": 15000.0,
                "patrimonial": False,
                "industrial_incompatible": False,
                "cerca_rio": False
            },
            "nombre": "Test Terreno ML API"
        }
        
        response = self.client.post("/api/evaluar", json=payload)
        self.assertEqual(response.status_code, 200)
        
        res = response.json()
        self.assertIn("prediccion_ml", res)
        
        ml_prediction = res["prediccion_ml"]
        self.assertTrue(ml_prediction["modelo_activo"], "ML model should be active and loaded.")
        self.assertIn("iat_predicho", ml_prediction)
        self.assertIn("apto_predicho", ml_prediction)
        
        self.assertTrue(0.0 <= ml_prediction["iat_predicho"] <= 100.0)
        self.assertIsInstance(ml_prediction["apto_predicho"], bool)

if __name__ == '__main__':
    unittest.main()
