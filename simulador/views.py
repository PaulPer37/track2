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
        primer_dia = datos['daily']['precipitation_sum'].pop(0)
        return float(primer_dia)
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
        if request.POST.get('pronostico_manana'):
            lluvia = obtener_clima_manana()
            marea = 3.5 
        else:
            lluvia = float(request.POST.get('lluvia', 0.0))
            marea = float(request.POST.get('marea', 0.0))
    else:
        lluvia = obtener_clima_manana()
        marea = 0.0

    poblacion_conteo = 0
    hectareas_manglar = 0
    
    # Mapa base configurado para zoom profundo
    m = folium.Map(
        location=[-2.18, -79.90], 
        zoom_start=11, 
        min_zoom=9,
        max_zoom=22,
        tiles='CartoDB voyager',
        max_bounds=True
    )
    
    m.fit_bounds([[-3.2, -80.6], [-1.0, -79.0]])

    try:
        guayaquil = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.eq('ADM2_NAME', 'Guayaquil'))
        dem = ee.Image("USGS/SRTMGL1_003")
        slope = ee.Terrain.slope(dem)
        tierra_firme = dem.gt(0)
        dem_terrestre = dem.updateMask(tierra_firme)
        manglares = ee.ImageCollection("LANDSAT/MANGROVE_FORESTS").mosaic().unmask(0)
        
        # EL ARREGLO: Distancia euclidiana directa pero con un radio máximo de 1500m 
        # Esto es rápido de procesar y nunca confunde metros con píxeles.
        agua_global = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        agua_mask = agua_global.select('max_extent').eq(1)
        dist_agua = agua_mask.distance(ee.Kernel.euclidean(1500, 'meters'))

        imagen_clasificar = ee.Image.cat([
            dem_terrestre.rename('elevation'), 
            slope.rename('slope'), 
            manglares.rename('mangrove'),
            dist_agua.rename('dist_water')
        ])

        mascara_lluvia_ia = ee.Image(0)
        mascara_marea_ia = ee.Image(0)
        modelos_listos = False
        
        try:
            asset_lluvia = f"projects/{PROYECTO_EE}/assets/rf_modelo_lluvia"
            asset_marea = f"projects/{PROYECTO_EE}/assets/rf_modelo_marea"
            
            rf_lluvia = ee.Classifier.load(asset_lluvia)
            rf_marea = ee.Classifier.load(asset_marea)
            
            prediccion_lluvia = imagen_clasificar.classify(rf_lluvia)
            prediccion_marea = imagen_clasificar.classify(rf_marea)
            
            umbral_lluvia = lluvia / 15.0
            mascara_lluvia_ia = prediccion_lluvia.eq(1).And(dem_terrestre.lte(umbral_lluvia))
            
            umbral_marea = marea / 1.5
            # OBLIGAMOS a la IA a respetar la regla de estar a menos de 1500m del agua
            mascara_marea_ia = prediccion_marea.eq(1).And(dem_terrestre.lte(umbral_marea)).And(dist_agua.lt(1500))
            
            modelos_listos = True
        except Exception as e:
            print(f"Usando heurística veloz: {e}")
            umbral_lluvia = lluvia / 20.0
            mascara_lluvia_ia = dem_terrestre.lte(umbral_lluvia)
            
            umbral_marea = marea / 1.5
            # OBLIGAMOS al modelo físico a respetar la regla de los 1500m
            mascara_marea_ia = dem_terrestre.lte(umbral_marea).And(dist_agua.lt(1500))

        # Solución Z-Fighting (Le quitamos a la lluvia lo que ya es marea)
        mascara_lluvia_pura = mascara_lluvia_ia.And(mascara_marea_ia.Not())

        riesgo_total = mascara_lluvia_pura.Or(mascara_marea_ia)
        wsf = ee.Image("DLR/WSF/WSF2015/v1")
        worldpop = ee.ImageCollection("WorldPop/GP/100m/pop").mosaic()
        poblacion_riesgo = worldpop.updateMask(wsf.gt(0)).updateMask(riesgo_total.eq(1))
        
        if lluvia > 0 or marea > 0:
            stats_pob = poblacion_riesgo.reduceRegion(
                reducer=ee.Reducer.sum(), geometry=guayaquil.geometry(),
                scale=250, maxPixels=1e9
            ).getInfo()
            
            valores_pob = list(stats_pob.values())
            if len(valores_pob) > 0 and valores_pob is not None:
                poblacion_conteo = int(valores_pob.pop(0))

        area_manglar = manglares.gt(0).multiply(ee.Image.pixelArea())
        stats_manglar = area_manglar.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=guayaquil.geometry(),
            scale=100, maxPixels=1e9
        ).getInfo()
        
        valores_manglar = list(stats_manglar.values())
        if len(valores_manglar) > 0 and valores_manglar is not None:
            valor_real = valores_manglar.pop(0)
            hectareas_manglar = round(valor_real / 10000, 2)

        # --- RENDERIZADO VISUAL EN FOLIUM ---
        manglares_vis = manglares.updateMask(manglares.gt(0))
        map_id_m = manglares_vis.getMapId({'min': 0, 'max': 1, 'palette': ['#2ecc71']})
        
        folium.TileLayer(
            tiles=map_id_m['tile_fetcher'].url_format, 
            attr='NASA', overlay=True, name='Manglares', opacity=0.4
        ).add_to(m)
        
        prefijo_nombre = "IA -" if modelos_listos else "Físico -"

        if lluvia > 0:
            riesgo_vis_lluvia = mascara_lluvia_pura.updateMask(mascara_lluvia_pura.eq(1))
            map_id_ll = riesgo_vis_lluvia.getMapId({'min': 0, 'max': 1, 'palette': ['#3498db']})
            
            folium.TileLayer(
                tiles=map_id_ll['tile_fetcher'].url_format, 
                attr='GEE', overlay=True, name=f'{prefijo_nombre} Lluvia ({lluvia}mm)', opacity=0.6, control=True
            ).add_to(m)

        if marea > 0:
            riesgo_vis_marea = mascara_marea_ia.updateMask(mascara_marea_ia.eq(1))
            map_id_ma = riesgo_vis_marea.getMapId({'min': 0, 'max': 1, 'palette': ['#9b59b6']}) 
            
            folium.TileLayer(
                tiles=map_id_ma['tile_fetcher'].url_format, 
                attr='GEE', overlay=True, name=f'{prefijo_nombre} Marea ({marea}m)', opacity=0.6, control=True
            ).add_to(m)

    except Exception as e:
        print(f"Error crítico en cálculos: {e}")

    folium.LayerControl().add_to(m)

    contexto = {
        'mapa': m.get_root().render(),
        'lluvia_actual': lluvia,
        'marea_actual': marea,
        'poblacion_riesgo': f"{poblacion_conteo:,}", 
        'hectareas_manglar': f"{hectareas_manglar:,}"
    }
    return render(request, 'simulador/index.html', contexto)