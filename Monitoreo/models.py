from django.db.models import Q, Value, BooleanField, IntegerField
from Persona.models import Supervisados, Tutores
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db import transaction
from Persona.image import Image
from django.db import models
import datetime
from datetime import datetime as dt
import cv2

# Create your models here.
class TiposDistraccion(models.Model):
    nombre = models.CharField(max_length = 25)

class Camaras(models.Model):
    direccion_ruta = models.CharField(max_length = 150)
    habilitada = models.BooleanField()
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT, related_name = "camaras_tutor")

    @staticmethod
    def obtener_datos(request):
        try:
            if 'id' in request.GET and 'tutor_id' in request.GET:
                camaras = Camaras.objects.filter(Q(pk = request.GET['id']) & Q(tutor_id = request.GET['tutor_id']))   
            elif 'tutor_id' in request.GET:
                camaras = Camaras.objects.filter(tutor_id = request.GET['tutor_id'])
            camaras = camaras.order_by('tutor_id').select_related('tutor').values('id', 'direccion_ruta', 'habilitada', 'tutor_id')
            return camaras
        except Exception as e: 
            return 'error'

    def guardar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'direccion_ruta' in json_data:
                self.direccion_ruta = json_data['direccion_ruta']
                self.habilitada = True
            if 'tutor_id' in json_data:
                self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
            tiene_camara = Camaras.objects.filter(tutor_id = self.tutor.pk)
            if(len(tiene_camara)) and not tiene_camara[0].pk == self.pk:
                return 'El tutor ya tiene una cámara'    
            self.save()
            return 'Dispositivo guardado'
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
                if len(PermisosObjetos.objects.filter(Q(tutor_id = json_data['tutor_id']) & Q(objeto_id = json_data['objeto_id']))) == 0:
                    self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
                    self.objeto = Objetos.objects.get(pk = json_data['objeto_id'])
                    self.save()
                    return 'activado'
                else:
                    return 'el objeto ya está activado'
            return 'error'
        except Tutores.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'no existe el tutor'
        except Objetos.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'no existe el objeto'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
    
    def desactivar(self, request):
        punto_guardado = transaction.savepoint()
        try:
            permiso = PermisosObjetos.objects.get(Q(tutor_id = request.GET['tutor_id']) & Q(objeto_id = request.GET['objeto_id']))
            permiso.delete()
            return 'eliminado'
        except PermisosObjetos.DoesNotExist:
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
                if len(Monitoreo.objects.filter(Q(tutor_id = json_data['tutor_id']) & Q(tipo_distraccion_id = json_data['tipo_dist_id']))) == 0:
                    self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])
                    self.tipo_distraccion = TiposDistraccion.objects.get(pk = json_data['tipo_dist_id'])
                    self.save()
                    return '', 'Parámetro activado'
                else:
                    return 'error', 'el tipo de distracción ya está activado'
            return 'error', 'error'
        except Tutores.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error', 'no existe el tutor'
        except TiposDistraccion.DoesNotExist:
            transaction.savepoint_rollback(punto_guardado)
            return 'error', 'no existe el tipo de distracción'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error', 'error'
    
    def desactivar(self, request):
        punto_guardado = transaction.savepoint()
        try:
            monitoreo = Monitoreo.objects.get(Q(tutor_id = request.GET['tutor_id']) & Q(tipo_distraccion_id = request.GET['tipo_dist_id']))
            monitoreo.delete()
            return 'Parámetro desactivado'
        except Monitoreo.DoesNotExist:
            return 'el tipo de distracción no está activado'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'
    
    @staticmethod
    def existeDistraccion(request):
        try:
            if 'direccion_ruta' in request.GET:
                if Supervisados.objects.filter(Q(tutor_id = Camaras.objects.filter(direccion_ruta = request.GET['direccion_ruta'])[0].tutor.id) & Q(distraido = True)).count() > 0:
                    return True
                return False
            return False
        except Exception as e: 
            return False


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
                fecha = datetime.datetime.strptime(request.GET['fecha'], "%Y-%m-%d").date() + datetime.timedelta(days = 1)
                historial = Historial.objects.filter(Q(supervisado_id = request.GET['supervisado_id']) & Q(fecha_hora__lte = fecha)).values('id', 'fecha_hora', 'imagen_evidencia',
                'observacion', 'tipo_distraccion_id', 'tipo_distraccion__nombre' , 'supervisado_id', 'supervisado__persona__nombres', 'supervisado__persona__apellidos')
                return historial
            elif 'tutor_id' in request.GET and 'fecha_actual' in request.GET:
                supervisados = Supervisados.objects.filter(tutor_id = request.GET['tutor_id'])
                hoy = datetime.datetime.today().date()
                historial = Historial.objects.filter(fecha_hora__range = [str(hoy) + ' 00:00:00.000000', str(hoy) + ' 23:59:59.000000']).exclude(~Q(supervisado_id__in = supervisados.values('id'))
                ).values('id', 'fecha_hora', 'imagen_evidencia', 'observacion', 'tipo_distraccion_id', 'tipo_distraccion__nombre' , 'supervisado_id', 'supervisado__persona__nombres', 
                'supervisado__persona__apellidos')
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
            return {'historial': 'No existe el historial'}
        except Exception as e: 
            return {'historial': 'error'}
    
    @staticmethod
    def crear(supervisado_id, observacion, tipo_distraccion_id, imagen):
        try:
            historial = Historial()
            historial.fecha_hora = dt.now()
            historial.observacion = observacion
            historial.supervisado = Supervisados.objects.get(pk = supervisado_id)
            historial.tipo_distraccion = TiposDistraccion.objects.get(pk = tipo_distraccion_id)
            foto_450 = cv2.resize(imagen, (450, 450), interpolation = cv2.INTER_CUBIC)
            frame_jpg = cv2.imencode('.png', foto_450)
            file = ContentFile(frame_jpg[1]) 
            historial.imagen_evidencia.save('dis_' + str(tipo_distraccion_id) + '_id_' + str(historial.supervisado.persona.id) + '_' + str(historial.fecha_hora) + '.png', file, save = True)
            historial.save()
            return True
        except Exception as e:
            print('Error en historial: ' + str(e))
            return False

    @staticmethod
    def graficos(request):
        try:
            if 'supervisado_id' in request.GET and 'fecha' in request.GET:
                supervisado = Supervisados.objects.get(pk = request.GET['supervisado_id'])
                historial = supervisado.historial_supervisado.all().values()
                if (len(historial)):
                    fecha_maxima = (datetime.datetime.strptime(request.GET['fecha'], "%Y-%m-%d").date())
                    fecha_minima = fecha_maxima - datetime.timedelta(days = 6)
                    historial_grafico = []
                    historial = historial.filter(fecha_hora__range = [str(fecha_minima) + ' 00:00:00.000000', str(fecha_maxima) + ' 23:59:59.000000'])
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
                        'tipo_grafico': 'Sueño'
                    }
                    grafico_objetos = { 
                        'tipo_grafico': 'Objetos'
                    }
                    fecha = fecha_maxima
                    for i in range(7):
                        historial_diario = historial.filter(fecha_hora__range = [str(fecha) + ' 00:00:00.000000', str(fecha) + ' 23:59:59.000000'])
                        grafico_sueno[f'dia_{(i+1)}'] = historial_diario.filter(tipo_distraccion_id = 3).count()
                        grafico_objetos[f'dia_{(i+1)}'] = historial_diario.filter(tipo_distraccion_id = 4).count()
                        fecha = fecha_maxima - datetime.timedelta(days = (i + 1))
                    historial_grafico.append(grafico_expresiones)
                    historial_grafico.append(grafico_sueno)
                    historial_grafico.append(grafico_objetos)
                    return historial_grafico
                else:
                    return []
            else:
                return []
        except Supervisados.DoesNotExist:    
            return {'grafico': 'no existe el supervisado'}
        except Exception as e: 
            return {'grafico': 'error'}