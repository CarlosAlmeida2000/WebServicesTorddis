from django.db import models
from django.db import transaction
from django.db.models import Q, Value, BooleanField
from django.db.models.functions import Concat
from Persona.models import Supervisados, Tutores
from Persona.image import Image

# Create your models here.
class TiposDistraccion(models.Model):
    nombre = models.CharField(max_length = 25)

class Camaras(models.Model):
    direccion_ip = models.CharField(max_length = 100)
    nombre_camara = models.CharField(max_length = 20)
    habilitada = models.BooleanField()
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "camaras_tutor")

    @staticmethod
    def obtener_datos(request):
        try:
            if 'id' in request.GET:
                camaras = Camaras.objects.filter(pk = request.GET['id'])   
            elif 'direccion_ip' in request.GET:
                camaras = Camaras.objects.filter(direccion_ip__icontains = request.GET['direccion_ip'])   
            elif 'nombre_camara' in request.GET:
                camaras = Camaras.objects.filter(nombre_camara__icontains = request.GET['nombre_camara'])   
            else:
                camaras = Camaras.objects.all()
            camaras = camaras.order_by('tutor_id').select_related('tutor').values('id', 'direccion_ip', 'nombre_camara', 'habilitada', 'tutor_id')
            return list(camaras)
        except Exception as e: 
            return 'error'

    def guardar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'direccion_ip' in json_data:
                self.direccion_ip = json_data['direccion_ip']
            if 'nombre_camara' in json_data:
                self.nombre_camara = json_data['nombre_camara']
            if 'habilitada' in json_data:
                self.habilitada = json_data['habilitada']
            if 'tutor_id' in json_data:
                self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
            self.save()
            return 'guardada'
        except Tutores.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'

class Objetos(models.Model):
    nombre = models.CharField(max_length = 20)
    foto_objeto = models.ImageField(upload_to = 'Objetos', null = True, blank = True)

class PermisosObjetos(models.Model):
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "objetos_tutor")
    objeto = models.ForeignKey('Monitoreo.Objetos', on_delete = models.PROTECT)

    @staticmethod
    def obtener_datos(request):
        try:
            objetos = Objetos.objects.all().annotate(habilitado = Value(False, output_field = BooleanField()))
            permisos_obj = PermisosObjetos.objects.filter(tutor_id = request.GET['tutor_id'])
            for obj in objetos:
                if(len(permisos_obj.filter(tipos_distraccion_id = obj.pk))):
                    ## MIRAR ESTA ASIGNACIÓN
                    obj.habilitado = True
            return list(objetos)
        except Exception as e: 
            return 'error'

    def activar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'tutor_id' in json_data and 'objeto_id' in json_data:
                self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
                self.objeto = Objetos.objects.get(pk = json_data['objeto_id'])
                self.save()
            return 'guardado'
        except Tutores.DoesNotExist or Objetos.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
    
    def desactivar(self, permiso_objeto_id):
        punto_guardado = transaction.savepoint()
        try:
            permiso_objeto = PermisosObjetos.objects.get(pk = permiso_objeto_id)
            permiso_objeto.delete()
            return 'eliminado'
        except PermisosObjetos.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'

class Monitoreo(models.Model):
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "ajustes_monitoreo") 
    tipo_distraccion = models.ForeignKey('Monitoreo.TiposDistraccion', on_delete = models.PROTECT)

    @staticmethod
    def obtener_datos(request):
        try:
            tipos_distraccion = TiposDistraccion.objects.all().annotate(habilitado = Value(False, output_field = BooleanField()))
            monitoreo = Monitoreo.objects.filter(tutor_id = request.GET['tutor_id'])
            for tipo in tipos_distraccion:
                if(len(monitoreo.filter(tipos_distraccion_id = tipo.pk))):
                    ## MIRAR ESTA ASIGNACIÓN
                    tipo.habilitado = True
            return list(tipos_distraccion)
        except Exception as e: 
            return 'error'

    def activar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'tutor_id' in json_data and 'tipo_distraccion_id' in json_data:
                self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
                self.tipo_distraccion = TiposDistraccion.objects.get(pk = json_data['tipo_distraccion_id'])
                self.save()

                # INICIA LA MONITORIZACIÓN, CREANDO HILOS POR CADA CAMARA HABILITADA DEL TUTOR
                #
                #

            return 'guardado'
        except Tutores.DoesNotExist or TiposDistraccion.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
    
    def desactivar(self, monitoreo_id):
        punto_guardado = transaction.savepoint()
        try:
            monitoreo = Monitoreo.objects.get(pk = monitoreo_id)
            monitoreo.delete()
            return 'eliminado'
        except Monitoreo.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'

class Historial(models.Model):
    fecha_hora = models.DateTimeField()
    imagen_evidencia = models.ImageField(upload_to = 'Evidencias', null = True, blank = True)
    supervisado = models.ForeignKey('Persona.Supervisados', on_delete = models.PROTECT, related_name = "historial_supervisado")
    tipo_distraccion = models.ForeignKey('Monitoreo.TiposDistraccion', on_delete = models.PROTECT, related_name = "historial_distraccion")

    @staticmethod
    def obtener_datos(request):
        try:
            if 'persona__cedula' in request.GET and 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(Q(persona__cedula__icontains = request.GET['persona__cedula']) & Q(tutor__pk = request.GET['tutor_id']))   
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            elif 'nombres_apellidos' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id']).select_related('persona')).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                supervisados = supervisados.filter(nombres_completos__icontains = request.GET['nombres_apellidos'])
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            else:
                supervisados = Supervisados.objects.all()
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            historial = historial.values('id', 'fecha_hora', 'imagen_evidencia', 'tipo_distraccion_id', 'tipo_distraccion__nombre' 'supervisado_id', 'supervisado__persona__nombres', 'supervisado__persona__apellidos', 'supervisado__persona__cedula')
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
                supervisados = Supervisados.objects.filter(Q(persona__cedula__icontains = request.GET['persona__cedula']) & Q(tutor__pk = request.GET['tutor_id']))
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