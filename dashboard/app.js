// Check saved theme preference immediately to prevent theme flashing on load
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
    document.body.classList.add('light-theme');
}

// Global State Variables
let map;
let tileLayer;
let layers = {
    distritos: null,
    topografia: null,
    vias: null,
    terrenos: null,
    crecimiento: null,
    restringidas: null,
    coberturaHospitalaria: null,
    coberturaUnificada: null,
    areasDescubiertas: null
};

let coverageData = null;

// Global Weight Coefficients (initially matches backend defaults)
let weights = {
    crecimiento: 0.25,
    accesibilidad: 0.20,
    cobertura: 0.15,
    infraestructura: 0.15,
    uso_suelo: 0.10,
    topografia: 0.10,
    riesgos: 0.05
};

let selectedTerrain = null;      // Currently selected terrain object
let customEvaluationMode = false; // Is click-to-evaluate mode active?
let customMarker = null;          // Temporary marker for custom evaluated point
let criteriaChart = null;         // Chart.js instance
let rawHospitalesData = null;      // Raw GeoJSON array for specialties filtering
let comparisonList = [];          // Terrains currently selected for side-by-side comparison

// Styling function for terrains based on IAT score
function getTerrainColor(iat, isApto) {
    if (!isApto || iat < 60) return '#EF4444'; // Red (No Recomendable / Restricted)
    if (iat >= 90) return '#10B981';           // Emerald (Excelente)
    if (iat >= 80) return '#34D399';           // Mint (Muy Bueno)
    if (iat >= 70) return '#A7F3D0';           // Light Mint (Adecuado)
    return '#F59E0B';                          // Amber (Aceptable)
}

function getTerrainStyle(feature) {
    // If evaluated, use its score. Otherwise use base properties if exists.
    const iat = feature.properties.iat || 0;
    const apto = feature.properties.apto !== false;
    const isLight = document.body.classList.contains('light-theme');
    return {
        fillColor: getTerrainColor(iat, apto),
        weight: 2.2,
        opacity: 0.9,
        color: apto ? (isLight ? '#475569' : '#FFFFFF') : '#EF4444',
        fillOpacity: 0.5,
        dashArray: apto ? '' : '4, 4'
    };
}

function getHospitalCoverageConfig(nivel) {
    if (nivel >= 3) {
        return {
            radius: 5000,
            color: '#2563EB',
            fillColor: '#3B82F6',
            label: 'Cobertura 3er nivel'
        };
    }

    if (nivel === 2) {
        return {
            radius: 3000,
            color: '#F59E0B',
            fillColor: '#FBBF24',
            label: 'Cobertura 2do nivel'
        };
    }

    return {
        radius: 1500,
        color: '#64748B',
        fillColor: '#94A3B8',
        label: 'Cobertura hospitalaria'
    };
}

