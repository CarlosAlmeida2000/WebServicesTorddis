from Monitoreo.entrenamiento_facial import EntrenamiFacial
from Monitoreo.reconocimiento import Vigilancia
from django.http import StreamingHttpResponse,HttpResponseServerError
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
import json, cv2, threading
from .models import *

# Create your views here.
vigilancia = Vigilancia()
entrenar_rostros = EntrenamiFacial()

class vWvideo(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                if 'tipo' in request.GET:
                    if request.GET['tipo'] == 'monitoreo':
                        return StreamingHttpResponse(vWvideo.trans_monitoreo(), content_type="multipart/x-mixed-replace;boundary=frame")
                    elif request.GET['tipo'] == 'entrenamiento':
                        return StreamingHttpResponse(vWvideo.trans_entrena(), content_type="multipart/x-mixed-replace;boundary=frame")
            except Exception as e:
                return Response({'video': 'error'})
    
    @staticmethod
    def trans_monitoreo():
        while not vigilancia.fin_vigilancia:
            _, png = cv2.imencode('.png', vigilancia.video)
            imagen = png.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/png\r\n\r\n' + imagen + b'\r\n\r\n')
    
    @staticmethod
    def trans_entrena():
        while not entrenar_rostros.fin_entrenamiento:
            _, png = cv2.imencode('.png', entrenar_rostros.video)
            imagen = png.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/png\r\n\r\n' + imagen + b'\r\n\r\n')

#Mostrar template                
def streamEntrenamiento(request): 
        template = "streamEntrenamiento.html"
        return render(request,template)

def streamMonitoreo(request): 
        template = "streamMonitoreo.html"
        return render(request,template)

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
                entrenar_rostros.inicializar()
                entrenar_rostros.supervisado_id = json_data['supervisado_id']
                entrenar_rostros.tutor_id = json_data['tutor_id']
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
                fallo, mensaje = monitoreo.activar(json_data)
                
                if fallo != 'error' and (vigilancia.fin_vigilancia or len(Monitoreo.objects.filter(tutor_id = json_data['tutor_id'])) == 1):
                    vigilancia.inicializar()
                    vigilancia.tutor_id = json_data['tutor_id']
                    hilo_vigilar = threading.Thread(target = vigilancia.iniciar)
                    hilo_vigilar.start()
                return Response({'monitoreo': mensaje})
            except Exception as e: 
                return Response({'monitoreo': 'error'})
        
    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                if 'tutor_id' in request.GET:
                    vigilancia.inicializar()
                    vigilancia.tutor_id = request.GET['tutor_id']
                    hilo_vigilar = threading.Thread(target = vigilancia.iniciar)
                    hilo_vigilar.start()
                    return Response({'monitoreo': 'monitoreando.....'})
                return Response({'monitoreo': 'error'})
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

class vwDistraccion(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response({'distraccion': Monitoreo.existe_distraccion(request)})
            except Exception as e:
                return Response({'distraccion': 'error'})