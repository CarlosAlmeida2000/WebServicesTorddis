from django.urls import path
from Monitoreo import views

urlpatterns = [
    path('video/', views.vWvideo.as_view()),
    path('camara/', views.vwCamara.as_view()),
    path('entrenamiento-facial/', views.vwEntrenamientoFacial.as_view()),
    path('permisos-objeto/', views.vwPermisosObjetos.as_view()),
    path('tipos-distraccion/', views.vwTiposDistraccion.as_view()),
    path('historial/', views.vwHistorial.as_view()),
    path('graficos/', views.vwGrafico.as_view()),
    path('distraccion/', views.vwDistraccion.as_view()),
    path('stream-entrenamiento/',views.streamEntrenamiento),
    path('stream-monitoreo/',views.streamMonitoreo),
]