// Initialize Leaflet Map
function initMap() {
    // Center at Sucre, Bolivia
    map = L.map('map', {
        zoomControl: false, // Turn off default top-left zoom control
        attributionControl: true
    }).setView([-19.042, -65.255], 13.5);

    // Place zoom control in top-right corner
    L.control.zoom({
        position: 'topright'
    }).addTo(map);

    // Load light or dark tiles based on active theme
    const isLight = document.body.classList.contains('light-theme');
    const tileUrl = isLight 
        ? 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
        : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

    tileLayer = L.tileLayer(tileUrl, {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);
}

// Load Vector & Spatial Layers from FastAPI API
async function loadLayers() {
    try {
        // 1. Existing Road network (Vías)
        const viasRes = await fetch('/api/vias');
        if (viasRes.ok) {
            const viasData = await viasRes.json();
            layers.vias = L.geoJSON(viasData, {
                style: {
                    color: '#64748B', // Slate gray
                    weight: 2.5,
                    opacity: 0.6
                }
            }).addTo(map);
        }

        // 2. Elevation contours (Topografía)
        const topoRes = await fetch('/api/topografia');
        if (topoRes.ok) {
            const topoData = await topoRes.json();
            layers.topografia = L.geoJSON(topoData, {
                style: function(feature) {
                    // Render contour lines with subtle color based on elevation
                    const elev = feature.properties.ELEV;
                    return {
                        color: elev > 2800 ? '#475569' : '#334155',
                        weight: 0.8,
                        opacity: 0.4
                    };
                }
            }).addTo(map);
        }

        // 3. Sucre District Boundaries
        const distritosRes = await fetch('/api/distritos');
        if (distritosRes.ok) {
            const distritosData = await distritosRes.json();
            layers.distritos = L.geoJSON(distritosData, {
                style: function(feature) {
                    // Colors districts by estimated population density / growth pressure
                    const cod = feature.properties.COD;
                    let fillColor = '#1E293B';
                    if (cod === 'D-5') fillColor = '#581C87'; // Critical South
                    if (cod === 'D-3') fillColor = '#701A75'; // High growth North
                    if (cod === 'D-4') fillColor = '#0369A1'; // West
                    if (cod === 'D-2') fillColor = '#0F766E'; // Medium
                    if (cod === 'D-1') fillColor = '#374151'; // Central
                    
                    return {
                        fillColor: fillColor,
                        weight: 1.5,
                        opacity: 0.7,
                        color: '#475569',
                        fillOpacity: 0.25
                    };
                },
                onEachFeature: function(feature, layer) {
                    const props = feature.properties;
                    const popupContent = `
                        <div class="custom-popup">
                            <h4 class="popup-title">${props.nombre || props.Distritos}</h4>
                            <p class="popup-detail"><strong>Población:</strong> ${props.poblacion_estimada.toLocaleString()} hab</p>
                            <p class="popup-detail"><strong>Crecimiento:</strong> ${(props.crecimiento_anual*100).toFixed(1)}% anual</p>
                            <p class="popup-detail"><strong>Cobertura Básica:</strong> ${(props.servicios_basicos_pct*100).toFixed(0)}%</p>
                            <p class="popup-detail"><strong>Camas Existentes:</strong> ${props.camas_actuales} camas</p>
                        </div>
                    `;
                    layer.bindPopup(popupContent, { className: 'custom-popup' });
                }
            }).addTo(map);
        }

        // 4. Existing Hospitals Layer (Red de Salud)
        const hospitalesRes = await fetch('/api/hospitales');
        if (hospitalesRes.ok) {
            rawHospitalesData = await hospitalesRes.json();
            layers.coberturaHospitalaria = L.layerGroup();
            filterHospitalesBySpecialty("");
            layers.coberturaHospitalaria.addTo(map);
        }

        // 5. Unified coverage analysis (union polygons + uncovered areas)
        const coberturaRes = await fetch('/api/cobertura');
        if (coberturaRes.ok) {
            const coberturaData = await coberturaRes.json();
            coverageData = coberturaData;

            layers.coberturaUnificada = L.layerGroup();
            layers.areasDescubiertas = L.layerGroup();

            if (coberturaData.cobertura_nivel2) {
                L.geoJSON(coberturaData.cobertura_nivel2, {
                    style: {
                        color: '#FBBF24',
                        weight: 1.5,
                        opacity: 0.5,
                        fillColor: '#FBBF24',
                        fillOpacity: 0.08
                    }
                }).addTo(layers.coberturaUnificada);
            }

            if (coberturaData.cobertura_nivel3) {
                L.geoJSON(coberturaData.cobertura_nivel3, {
                    style: {
                        color: '#3B82F6',
                        weight: 1.5,
                        opacity: 0.5,
                        fillColor: '#3B82F6',
                        fillOpacity: 0.08
                    }
                }).addTo(layers.coberturaUnificada);
            }

            if (coberturaData.areas_descubiertas) {
                L.geoJSON(coberturaData.areas_descubiertas, {
                    style: {
                        color: '#EF4444',
                        weight: 2.5,
                        opacity: 0.8,
                        fillColor: '#EF4444',
                        fillOpacity: 0.25,
                        dashArray: '6, 4'
                    }
                }).addTo(layers.areasDescubiertas);
            }

            updateCoverageMetrics(coberturaData.metricas);
        }

        // 6. Pre-evaluated Candidate terrains
        const terrenosRes = await fetch('/api/terrenos');
        if (terrenosRes.ok) {
            const terrenosData = await terrenosRes.json();
            layers.terrenos = L.geoJSON(terrenosData, {
                style: getTerrainStyle,
                onEachFeature: function(feature, layer) {
                    layer.on('click', function(e) {
                        L.DomEvent.stopPropagation(e);
                        selectTerrainFeature(feature);
                    });
                }
            }).addTo(map);
        }

        // 6. Projected Growth & 7. Restricted zones (moderado scenario by default)
        await reloadGrowthZones("moderado");
        await reloadRestrictedZones("moderado");

        // 8. Load deficit hospitalario data
        await loadDeficitData();

    } catch (error) {
        console.error("Error al cargar las capas geográficas: ", error);
    }
}

async function loadDeficitData() {
    try {
        const res = await fetch('/api/deficit/hospitalario');
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('deficit-panel').classList.remove('hidden');
        document.getElementById('deficit-loading').classList.add('hidden');
        document.getElementById('deficit-content').classList.remove('hidden');

        document.getElementById('deficit-total-camas').textContent = data.resumen.total_camas;
        document.getElementById('deficit-ratio').textContent = data.resumen.ratio_camas_1000_actual;
        document.getElementById('deficit-faltantes').textContent = data.resumen.deficit_total_actual;

        const container = document.getElementById('deficit-distritos-list');
        container.replaceChildren();

        data.distritos.forEach(d => {
            const row = document.createElement('div');
            row.className = 'deficit-distrito-row';

            const name = document.createElement('span');
            name.className = 'ddr-name';
            name.textContent = d.codigo;

            const camas = document.createElement('span');
            camas.className = 'ddr-camas';
            camas.textContent = `${d.camas_actuales} camas`;

            const deficit = document.createElement('span');
            deficit.className = 'ddr-deficit';
            if (d.deficit_actual > 0) {
                deficit.classList.add('positivo');
                deficit.textContent = `-${d.deficit_actual}`;
            } else if (d.superavit_actual > 0) {
                deficit.classList.add('negativo');
                deficit.textContent = `+${d.superavit_actual}`;
            } else {
                deficit.textContent = '0';
            }

            row.appendChild(name);
            row.appendChild(camas);
            row.appendChild(deficit);
            container.appendChild(row);
        });
    } catch (e) {
        console.error('Error al cargar déficit:', e);
    }
}

// Display selected terrain details in the side panel card
function selectTerrainFeature(feature) {
    selectedTerrain = feature;
    
    // Show results panel
    document.getElementById('results-panel').classList.remove('hidden');
    
    const props = feature.properties;
    const evalRes = props.evaluacion;
    
    // Update textual properties safely (textContent prevents XSS)
    document.getElementById('selected-name').textContent = props.nombre || "Terreno Candidato";
    document.getElementById('detail-distrito').textContent = evalRes.distrito_nombre;
    document.getElementById('detail-elevacion').textContent = `${evalRes.elevacion_m} msnm`;
    document.getElementById('detail-pendiente').textContent = `${evalRes.pendiente_pct}%`;
    document.getElementById('detail-superficie').textContent = `${Math.round(evalRes.area_m2).toLocaleString()} m²`;
    document.getElementById('detail-vias').textContent = `${Math.round(evalRes.distancia_vias_m)} m`;
    document.getElementById('detail-hospitales').textContent = `${Math.round(evalRes.distancia_hosp_m)} m`;
    
    // Update ML Prediction display securely
    const mlRow = document.getElementById('ml-prediction-row');
    const mlScoreText = document.getElementById('detail-ml-score');
    const mlRes = evalRes.prediccion_ml;
    
    if (mlRes && mlRes.modelo_activo) {
        mlRow.classList.remove('hidden');
        const mlAptoLabel = mlRes.apto_predicho ? "Apto" : "No Apto";
        mlScoreText.textContent = `${mlRes.iat_predicho.toFixed(1)} (${mlAptoLabel})`;
        mlScoreText.style.color = getTerrainColor(mlRes.iat_predicho, mlRes.apto_predicho);
    } else {
        mlRow.classList.add('hidden');
    }
    
    // Compute current weight-adjusted IAT client-side
    updateTerrainScoreDisplay(evalRes);
    
    // Handle restrictions warning box
    const restrictionsBox = document.getElementById('restrictions-box');
    const restrictionsList = document.getElementById('restrictions-list');
    
    // Clear list safely
    restrictionsList.replaceChildren();
    
    if (evalRes.restricciones && evalRes.restricciones.length > 0) {
        restrictionsBox.classList.remove('hidden');
        evalRes.restricciones.forEach(r => {
            const li = document.createElement('li');
            li.textContent = r;
            restrictionsList.appendChild(li);
        });
    } else {
        restrictionsBox.classList.add('hidden');
    }
}

// Calculates and updates the terrain suitability score based on weights
function updateTerrainScoreDisplay(evalRes) {
    // 1. Calculate weighted IAT
    const scores = evalRes.criterios;
    let iatSum = 0.0;
    let weightSum = 0.0;
    
    for (const key in weights) {
        if (key in scores) {
            iatSum += scores[key] * weights[key];
            weightSum += weights[key];
        }
    }
    
    let finalIat = weightSum > 0 ? (iatSum / weightSum) : 0.0;
    
    // If restricted, force score to 0
    const isApto = !evalRes.restricciones || evalRes.restricciones.length === 0;
    if (!isApto) {
        finalIat = 0.0;
    }
    
    // 2. Update Ring Bar Score
    const scoreValText = document.getElementById('score-value');
    scoreValText.textContent = finalIat.toFixed(1);
    
    const circle = document.getElementById('score-ring-bar');
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    
    // Calculate offset
    const offset = circumference - (finalIat / 100) * circumference;
    circle.style.strokeDashoffset = offset;
    
    // Set color based on suitability
    const color = getTerrainColor(finalIat, isApto);
    circle.style.stroke = color;
    scoreValText.style.color = color;
    
    // Update label quality
    const ratingText = document.getElementById('selected-rating');
    const label = !isApto ? "NO RECOMENDABLE (Restricciones)" :
                  finalIat >= 90 ? "APTITUD EXCELENTE" :
                  finalIat >= 80 ? "APTITUD MUY BUENA" :
                  finalIat >= 70 ? "APTITUD ADECUADA" :
                  finalIat >= 60 ? "APTITUD ACEPTABLE" : "NO RECOMENDABLE";
    ratingText.textContent = label;
    ratingText.style.color = color;
    
    // 3. Update Radar Chart
    updateChart(scores);
    
    // 4. Update Justification details
    // If it's a dynamic weight calculation, keep it simple. Otherwise, render default or dynamic explanation
    const expText = document.getElementById('selected-explanation');
    if (!isApto) {
        expText.textContent = "Terreno NO RECOMENDABLE debido a las siguientes restricciones críticas:\n" + evalRes.restricciones.join("\n");
    } else {
        // Dynamic summary
        const points = [];
        if (evalRes.pendiente_pct < 5.0) points.push(`- Topografía óptima, pendiente muy suave de ${evalRes.pendiente_pct}%.`);
        if (scores.crecimiento > 70) points.push(`- Ubicado en zona de alto dinamismo demográfico.`);
        if (evalRes.distancia_hosp_m > 2000.0) points.push(`- Alta idoneidad para cubrir áreas desabendidas (a ${(evalRes.distancia_hosp_m/1000).toFixed(1)} km de hospitales).`);
        if (evalRes.distancia_vias_m < 200.0) points.push(`- Rápida conexión a la red vial troncal.`);
        if (scores.infraestructura === 100) points.push(`- Cobertura total de infraestructura de agua, luz y drenajes.`);
        
        expText.textContent = `Aptitud global evaluada con un puntaje de ${finalIat.toFixed(1)}/100.\n\nJustificación técnica:\n` + points.join("\n");
    }
}

// Chart.js Radar representation of 7 dimensions suitability
function updateChart(scores) {
    const ctx = document.getElementById('criteriaChart').getContext('2d');
    
    const labels = [
        'Crecimiento',
        'Vías/Acceso',
        'Déficit',
        'Servicios',
        'Suelo',
        'Topografía',
        'Riesgos'
    ];
    
    const data = [
        scores.crecimiento,
        scores.accesibilidad,
        scores.cobertura,
        scores.infraestructura,
        scores.uso_suelo,
        scores.topografia,
        scores.riesgos
    ];

    const isLight = document.body.classList.contains('light-theme');
    const gridColor = isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.1)';
    const angleColor = isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.1)';
    const labelColor = isLight ? '#475569' : '#94A3B8';
    
    if (criteriaChart) {
        criteriaChart.data.datasets[0].data = data;
        criteriaChart.options.scales.r.grid.color = gridColor;
        criteriaChart.options.scales.r.angleLines.color = angleColor;
        criteriaChart.options.scales.r.pointLabels.color = labelColor;
        criteriaChart.update();
    } else {
        criteriaChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Puntaje de Criterio',
                    data: data,
                    fill: true,
                    backgroundColor: 'rgba(16, 185, 129, 0.2)', // Emerald tint
                    borderColor: '#10B981',
                    pointBackgroundColor: '#10B981',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#10B981'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    r: {
                        grid: { color: gridColor },
                        angleLines: { color: angleColor },
                        pointLabels: {
                            color: labelColor,
                            font: { size: 9, family: 'Inter' }
                        },
                        ticks: {
                            display: false,
                            maxTicksLimit: 5
                        },
                        min: 0,
                        max: 100
                    }
                }
            }
        });
    }
}

