Simulador de Resiliencia Costera: Gran Guayaquil

Plataforma web desarrollada con Django y Google Earth Engine para simular el riesgo de inundaciones y visualizar la protección natural que ofrecen los ecosistemas de manglar frente a escenarios de lluvias extremas y mareas altas.

Desarrollado por
Paúl Perdomo - Ciencias de la Computación, ESPOL

Requisitos Previos

    Python 3.12 o superior

    Cuenta activa en Google Earth Engine con Project ID

Instalación y Ejecución

    Clonar el repositorio:
    git clone URL_DE_TU_REPOSITORIO
    cd hackaton

    Crear y activar el entorno virtual:
    python3 -m venv env
    source env/bin/activate

    Instalar dependencias:
    pip install -r requirements.txt

    Configurar variables de entorno:
    Crea un archivo .env en la raíz del proyecto y añade el ID de proyecto de Google Earth Engine:
    EE_PROJECT_ID=tu-id-de-proyecto-aqui

    Añadir los Datasets (Archivos Vectoriales):
    Descarga los shapefiles de cobertura de manglar y colócalos manteniendo esta estructura de directorios:
    datos/2022/MAN_2022.shp (junto con sus archivos .dbf, .shx y .prj asociados).

    Ejecutar el servidor local:
    python manage.py migrate
    python manage.py runserver

El proyecto estará disponible localmente en http://127.0.0.1:8000/