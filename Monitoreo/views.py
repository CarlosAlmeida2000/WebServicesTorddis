from Monitoreo.entrenamiento_facial import EntrenamientoFacial
from Monitoreo.reconocimiento import Vigilancia
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
import json

# Create your views here.
class vwCamara(APIView):

    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response(Camaras.obtener_datos(request))
            except Exception as e:
                return Response({'camara': 'error'})

    def post(self, request, format = None):
        if request.method == 'POST':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                camara = Camaras()
                return Response({'camara': camara.guardar(json_data)})
            except Exception as e: 
                return Response({'camara': 'error'})

    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                camara = Camaras.objects.get(pk = json_data['id'])
                return Response({'camara': camara.guardar(json_data)})
            except Exception as e: 
                return Response({'camara': 'error'})

class vwEntrenamientoFacial(APIView):

    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response(Camaras.obtener_datos(request))
            except Exception as e:
                return Response({'camara': 'error'})

    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                entrenar_rostros = EntrenamientoFacial(json_data['supervisado_id'])
                return Response({'entrenamiento_facial': entrenar_rostros.entrenar()})
            except Exception as e: 
                return Response({'entrenamiento_facial': 'error'})

class vwPermisosObjetos(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response(PermisosObjetos.obtener_datos(request))
            except Exception as e:
                return Response({'objetos': 'error'})
    
    def post(self, request, format = None):
        if request.method == 'POST':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                permiso = PermisosObjetos()
                return Response({'objetos': permiso.activar(json_data)})
            except Exception as e: 
                return Response({'objetos': 'error'})

    def delete(self, request, format = None):
        if request.method == 'DELETE':
            try:
                permiso = PermisosObjetos()
                return Response({'objetos': permiso.desactivar(request)})
            except Exception as e: 
                return Response({'objetos': 'error'})

class vwTiposDistraccion(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response(Monitoreo.obtener_datos(request))
            except Exception as e:
                return Response({'monitoreo': 'error'})

    def post(self, request, format = None):
        if request.method == 'POST':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                monitoreo = Monitoreo()
                respuesta = monitoreo.activar(json_data)
                if respuesta != 'error':
                    vigilancia = Vigilancia(tutor_id = json_data['tutor_id'])
                    hilo_vigilar = threading.Thread(target = vigilancia.iniciar)
                    hilo_vigilar.start()
                return Response({'monitoreo': respuesta})
            except Exception as e: 
                return Response({'monitoreo': 'error'})
        
    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                vigilancia = Vigilancia(tutor_id = 1)
                hilo_vigilar = threading.Thread(target = vigilancia.iniciar)
                hilo_vigilar.start()
                return Response({'monitoreo': 'monitoreando.....'})
            except Exception as e: 
                return Response({'monitoreo': 'error'})

    def delete(self, request, format = None):
        if request.method == 'DELETE':
            try:
                monitoreo = Monitoreo()
                return Response({'monitoreo': monitoreo.desactivar(request)})
            except Exception as e: 
                return Response({'monitoreo': 'error'})

class vwHistorial(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response(Historial.obtener_datos(request))
            except Exception as e:
                return Response({'historial': 'error'})

class vwGrafico(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response(Historial.graficos(request))
            except Exception as e:
                return Response({'grafico': 'error'})