// Recalculates IAT on all loaded terrains when sliders adjust
function recalculateAllTerrains() {
    if (!layers.terrenos) return;
    
    layers.terrenos.eachLayer(layer => {
        const feature = layer.feature;
        const evalRes = feature.properties.evaluacion;
        
        // Recalculate
        const scores = evalRes.criterios;
        let iatSum = 0.0;
        let weightSum = 0.0;
        for (const key in weights) {
            if (key in scores) {
                iatSum += scores[key] * weights[key];
                weightSum += weights[key];
            }
        }
        
        let newIat = weightSum > 0 ? (iatSum / weightSum) : 0.0;
        const isApto = !evalRes.restricciones || evalRes.restricciones.length === 0;
        if (!isApto) newIat = 0.0;
        
        // Update feature properties
        feature.properties.iat = newIat;
        
        // Repaint layer
        layer.setStyle({
            fillColor: getTerrainColor(newIat, isApto)
        });
    });
    
    // Update selected display if any
    if (selectedTerrain) {
        updateTerrainScoreDisplay(selectedTerrain.properties.evaluacion);
    }
}

// Synchronize weights and validate sum to 100%
function setupWeightSliders() {
    const sliderKeys = [
        'crecimiento', 'accesibilidad', 'cobertura', 
        'infraestructura', 'uso_suelo', 'topografia', 'riesgos'
    ];
    
    sliderKeys.forEach(key => {
        const input = document.getElementById(`weight-${key}`);
        const output = document.getElementById(`weight-${key}-val`);
        
        input.addEventListener('input', function() {
            output.textContent = `${this.value}%`;
            weights[key] = parseFloat(this.value) / 100.0;
            
            // Recalculate Sum
            updateWeightsTotalSum();
            
            // Recalculate candidate properties dynamically
            recalculateAllTerrains();
        });
    });
}

