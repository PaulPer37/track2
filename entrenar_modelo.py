import os
import ee
from dotenv import load_dotenv

load_dotenv()

def pre_entrenar():
    PROYECTO_EE = os.getenv('EE_PROJECT_ID')
    RUTA_CREDS = 'google-creds.json'

    if os.path.exists(RUTA_CREDS):
        creds = ee.ServiceAccountCredentials('', RUTA_CREDS)
        ee.Initialize(credentials=creds, project=PROYECTO_EE)
    else:
        ee.Initialize(project=PROYECTO_EE)

    print("Iniciando la recolección de variables predictoras en GEE...")
    dem = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(dem)
    manglares_nasa = ee.ImageCollection("LANDSAT/MANGROVE_FORESTS").mosaic().unmask(0)
    
    jrc_water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence')
    water_label = jrc_water.gt(5).rename('flooded')

    dataset_ml = ee.Image.cat([
        dem.rename('elevation'), 
        slope.rename('slope'), 
        manglares_nasa.rename('mangrove'), 
        water_label
    ])
    
    roi = ee.Geometry.Rectangle([-80.2, -2.4, -79.6, -1.9])
    
    print("Tomando muestras de terreno...")
    training_samples = dataset_ml.sample(region=roi, scale=30, numPixels=1500, seed=42, geometries=True)

    print("Entrenando el algoritmo Random Forest...")
    rf_classifier = ee.Classifier.smileRandomForest(15).train(
        features=training_samples, 
        classProperty='flooded', 
        inputProperties=['elevation', 'slope', 'mangrove']
    )

    asset_id = f"projects/{PROYECTO_EE}/assets/rf_modelo_inundacion"
    
    print(f"Exportando el modelo entrenado a {asset_id}...")
    tarea = ee.batch.Export.classifier.toAsset(
        classifier=rf_classifier,
        description='Exportar_Modelo_Riesgo',
        assetId=asset_id
    )
    
    tarea.start()
    print("Tarea enviada a los servidores de Google.")
    print("El modelo se está guardando de forma permanente.")

if __name__ == "__main__":
    pre_entrenar()