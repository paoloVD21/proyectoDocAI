from django.contrib import admin
from .models import Project
from .models import Artefacto
from .models import Fase
from .models import SubArtefacto
# Register your models here.

admin.site.register(Project)
admin.site.register(Artefacto)
admin.site.register(Fase)
admin.site.register(SubArtefacto)