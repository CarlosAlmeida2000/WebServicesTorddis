from django.db.models import Q, Value, BooleanField, IntegerField
from Persona.models import Supervisados, Tutores
from django.db.models.functions import Concat
from django.db import IntegrityError
from django.db import transaction
from Persona.image import Image
from django.db import models
import threading

# Create your models here.
class TiposDistraccion(models.Model):
    nombre = models.CharField(max_length = 25)

class Camaras(models.Model):
    direccion_ip = models.CharField(max_length = 100, unique = True)
    nombre_camara = models.CharField(max_length = 20)
    habilitada = models.BooleanField()
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "camaras_tutor")

    @staticmethod
    def obtener_datos(request):
        try:
            if 'id' in request.GET and 'tutor_id' in request.GET:
                camaras = Camaras.objects.filter(Q(pk = request.GET['id']) & Q(tutor_id = request.GET['tutor_id']))   
            elif 'nombre_camara' in request.GET and 'tutor_id' in request.GET:
                camaras = Camaras.objects.filter(Q(nombre_camara__icontains = request.GET['nombre_camara']) & Q(tutor_id = request.GET['tutor_id']))   
            elif 'tutor_id' in request.GET:
                camaras = Camaras.objects.filter(tutor_id = request.GET['tutor_id'])
            camaras = camaras.order_by('tutor_id').select_related('tutor').values('id', 'direccion_ip', 'nombre_camara', 'habilitada', 'tutor_id')
            return camaras
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
            existe_camara = Camaras.objects.filter(Q(tutor_id = self.tutor.pk) & Q(nombre_camara = self.nombre_camara))
            if(len(existe_camara)) and not existe_camara[0].pk == self.pk:
                return 'cámara repetida'    
            self.save()
            return 'guardada'
        except IntegrityError:
            transaction.savepoint_rollback(punto_guardado)
            return 'cámara repetida'
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
            if 'tutor_id' in request.GET and 'nombre_id' in request.GET:
                objetos = Objetos.objects.filter(Q(pk__startswith = request.GET['nombre_id']) | Q(nombre__icontains = request.GET['nombre_id'])).annotate(habilitado = Value(False, output_field = BooleanField())).annotate(permiso_objeto_id = Value(0, output_field = IntegerField())).values()
                permisos_obj = PermisosObjetos.objects.filter(tutor_id = request.GET['tutor_id'])
                for i in range(len(objetos)):
                    permiso = permisos_obj.filter(objeto_id = objetos[i]['id'])
                    if(len(permiso)):
                        objetos[i]['habilitado'] = True
                        objetos[i]['permiso_objeto_id'] = permiso[0].id
                return objetos
            elif 'tutor_id' in request.GET:
                objetos = Objetos.objects.all().annotate(habilitado = Value(False, output_field = BooleanField())).annotate(permiso_objeto_id = Value(0, output_field = IntegerField())).values()
                permisos_obj = PermisosObjetos.objects.filter(tutor_id = request.GET['tutor_id'])
                for i in range(len(objetos)):
                    permiso = permisos_obj.filter(objeto_id = objetos[i]['id'])
                    if(len(permiso)):
                        objetos[i]['habilitado'] = True
                        objetos[i]['permiso_objeto_id'] = permiso[0].id
                return objetos
        except Exception as e: 
            return 'error'

    def activar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'id' in json_data and 'tutor_id' in json_data:
                self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
                self.objeto = Objetos.objects.get(pk = json_data['id'])
                self.save()
                return 'guardado'
            return 'error'
        except Tutores.DoesNotExist or Objetos.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
    
    def desactivar(self, request):
        punto_guardado = transaction.savepoint()
        try:
            self = PermisosObjetos.objects.filter(Q(tutor_id = request.GET['tutor_id']) & Q(objeto_id = request.GET['id']))
            if(len(self)):
                self[0].delete()
                return 'eliminado'
            return 'el objeto no tiene un permiso'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'