function updateWeightsTotalSum() {
    let sum = 0;
    const sliderKeys = [
        'crecimiento', 'accesibilidad', 'cobertura', 
        'infraestructura', 'uso_suelo', 'topografia', 'riesgos'
    ];
    sliderKeys.forEach(k => {
        sum += parseInt(document.getElementById(`weight-${k}`).value);
    });
    
    const indicator = document.getElementById('total-weight-indicator');
    indicator.textContent = `${sum}%`;
    
    if (sum === 100) {
        indicator.className = 'weight-valid';
    } else {
        indicator.className = 'weight-invalid';
    }
}

// Setup custom evaluation mode (click-to-evaluate)
function setupCustomEvaluation() {
    const btn = document.getElementById('btn-custom-mode');
    
    btn.addEventListener('click', function() {
        customEvaluationMode = !customEvaluationMode;
        
        if (customEvaluationMode) {
            btn.classList.add('btn-active-custom');
            btn.innerHTML = `<i class="fa-solid fa-circle-dot"></i> Haz clic en el Mapa...`;
            document.getElementById('map').style.cursor = 'crosshair';
        } else {
            resetCustomEvaluationMode();
        }
    });
    
    // Map click handler
    map.on('click', async function(e) {
        if (!customEvaluationMode) return;
        
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;
        
        // Construct evaluation payload
        const payload = {
            geometry: {
                type: "Point",
                coordinates: [lon, lat]
            },
            properties: {
                agua: document.getElementById('param-agua').checked,
                electricidad: document.getElementById('param-electricidad').checked,
                alcantarillado: document.getElementById('param-alcantarillado').checked,
                uso_suelo: document.getElementById('param-uso-suelo').value,
                area_m2: 12000.0, // Default typical parcel size for 2nd level hospital
                patrimonial: document.getElementById('param-uso-suelo').value === 'Patrimonial Histórico',
                industrial_incompatible: document.getElementById('param-uso-suelo').value === 'Industrial Incompatible',
                cerca_rio: document.getElementById('param-cerca-rio').checked
            },
            nombre: "Terreno Personalizado"
        };
        
        try {
            const response = await fetch('/api/evaluar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                const errData = await response.json();
                alert(`Error en evaluación: ${errData.detail}`);
                return;
            }
            
            const result = await response.json();
            
            // Remove previous marker if exists
            if (customMarker) {
                map.removeLayer(customMarker);
            }
            
            // Create nice looking circle marker on click location
            const color = getTerrainColor(result.iat, result.apto);
            const isLight = document.body.classList.contains('light-theme');
            customMarker = L.circleMarker([lat, lon], {
                radius: 12,
                fillColor: color,
                color: isLight ? '#1E293B' : '#ffffff',
                weight: 3,
                opacity: 1,
                fillOpacity: 0.95
            }).addTo(map);
            
            // Focus map on evaluated terrain
            map.panTo([lat, lon]);
            
            // Create mock feature to load selection details
            const mockFeature = {
                properties: {
                    nombre: "Terreno Personalizado",
                    evaluacion: result
                },
                geometry: payload.geometry
            };
            
            // Load and update sidebar displays
            selectTerrainFeature(mockFeature);
            
        } catch (error) {
            console.error("Error al evaluar el terreno: ", error);
            alert("No se pudo conectar con el servidor de evaluación.");
        } finally {
            resetCustomEvaluationMode();
        }
    });
}

