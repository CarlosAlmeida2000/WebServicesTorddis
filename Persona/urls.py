from django.urls import path
from Persona import views

urlpatterns = [
    path('tutor/', views.vwTutor.as_view()),
    path('autenticacion/', views.vwAutenticacion.as_view()),
    path('supervisado/', views.vwSupervisados.as_view())
]