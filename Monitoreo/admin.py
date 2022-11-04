from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(TiposDistraccion)
admin.site.register(Camaras)
admin.site.register(Monitoreo)
admin.site.register(Objetos)
admin.site.register(PermisosObjetos)
admin.site.register(Historial)