function resetCustomEvaluationMode() {
    customEvaluationMode = false;
    const btn = document.getElementById('btn-custom-mode');
    btn.classList.remove('btn-active-custom');
    btn.innerHTML = `<i class="fa-solid fa-crosshairs"></i> Evaluar en el Mapa`;
    document.getElementById('map').style.cursor = '';
}

// Setup report export handler
function setupExportPDF() {
    const btn = document.getElementById('btn-pdf-report');
    
    btn.addEventListener('click', async function() {
        if (!selectedTerrain) return;
        
        const props = selectedTerrain.properties;
        const evalRes = props.evaluacion;
        
        const payload = {
            geometry: selectedTerrain.geometry,
            properties: {
                agua: evalRes.criterios.infraestructura >= 33,
                electricidad: evalRes.criterios.infraestructura >= 66,
                alcantarillado: evalRes.criterios.infraestructura === 100,
                uso_suelo: props.uso_suelo || "Residencial de Expansión",
                area_m2: evalRes.area_m2,
                patrimonial: evalRes.restricciones.some(r => r.includes("patrimonial")),
                industrial_incompatible: evalRes.restricciones.some(r => r.includes("industrial")),
                cerca_rio: evalRes.restricciones.some(r => r.includes("influencia") || r.includes("riesgo"))
            },
            nombre: props.nombre
        };
        
        try {
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generando PDF...`;
            btn.disabled = true;
            
            const response = await fetch('/api/reporte/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) throw new Error("Fallo en la generación de PDF");
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `reporte_${props.nombre.toLowerCase().replace(/ /g, '_')}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error("Error al exportar reporte: ", error);
            alert("No se pudo descargar el reporte PDF.");
        } finally {
            btn.innerHTML = `<i class="fa-solid fa-file-pdf"></i> Descargar Reporte PDF`;
            btn.disabled = false;
        }
    });
}

// Setup Theme switching (Dark/Light)
function setupThemeToggle() {
    const btn = document.getElementById('btn-theme-toggle');
    if (!btn) return;
    
    // Sync initial button icon based on current class
    const isLight = document.body.classList.contains('light-theme');
    const icon = btn.querySelector('i');
    if (icon) {
        icon.className = isLight ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
    }
    
    btn.addEventListener('click', function() {
        const lightModeActive = document.body.classList.toggle('light-theme');
        
        // Update icon and local storage preference
        if (icon) {
            icon.className = lightModeActive ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
        }
        localStorage.setItem('theme', lightModeActive ? 'light' : 'dark');
        
        // Dynamically update Leaflet map tiles
        if (map && tileLayer) {
            const newUrl = lightModeActive 
                ? 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
                : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
            tileLayer.setUrl(newUrl);
        }

        // Redraw terrain layers to apply dynamic stroke colors (white/dark gray)
        if (layers.terrenos) {
            layers.terrenos.setStyle(getTerrainStyle);
        }

        // Update active custom marker border color
        if (customMarker) {
            customMarker.setStyle({
                color: lightModeActive ? '#1E293B' : '#ffffff'
            });
        }

        // Update radar chart colors dynamically on theme toggle click
        if (criteriaChart) {
            criteriaChart.options.scales.r.grid.color = lightModeActive ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.1)';
            criteriaChart.options.scales.r.angleLines.color = lightModeActive ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.1)';
            criteriaChart.options.scales.r.pointLabels.color = lightModeActive ? '#475569' : '#94A3B8';
            criteriaChart.update();
        }
    });
}

