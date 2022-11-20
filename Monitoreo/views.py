from Monitoreo.entrenamiento_facial import EntrenamientoFacial
from Monitoreo.reconocimiento import Monitorizar
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

    def delete(self, request, format = None):
        if request.method == 'DELETE':
            try:
                if 'id' in request.GET:
                    camara = Camaras.objects.get(pk = request.GET['id'])
                elif 'direccion_ip' in request.GET:
                    camara = Camaras.objects.get(direccion_ip = request.GET['direccion_ip'])
                camara.delete()
                return Response({'camara': 'eliminada'})
            except Camaras.DoesNotExist:
                return Response({'camara': 'error'})
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
                entrenar_rostros = EntrenamientoFacial(json_data['persona_id'], json_data['camara_id'])
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
                return Response({'camara': permiso.activar(json_data)})
            except Exception as e: 
                return Response({'camara': 'error'})

    def delete(self, request, format = None):
        if request.method == 'DELETE':
            try:
                permiso = PermisosObjetos()
                return Response({'camara': permiso.desactivar(request)})
            except Exception as e: 
                return Response({'camara': 'error'})

class vwConfiguracion(APIView):
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
                return Response({'monitoreo': monitoreo.activar(json_data)})
            except Exception as e: 
                return Response({'monitoreo': 'error'})

    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                monitoreo = Monitorizar()
                hilo_vigilar = threading.Thread(target=monitoreo.reconocer)
                hilo_vigilar.start()
                # POR CADA CAMARA HABILITADA SE CREA UN HILO DE VIGILANCIA 
                    # for camara in Camaras.objects.filter(Q(tutor_id = json_data['tutor_id']) & Q(habilitada = True)):
                    #     monitoreo = Monitorizar()
                    #     hilo_vigilar = threading.Thread(target=monitoreo.reconocer, args=(camara.direccion_ip,))
                    #     hilo_vigilar.start()
                return Response({'monitoreo': 'monitoreando........'})
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
                if request.GET['tipo_grafico'] == 'grafico_sueno':
                    return Response(Historial.grafico_sueno(request))
                elif request.GET['tipo_grafico'] == 'grafico_objetos':
                    return Response(Historial.grafico_objetos(request))
                else:
                    return Response(Historial.grafico_expresion(request))
            except Exception as e:
                return Response({'grafico': 'error'})