class Monitoreo(models.Model):
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "ajustes_monitoreo") 
    tipo_distraccion = models.ForeignKey('Monitoreo.TiposDistraccion', on_delete = models.PROTECT)

    @staticmethod
    def obtener_datos(request):
        try:
            if 'tutor_id' in request.GET and 'id' in request.GET:
                tipos_distraccion = TiposDistraccion.objects.filter(pk = request.GET['id']).annotate(habilitado = Value(False, output_field = BooleanField())).annotate(monitoreo_id = Value(0, output_field = IntegerField())).values()
                monitoreo_dis = Monitoreo.objects.filter(tutor_id = request.GET['tutor_id'])
                for i in range(len(tipos_distraccion)):
                    monitoreo = monitoreo_dis.filter(tipo_distraccion_id = tipos_distraccion[i]['id'])
                    if(len(monitoreo)):
                        tipos_distraccion[i]['habilitado'] = True
                        tipos_distraccion[i]['monitoreo_id'] = monitoreo[0].id
                return tipos_distraccion
            elif 'tutor_id' in request.GET:
                tipos_distraccion = TiposDistraccion.objects.all().annotate(habilitado = Value(False, output_field = BooleanField())).annotate(monitoreo_id = Value(0, output_field = IntegerField())).values()
                monitoreo_dis = Monitoreo.objects.filter(tutor_id = request.GET['tutor_id'])
                for i in range(len(tipos_distraccion)):
                    monitoreo = monitoreo_dis.filter(tipo_distraccion_id = tipos_distraccion[i]['id'])
                    if(len(monitoreo)):
                        tipos_distraccion[i]['habilitado'] = True
                        tipos_distraccion[i]['monitoreo_id'] = monitoreo[0].id
                return tipos_distraccion
        except Exception as e: 
            return 'error'

    def activar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'tutor_id' in json_data and 'id' in json_data:
                self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
                self.tipo_distraccion = TiposDistraccion.objects.get(pk = json_data['id'])
                self.save()
                return 'activado'
            return 'error'
        except Tutores.DoesNotExist or TiposDistraccion.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
    
    def desactivar(self, request):
        punto_guardado = transaction.savepoint()
        try:
            self = Monitoreo.objects.filter(Q(tutor_id = request.GET['tutor_id']) & Q(tipo_distraccion_id = request.GET['id']))
            if(len(self)):
                self[0].delete()
                return 'desactivado'
            return 'el tipo de distracción no está activado'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'