// Setup floating layer toggles
function updateCoverageMetrics(metrics) {
    if (!metrics) return;
    document.getElementById('coverage-metrics').classList.remove('hidden');
    document.getElementById('metric-cobertura-pct').textContent = `${metrics.porcentaje_cobertura_urbana}%`;
    document.getElementById('metric-descubierto').textContent = `${metrics.area_descubierta_km2} km²`;
    document.getElementById('metric-h3').textContent = metrics.hospitales_nivel3;
    document.getElementById('metric-h2').textContent = metrics.hospitales_nivel2;
}

function setupLayerToggles() {
    const toggles = {
        'toggle-distritos': 'distritos',
        'toggle-topografia': 'topografia',
        'toggle-vias': 'vias',
        'toggle-cobertura-hospitalaria': 'coberturaHospitalaria',
        'toggle-crecimiento': 'crecimiento',
        'toggle-restringidas': 'restringidas'
    };
    
    for (const id in toggles) {
        const btn = document.getElementById(id);
        if (!btn) continue;
        
        const layerKey = toggles[id];
        
        btn.addEventListener('click', function() {
            if (!layers[layerKey]) {
                console.warn(`La capa ${layerKey} aún no se ha cargado.`);
                return;
            }
            this.classList.toggle('active');
            
            if (this.classList.contains('active')) {
                map.addLayer(layers[layerKey]);
                // When coverage is enabled, also show unified coverage + uncovered areas
                if (layerKey === 'coberturaHospitalaria') {
                    if (layers.coberturaUnificada) map.addLayer(layers.coberturaUnificada);
                    if (layers.areasDescubiertas) map.addLayer(layers.areasDescubiertas);
                }
            } else {
                map.removeLayer(layers[layerKey]);
                // When coverage is disabled, hide unified layers too
                if (layerKey === 'coberturaHospitalaria') {
                    if (layers.coberturaUnificada) map.removeLayer(layers.coberturaUnificada);
                    if (layers.areasDescubiertas) map.removeLayer(layers.areasDescubiertas);
                }
            }
        });
    }
}

// Initialise App on document load
window.addEventListener('DOMContentLoaded', async () => {
    initMap();
    await loadLayers();
    setupWeightSliders();
    setupCustomEvaluation();
    setupExportPDF();
    setupLayerToggles();
    setupThemeToggle();
    
    // Bind specialties filter listener
    const specFilter = document.getElementById('filter-especialidad');
    if (specFilter) {
        specFilter.addEventListener('change', function() {
            filterHospitalesBySpecialty(this.value);
        });
    }

    // Bind scenario select dropdown listener
    const scenSelect = document.getElementById('select-escenario');
    if (scenSelect) {
        scenSelect.addEventListener('change', async function() {
            const scen = this.value;
            await reloadGrowthZones(scen);
            await reloadRestrictedZones(scen);
        });
    }

    // Bind Terrain Comparison button list listener
    const btnAddCompare = document.getElementById('btn-add-compare');
    if (btnAddCompare) {
        btnAddCompare.addEventListener('click', function() {
            if (!selectedTerrain) {
                alert("Selecciona primero un terreno para poder compararlo.");
                return;
            }
            
            const alreadyExists = comparisonList.some(item => {
                return item.properties.nombre === selectedTerrain.properties.nombre &&
                       item.geometry.coordinates[0] === selectedTerrain.geometry.coordinates[0];
            });
            
            if (alreadyExists) {
                alert("Este terreno ya está agregado al comparador.");
                return;
            }
            
            if (comparisonList.length >= 3) {
                alert("Puedes comparar un máximo de 3 terrenos en paralelo.");
                return;
            }
            
            comparisonList.push(selectedTerrain);
            updateComparisonPanel();
        });
    }

    // Bind close comparison button listener
    const btnCloseCompare = document.getElementById('btn-close-comparison');
    if (btnCloseCompare) {
        btnCloseCompare.addEventListener('click', function() {
            comparisonList = [];
            updateComparisonPanel();
        });
    }
});

