import datetime
from django.db.models import Q, Value, BooleanField, IntegerField
from Persona.models import Supervisados, Tutores
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
            if 'tutor_id' in request.GET and ('objeto_id' in request.GET or 'nombre' in request.GET):
                if 'objeto_id' in request.GET:
                    objetos = Objetos.objects.filter(pk = request.GET['objeto_id']).annotate(habilitado = Value(False, output_field = BooleanField())).annotate(permiso_objeto_id = Value(0, output_field = IntegerField())).values()
                elif 'nombre' in request.GET:
                    objetos = Objetos.objects.filter(nombre__icontains = request.GET['nombre']).annotate(habilitado = Value(False, output_field = BooleanField())).annotate(permiso_objeto_id = Value(0, output_field = IntegerField())).values()
                permisos_obj = PermisosObjetos.objects.filter(tutor_id = request.GET['tutor_id'])
                file = Image()
                for i in range(len(objetos)):
                    permiso = permisos_obj.filter(objeto_id = objetos[i]['id'])
                    if(len(permiso)):
                        objetos[i]['habilitado'] = True
                        objetos[i]['permiso_objeto_id'] = permiso[0].id
                    if objetos[i]['foto_objeto'] != '':
                        file.ruta = objetos[i]['foto_objeto']
                        objetos[i]['foto_objeto'] = file.get_base64()
                return objetos
            elif 'tutor_id' in request.GET:
                objetos = Objetos.objects.all().annotate(habilitado = Value(False, output_field = BooleanField())).annotate(permiso_objeto_id = Value(0, output_field = IntegerField())).values()
                permisos_obj = PermisosObjetos.objects.filter(tutor_id = request.GET['tutor_id'])
                file = Image()
                for i in range(len(objetos)):
                    permiso = permisos_obj.filter(objeto_id = objetos[i]['id'])
                    if(len(permiso)):
                        objetos[i]['habilitado'] = True
                        objetos[i]['permiso_objeto_id'] = permiso[0].id
                    if objetos[i]['foto_objeto'] != '':
                        file.ruta = objetos[i]['foto_objeto']
                        objetos[i]['foto_objeto'] = file.get_base64()
                return objetos
        except Exception as e: 
            return 'error'

    def activar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'objeto_id' in json_data and 'tutor_id' in json_data:
                self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
                self.objeto = Objetos.objects.get(pk = json_data['objeto_id'])
                self.save()
                return 'guardado'
            return 'error'
        except Tutores.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'No existe el tutor'
        except Objetos.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'No existe el objeto'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
    
    def desactivar(self, request):
        punto_guardado = transaction.savepoint()
        try:
            self = PermisosObjetos.objects.filter(Q(tutor_id = request.GET['tutor_id']) & Q(objeto_id = request.GET['objeto_id']))
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
            if 'tutor_id' in request.GET and 'tipo_dist_id' in request.GET:
                tipos_distraccion = TiposDistraccion.objects.filter(pk = request.GET['tipo_dist_id']).annotate(habilitado = Value(False, output_field = BooleanField())).annotate(monitoreo_id = Value(0, output_field = IntegerField())).values()
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
            if 'tutor_id' in json_data and 'tipo_dist_id' in json_data:
                self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
                self.tipo_distraccion = TiposDistraccion.objects.get(pk = json_data['tipo_dist_id'])
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
            self = Monitoreo.objects.filter(Q(tutor_id = request.GET['tutor_id']) & Q(tipo_distraccion_id = request.GET['tipo_dist_id']))
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

    @staticmethod
    def obtener_datos(request):
        try:
            if 'supervisado_id' in request.GET and 'fecha' in request.GET:
                fecha = datetime.datetime.strptime(request.GET['fecha'], "%Y-%m-%d").date()
                fecha = fecha + datetime.timedelta(days = 1)
                historial = Historial.objects.filter(Q(supervisado_id = request.GET['supervisado_id']) & Q(fecha_hora__lte = fecha)).values('id', 'fecha_hora', 'imagen_evidencia', 'observacion', 'tipo_distraccion_id', 'tipo_distraccion__nombre' , 'supervisado_id', 'supervisado__persona__nombres', 'supervisado__persona__apellidos')
                return historial
            elif 'historial_id' in request.GET:
                historial = Historial.objects.get(pk = request.GET['historial_id'])
                file = Image()
                base64 = ''
                if(historial.imagen_evidencia != ''):
                    file.ruta = historial.imagen_evidencia
                    base64 = file.get_base64()
                json_historial =  [{
                    'id': historial.pk,
                    'fecha_hora': historial.fecha_hora,
                    'imagen_evidencia': base64,
                    'observacion': historial.observacion,
                    'tipo_distraccion_id': historial.tipo_distraccion.pk,
                    'tipo_distraccion__nombre': historial.tipo_distraccion.nombre,
                    'supervisado_id': historial.supervisado.pk,
                    'supervisado__persona__nombres': historial.supervisado.persona.nombres,
                    'supervisado__persona__apellidos': historial.supervisado.persona.apellidos
                }]
                return json_historial
            else:
                return []
        except Historial.DoesNotExist:
            return 'No existe el historial'
        except Exception as e: 
            return 'error'
    
    @staticmethod
    def graficos(request):
        try:
            if 'supervisado_id' in request.GET and 'fecha' in request.GET:
                supervisado = Supervisados.objects.get(pk = request.GET['supervisado_id'])
                historial = supervisado.historial_supervisado.all().values()
                if (len(historial)):
                    fecha = datetime.datetime.strptime(request.GET['fecha'], "%Y-%m-%d").date()
                    fecha = fecha + datetime.timedelta(days = 1)
                    historial_grafico = []
                    historial = historial.filter(fecha_hora__lte = fecha)
                    grafico_expresiones = { 
                    'tipo_grafico': 'Expresiones',
                    'enfadado': (historial.filter(observacion = 'Enfadado').count()),
                    'disgustado': (historial.filter(observacion = 'Disgustado').count()),
                    'temeroso': (historial.filter(observacion = 'Temeroso').count()),
                    'feliz': (historial.filter(observacion = 'Feliz').count()),
                    'neutral': (historial.filter(observacion = 'Neutral').count()),
                    'triste': (historial.filter(observacion = 'Triste').count()),
                    'sorprendido': (historial.filter(observacion = 'Sorprendido').count())
                    }
                    grafico_sueno = { 
                    'tipo_grafico': 'Sueño',
                    'dia_7': 0,
                    'dia_6': 0,
                    'dia_5': 0,
                    'dia_4': 0,
                    'dia_3': 0,
                    'dia_2': 0,
                    'dia_1': 0,
                    }
                    grafico_objetos = { 
                    'tipo_grafico': 'Objetos',
                    'dia_7': 0,
                    'dia_6': 0,
                    'dia_5': 0,
                    'dia_4': 0,
                    'dia_3': 0,
                    'dia_2': 0,
                    'dia_1': 0,
                    }
                    historial_grafico.append(grafico_expresiones)
                    historial_grafico.append(grafico_sueno)
                    historial_grafico.append(grafico_objetos)
                    return historial_grafico
                else:
                    return []
            else:
                return []
        except Supervisados.DoesNotExist:    
            return 'No existe el supervisado'
        except Exception as e: 
            return 'error'