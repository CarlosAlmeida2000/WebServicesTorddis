from rest_framework.views import APIView
from rest_framework.response import Response
from .models import *
import json

# Create your views here.
class vwTutor(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response(Tutores.obtener_datos(request))
            except Exception as e:
                return Response({'tutores': 'error'})
        
    def post(self, request, format = None):
        if request.method == 'POST':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                tutores = Tutores()
                return Response({'tutores': tutores.guardar(json_data)})
            except Exception as e: 
                return Response({'tutores': 'error'})
    
    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                tutores = Tutores.objects.get(id = json_data['id'])
                return Response({'tutores': tutores.guardar(json_data)})
            except Exception as e: 
                return Response({'tutores': 'error'})

class vwAutenticacion(APIView):
    def post(self, request, format = None):
        if request.method == 'POST':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                return Response(Tutores.login(json_data))
            except Exception as e: 
                return Response({'tutores': 'error'})

class vwSupervisados(APIView):
    def get(self, request, format = None):
        if request.method == 'GET':
            try:
                return Response(Supervisados.obtener_datos(request))
            except Exception as e:
                return Response({'supervisados': 'error'})

    def post(self, request, format = None):
        if request.method == 'POST':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                supervisados = Supervisados()
                return Response({'supervisados': supervisados.guardar(json_data)})
            except Exception as e: 
                return Response({'supervisados': 'error'})

    def put(self, request, format = None):
        if request.method == 'PUT':
            try:
                json_data = json.loads(request.body.decode('utf-8'))
                supervisados = Supervisados.objects.get(id = json_data['id'])
                return Response({'supervisados': supervisados.guardar(json_data)})
            except Exception as e: 
                return Response({'supervisados': 'error'})