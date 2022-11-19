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
class Roles(models.Model):
    nombre = models.CharField(max_length = 15)

class Personas(models.Model):
    nombres = models.CharField(max_length = 40)
    apellidos = models.CharField(max_length = 40)
    cedula = models.CharField(max_length = 10, unique = True)
    fecha_nacimiento = models.DateField()
    foto_perfil = models.ImageField(upload_to = 'Perfiles', null = True, blank = True)
    
    @staticmethod
    def calcular_edad(fecha_naci):
        fecha_inicio = date(int((datetime.strptime(str(fecha_naci), '%Y-%m-%d')).year), 
            int((datetime.strptime(str(fecha_naci), '%Y-%m-%d')).month), 
            int((datetime.strptime(str(fecha_naci), '%Y-%m-%d')).day))
        fecha_fin = date(datetime.today().year, datetime.today().month, datetime.today().day)
        # Calcular el periodo transcurrido entre las fechas
        periodo = rdelta.relativedelta(fecha_fin, fecha_inicio)
        return periodo.years, periodo.months, periodo.days

    def guardar(self, json_data, rol):
        punto_guardado = transaction.savepoint()
        try:
            if 'persona__nombres' in json_data:
                self.nombres = json_data['persona__nombres']
            if 'persona__apellidos' in json_data:
                self.apellidos = json_data['persona__apellidos']
            if 'persona__cedula' in json_data:
                self.cedula = json_data['persona__cedula']
            if 'persona__fecha_nacimiento' in json_data:
                self.fecha_nacimiento = json_data['persona__fecha_nacimiento']
            self.save()
            if rol != '' and len(RolesPersonas.objects.filter(persona__cedula = json_data['persona__cedula']).select_related('rol').filter(rol__nombre = rol)) == 0:
                rol_persona = RolesPersonas()
                rol_persona.persona = self
                rol_persona.rol = (Roles.objects.get(nombre = rol))
                rol_persona.save()                    
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
        except IntegrityError:
            transaction.savepoint_rollback(punto_guardado)
            return 'cédula repetida', None
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error', None

class RolesPersonas(models.Model):
    persona = models.ForeignKey('Persona.Personas', on_delete = models.PROTECT, related_name = 'roles_persona')
    rol = models.ForeignKey('Persona.Roles', on_delete = models.PROTECT)
    
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
            elif 'persona__cedula' in request.GET:
                tutores = Tutores.objects.filter(persona__cedula__icontains = request.GET['persona__cedula'])   
            elif 'nombres_apellidos' in request.GET:
                tutores = (Tutores.objects.all().select_related('persona')).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos'))
                tutores = tutores.filter(nombres_completos__icontains = request.GET['nombres_apellidos'])
            else:
                tutores = Tutores.objects.all()
            tutores = tutores.order_by('usuario').select_related('persona').values('id', 'usuario', 'correo',
                'persona_id','persona__nombres', 'persona__apellidos', 'persona__cedula', 'persona__fecha_nacimiento', 'persona__foto_perfil')
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
            existe_persona = Personas.objects.filter(cedula = json_data['persona__cedula'])
            if(len(existe_persona) > 0):
                # Ya existe la persona
                self.persona = existe_persona[0]
            else:
                # Es una nueva persona
                self.persona = Personas()
            persona_guardada, self.persona = self.persona.guardar(json_data, 'Tutor')
            if(persona_guardada == 'si'):
                if 'usuario' in json_data:
                    self.usuario = json_data['usuario']
                if 'clave' in json_data:
                    self.clave = json_data['clave']
                if 'correo' in json_data:
                    self.correo = json_data['correo']
                self.save()
                return 'guardado'
            else:
                return persona_guardada
        except IntegrityError:
            transaction.savepoint_rollback(punto_guardado)
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
                        'persona__cedula': tutor.persona.cedula,
                        'persona__fecha_nacimiento': tutor.persona.fecha_nacimiento
                        }
                return json_usuario
            else:   
                return 'credenciales incorrectas'
        except Tutores.DoesNotExist:
            return 'credenciales incorrectas'
        except Exception as e: 
            return 'error'

class Supervisados(models.Model):
    tutor = models.ForeignKey('Persona.Tutores', on_delete = models.PROTECT)
    persona = models.ForeignKey('Persona.Personas', on_delete = models.PROTECT)

    @staticmethod
    def obtener_datos(request):
        try:
            if 'id' in request.GET and 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(Q(pk = request.GET['id']) & Q(tutor__pk = request.GET['tutor_id'])).annotate(persona__edad = Value('', output_field = CharField()))   
            elif 'persona__cedula' in request.GET and 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(Q(persona__cedula__icontains = request.GET['persona__cedula']) & Q(tutor__pk = request.GET['tutor_id'])).annotate(persona__edad = Value('', output_field = CharField()))      
            elif 'nombres_apellidos' in request.GET and 'tutor_id' in request.GET:
                supervisados = (Supervisados.objects.filter(tutor__pk = request.GET['tutor_id'])).annotate(nombres_completos = Concat('persona__nombres', Value(' '), 'persona__apellidos')).annotate(persona__edad = Value('', output_field = CharField()))   
                supervisados = supervisados.filter(nombres_completos__icontains = request.GET['nombres_apellidos'])
            elif 'tutor_id' in request.GET:
                supervisados = Supervisados.objects.filter(tutor__pk = request.GET['tutor_id']).annotate(persona__edad = Value('', output_field = CharField()))   
            supervisados = supervisados.values('id', 'tutor_id',
                'persona_id','persona__nombres', 'persona__apellidos', 'persona__cedula', 'persona__fecha_nacimiento', 'persona__edad', 'persona__foto_perfil')
            file = Image()
            for u in range(len(supervisados)):
                if(supervisados[u]['persona__foto_perfil'] != ''):
                    file.ruta = supervisados[u]['persona__foto_perfil']
                    supervisados[u]['persona__foto_perfil'] = file.get_base64()
                # Calcular edad del supervisado
                anios, meses, dias = Personas.calcular_edad(supervisados[u]['persona__fecha_nacimiento'])
                supervisados[u]['persona__edad'] = (str(anios) + ' años ' + str(meses) + ' meses ' + str(dias) + ' días')
            return supervisados
        except Exception as e: 
            return 'error'

    def guardar(self, json_data):
        punto_guardado = transaction.savepoint()
        try:
            existe_persona = Personas.objects.filter(cedula = json_data['persona__cedula'])
            if(len(existe_persona) > 0):
                # Ya existe la persona
                self.persona = existe_persona[0]
            else:
                # Es una nueva persona
                self.persona = Personas()
            # Calcular edad del supervisado
            anios, meses, dias = Personas.calcular_edad(json_data['persona__fecha_nacimiento'])
            if anios <= 15:
                persona_guardada, self.persona = self.persona.guardar(json_data, 'Supervisado')
                if(persona_guardada == 'si'):
                    self.tutor = Tutores.objects.get(pk = json_data['tutor_id'])    
                    self.save()
                    return 'guardado'
                else:
                    return persona_guardada  
            else:
                return 'Edad máxima 15 años'  
        except Exception as e: 
            transaction.savepoint_rollback(punto_guardado)
            return 'error'