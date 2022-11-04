from django.urls import path
from Monitoreo import views

urlpatterns = [
    path('historial/', views.vwHistorial.as_view()),
    path('grafico/', views.vwGrafico.as_view()),
    path('entrenamiento-facial/', views.vwEntrenamientoFacial.as_view()),
    path('vigilancia/', views.vwVigilancia.as_view())
]