class Historial(models.Model):
    fecha_hora = models.DateTimeField()
    imagen_evidencia = models.ImageField(upload_to = 'Evidencias', null = True, blank = True)
    observacion = models.CharField(max_length = 200)
    supervisado = models.ForeignKey('Persona.Supervisados', on_delete = models.PROTECT, related_name = "historial_supervisado")
    tipo_distraccion = models.ForeignKey('Monitoreo.TiposDistraccion', on_delete = models.PROTECT, related_name = "historial_distraccion")

    # Filtrar con >,<,>=,<=
    # __lte -> Less than or equal
    #  __gte -> Greater than or equal
    #  __lt -> Less than
    #  __gt -> Greater than
    # QuerySet(foo__lte=10) # foo <= 10
    # QuerySet(foo__gte=10) # foo >= 10
    # QuerySet(foo__lt=10) # foo < 10
    # QuerySet(foo__gt=10) # foo > 10

    @staticmethod
    def obtener_datos(request):
        try:
            if 'nombres_cedula' in request.GET and 'fecha' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id']).select_related('persona')).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                supervisados = supervisados.filter(Q(nombres_completos__icontains = request.GET['nombres_cedula']) | Q(persona__cedula__icontains = request.GET['nombres_cedula']))
                historial = Historial.objects.filter(fecha_hora__lte = request.GET['fecha']).exclude(~Q(supervisado_id__in = supervisados.values('id')))
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])
                historial = Historial.objects.all().exclude(~Q(supervisado_id__in = supervisados.values('id')))
            historial = historial.values('id', 'fecha_hora', 'observacion', 'imagen_evidencia', 'tipo_distraccion_id', 'tipo_distraccion__nombre' , 'supervisado_id', 'supervisado__persona__nombres', 'supervisado__persona__apellidos', 'supervisado__persona__cedula')
            # Conversar con Jhon para ver si se envia de forma unitaria la foto de un historial mediante el id, y no todas las fotos de golpe
            # file = Image()
            # for u in range(len(historial)):
            #     historial[u]['fecha_hora'] = historial[u]['fecha_hora'].strftime('%Y-%m-%d %H:%M')
            #     if(historial[u]['imagen_evidencia'] != ''):
            #         file.ruta = historial[u]['imagen_evidencia']
            #         historial[u]['imagen_evidencia'] = file.get_base64()
            return historial
        except Exception as e: 
            return 'error'+str(e)
    
    @staticmethod
    def grafico_expresion(request):
        try:
            supervisados = Supervisados()
            if 'nombres_cedula' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                supervisados = supervisados.filter(Q(nombres_completos__icontains = request.GET['nombres_cedula']) | Q(persona__cedula__icontains = request.GET['nombres_cedula']))
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])
            historial_grafico = []
            for supervisado in supervisados: 
                historial = supervisado.historial_supervisado.all().values()
                if (len(historial)):
                    object_json =  { 
                    'supervisado_id': supervisado.pk,
                    'nombres': supervisado.persona.nombres,
                    'apellidos': supervisado.persona.apellidos,
                    'cedula': supervisado.persona.cedula,
                    'enfadado': (historial.filter(observacion = 'Enfadado').count()),
                    'disgustado': (historial.filter(observacion = 'Disgustado').count()),
                    'temeroso': (historial.filter(observacion = 'Temeroso').count()),
                    'feliz': (historial.filter(observacion = 'Feliz').count()),
                    'neutral': (historial.filter(observacion = 'Neutral').count()),
                    'triste': (historial.filter(observacion = 'Triste').count()),
                    'sorprendido': (historial.filter(observacion = 'Sorprendido').count())
                    }
                    historial_grafico.append(object_json)
            return historial_grafico
        except Supervisados.DoesNotExist:    
            return []
        except Exception as e: 
            return 'error'
    
    @staticmethod
    def grafico_sueno(request):
        try:
            supervisados = Supervisados()
            if 'nombres_cedula' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                supervisados = supervisados.filter(Q(nombres_completos__icontains = request.GET['nombres_cedula']) | Q(persona__cedula__icontains = request.GET['nombres_cedula']))
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])
            historial_grafico = []
            for supervisado in supervisados: 
                historial = supervisado.historial_supervisado.all().values()
                if (len(historial)):
                    object_json =  { 
                    'supervisado_id': supervisado.pk,
                    'nombres': supervisado.persona.nombres,
                    'apellidos': supervisado.persona.apellidos,
                    'cedula': supervisado.persona.cedula,
                    'semana8': 0,
                    'semana7': 0,
                    'semana6': 0,
                    'semana5': 0,
                    'semana4': 0,
                    'semana3': 0,
                    'semana2': 0,
                    'semana1': 0,
                    }
                    historial_grafico.append(object_json)
            return historial_grafico
        except Supervisados.DoesNotExist:    
            return []
        except Exception as e: 
            return 'error'
            
    @staticmethod
    def grafico_objetos(request):
        try:
            supervisados = Supervisados()
            if 'nombres_cedula' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                supervisados = supervisados.filter(Q(nombres_completos__icontains = request.GET['nombres_cedula']) | Q(persona__cedula__icontains = request.GET['nombres_cedula']))
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])
            historial_grafico = []
            for supervisado in supervisados: 
                historial = supervisado.historial_supervisado.all().values()
                if (len(historial)):
                    object_json =  { 
                    'supervisado_id': supervisado.pk,
                    'nombres': supervisado.persona.nombres,
                    'apellidos': supervisado.persona.apellidos,
                    'cedula': supervisado.persona.cedula,
                    'semana8': 0,
                    'semana7': 0,
                    'semana6': 0,
                    'semana5': 0,
                    'semana4': 0,
                    'semana3': 0,
                    'semana2': 0,
                    'semana1': 0,
                    }
                    historial_grafico.append(object_json)
            return historial_grafico
        except Supervisados.DoesNotExist:    
            return []
        except Exception as e: 
            return 'error'