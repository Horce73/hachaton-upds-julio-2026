import sys
import os
# Add parent directory of 'src' to python path to resolve package imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import io
import pickle
import pandas as pd
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field

# Import our custom modules
from src.spatial.projection import reproject_geojson
from src.models.mcda import MCDAModel
from src.validacion.hospitales import HospitalValidator
from src.analisis.cobertura import CoverageAnalyzer
from src.analisis.deficit import DeficitAnalyzer

# Load trained Machine Learning models if available
REGRESSOR_PATH = "src/models/model_regressor.pkl"
CLASSIFIER_PATH = "src/models/model_classifier.pkl"
FEATURES_PATH = "src/models/model_features.pkl"

model_regressor = None
model_classifier = None
model_features = None

if os.path.exists(REGRESSOR_PATH) and os.path.exists(CLASSIFIER_PATH) and os.path.exists(FEATURES_PATH):
    try:
        with open(REGRESSOR_PATH, "rb") as f:
            model_regressor = pickle.load(f)
        with open(CLASSIFIER_PATH, "rb") as f:
            model_classifier = pickle.load(f)
        with open(FEATURES_PATH, "rb") as f:
            model_features = pickle.load(f)
        print("Modelos de Machine Learning cargados exitosamente.")
    except Exception as e:
        print(f"Advertencia: Error al cargar los modelos de ML: {e}")
else:
    print("Advertencia: No se encontraron los modelos de ML entrenados. Por favor ejecute train.py primero.")

def predict_ml(result: dict, properties: dict) -> dict:
    """Predicts IAT score and suitability using RandomForest models."""
    if not (model_regressor and model_classifier and model_features):
        return {
            "modelo_activo": False,
            "error": "Modelos de Machine Learning no cargados o incompletos"
        }
        
    try:
        from src.preprocessing.generate_mock_data import DISTRICT_PROFILES
        profile = DISTRICT_PROFILES.get(result["distrito_cod"], {
            "poblacion_estimada": 0,
            "crecimiento_anual": 0.0
        })
        
        uso_suelo = properties.get("uso_suelo", "Residencial de Expansión")
        uso_suelo_comp = 1.0 if "expansión" in uso_suelo.lower() or "reserva" in uso_suelo.lower() or "mixto" in uso_suelo.lower() else (0.8 if "residencial" in uso_suelo.lower() else 0.5)
        
        features_vector = [[
            result["pendiente_pct"],
            result["elevacion_m"],
            result["distancia_hosp_m"],
            result["distancia_vias_m"],
            profile["poblacion_estimada"],
            profile["crecimiento_anual"],
            1 if properties.get("agua", True) else 0,
            1 if properties.get("electricidad", True) else 0,
            1 if properties.get("alcantarillado", True) else 0,
            result["area_m2"],
            1 if properties.get("patrimonial", False) or result["distrito_cod"] == "D-1" else 0,
            1 if properties.get("industrial_incompatible", False) or uso_suelo == "Industrial" else 0,
            1 if properties.get("cerca_rio", False) else 0,
            uso_suelo_comp
        ]]
        
        features_df = pd.DataFrame(features_vector, columns=model_features)
        
        pred_iat = float(model_regressor.predict(features_df)[0])
        pred_apto = bool(model_classifier.predict(features_df)[0])
        
        return {
            "iat_predicho": round(pred_iat, 1),
            "apto_predicho": pred_apto,
            "modelo_activo": True
        }
    except Exception as e:
        return {
            "modelo_activo": False,
            "error": f"Error en inferencia ML: {str(e)}"
        }

# Initialize FastAPI
app = FastAPI(
    title="Plataforma de Apoyo a la Planificación Urbana - Sucre",
    description="Sistema inteligente para la selección y evaluación de terrenos para hospitales",
    version="1.0"
)

# Bounding box of Sucre municipality to validate inputs
SUCRE_BBOX = {
    "min_lon": -65.36,
    "max_lon": -65.16,
    "min_lat": -19.12,
    "max_lat": -18.96
}

