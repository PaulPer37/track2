## ⚙️ Configuración de Google Earth Engine (GEE)

Para que la simulación satelital funcione, el sistema necesita conectarse a la nube de Google Earth Engine. Debes seguir estos pasos antes de levantar el servidor:

### 1. Requisitos Previos
Debes tener una cuenta de Google registrada en [Google Earth Engine](https://earthengine.google.com/) y un Proyecto de Google Cloud con la API de Earth Engine habilitada.

### 2. Variables de Entorno
En la raíz del proyecto (al mismo nivel que el archivo `manage.py`), crea un archivo llamado exactamente `.env`. Dentro de este archivo, coloca el ID de tu proyecto de Google Cloud de la siguiente manera:

\`\`\`env
EE_PROJECT_ID=el-id-de-tu-proyecto-aqui
\`\`\`

### 3. Autenticación Local
Antes de correr la aplicación por primera vez, debes autorizar a tu computadora para que consuma los recursos de GEE. Abre tu terminal con el entorno virtual activado y ejecuta:

\`\`\`bash
earthengine authenticate
\`\`\`

Esto abrirá una pestaña en tu navegador web. Inicia sesión con tu cuenta de Google, selecciona tu proyecto, genera el token de acceso y pégalo de vuelta en la terminal si te lo solicita. 

Una vez autenticado, ya puedes iniciar el servidor con `python manage.py runserver` y el modelo de Machine Learning funcionará correctamente.