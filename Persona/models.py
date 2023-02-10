# Create your models here.
from django.db import models, IntegrityError, transaction
from django.db.models import Q, Value, CharField
from django.db.models.functions import Concat
from fernet_fields import EncryptedTextField
from dateutil import relativedelta as rdelta
from datetime import date, datetime
from Persona.image import Image
import os

# Create your models here.
class Personas(models.Model):
    nombres = models.CharField(max_length = 40)
    apellidos = models.CharField(max_length = 40)
    fecha_nacimiento = models.DateField()
    foto_perfil = models.ImageField(upload_to = 'Perfiles', null = True, blank = True)
    
    @staticmethod
    def calcularEdad(fecha_naci):
        fecha_inicio = date(int((datetime.strptime(str(fecha_naci), '%Y-%m-%d')).year), 
            int((datetime.strptime(str(fecha_naci), '%Y-%m-%d')).month), 
            int((datetime.strptime(str(fecha_naci), '%Y-%m-%d')).day))
        fecha_fin = date(datetime.today().year, datetime.today().month, datetime.today().day)
        # Calcular el periodo transcurrido entre las fechas
        periodo = rdelta.relativedelta(fecha_fin, fecha_inicio)
        return periodo.years, periodo.months, periodo.days

    def guardar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'persona__nombres' in json_data:
                self.nombres = json_data['persona__nombres']
            if 'persona__apellidos' in json_data:
                self.apellidos = json_data['persona__apellidos']
            if 'persona__fecha_nacimiento' in json_data:
                self.fecha_nacimiento = json_data['persona__fecha_nacimiento']
            self.save()
            if 'persona__foto_perfil' in json_data and json_data['persona__foto_perfil'] != '':
                ruta_img_borrar = ''
                if(str(self.foto_perfil) != ''):
                    ruta_img_borrar = self.foto_perfil.url[1:]
                file = Image()
                file.base64 = json_data['persona__foto_perfil']
                file.nombre_file = '\\'+str(self.id)+'\\'+str(self.id) + '_'
                self.foto_perfil = file.get_file()
                self.save()
                if(ruta_img_borrar != ''):
                    os.remove(ruta_img_borrar)
            return 'si', self
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error', None
    
class Tutores(models.Model):
    usuario = models.CharField(max_length = 20, unique = True)
    clave = EncryptedTextField()
    correo = models.CharField(max_length = 100)
    persona = models.OneToOneField('Persona.Personas', on_delete = models.PROTECT, unique = True)

    @staticmethod
    def obtener_datos(request):
        try:
            if 'id' in request.GET:
                tutores = Tutores.objects.filter(pk = request.GET['id'])   
            elif 'nombres' in request.GET:
                tutores = (Tutores.objects.all().select_related('persona')).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                tutores = tutores.filter(nombres_completos__icontains = request.GET['nombres'])
            else:
                tutores = Tutores.objects.all()
            tutores = tutores.order_by('usuario').select_related('persona').values('id', 'usuario', 'correo',
                'persona_id','persona__nombres', 'persona__apellidos', 'persona__fecha_nacimiento', 'persona__foto_perfil')
            file = Image()
            for u in range(len(tutores)):
                if(tutores[u]['persona__foto_perfil'] != ''):
                    file.ruta = tutores[u]['persona__foto_perfil']
                    tutores[u]['persona__foto_perfil'] = file.get_base64()
            return tutores
        except Exception as e: 
            return 'error'

    def guardar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if 'usuario' in json_data:
                existe_usuario = len(Tutores.objects.filter(usuario = json_data['usuario']))
                if existe_usuario == 0 or (existe_usuario == 1 and self.pk != None):
                    if(self.pk == None):
                        # Es una nueva persona
                        self.persona = Personas()
                    persona_guardada, self.persona = self.persona.guardar(json_data)
                    if(persona_guardada == 'si'):
                        self.usuario = json_data['usuario']
                        if 'clave' in json_data:
                            self.clave = json_data['clave']
                        if 'correo' in json_data:
                            self.correo = json_data['correo']
                        self.save()
                        return 'guardado'
                    else:
                        return persona_guardada
                else:
                    return 'usuario repetido'
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'

    @staticmethod
    def login(json_data):
        try:
            tutor = Tutores.objects.get(usuario = json_data['usuario'])
            if(tutor.clave == json_data['clave']):
                file = Image()
                base64 = ''
                if(tutor.persona.foto_perfil != ''):
                    file.ruta = tutor.persona.foto_perfil
                    base64 = file.get_base64()
                json_usuario = {
                        'id': tutor.pk,
                        'usuario': tutor.usuario,
                        'correo': tutor.correo,
                        'foto_perfil': base64,
                        'persona_id': tutor.persona.pk,
                        'persona__nombres': tutor.persona.nombres,
                        'persona__apellidos': tutor.persona.apellidos,
                        'persona__fecha_nacimiento': tutor.persona.fecha_nacimiento
                        }
                return json_usuario
            else:   
                return {'tutores': 'credenciales incorrectas'}
        except Tutores.DoesNotExist:
            return {'tutores': 'credenciales incorrectas'}
        except Exception as e: 
            return {'tutores': 'error'}

class Supervisados(models.Model):
    distraido = models.BooleanField(default = False)
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT)
    persona = models.ForeignKey('Persona.Personas', on_delete = models.PROTECT)

    @staticmethod
    def obtener_datos(request):
        try:
            if 'id' in request.GET and 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(Q(pk = request.GET['id']) & Q(tutor__pk = request.GET['tutor_id'])).annotate(persona__edad = Value('', output_field = CharField()))   
            elif 'nombres' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos')).annotate(persona__edad = Value('', output_field = CharField()))   
                supervisados = supervisados.filter(nombres_completos__icontains = request.GET['nombres'])
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(tutor__pk = request.GET['tutor_id']).annotate(persona__edad = Value('', output_field = CharField()))   
            supervisados = supervisados.values('id', 'tutor_id',
                'persona_id','persona__nombres', 'persona__apellidos', 'persona__fecha_nacimiento', 'persona__edad', 'persona__foto_perfil')
            file = Image()
            for u in range(len(supervisados)):
                if(supervisados[u]['persona__foto_perfil'] != ''):
                    file.ruta = supervisados[u]['persona__foto_perfil']
                    supervisados[u]['persona__foto_perfil'] = file.get_base64()
                # Calcular edad del supervisado
                anios, meses, dias = Personas.calcularEdad(supervisados[u]['persona__fecha_nacimiento'])
                supervisados[u]['persona__edad'] = (str(anios) + ' años ' + str(meses) + ' meses ' + str(dias) + ' días')
            return supervisados
        except Exception as e: 
            return 'error'

    def guardar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            if(self.pk == None):
                # Es una nueva persona
                self.persona = Personas()
            # Calcular edad del supervisado
            anios, meses, dias = Personas.calcularEdad(json_data['persona__fecha_nacimiento'])
            if anios <= 12:
                persona_guardada, self.persona = self.persona.guardar(json_data)
                if(persona_guardada == 'si'):
                    self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])    
                    self.save()
                    return 'guardado'
                else:
                    return persona_guardada  
            else:
                return 'Edad máxima 12 años'  
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'

    @staticmethod
    def cambiarEstado(supervisado_id, distraido):
        try:
            unSupervisado = Supervisados.objects.get(pk = supervisado_id)
            unSupervisado.distraido = distraido
            unSupervisado.save()
            return True
        except Exception as e:
            return False