def validate_wgs84_coordinates(lon: float, lat: float):
    """Ensures coordinates fall within the geographical boundaries of Sucre, Bolivia."""
    if not (SUCRE_BBOX["min_lon"] <= lon <= SUCRE_BBOX["max_lon"]):
        raise HTTPException(status_code=400, detail=f"Longitud {lon} fuera de los límites de Sucre [{SUCRE_BBOX['min_lon']}, {SUCRE_BBOX['max_lon']}]")
    if not (SUCRE_BBOX["min_lat"] <= lat <= SUCRE_BBOX["max_lat"]):
        raise HTTPException(status_code=400, detail=f"Latitud {lat} fuera de los límites de Sucre [{SUCRE_BBOX['min_lat']}, {SUCRE_BBOX['max_lat']}]")

# Pydantic schemas for input validation
class GeometryInput(BaseModel):
    type: str = Field(..., description="Tipo de geometría: Point o Polygon")
    coordinates: list = Field(..., description="Coordenadas en formato GeoJSON WGS84")

class ParcelProperties(BaseModel):
    agua: bool = True
    electricidad: bool = True
    alcantarillado: bool = True
    uso_suelo: str = "Residencial de Expansión"
    area_m2: float = 10000.0
    patrimonial: bool = False
    industrial_incompatible: bool = False
    cerca_rio: bool = False

class EvaluationRequest(BaseModel):
    geometry: GeometryInput
    properties: ParcelProperties
    nombre: str = "Terreno Personalizado"

