import os
import ee
from dotenv import load_dotenv

load_dotenv()

def entrenar_y_exportar():
    PROYECTO_EE = os.getenv('EE_PROJECT_ID')
    RUTA_CREDS = 'google-creds.json'

    if os.path.exists(RUTA_CREDS):
        creds = ee.ServiceAccountCredentials('', RUTA_CREDS)
        ee.Initialize(credentials=creds, project=PROYECTO_EE)
    else:
        ee.Initialize(project=PROYECTO_EE)

    print("Preparando variables predictoras...")
    dem = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(dem)
    manglares = ee.ImageCollection("LANDSAT/MANGROVE_FORESTS").mosaic().unmask(0)
    agua_global = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
    
    distancia_agua = agua_global.select('max_extent').eq(1).distance(ee.Kernel.euclidean(5000, 'meters'))
    
    # --- LAS NUEVAS ETIQUETAS A PRUEBA DE FALLOS ---
    # Lluvia: Zonas propensas a acumular agua (elevación < 15m, planas < 5°) y lejos del estero (>500m)
    label_lluvia = dem.lt(15).And(slope.lt(5)).And(distancia_agua.gt(500)).rename('riesgo')
    
    # Marea: Zonas que históricamente tienen agua (max_extent) y están pegadas al estero (<= 1000m)
    label_marea = agua_global.select('max_extent').eq(1).And(distancia_agua.lte(1000)).rename('riesgo')

    dataset_base = ee.Image.cat([
        dem.rename('elevation'), 
        slope.rename('slope'), 
        manglares.rename('mangrove'),
        distancia_agua.rename('dist_water')
    ])
    
    dataset_lluvia = dataset_base.addBands(label_lluvia)
    dataset_marea = dataset_base.addBands(label_marea)
    
    roi = ee.Geometry.Rectangle([-80.2, -2.4, -79.6, -1.9])
    
    # --- MUESTREO ESTRATIFICADO ---
    # Esto OBLIGA a GEE a tomar 1000 puntos de Clase 0 y 1000 puntos de Clase 1.
    # Así garantizamos que NUNCA vuelva a salir el error "Only one class"
    print("Extrayendo muestras balanceadas...")
    muestras_lluvia = dataset_lluvia.stratifiedSample(
        numPoints=1000, classBand='riesgo', region=roi, scale=100, seed=42
    )
    muestras_marea = dataset_marea.stratifiedSample(
        numPoints=1000, classBand='riesgo', region=roi, scale=100, seed=42
    )

    print("Entrenando Bosques Aleatorios (Random Forest)...")
    rf_lluvia = ee.Classifier.smileRandomForest(15).train(
        features=muestras_lluvia, classProperty='riesgo', 
        inputProperties=['elevation', 'slope', 'mangrove', 'dist_water']
    )
    
    rf_marea = ee.Classifier.smileRandomForest(15).train(
        features=muestras_marea, classProperty='riesgo', 
        inputProperties=['elevation', 'slope', 'mangrove', 'dist_water']
    )

    asset_lluvia = f"projects/{PROYECTO_EE}/assets/rf_modelo_lluvia"
    asset_marea = f"projects/{PROYECTO_EE}/assets/rf_modelo_marea"
    
    print("Enviando tareas a Google Earth Engine...")
    tarea_lluvia = ee.batch.Export.classifier.toAsset(
        classifier=rf_lluvia, description='Exportar_RF_Lluvia_V2', assetId=asset_lluvia
    )
    tarea_marea = ee.batch.Export.classifier.toAsset(
        classifier=rf_marea, description='Exportar_RF_Marea_V2', assetId=asset_marea
    )
    
    tarea_lluvia.start()
    tarea_marea.start()
    
    print("✅ ¡Tareas enviadas! Ve a la pestaña Tasks en GEE para ver el progreso.")

if __name__ == "__main__":
    entrenar_y_exportar()