import os
import sys
import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import r2_score, mean_absolute_error, accuracy_score, classification_report, confusion_matrix

def main():
    dataset_path = "data/dataset_entrenamiento.csv"
    if not os.path.exists(dataset_path):
        print(f"Error: El dataset no se encuentra en {dataset_path}.")
        print("Por favor ejecuta primero 'src/preprocessing/generate_training_dataset.py'.")
        sys.exit(1)
        
    print(f"Cargando dataset desde {dataset_path}...")
    df = pd.read_csv(dataset_path)
    
    print(f"Dataset cargado con éxito. Tamaño: {df.shape[0]} filas, {df.shape[1]} columnas.")
    print("Distribución de Aptitud (apto):")
    print(df["apto"].value_counts(normalize=True))
    
    # Feature columns
    features = [
        "pendiente",
        "elevacion",
        "distancia_hospital",
        "distancia_via",
        "poblacion_distrito",
        "crecimiento_distrito",
        "agua",
        "electricidad",
        "alcantarillado",
        "area_m2",
        "patrimonial",
        "industrial_incompatible",
        "cerca_rio",
        "uso_suelo_compatible"
    ]
    
    X = df[features]
    y_reg = df["iat"]
    y_clf = df["apto"]
    
    print("\nCaracterísticas seleccionadas para entrenamiento:")
    for i, col in enumerate(features, 1):
        print(f"  {i}. {col}")
        
    # --- Split Data ---
    X_train, X_test, y_train_reg, y_test_reg, y_train_clf, y_test_clf = train_test_split(
        X, y_reg, y_clf, test_size=0.2, random_state=42
    )
    
    print(f"\nDatos divididos en:")
    print(f"  - Set de entrenamiento: {X_train.shape[0]} muestras")
    print(f"  - Set de evaluación: {X_test.shape[0]} muestras")
    
    # --- Train Regressor ---
    print("\nEntrenando RandomForestRegressor para predicción del IAT...")
    reg = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    reg.fit(X_train, y_train_reg)
    
    # Evaluate Regressor
    y_pred_reg = reg.predict(X_test)
    r2 = r2_score(y_test_reg, y_pred_reg)
    mae = mean_absolute_error(y_test_reg, y_pred_reg)
    print(f"Evaluación del Regresor (IAT):")
    print(f"  - Coeficiente de determinación R²: {r2:.4f}")
    print(f"  - Error Medio Absoluto (MAE): {mae:.4f} puntos")
    
    # --- Train Classifier ---
    print("\nEntrenando RandomForestClassifier para predicción de Aptitud (apto/no apto)...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train_clf)
    
    # Evaluate Classifier
    y_pred_clf = clf.predict(X_test)
    acc = accuracy_score(y_test_clf, y_pred_clf)
    print(f"Evaluación del Clasificador (Aptitud):")
    print(f"  - Precisión Global (Accuracy): {acc*100:.2f}%")
    print("\nReporte de Clasificación:")
    print(classification_report(y_test_clf, y_pred_clf, target_names=["No Apto", "Apto"]))
    print("Matriz de Confusión:")
    print(confusion_matrix(y_test_clf, y_pred_clf))
    
    # --- Save Trained Models ---
    os.makedirs("src/models", exist_ok=True)
    
    reg_path = "src/models/model_regressor.pkl"
    clf_path = "src/models/model_classifier.pkl"
    
    print(f"\nGuardando modelos entrenados en disco...")
    with open(reg_path, "wb") as f:
        pickle.dump(reg, f)
    print(f"  - Regresor IAT guardado en: {reg_path}")
        
    with open(clf_path, "wb") as f:
        pickle.dump(clf, f)
    print(f"  - Clasificador Aptitud guardado en: {clf_path}")
    
    # Save features list for interface consistency during inference
    features_path = "src/models/model_features.pkl"
    with open(features_path, "wb") as f:
        pickle.dump(features, f)
    print(f"  - Lista de características guardada en: {features_path}")
    
    print("\n¡Proceso de entrenamiento finalizado con éxito!")

if __name__ == "__main__":
    main()