// Reload growth zones dynamically based on selected scenario
async function reloadGrowthZones(escenario = "moderado") {
    try {
        const res = await fetch(`/api/zonas/crecimiento?escenario=${escenario}`);
        if (res.ok) {
            const data = await res.json();
            if (layers.crecimiento && map.hasLayer(layers.crecimiento)) {
                map.removeLayer(layers.crecimiento);
            }
            layers.crecimiento = L.geoJSON(data, {
                style: {
                    color: '#6366F1',
                    weight: 2.1,
                    opacity: 0.85,
                    fillColor: '#4F46E5',
                    fillOpacity: 0.18
                },
                onEachFeature: function(feature, layer) {
                    const props = feature.properties;
                    layer.bindPopup(`
                        <div class="custom-popup">
                            <h4 class="popup-title" style="color: #6366F1; border-bottom: 1px solid rgba(99, 102, 241, 0.2); padding-bottom: 6px; margin-bottom: 8px; font-weight: 600;"><i class="fa-solid fa-chart-line" style="margin-right: 6px;"></i>${props.nombre}</h4>
                            <p class="popup-detail" style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">${props.descripcion}</p>
                        </div>
                    `, { className: 'custom-popup' });
                }
            });
            if (document.getElementById('toggle-crecimiento').classList.contains('active')) {
                layers.crecimiento.addTo(map);
            }
        }
    } catch (error) {
        console.error("Error al recargar zonas de crecimiento: ", error);
    }
}

// Reload restricted zones dynamically based on selected scenario
async function reloadRestrictedZones(escenario = "moderado") {
    try {
        const res = await fetch(`/api/zonas/restringidas?escenario=${escenario}`);
        if (res.ok) {
            const data = await res.json();
            if (layers.restringidas && map.hasLayer(layers.restringidas)) {
                map.removeLayer(layers.restringidas);
            }
            layers.restringidas = L.geoJSON(data, {
                style: {
                    color: '#EF4444',
                    weight: 2.1,
                    opacity: 0.75,
                    fillColor: '#DC2626',
                    fillOpacity: 0.22,
                    dashArray: '5, 5'
                },
                onEachFeature: function(feature, layer) {
                    const props = feature.properties;
                    layer.bindPopup(`
                        <div class="custom-popup">
                            <h4 class="popup-title" style="color: #EF4444; border-bottom: 1px solid rgba(239, 68, 68, 0.2); padding-bottom: 6px; margin-bottom: 8px; font-weight: 600;"><i class="fa-solid fa-triangle-exclamation" style="margin-right: 6px;"></i>${props.nombre}</h4>
                            <p class="popup-detail" style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">${props.descripcion}</p>
                        </div>
                    `, { className: 'custom-popup' });
                }
            });
            if (document.getElementById('toggle-restringidas').classList.contains('active')) {
                layers.restringidas.addTo(map);
            }
        }
    } catch (error) {
        console.error("Error al recargar zonas restringidas: ", error);
    }
}

// Filter and redraw hospitals on map based on clinical specialty
function filterHospitalesBySpecialty(specialty) {
    if (!rawHospitalesData) return;
    
    layers.coberturaHospitalaria.clearLayers();
    
    L.geoJSON(rawHospitalesData, {
        pointToLayer: function(feature, latlng) {
            const props = feature.properties;
            const specs = props.especialidades || [];
            
            if (specialty && !specs.includes(specialty)) {
                return null;
            }
            
            const htmlIcon = L.divIcon({
                html: `<div class="hospital-marker-icon"><i class="fa-solid fa-square-h"></i></div>`,
                className: 'hospital-marker-container',
                iconSize: [20, 20]
            });
            return L.marker(latlng, { icon: htmlIcon });
        },
        onEachFeature: function(feature, layer) {
            if (!layer) return;
            
            const props = feature.properties;
            const nivel = Number(props.nivel || 0);
            const coverage = getHospitalCoverageConfig(nivel);
            const coordinates = feature.geometry.coordinates;
            const specs = props.especialidades || [];
            
            const specsHtml = specs.map(s => `<span class="badge" style="font-size:9px; background:rgba(16, 185, 129, 0.12); color:var(--accent-primary); padding:2px 6px; border-radius:4px; margin-right:4px; display:inline-block; margin-top:4px;">${s}</span>`).join(' ');

            const popupContent = `
                <div class="custom-popup">
                    <h4 class="popup-title">${props.nombre}</h4>
                    <p class="popup-detail"><strong>Nivel:</strong> ${props.nivel}° Nivel</p>
                    <p class="popup-detail"><strong>Capacidad:</strong> ${props.camas} camas</p>
                    <p class="popup-detail"><strong>Tipo:</strong> ${props.tipo}</p>
                    <p class="popup-detail"><strong>Cobertura:</strong> ${coverage.label} (${coverage.radius / 1000} km)</p>
                    <div style="margin-top: 8px; border-top: 1px solid var(--border-card); padding-top: 6px;">
                        <strong>Especialidades:</strong><br>${specsHtml || 'Ninguna'}
                    </div>
                </div>
            `;
            layer.bindPopup(popupContent, { className: 'custom-popup' });

            if (nivel >= 2) {
                const circle = L.circle([coordinates[1], coordinates[0]], {
                    radius: coverage.radius,
                    color: coverage.color,
                    weight: 1.6,
                    opacity: 0.8,
                    fillColor: coverage.fillColor,
                    fillOpacity: 0.12,
                    dashArray: nivel >= 3 ? '8, 6' : '5, 5'
                }).bindPopup(popupContent, { className: 'custom-popup' });

                layers.coberturaHospitalaria.addLayer(circle);
            }
            layers.coberturaHospitalaria.addLayer(layer);
        }
    });
}

