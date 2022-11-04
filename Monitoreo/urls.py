from django.urls import path
from Monitoreo import views

urlpatterns = [
    path('camara/', views.vwCamara.as_view()),
    path('entrenamiento-facial/', views.vwEntrenamientoFacial.as_view()),
    path('permisos-objeto/', views.vwPermisosObjetos.as_view()),
    path('configuracion/', views.vwConfiguracion.as_view()),
    path('historial/', views.vwHistorial.as_view()),
    path('grafico/', views.vwGrafico.as_view()),
]