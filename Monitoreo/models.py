from django.db import models
from django.db.models import Q, Value
from django.db.models.functions import Concat
from Persona.models import Supervisados
from Persona.image import Image

# Create your models here.

class TiposDistraccion(models.Model):
    nombre_distraccion = models.CharField(max_length = 25)

class CamarasTutor(models.Model):
    direccion_ip = models.CharField(max_length = 100)
    nombre_camara = models.CharField(max_length = 20)
    habilitada = models.BooleanField()
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "camaras_tutor")

    
    # CRUD


class Monitoreo(models.Model):
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "ajustes_monitoreo") 
    tipo_distraccion = models.ForeignKey('Monitoreo.TiposDistraccion', on_delete = models.PROTECT)

    # CREATE, DELETE

class Objetos(models.Model):
    nombre = models.CharField(max_length = 20)
    foto_objeto = models.ImageField(upload_to = 'Objetos')

class PermisosObjetos(models.Model):
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "objetos_tutor")
    objeto = models.ForeignKey('Monitoreo.Objetos', on_delete = models.PROTECT)

    # CREATE, DELETE

class Historial(models.Model):
    fecha_hora = models.DateTimeField()
    imagen_evidencia = models.ImageField(upload_to = 'Evidencias', null = True, blank = True)
    supervisado = models.ForeignKey('Persona.Supervisados', on_delete = models.PROTECT, related_name = "historial_supervisado")
    tipo_distraccion = models.ForeignKey('Monitoreo.TiposDistraccion', on_delete = models.PROTECT, related_name = "historial_distraccion")

    @staticmethod
    def obtener_historial(request):
        try:
            if 'persona__cedula' in request.GET and 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(Q(persona__cedula__icontains = request.GET['persona__cedula']) & Q(tutor__pk = request.GET['tutor_id']))   
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            elif 'nombres_apellidos' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id']).select_related('persona')).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                supervisados = supervisados.filter(nombres_completos__icontains = request.GET['nombres_apellidos'])
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(cuidador__pk = request.GET['tutor_id'])
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            else:
                supervisados = Supervisados.objects.all()
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            historial = historial.values('id', 'fecha_hora', 'imagen_evidencia', 'supervisado_id', 'supervisado__persona__nombres', 'supervisado__persona__apellidos', 'supervisado__persona__cedula')
            file = Image()
            for u in range(len(historial)):
                historial[u]['fecha_hora'] = historial[u]['fecha_hora'].strftime('%Y-%m-%d %H:%M')
                if(historial[u]['imagen_evidencia'] != ''):
                    file.ruta = historial[u]['imagen_evidencia']
                    historial[u]['imagen_evidencia'] = file.get_base64()
            return list(historial)
        except Exception as e: 
            return 'error'
    
    @staticmethod
    def grafico_sueno(request):
        pass
    
    @staticmethod
    def grafico_objetos(request):
        pass

    @staticmethod
    def grafico_expresion(request):
        try:
            supervisados = Supervisados()
            if 'persona__cedula' in request.GET and 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(Q(persona__cedula__icontains = request.GET['persona__cedula']) & Q(cuidador__pk = request.GET['tutor_id']))
            elif 'nombres_apellidos' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                supervisados = supervisados.filter(nombres_completos__icontains = request.GET['nombres_apellidos'])
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])
            historial_grafico = []
            for supervisado in supervisados: 
                historial = supervisado.historial_supervisado.all().values()
                if (len(historial)):
                    
                    fecha_minima = (historial.order_by('fecha_hora'))[0]['fecha_hora']
                    fecha_maxima = (historial.order_by('-fecha_hora'))[0]['fecha_hora']

                    object_json =  { 
                    'fecha_inicio_fin': 'Desde '+ str(fecha_minima.strftime('%Y-%m-%d %H:%M')) + ' hasta ' + str(fecha_maxima.strftime('%Y-%m-%d %H:%M')),
                    'supervisado__persona__nombres': supervisado.persona.nombres,
                    'supervisado__persona__apellidos': supervisado.persona.apellidos,
                    'supervisado__persona__cedula': supervisado.persona.cedula,
                    'enfadado': (historial.filter(expresion_facial = 'Angry').count()),
                    'asqueado': (historial.filter(expresion_facial = 'Disgusted').count()),
                    'temeroso': (historial.filter(expresion_facial = 'Afraid').count()),
                    'feliz': (historial.filter(expresion_facial = 'Happy').count()),
                    'neutral': (historial.filter(expresion_facial = 'Neutral').count()),
                    'triste': (historial.filter(expresion_facial = 'Sad').count()),
                    'sorprendido': (historial.filter(expresion_facial = 'Surprised').count())
                    }
                    historial_grafico.append(object_json)
            return historial_grafico
        except Supervisados.DoesNotExist:    
            return []
        except Exception as e: 
            return 'error'
