from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from typing import Any, List, Tuple
from .utils import hash_respuesta

class SecurityQuestions(models.Model):
    PREGUNTAS_CHOICES: List[Tuple[str, str]] = [
        ('color', '¿Cuál es tu color favorito?'),
        ('comida', '¿Cuál es tu comida favorita?'),
        ('pelicula', '¿Cuál es tu película favorita?'),
        ('libro', '¿Cuál es tu libro favorito?'),
        ('deporte', '¿Cuál es tu deporte favorito?'),
        ('musica', '¿Cuál es tu género de música favorito?')
    ]

    user: models.OneToOneField = models.OneToOneField(User, on_delete=models.CASCADE)
    pregunta1: models.CharField = models.CharField(max_length=50, choices=PREGUNTAS_CHOICES)
    respuesta1: models.CharField = models.CharField(max_length=128)  # Aumentado para almacenar el hash
    pregunta2: models.CharField = models.CharField(max_length=50, choices=PREGUNTAS_CHOICES)
    respuesta2: models.CharField = models.CharField(max_length=128)  # Aumentado para almacenar el hash
    pregunta3: models.CharField = models.CharField(max_length=50, choices=PREGUNTAS_CHOICES)
    respuesta3: models.CharField = models.CharField(max_length=128)  # Aumentado para almacenar el hash
    
    def save(self, *args, **kwargs):
        # Hash las respuestas antes de guardar si no están hasheadas
        if not self.pk or (self.respuesta1 and len(self.respuesta1) < 50):  # Si es nuevo o respuesta no hasheada
            self.respuesta1 = hash_respuesta(self.respuesta1)
        if not self.pk or (self.respuesta2 and len(self.respuesta2) < 50):
            self.respuesta2 = hash_respuesta(self.respuesta2)
        if not self.pk or (self.respuesta3 and len(self.respuesta3) < 50):
            self.respuesta3 = hash_respuesta(self.respuesta3)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Pregunta de Seguridad"
        verbose_name_plural = "Preguntas de Seguridad"

    def clean(self):
        # Verificar que no se repitan las preguntas
        preguntas = [self.pregunta1, self.pregunta2, self.pregunta3]
        if len(set(preguntas)) != 3:
            raise ValidationError('Las tres preguntas deben ser diferentes')

class Project(models.Model):
    nombre: models.CharField = models.CharField(max_length=100)
    descripcion: models.TextField = models.TextField(blank=True)
    usuarios_necesidades: models.TextField = models.TextField(blank=True, null=True, help_text="Usuarios finales y sus necesidades específicas")
    propietario: models.ForeignKey = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proyectos')
    creado: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    actualizado: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"

    def __str__(self) -> str:
        return self.nombre

    @property
    def fases(self) -> models.QuerySet:
        return self.fase_set.all() # type: ignore


class Fase(models.Model):
    proyecto: models.ForeignKey = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='fases')
    nombre: models.CharField = models.CharField(max_length=100)

    class Meta:
        unique_together = ('proyecto', 'nombre')
        ordering = ['nombre']
        verbose_name = "Fase"
        verbose_name_plural = "Fases"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.proyecto.nombre})"


class SubArtefacto(models.Model):
    fase: models.ForeignKey = models.ForeignKey(Fase, on_delete=models.CASCADE, related_name='subartefactos')
    nombre: models.CharField = models.CharField(max_length=100)
    enlace: models.URLField = models.URLField(blank=True)

    class Meta:
        unique_together = ('fase', 'nombre')
        ordering = ['nombre']
        verbose_name = "Subartefacto"
        verbose_name_plural = "Subartefactos"

    def __str__(self) -> str:
        return f"{self.nombre} - {self.fase.nombre}"


class Artefacto(models.Model):
    TIPO_CHOICES: List[Tuple[str, str]] = [
        ('AREQ', 'Análisis de Requisitos'),
        ('DISE', 'Diseño'),
        ('DEVS', 'Desarrollo'),
        ('PRUE', 'Pruebas'),
        ('DESP', 'Despliegue'),
    ]

    proyecto: models.ForeignKey = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='artefactos')
    fase: models.ForeignKey = models.ForeignKey(Fase, on_delete=models.CASCADE, related_name='artefactos')
    subartefacto: models.ForeignKey = models.ForeignKey(SubArtefacto, on_delete=models.SET_NULL, null=True, blank=True, related_name='artefactos')

    tipo: models.CharField = models.CharField(max_length=4, choices=TIPO_CHOICES)
    titulo: models.CharField = models.CharField(max_length=100)
    contenido: models.TextField = models.TextField()
    contexto: models.TextField = models.TextField(blank=True, null=True)  # Nuevo campo para requisitos
    requisitos_relacionados: models.JSONField = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de RF implementados en este artefacto"
    )
    historia_usuario_relacionada: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Nombre de la HU a la que pertenece este diagrama"
    )
    generado_por_ia: models.BooleanField = models.BooleanField(default=True)
    creado: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    actualizado: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = "Artefacto"
        verbose_name_plural = "Artefactos"

    def __str__(self) -> str:
        return f"{self.titulo} [{self.get_tipo_display()}]"
    
    def get_tipo_display(self) -> str:
        return dict(self.TIPO_CHOICES).get(self.tipo, "")
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.subartefacto and not self.fase:
            self.fase = self.subartefacto.fase
        super().save(*args, **kwargs)


class PruebacajaNegra(models.Model):
    """Modelo para almacenar pruebas de caja negra basadas en requisitos funcionales"""
    
    ESTADO_CHOICES: List[Tuple[str, str]] = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_EJECUCION', 'En Ejecución'),
        ('FINALIZADO', 'Finalizado'),
    ]
    
    RESULTADO_CHOICES: List[Tuple[str, str]] = [
        ('APTO', 'Apto'),
        ('NO_APTO', 'No Apto'),
        ('PENDIENTE', 'Pendiente'),
    ]

    proyecto: models.ForeignKey = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='pruebas_caja_negra')
    requisito_id: models.CharField = models.CharField(max_length=50, help_text="Ej: RF1, RF2, etc.")
    numero_prueba: models.IntegerField = models.IntegerField(help_text="Número secuencial de la prueba")
    
    # Información del requisito
    descripcion_requisito: models.TextField = models.TextField(help_text="Descripción del RF")
    historia_usuario_relacionada: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="HU a la que pertenece el RF"
    )
    requisitos_relacionados: models.JSONField = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de RFs que cubre esta prueba"
    )
    
    # Contenido de la prueba
    objetivo_prueba: models.TextField = models.TextField()
    datos_entrada: models.TextField = models.TextField()
    procedimiento: models.TextField = models.TextField()
    resultado_esperado: models.TextField = models.TextField()
    
    # Resultados de ejecución (editable por usuario)
    resultado_obtenido: models.TextField = models.TextField(blank=True, null=True)
    estado: models.CharField = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE'
    )
    resultado_final: models.CharField = models.CharField(
        max_length=20,
        choices=RESULTADO_CHOICES,
        default='PENDIENTE'
    )
    observaciones: models.TextField = models.TextField(blank=True, null=True)
    
    # Metadata
    generado_por_ia: models.BooleanField = models.BooleanField(default=True)
    creado: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    actualizado: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['numero_prueba']
        verbose_name = "Prueba de Caja Negra"
        verbose_name_plural = "Pruebas de Caja Negra"
        unique_together = ('proyecto', 'requisito_id', 'numero_prueba')

    def __str__(self) -> str:
        return f"PCN{self.numero_prueba} - {self.requisito_id} ({self.proyecto.nombre})"
        
