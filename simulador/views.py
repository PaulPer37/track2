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
        lluvia_manana = datos['daily']['precipitation_sum']
        return float(lluvia_manana)
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
        print(f"Error de autenticación GEE: {e}")

    if request.method == 'POST':
        lluvia = float(request.POST.get('lluvia', 0.0))
    else:
        lluvia = obtener_clima_manana()

    m = folium.Map(
        location=[-2.18, -79.90], 
        zoom_start=11, 
        tiles='CartoDB voyager',
        min_zoom=9,
        max_bounds=True
    )
    
    m.fit_bounds([[-3.2, -80.6], [-1.0, -79.0]])

    plugins.Geocoder(
        position='topright',
        add_marker=True,
        provider='nominatim',
        provider_options={
            'geocodingQueryParams': {
                'countrycodes': 'ec',
                'viewbox': '-81.0,-1.0,-79.0,-3.3',
                'bounded': 1
            }
        }
    ).add_to(m)

    # 1. OPTIMIZACIÓN EXTREMA: Delegamos los manglares a Google Earth Engine
    # Ya no leemos archivos .shp locales, Google renderiza los tiles instantáneamente
    try:
        manglares_nasa = ee.ImageCollection("LANDSAT/MANGROVE_FORESTS").mosaic()
        manglares_mask = manglares_nasa.updateMask(manglares_nasa.gt(0))
        map_id_manglar = ee.Image(manglares_mask).getMapId({'min': 0, 'max': 1, 'palette': ['#2ecc71']})
        
        folium.TileLayer(
            tiles=map_id_manglar['tile_fetcher'].url_format, 
            attr='GEE NASA', 
            overlay=True, 
            name='Barrera Natural (Manglares)',
            opacity=0.35
        ).add_to(m)
    except Exception as e:
        print(f"Error cargando manglares GEE: {e}")

    # 2. Lógica de Riesgo de Inundación
    dem = ee.Image("USGS/SRTMGL1_003")
    tierra_firme = dem.gt(0)
    dem_terrestre = dem.updateMask(tierra_firme)

    umbral_inundacion = lluvia / 20.0 
    
    if lluvia > 0:
        zonas_riesgo = dem_terrestre.lte(umbral_inundacion)
        riesgo_mask = zonas_riesgo.updateMask(zonas_riesgo.eq(1))
        
        map_id_riesgo = ee.Image(riesgo_mask).getMapId({'min': 0, 'max': 1, 'palette': ['#0074D9']})
        
        folium.TileLayer(
            tiles=map_id_riesgo['tile_fetcher'].url_format, 
            attr='GEE', 
            overlay=True, 
            name=f'Riesgo Inundación ({lluvia}mm)',
            opacity=0.35
        ).add_to(m)

    folium.LayerControl().add_to(m)
    mapa_html = m.get_root().render()

    # El cálculo de pérdida de hectáreas es estático (2018-2022). 
    # Lo inyectamos directo para no consumir RAM del servidor.
    contexto = {
        'mapa': mapa_html,
        'lluvia_actual': lluvia,
        'hectareas_perdidas': 227.52
    }
    
    return render(request, 'simulador/index.html', contexto)