# Reportlab PDF generator
def generate_pdf_report(result: dict, name: str) -> io.BytesIO:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom Styles (Safe styling to avoid crashing)
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0F172A'),  # Slate 900
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#475569'),  # Slate 600
        spaceAfter=25
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1E293B'),  # Slate 800
        spaceBefore=15,
        spaceAfter=10
    )
    
    body_style = styles['BodyText']
    
    # Header
    story.append(Paragraph("PLANIFICACIÓN URBANA - SUCRE, BOLIVIA", title_style))
    story.append(Paragraph(f"Reporte de Aptitud Territorial para Hospital de Segundo Nivel<br/>Terreno Evaluado: <b>{name}</b>", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Suitability Card (Coloring based on status)
    status = "RECOMENDABLE" if result["apto"] else "NO RECOMENDABLE"
    status_color = '#16A34A' if result["apto"] else '#DC2626'
    
    # Main Metrics Table
    data = [
        [Paragraph("<b>Indicador Técnico</b>", body_style), Paragraph("<b>Valor Calculado</b>", body_style)],
        [Paragraph("Distrito Urbano", body_style), Paragraph(f"{result['distrito_nombre']} ({result['distrito_cod']})", body_style)],
        [Paragraph("Elevación Promedio", body_style), Paragraph(f"{result['elevacion_m']} msnm", body_style)],
        [Paragraph("Pendiente Estimada", body_style), Paragraph(f"{result['pendiente_pct']}%", body_style)],
        [Paragraph("Superficie Evaluada", body_style), Paragraph(f"{result['area_m2']:.0f} m²", body_style)],
        [Paragraph("Distancia a Avenidas Principales", body_style), Paragraph(f"{result['distancia_vias_m']:.0f} m", body_style)],
        [Paragraph("Distancia a Red de Salud Existente", body_style), Paragraph(f"{result['distancia_hosp_m']:.0f} m", body_style)],
        [Paragraph("Índice de Aptitud Territorial (IAT)", body_style), Paragraph(f"<b>{result['iat']} / 100</b>", body_style)],
        [Paragraph("Estado de Aptitud", body_style), Paragraph(f"<font color='{status_color}'><b>{status}</b></font>", body_style)]
    ]
    
    t = Table(data, colWidths=[200, 320])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#F1F5F9')), # Slate 100
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')), # Slate 200
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Criteria Weights Table
    story.append(Paragraph("Desglose de Ponderación Multicriterio", section_style))
    crit_data = [
        [Paragraph("<b>Criterio de Evaluación</b>", body_style), Paragraph("<b>Peso</b>", body_style), Paragraph("<b>Puntaje (0-100)</b>", body_style)],
        [Paragraph("Crecimiento Poblacional", body_style), Paragraph("25%", body_style), Paragraph(str(result["criterios"]["crecimiento"]), body_style)],
        [Paragraph("Accesibilidad Vial", body_style), Paragraph("20%", body_style), Paragraph(str(result["criterios"]["accesibilidad"]), body_style)],
        [Paragraph("Cobertura Hospitalaria", body_style), Paragraph("15%", body_style), Paragraph(str(result["criterios"]["cobertura"]), body_style)],
        [Paragraph("Infraestructura Básica", body_style), Paragraph("15%", body_style), Paragraph(str(result["criterios"]["infraestructura"]), body_style)],
        [Paragraph("Uso del Suelo", body_style), Paragraph("10%", body_style), Paragraph(str(result["criterios"]["uso_suelo"]), body_style)],
        [Paragraph("Topografía (Pendientes)", body_style), Paragraph("10%", body_style), Paragraph(str(result["criterios"]["topografia"]), body_style)],
        [Paragraph("Riesgos Ambientales", body_style), Paragraph("5%", body_style), Paragraph(str(result["criterios"]["riesgos"]), body_style)],
    ]
    t2 = Table(crit_data, colWidths=[240, 100, 180])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (2,0), colors.HexColor('#F1F5F9')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t2)
    story.append(Spacer(1, 20))
    
    # ML Prediction Box (if active)
    ml_res = result.get("prediccion_ml", {})
    if ml_res.get("modelo_activo"):
        story.append(Paragraph("Predicción del Modelo de Inteligencia Artificial (Random Forest)", section_style))
        ml_status = "RECOMENDABLE" if ml_res["apto_predicho"] else "NO RECOMENDABLE"
        ml_status_color = '#16A34A' if ml_res["apto_predicho"] else '#DC2626'
        ml_text = f"El modelo de aprendizaje automático (entrenado sobre el territorio de Sucre) predice un <b>Índice de Aptitud Territorial (IAT) de {ml_res['iat_predicho']} / 100</b>.<br/>"
        ml_text += f"Clasificación estimada por Inteligencia Artificial: <font color='{ml_status_color}'><b>{ml_status}</b></font>."
        story.append(Paragraph(ml_text, body_style))
        story.append(Spacer(1, 15))

    # Explanatory Text
    story.append(Paragraph("Análisis y Justificación Técnica", section_style))
    # Replace newlines with HTML breaks for reportlab paragraph rendering
    formatted_exp = result["explicacion"].replace("\n", "<br/>")
    story.append(Paragraph(formatted_exp, body_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# Secure HTTP Headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response

# API Endpoints
@app.get("/api/distritos")
def get_distritos():
    """
    Returns Sucre's districts reprojected from UTM 20S to WGS84 for Leaflet rendering.
    Enriches the properties with district demographics.
    """
    try:
        mcda = MCDAModel.get_instance()
        # Reproject UTM to WGS84
        distritos_wgs84 = reproject_geojson(mcda.distritos_utm, to_crs="epsg:4326", from_crs="epsg:32720")
        
        # Enrich properties
        from src.preprocessing.generate_mock_data import DISTRICT_PROFILES
        for feature in distritos_wgs84.get("features", []):
            cod = feature["properties"]["COD"]
            if cod in DISTRICT_PROFILES:
                feature["properties"].update(DISTRICT_PROFILES[cod])
                
        return distritos_wgs84
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar distritos: {str(e)}")

@app.get("/api/hospitales")
def get_hospitales():
    """Returns the WGS84 layer of existing hospitals."""
    try:
        with open("geojson/hospitales_sucre.geojson", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer hospitales: {str(e)}")

class CamasEmergenciaUpdate(BaseModel):
    camas_emergencia_disponibles: int = Field(..., ge=0, description="Número de camas desocupadas actualmente")

@app.post("/api/hospitales/{hospital_id}/camas")
def update_camas_emergencia(hospital_id: int, payload: CamasEmergenciaUpdate):
    """
    Updates the available emergency beds count for a specific hospital in the GeoJSON file.
    """
    geojson_path = "geojson/hospitales_sucre.geojson"
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        hospital_found = None
        for feature in data.get("features", []):
            if feature["properties"].get("id") == hospital_id:
                hospital_found = feature
                break
                
        if not hospital_found:
            raise HTTPException(status_code=404, detail=f"Hospital con ID {hospital_id} no encontrado.")
            
        props = hospital_found["properties"]
        totales = props.get("camas_emergencia_totales", 0)
        disponibles = payload.camas_emergencia_disponibles
        
        if disponibles > totales:
            raise HTTPException(
                status_code=400, 
                detail=f"Las camas disponibles ({disponibles}) no pueden exceder las camas de emergencia totales ({totales})."
            )
            
        props["camas_emergencia_disponibles"] = disponibles
        
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        return {"status": "success", "hospital": props["nombre"], "camas_emergencia_disponibles": disponibles}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar camas de emergencia: {str(e)}")

@app.post("/api/hospitales/simular")
def simulate_camas_emergencia():
    """
    Simulates real-time telemetry changes by randomly fluctuating available emergency beds 
    by +/- 1 or 2 (staying within [0, total_emergency_beds] limits) for all hospitals.
    """
    import random
    geojson_path = "geojson/hospitales_sucre.geojson"
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        updates = []
        for feature in data.get("features", []):
            props = feature["properties"]
            totales = props.get("camas_emergencia_totales", 0)
            if totales == 0:
                continue
            disponibles = props.get("camas_emergencia_disponibles", 0)
            
            # Fluctuate by -2, -1, 0, 1, 2
            delta = random.choice([-2, -1, 0, 1, 2])
            new_disponibles = max(0, min(totales, disponibles + delta))
            
            props["camas_emergencia_disponibles"] = new_disponibles
            updates.append({
                "id": props.get("id"),
                "nombre": props.get("nombre"),
                "camas_emergencia_totales": totales,
                "camas_emergencia_disponibles": new_disponibles
            })
            
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        return {"status": "success", "updates": updates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la simulación de telemetría: {str(e)}")

@app.get("/api/vias")
def get_vias():
    """Returns the WGS84 layer of main roads."""
    try:
        with open("geojson/vias_sucre.geojson", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer red vial: {str(e)}")

@app.get("/api/topografia")
def get_topografia():
    """Returns the WGS84 layer of topography contours."""
    try:
        with open("geojson/topografia_sucre.geojson", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer topografía: {str(e)}")

@app.get("/api/zonas/crecimiento")
def get_zonas_crecimiento(escenario: str = "moderado"):
    """
    Returns urban growth forecast zones reprojected to WGS84 for Leaflet rendering.
    Allows selecting scenario: 'conservador', 'moderado', or 'expansivo'.
    """
    if escenario not in ["conservador", "moderado", "expansivo"]:
        raise HTTPException(status_code=400, detail="Escenario inválido. Debe ser 'conservador', 'moderado' o 'expansivo'.")
        
    try:
        filename = f"geojson/zonas_crecimiento_{escenario}.geojson"
        with open(filename, encoding="utf-8") as f:
            utm_data = json.load(f)
        wgs84_data = reproject_geojson(utm_data, to_crs="epsg:4326", from_crs="epsg:32720")
        return wgs84_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar zonas de crecimiento ({escenario}): {str(e)}")

@app.get("/api/zonas/restringidas")
def get_zonas_restringidas(escenario: str = "moderado"):
    """
    Returns environmental/heritage restricted zones reprojected to WGS84 for Leaflet rendering.
    Allows selecting scenario: 'conservador', 'moderado', or 'expansivo'.
    """
    if escenario not in ["conservador", "moderado", "expansivo"]:
        raise HTTPException(status_code=400, detail="Escenario inválido. Debe ser 'conservador', 'moderado' o 'expansivo'.")
        
    try:
        filename = f"geojson/zonas_no_recomendadas_{escenario}.geojson"
        with open(filename, encoding="utf-8") as f:
            utm_data = json.load(f)
        wgs84_data = reproject_geojson(utm_data, to_crs="epsg:4326", from_crs="epsg:32720")
        return wgs84_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar zonas restringidas ({escenario}): {str(e)}")

@app.get("/api/terrenos")
def get_terrenos():
    """
    Returns candidate terrains in WGS84, pre-evaluated with their IAT scores
    so the map can color-code them immediately.
    """
    try:
        mcda = MCDAModel.get_instance()
        with open("geojson/terrenos_candidatos.geojson", encoding="utf-8") as f:
            parcels = json.load(f)
            
        for feature in parcels.get("features", []):
            geom = feature["geometry"]
            props = feature["properties"]
            # Evaluate using MCDA
            eval_res = mcda.evaluate_parcel(geom, props)
            # Add ML prediction
            eval_res["prediccion_ml"] = predict_ml(eval_res, props)
            # Add results to properties
            feature["properties"]["evaluacion"] = eval_res
            feature["properties"]["iat"] = eval_res["iat"]
            feature["properties"]["apto"] = eval_res["apto"]
            
        return parcels
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar terrenos candidatos: {str(e)}")

@app.post("/api/evaluar")
def evaluar_terreno(req: EvaluationRequest):
    """
    Evaluates a user-submitted coordinate point or polygon geometry against the MCDA criteria.
    """
    try:
        # Validate coordinates coordinates bounding box
        coords = req.geometry.coordinates
        if req.geometry.type == "Point":
            validate_wgs84_coordinates(coords[0], coords[1])
        elif req.geometry.type == "Polygon":
            for ring in coords:
                for pt in ring:
                    validate_wgs84_coordinates(pt[0], pt[1])
                    
        mcda = MCDAModel.get_instance()
        result = mcda.evaluate_parcel(req.geometry.model_dump(), req.properties.model_dump())
        result["prediccion_ml"] = predict_ml(result, req.properties.model_dump())
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la evaluación: {str(e)}")

@app.post("/api/reporte/pdf")
def exportar_reporte(req: EvaluationRequest):
    """Generates a professional PDF report of the evaluation and streams it back to the client."""
    try:
        mcda = MCDAModel.get_instance()
        result = mcda.evaluate_parcel(req.geometry.model_dump(), req.properties.model_dump())
        result["prediccion_ml"] = predict_ml(result, req.properties.model_dump())
        
        pdf_buffer = generate_pdf_report(result, req.nombre)
        
        filename = f"reporte_{req.nombre.lower().replace(' ', '_')}.pdf"
        # Sanitize filename to prevent header injection or traversal
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte PDF: {str(e)}")

@app.get("/api/cobertura")
def get_cobertura():
    """
    Returns coverage analysis: union of hospital coverage areas,
    uncovered urban zones, and metrics.
    """
    try:
        analyzer = CoverageAnalyzer.get_instance()
        result = analyzer.get_coverage()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis de cobertura: {str(e)}")

@app.get("/api/deficit/hospitalario")
def get_deficit_hospitalario():
    """
    Returns hospital bed deficit analysis per district,
    with population projections up to 20 years.
    """
    try:
        analyzer = DeficitAnalyzer.get_instance()
        result = analyzer.get_deficit()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en déficit hospitalario: {str(e)}")

@app.get("/api/validar/hospitales")
def validar_hospitales():
    """
    Validates hospital coordinates against district boundaries,
    detects duplicates, and checks data consistency.
    """
    try:
        validator = HospitalValidator.get_instance()
        result = validator.validar_todos()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en validación de hospitales: {str(e)}")

# Mount static files at /dashboard/ (index.html, styles.css, app.js)
dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
if os.path.exists(dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")

# Redirect root to dashboard
@app.get("/")
def redirect_to_dashboard():
    dashboard_index = os.path.join(dashboard_dir, "index.html")
    if os.path.exists(dashboard_index):
        return FileResponse(dashboard_index)
    return {"message": "Servidor activo. Ingrese a /dashboard para ver el mapa interactivo."}

if __name__ == "__main__":
    import uvicorn
    # Bind to 127.0.0.1 (localhost) strictly for secure local testing
    uvicorn.run("src.server:app", host="127.0.0.1", port=8000, reload=True)
