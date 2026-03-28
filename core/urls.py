from django.contrib import admin
from django.urls import path, include  # <-- ¡Aquí es donde debe estar "include"!

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('simulador.urls')),
]