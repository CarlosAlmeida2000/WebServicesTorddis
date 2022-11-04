from rest_framework.views import APIView
from rest_framework.response import Response
from Monitoreo.reconocimiento import ExpresionFacial
from Monitoreo.entrenamiento_facial import EntrenamientoFacial
from .models import *
import json, threading

# Create your views here.
class vwHistorial(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response({'historial': Historial.obtener_historial(request)})
            except Exception as e:
                return Response({'historial': 'error'})

class vwGrafico(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response({'grafico': Historial.obtener_grafico(request)})
            except Exception as e:
                return Response({'grafico': 'error'})

class vwEntrenamientoFacial(APIView):
    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                entrenar_rostros = EntrenamientoFacial(json_data['persona_id'])
                return Response({'entrenamiento_facial': entrenar_rostros.entrenar()})
            except Exception as e: 
                return Response({'entrenamiento_facial': 'error'})

class vwVigilancia(APIView):
    def __init__(self):
        self.expresionFacial = ExpresionFacial()

    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response({'vigilancia': Vigilancia.objects.filter().first().estado})
            except Exception as e:
                return Response({'vigilancia': 'error'})

    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                respuesta = bool(json_data['vigilancia'])
                vigilancia = Vigilancia.objects.filter().first()
                vigilancia.estado = respuesta
                vigilancia.save()
                if respuesta:
                    hilo_vigilar = threading.Thread(target=self.expresionFacial.reconocer)
                    hilo_vigilar.start()
                return Response({'vigilancia': Vigilancia.objects.filter().first().estado})
            except Exception as e: 
                return Response({'vigilancia': 'error'})