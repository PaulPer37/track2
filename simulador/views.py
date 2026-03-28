import os
import ee
import folium
from folium import plugins
import requests
from django.shortcuts import render
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

def obtener_clima_manana():
    url = "https://api.open-meteo.com/v1/forecast?latitude=-2.1962&longitude=-79.8862&daily=precipitation_sum&timezone=America%2FGuayaquil&forecast_days=2"
    try:
        respuesta = requests.get(url, timeout=5)
        datos = respuesta.json()
        return float(datos['daily']['precipitation_sum'][1])
    except:
        return 0.0

def index(request):
    PROYECTO_EE = os.getenv('EE_PROJECT_ID')
    RUTA_CREDS = os.path.join(settings.BASE_DIR, 'google-creds.json')

    try:
        if os.path.exists(RUTA_CREDS):
            creds = ee.ServiceAccountCredentials('', RUTA_CREDS)
            ee.Initialize(credentials=creds, project=PROYECTO_EE)
        else:
            ee.Initialize(project=PROYECTO_EE)
    except Exception as e:
        print(f"Error GEE: {e}")

    if request.method == 'POST':
        lluvia = float(request.POST.get('lluvia', 0.0))
    else:
        lluvia = obtener_clima_manana()

    # --- CÁLCULOS DINÁMICOS GEE (CROSS-DATA) ---
    poblacion_conteo = 0
    hectareas_manglar = 0

    try:
        # 1. Definir Geometrías y Capas Base
        guayaquil = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.eq('ADM2_NAME', 'Guayaquil'))
        dem = ee.Image("USGS/SRTMGL1_003")
        
        # 2. Modelo de Inundación
        umbral = lluvia / 20.0
        mascara_inundacion = dem.updateMask(dem.gt(0)).lte(umbral).clip(guayaquil)
        
        # 3. Módulo Población (WorldPop + WSF para filtrar áreas urbanas)
        wsf = ee.Image("DLR/WSF/WSF2015/v1")
        worldpop = ee.ImageCollection("WorldPop/GP/100m/pop").mosaic()
        poblacion_riesgo = worldpop.updateMask(wsf.gt(0)).updateMask(mascara_inundacion)
        
        # Reducción de Población
        stats_pob = poblacion_riesgo.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=guayaquil.geometry(),
            scale=100,
            maxPixels=1e9
        ).getInfo()
        poblacion_conteo = int(list(stats_pob.values())[0] or 0)

        # 4. Módulo Manglares (NASA Landsat Mangrove Forests)
        manglares = ee.ImageCollection("LANDSAT/MANGROVE_FORESTS").mosaic().clip(guayaquil)
        area_manglar = manglares.gt(0).multiply(ee.Image.pixelArea())
        
        stats_manglar = area_manglar.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=guayaquil.geometry(),
            scale=30,
            maxPixels=1e9
        ).getInfo()
        hectareas_manglar = round((list(stats_manglar.values())[0] or 0) / 10000, 2)

    except Exception as e:
        print(f"Error en cálculos dinámicos: {e}")

    # --- RENDERIZADO DEL MAPA ---
    m = folium.Map(location=[-2.18, -79.90], zoom_start=11, tiles='CartoDB voyager')
    
    # Capa Visual Manglares
    try:
        manglares_vis = manglares.updateMask(manglares.gt(0))
        map_id_m = manglares_vis.getMapId({'palette': ['#2ecc71']})
        folium.TileLayer(tiles=map_id_m['tile_fetcher'].url_format, attr='NASA', overlay=True, name='Manglares').add_to(m)
        
        # Capa Visual Inundación
        if lluvia > 0:
            riesgo_vis = mascara_inundacion.updateMask(mascara_inundacion.eq(1))
            map_id_r = riesgo_vis.getMapId({'palette': ['#0074D9']})
            folium.TileLayer(tiles=map_id_r['tile_fetcher'].url_format, attr='GEE', overlay=True, name='Zona Inundable').add_to(m)
    except: pass

    folium.LayerControl().add_to(m)

    contexto = {
        'mapa': m.get_root().render(),
        'lluvia_actual': lluvia,
        'poblacion_riesgo': poblacion_conteo,
        'hectareas_manglar': hectareas_manglar,
        'perdida_estatica': 227.52
    }
    return render(request, 'simulador/index.html', contexto)