// Side-by-side comparative table renderer for candidate/custom lands
function updateComparisonPanel() {
    const panel = document.getElementById('comparison-panel');
    if (comparisonList.length === 0) {
        panel.classList.add('hidden');
        return;
    }
    
    panel.classList.remove('hidden');
    
    const headersRow = document.getElementById('comparison-headers');
    headersRow.innerHTML = '<th>Criterio / Terreno</th>';
    
    comparisonList.forEach((terrain, index) => {
        headersRow.innerHTML += `
            <th>
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
                    <span style="font-weight:600; color:var(--text-primary); font-size:11px;">${terrain.properties.nombre}</span>
                    <button class="btn-remove-compare" data-index="${index}" style="background:none; border:none; color:var(--accent-danger); cursor:pointer; font-size:12px; display:inline-flex; align-items:center;" title="Remover"><i class="fa-solid fa-trash-can"></i></button>
                </div>
            </th>
        `;
    });
    
    const rows = [
        { label: "Aptitud (IAT)", key: "iat", isMCDA: true },
        { label: "Predicción IA (IAT)", key: "iat_predicho", isML: true },
        { label: "Clasificación IA", key: "apto_predicho", isML: true },
        { label: "Estado General", key: "apto", isMCDA: true },
        { label: "Distrito", key: "distrito", isEval: true },
        { label: "Pendiente (%)", key: "pendiente_pct", isEval: true },
        { label: "Elevación (msnm)", key: "elevacion_m", isEval: true },
        { label: "Distancia a Vías (m)", key: "dist_vias_m", isEval: true },
        { label: "Distancia a Hospitales (m)", key: "dist_hospitales_m", isEval: true },
        { label: "Servicios Básicos", key: "servicios", isCustom: true }
    ];
    
    const rowsContainer = document.getElementById('comparison-rows');
    rowsContainer.innerHTML = '';
    
    rows.forEach(row => {
        let rowHtml = `<tr><td>${row.label}</td>`;
        
        comparisonList.forEach(terrain => {
            const props = terrain.properties;
            const evalRes = props.evaluacion || {};
            let value = "--";
            
            if (row.isMCDA) {
                if (row.key === "iat") {
                    value = `<strong style="color: ${getTerrainColor(evalRes.iat, evalRes.apto)}; font-size: 13px;">${evalRes.iat ? evalRes.iat.toFixed(1) : '0.0'}</strong>`;
                } else if (row.key === "apto") {
                    value = evalRes.apto 
                        ? `<span style="color:var(--accent-primary); font-weight:600;"><i class="fa-solid fa-circle-check"></i> APTO</span>` 
                        : `<span style="color:var(--accent-danger); font-weight:600;"><i class="fa-solid fa-circle-xmark"></i> NO APTO</span>`;
                }
            } else if (row.isML) {
                const mlRes = evalRes.ml_prediccion || {};
                if (row.key === "iat_predicho") {
                    value = mlRes.iat_predicho !== undefined 
                        ? `<strong style="font-size:12px; color:var(--text-primary);">${mlRes.iat_predicho.toFixed(1)}</strong>` 
                        : "N/A";
                } else if (row.key === "apto_predicho") {
                    if (mlRes.apto_predicho !== undefined) {
                        value = mlRes.apto_predicho 
                            ? `<span style="color:var(--accent-primary); font-weight:600;">APTO</span>` 
                            : `<span style="color:var(--accent-danger); font-weight:600;">NO APTO</span>`;
                    } else {
                        value = "N/A";
                    }
                }
            } else if (row.isEval) {
                if (row.key === "pendiente_pct") {
                    value = `${evalRes.pendiente_pct ? evalRes.pendiente_pct.toFixed(1) : '0.0'}%`;
                } else if (row.key === "elevacion_m") {
                    value = `${evalRes.elevacion_m ? evalRes.elevacion_m.toFixed(0) : '0'} m`;
                } else if (row.key === "dist_vias_m") {
                    value = `${evalRes.dist_vias_m ? evalRes.dist_vias_m.toFixed(0) : '0'} m`;
                } else if (row.key === "dist_hospitales_m") {
                    value = `${evalRes.dist_hospitales_m ? evalRes.dist_hospitales_m.toFixed(0) : '0'} m`;
                } else {
                    value = evalRes[row.key] || "--";
                }
            } else if (row.isCustom) {
                if (row.key === "servicios") {
                    const servs = [];
                    if (evalRes.agua) servs.push("Agua");
                    if (evalRes.electricidad) servs.push("Luz");
                    if (evalRes.alcantarillado) servs.push("Alcant.");
                    value = servs.length > 0 ? servs.join(', ') : "Ninguno";
                }
            }
            
            rowHtml += `<td>${value}</td>`;
        });
        
        rowHtml += `</tr>`;
        rowsContainer.innerHTML += rowHtml;
    });
    
    const removeBtns = panel.querySelectorAll('.btn-remove-compare');
    removeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const index = parseInt(this.getAttribute('data-index'));
            comparisonList.splice(index, 1);
            updateComparisonPanel();
        });
    });
}
