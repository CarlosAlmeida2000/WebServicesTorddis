from django.db.models import Q, Value, BooleanField, IntegerField
from Monitoreo.reconocimiento import Monitorizar
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
            elif 'direccion_ip' in request.GET and 'tutor_id' in request.GET:
                camaras = Camaras.objects.filter(Q(direccion_ip__icontains = request.GET['direccion_ip']) & Q(tutor_id = request.GET['tutor_id']))   
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
            if 'tutor_id' in request.GET and 'id' in request.GET:
                objetos = Objetos.objects.filter(pk = request.GET['id']).annotate(habilitado = Value(False, output_field = BooleanField())).annotate(permiso_objeto_id = Value(0, output_field = IntegerField())).values()
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
                tipos_distraccion = TiposDistraccion.objects.filter(pk = request.GET['id']).annotate(habilitado = Value(False, output_field = BooleanField())).annotate(tipo_distraccion_id = Value(0, output_field = IntegerField())).values()
                monitoreo_dis = Monitoreo.objects.filter(tutor_id = request.GET['tutor_id'])
                for i in range(len(tipos_distraccion)):
                    monitoreo = monitoreo_dis.filter(tipo_distraccion_id = tipos_distraccion[i]['id'])
                    if(len(monitoreo)):
                        tipos_distraccion[i]['habilitado'] = True
                        tipos_distraccion[i]['tipo_distraccion_id'] = monitoreo[0].id
                return tipos_distraccion
            elif 'tutor_id' in request.GET:
                tipos_distraccion = TiposDistraccion.objects.all().annotate(habilitado = Value(False, output_field = BooleanField())).annotate(tipo_distraccion_id = Value(0, output_field = IntegerField())).values()
                monitoreo_dis = Monitoreo.objects.filter(tutor_id = request.GET['tutor_id'])
                for i in range(len(tipos_distraccion)):
                    monitoreo = monitoreo_dis.filter(tipo_distraccion_id = tipos_distraccion[i]['id'])
                    if(len(monitoreo)):
                        tipos_distraccion[i]['habilitado'] = True
                        tipos_distraccion[i]['tipo_distraccion_id'] = monitoreo[0].id
                return tipos_distraccion
        except Exception as e: 
            return 'error'

    
    @staticmethod
    def start():
        try:
            monitoreo = Monitorizar()
            hilo_vigilar = threading.Thread(target=monitoreo.reconocer)
            hilo_vigilar.start()
            # POR CADA CAMARA HABILITADA SE CREA UN HILO DE VIGILANCIA 
                # for camara in Camaras.objects.filter(Q(tutor_id = json_data['tutor_id']) & Q(habilitada = True)):
                #     monitoreo = Monitorizar()
                #     hilo_vigilar = threading.Thread(target=monitoreo.reconocer, args=(camara.direccion_ip,))
                #     hilo_vigilar.start()
            return 'monitoreando........'
        except Exception as e: 
            return 'error2 '+str(e)


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
            return historial
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
                    'enfadado': (historial.filter(expresion_facial = 'Enfadado').count()),
                    'asqueado': (historial.filter(expresion_facial = 'Asqueado').count()),
                    'temeroso': (historial.filter(expresion_facial = 'Temeroso').count()),
                    'feliz': (historial.filter(expresion_facial = 'Feliz').count()),
                    'neutral': (historial.filter(expresion_facial = 'Neutral').count()),
                    'triste': (historial.filter(expresion_facial = 'Triste').count()),
                    'sorprendido': (historial.filter(expresion_facial = 'Sorprendido').count())
                    }
                    historial_grafico.append(object_json)
            return historial_grafico
        except Supervisados.DoesNotExist:    
            return []
        except Exception as e: 
            return 'error'