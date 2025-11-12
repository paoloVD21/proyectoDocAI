from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('login/', views.login_view, name='login'),#para el loguin
    path('', TemplateView.as_view(template_name='home.html'), name='home'),# pantilla de inicio 
    path('dashboard/', views.dashboard, name='dashboard'),# plantilla de dashboard
    path('proyecto/nuevo/', views.crear_proyecto, name='crear_proyecto'),# pantilla de crear proyecto
    path('proyecto/<int:pk>/editar/', views.editar_proyecto, name='editar_proyecto'),#editar proyecto
    path('proyecto/<int:proyecto_id>/', views.detalle_proyecto, name='detalle_proyecto'),#detalle de proyecto
    path('proyecto/<int:proyecto_id>/eliminar/', views.eliminar_proyecto, name='eliminar_proyecto'),#eliminar proyecto
    path('proyecto/<int:proyecto_id>/artefacto/nuevo/', views.crear_artefacto, name='crear_artefacto'),# crear artefacto
    path('ver_artefacto/<int:artefacto_id>/', views.ver_artefacto, name='ver_artefacto'), #ver el artefacto
    path('artefacto/editar/<int:artefacto_id>/', views.editar_artefacto, name='editar_artefacto'),# editar artefacto
    path('logout/', views.cerrar_sesion, name='logout'),  # Importante para cerrar sesión
    path('proyecto/<int:proyecto_id>/generar/<str:subartefacto_nombre>/', views.generar_artefacto, name='generar_artefacto'),#generar artefactos
    path('proyecto/<int:proyecto_id>/diagramas-flujo/', views.ver_diagramas_flujo, name='ver_diagramas_flujo'),  # ver todos los diagramas de flujo
    path('proyecto/<int:proyecto_id>/diagramas-secuencia/', views.ver_diagramas_secuencia, name='ver_diagramas_secuencia'),  # ver todos los diagramas de secuencia
    path('proyecto/<int:proyecto_id>/requisitos/', views.ver_requisitos, name='ver_requisitos'),  # ver todos los requisitos por HU
    path('proyecto/<int:proyecto_id>/requisitos/eliminar-todos/', views.eliminar_todos_requisitos, name='eliminar_todos_requisitos'),  # eliminar todos los requisitos
    path('proyecto/<int:proyecto_id>/diagramas-flujo/regenerar/', views.regenerar_diagramas_flujo, name='regenerar_diagramas_flujo'),  # regenerar todos los diagramas
    path('proyecto/<int:proyecto_id>/diagramas-flujo/eliminar-todos/', views.eliminar_todos_diagramas_flujo, name='eliminar_todos_diagramas_flujo'),  # eliminar todos los diagramas
    path('proyecto/<int:proyecto_id>/diagramas-secuencia/regenerar/', views.regenerar_diagramas_secuencia, name='regenerar_diagramas_secuencia'),  # regenerar todos los diagramas de secuencia
    path('proyecto/<int:proyecto_id>/diagramas-secuencia/eliminar-todos/', views.eliminar_todos_diagramas_secuencia, name='eliminar_todos_diagramas_secuencia'),  # eliminar todos los diagramas de secuencia
    path('diagrama/<int:diagrama_id>/regenerar/', views.regenerar_diagrama_individual, name='regenerar_diagrama_individual'),  # regenerar un diagrama de flujo específico
    path('diagrama-secuencia/<int:diagrama_id>/regenerar/', views.regenerar_diagrama_secuencia_individual, name='regenerar_diagrama_secuencia_individual'),  # regenerar un diagrama de secuencia específico
    path('artefacto/eliminar/<int:artefacto_id>/', views.eliminar_artefacto, name='eliminar_artefacto'),# eliminar artefacto
    path('artefacto/<int:artefacto_id>/descargar/', views.descargar_diagrama, name='descargar_diagrama'), #descaegar diagramas 
    path('password-reset/', views.password_reset_request, name='password_reset_request'), # Solicitar restablecimiento de contraseña
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'), # Verificar respuestas de seguridad
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'), # Confirmar nueva contraseña
]