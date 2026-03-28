import os
import ee
import folium
import geopandas as gpd
from django.shortcuts import render
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

def index(request):
    PROYECTO_EE = os.getenv('EE_PROJECT_ID')

    try:
        ee.Initialize(project=PROYECTO_EE)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROYECTO_EE)

    # 1. Leer los datos enviados por el usuario en la barra lateral
    anio = request.POST.get('anio', '2018')
    lluvia = float(request.POST.get('lluvia', 70.0))
    marea = float(request.POST.get('marea', 5.0))

    # 2. SOLUCIÓN AL ERROR: Usamos 'cartodbpositron' como mapa base
    m = folium.Map(location=[-2.15, -79.9], zoom_start=11, tiles='cartodbpositron')

    # Topografía (DEM)
    dem = ee.Image("USGS/SRTMGL1_003")
    
    # 3. Lógica de Simulación de Inundación
    # Calculamos el umbral crítico de agua y creamos una máscara booleana
    nivel_agua = marea + (lluvia / 50.0)
    zonas_inundadas = dem.lte(nivel_agua)
    
    # Ocultamos los píxeles secos para dejar solo el agua visible
    inundacion_transparente = zonas_inundadas.updateMask(zonas_inundadas)
    
    vis_params_agua = {'min': 0, 'max': 1, 'palette': ['blue']}
    map_id_agua = ee.Image(inundacion_transparente).getMapId(vis_params_agua)
    
    folium.TileLayer(
        tiles=map_id_agua['tile_fetcher'].url_format,
        attr='GEE', overlay=True, name=f'Inundación ({lluvia}mm, {marea}m)'
    ).add_to(m)

    # 4. Integrar tus Datasets Locales (Los shapefiles)
    # Buscamos en la carpeta 'datos' que creamos anteriormente
    ruta_shp = os.path.join(settings.BASE_DIR, 'datos', anio, f'MAN_{anio}.shp')
    
    if os.path.exists(ruta_shp):
        manglares_gdf = gpd.read_file(ruta_shp)
        
        # Agregamos los polígonos al mapa con estilo verde transparente
        folium.GeoJson(
            manglares_gdf,
            name=f'Manglares {anio}',
            style_function=lambda feature: {
                'fillColor': '#27ae60',
                'color': '#145a32',
                'weight': 1,
                'fillOpacity': 0.6,
            }
        ).add_to(m)

    # Agregamos el control de capas
    folium.LayerControl().add_to(m)
    mapa_html = m.get_root().render()

    # Enviamos todo de vuelta al Frontend
    contexto = {
        'mapa': mapa_html,
        'anio_actual': anio,
        'lluvia_actual': lluvia,
        'marea_actual': marea
    }
    
    return render(request, 'simulador/index.html', contexto)