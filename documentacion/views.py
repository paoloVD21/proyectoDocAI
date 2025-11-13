from django.shortcuts import render, redirect, get_object_or_404 # pyright: ignore[reportMissingModuleSource]
from django.contrib.auth.decorators import login_required # pyright: ignore[reportMissingModuleSource]
from django.contrib.auth import authenticate, login, logout # pyright: ignore[reportMissingModuleSource]
from django.views.decorators.http import require_POST # pyright: ignore[reportMissingModuleSource]
from django.http import JsonResponse, HttpResponse # pyright: ignore[reportMissingModuleSource]
from django.contrib.auth.forms import AuthenticationForm # pyright: ignore[reportMissingModuleSource]
from django.contrib import messages # pyright: ignore[reportMissingModuleSource]
from django.contrib.auth.models import User # pyright: ignore[reportMissingModuleSource]
from django.views.decorators.csrf import csrf_exempt # pyright: ignore[reportMissingModuleSource]
from django.core.exceptions import ValidationError # pyright: ignore[reportMissingModuleSource]
from .models import Project, Artefacto, Fase, SubArtefacto, SecurityQuestions, PruebacajaNegra
from .forms import (ProjectForm, ArtefactoForm, CustomUserCreationForm, SecurityQuestionsForm,
                   PasswordResetRequestForm, SecurityAnswersForm, NewPasswordForm)
from core.ia import generar_subartefacto_con_prompt, extraer_requisitos, _generar_contenido, PROMPTS
import datetime
import re

# ===== FUNCIÓN AUXILIAR PARA EXTRAER RF =====

def extraer_rf_del_contenido(contenido: str) -> list:
    """
    Extrae la lista de requisitos funcionales (RF) del contenido.
    Busca patrones como: RF1, RF2, RF3, etc.
    
    Returns: Lista como ["RF1", "RF2", "RF3"]
    """
    if not contenido:
        return []
    
    # Buscar patrones RF# al inicio de línea
    patrones = re.findall(r'\bRF\d+\b', contenido)
    
    # Eliminar duplicados manteniendo orden
    rf_list = []
    for rf in patrones:
        if rf not in rf_list:
            rf_list.append(rf)
    
    return rf_list


def extraer_historias_de_usuario(contenido: str) -> list:
    """
    Extrae las historias de usuario (HU) del contenido.
    Busca patrones como: HU1, HU2, HU3, etc.
    
    Returns: Lista como ["HU1", "HU2", "HU3"]
    """
    if not contenido:
        return []
    
    # Buscar patrones HU# 
    patrones = re.findall(r'\bHU\d+\b', contenido)
    
    # Eliminar duplicados manteniendo orden
    hu_list = []
    for hu in patrones:
        if hu not in hu_list:
            hu_list.append(hu)
    
    return hu_list


# ===== TIPOS DE ARTEFACTOS DEFINIDOS DIRECTAMENTE =====

ARTEFACTOS_TEXTO = [
    "Historia de Usuario",
    "Requisitos",
    "caja negra"
]

ARTEFACTOS_MERMAID = [
    "Diagrama de flujo",
    "Diagrama de Entidad-Relacion",
    "Diagrama de secuencia",
    "Diagrama de estado",
    "Diagrama de Contexto C4",
    "Diagrama de Contenedor C4",
    "Diagrama de Componente C4",
    "Diagrama de Despliegue C4"
]

ARTEFACTOS_VALIDOS = set(ARTEFACTOS_TEXTO + ARTEFACTOS_MERMAID)

# ===== UTILIDAD PARA LIMPIAR BLOQUES MERMAID =====

def limpiar_mermaid(texto):
    texto = texto.strip()
    if texto.startswith("```mermaid"):
        texto = texto.replace("```mermaid", "", 1).strip()
    if texto.endswith("```"):
        texto = texto[:texto.rfind("```")].strip()
    return texto

# ========================= DASHBOARD =========================

@login_required
def dashboard(request):
    proyectos = Project.objects.filter(propietario=request.user).order_by('-creado')
    return render(request, 'documentacion/dashboard.html', {'proyectos': proyectos})

# ===================== CREAR Y EDITAR PROYECTOS =====================

@login_required
def crear_proyecto(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            proyecto = form.save(commit=False)
            proyecto.propietario = request.user
            proyecto.save()

            fases_con_subartefactos = {
                "Análisis": ["Historia de Usuario", "Requisitos"],
                "Diseño": ["Diagrama de flujo", "Diagrama de secuencia", "Diagrama de Entidad-Relacion"],
                "Pruebas": ["caja negra"],
                "Despliegue": ["Diagrama de Contexto C4", "Diagrama de Contenedor C4", "Diagrama de Componente C4", "Diagrama de Despliegue C4"]
            }

            for nombre_fase, subartefactos in fases_con_subartefactos.items():
                fase = Fase.objects.create(proyecto=proyecto, nombre=nombre_fase)
                SubArtefacto.objects.bulk_create([
                    SubArtefacto(fase=fase, nombre=nombre_sub) for nombre_sub in subartefactos
                ])

            return redirect('dashboard')
    else:
        form = ProjectForm()
    return render(request, 'documentacion/crear_proyecto.html', {'form': form})

@login_required
def editar_proyecto(request, pk):
    proyecto = get_object_or_404(Project, pk=pk, propietario=request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ProjectForm(instance=proyecto)
    return render(request, 'documentacion/editar_proyecto.html', {'form': form, 'proyecto': proyecto})

# ===================== ELIMINAR PROYECTO =====================
@require_POST
@login_required
def eliminar_proyecto(request, proyecto_id):
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    proyecto.delete()
    return redirect('dashboard')

# ===================== REGISTRO USUARIO=====================

def signup(request):
    if request.method == 'POST':
        print("Datos POST recibidos:", request.POST)  # Debug
        user_form = CustomUserCreationForm(request.POST)
        security_form = SecurityQuestionsForm(request.POST)
        print("¿El formulario es válido?:", user_form.is_valid() and security_form.is_valid())  # Debug
        if user_form.is_valid() and security_form.is_valid():
            try:
                print("Creando usuario con datos:", user_form.cleaned_data)  # Debug
                user = user_form.save()
                print("Usuario creado:", user)  # Debug
                
                # Guardar preguntas de seguridad
                security_questions = security_form.save(commit=False)
                security_questions.user = user
                security_questions.save()
                
                # Autenticar con username y password1 para obtener el backend
                user = authenticate(
                    request,
                    username=user_form.cleaned_data['username'],
                    password=user_form.cleaned_data['password1']
                )
                if user is not None:
                    login(request, user)
                    messages.success(request, "¡Registro exitoso!")
                    return redirect('home')
                else:
                    messages.error(request, "No se pudo iniciar sesión automáticamente. Intenta iniciar sesión manualmente.")
                    return redirect('login')
            except Exception as e:
                print("Error al crear usuario:", str(e))  # Debug
                messages.error(request, f"Error al crear el usuario: {str(e)}")
        else:
            print("Errores del formulario user:", user_form.errors)  # Debug
            print("Errores del formulario security:", security_form.errors)  # Debug
            for form in [user_form, security_form]:
                for field in form.errors:
                    for error in form.errors[field]:
                        messages.error(request, f"{field}: {error}")
    else:
        user_form = CustomUserCreationForm()
        security_form = SecurityQuestionsForm()

    return render(request, 'registration/signup.html', {
        'form': user_form,
        'security_form': security_form
    })

def cerrar_sesion(request):
    logout(request)
    return redirect('home')

# ===================== DETALLE PROYECTO =====================

@login_required
def detalle_proyecto(request, proyecto_id):
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    orden_deseado = [
        "Análisis",
        "Diseño",
        "Pruebas",
        "Despliegue"
    ]
    
    # Obtener las fases usando el manager de Fase directamente
    fases_queryset = Fase.objects.filter(proyecto=proyecto).select_related('proyecto').prefetch_related('subartefactos')
    fases = sorted(fases_queryset, key=lambda f: orden_deseado.index(f.nombre) if f.nombre in orden_deseado else 999)

    orden_subartefactos = {
        "Análisis": ["Historia de Usuario", "Requisitos"],
        "Diseño": ["Diagrama de flujo", "Diagrama de secuencia", "Diagrama de Entidad-Relacion"],
        "Pruebas": ["caja negra"],
        "Despliegue": ["Diagrama de Contexto C4", "Diagrama de Contenedor C4", "Diagrama de Componente C4", "Diagrama de Despliegue C4"]
    }

    for fase in fases:
        orden = orden_subartefactos.get(fase.nombre, [])
        fase.subartefactos_ordenados = sorted( # pyright: ignore[reportAttributeAccessIssue]
            fase.subartefactos.all(), # pyright: ignore[reportAttributeAccessIssue]
            key=lambda s: orden.index(s.nombre) if s.nombre in orden else 999
        )

    artefactos = proyecto.artefactos.select_related('fase', 'subartefacto') # pyright: ignore[reportAttributeAccessIssue]

    #=======  Buscar HU y verificar si tiene requisitos ===================
    hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
    hu_con_requisitos = hu and hu.contexto and hu.contexto.strip() != ""
    
    # Verificar si ya se generaron los requisitos (puede ser el general o por HU)
    requisitos_generados = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__in=["Requisitos", "Requisitos - HU1", "Requisitos - HU2"]
    ).exists() or Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__startswith="Requisitos -"
    ).exists()
    
    # Verificar si ya se generó el diagrama de flujo (por HU)
    diagrama_flujo_generado = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__startswith="Diagrama de flujo"
    ).exists()
    
    # Verificar si ya se generó el diagrama de secuencia (por HU)
    diagrama_secuencia_generado = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__startswith="Diagrama de secuencia"
    ).exists()
    
    # Verificar si ya se generó el diagrama de entidad-relacion
    diagrama_entidad_relacion_generado = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo="Diagrama de Entidad-Relacion"
    ).exists()
    
    # Verificar que ambos diagramas base existan para desbloquear Entidad-Relación
    # (Diagrama de Entidad-Relación depende de Flujo y Secuencia)
    ambos_diagramas_base_generados = diagrama_flujo_generado and diagrama_secuencia_generado
    
    # Verificar si se generaron todos los diagramas de Diseño
    # Para diagramas que se generan por HU (flujo y secuencia), usar startswith
    todos_diagramas_diseño = (
        Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de flujo"
        ).exists() and
        Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de secuencia"
        ).exists() and
        Artefacto.objects.filter(
            proyecto=proyecto,
            titulo="Diagrama de Entidad-Relacion"
        ).exists()
    )
    
    # Verificar que Requisitos siga existiendo (validación crítica)
    # Si se elimina Requisitos, se bloquean todos los diagramas
    requisitos_existe = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__in=["Requisitos", "Requisitos - HU1", "Requisitos - HU2"]
    ).exists() or Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__startswith="Requisitos -"
    ).exists()
    
    # Los 3 diagramas de diseño solo cuentan si Requisitos sigue existiendo
    todos_diagramas_diseño_validos = todos_diagramas_diseño and requisitos_existe
    
    # Detectar si hay requisitos por HU (novedad)
    requisitos_por_hu = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__startswith="Requisitos -"
    ).exists()
    
    # Verificar si ya se generaron pruebas de caja negra
    pruebas_caja_negra_generadas = PruebacajaNegra.objects.filter(
        proyecto=proyecto
    ).exists()
    
    # Verificar si se han generado diagramas C4
    diagramas_c4_generados = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__in=[
            "Diagrama de Contexto C4",
            "Diagrama de Contenedor C4",
            "Diagrama de Componente C4",
            "Diagrama de Despliegue C4"
        ]
    ).exists()
    
    # Determinar qué fases están desbloqueadas
    # Fase Análisis: siempre desbloqueada
    # Fase Diseño: 
    #   - Diagrama de Flujo: desbloqueado si hay HU + Requisitos
    #   - Otros diagramas: desbloqueados si hay Diagrama de Flujo
    # Fase Pruebas: desbloqueada solo si hay TODOS los diagramas de Diseño Y Requisitos existe
    # Fase Despliegue: desbloqueada SOLO si existen pruebas de Caja Negra
    
    fases_desbloqueadas = {
        "Análisis": True,
        "Diseño": hu_con_requisitos and requisitos_generados and requisitos_existe,
        "Pruebas": todos_diagramas_diseño_validos,
        "Despliegue": pruebas_caja_negra_generadas
    }
    
    return render(request, 'documentacion/detalle_proyecto.html', {
        'proyecto': proyecto,
        'fases': fases,
        'artefactos': artefactos,
        'caso_uso_con_requisitos': hu_con_requisitos,
        'requisitos_generados': requisitos_generados,
        'requisitos_existe': requisitos_existe,
        'requisitos_por_hu': requisitos_por_hu,
        'diagrama_flujo_generado': diagrama_flujo_generado,
        'diagrama_secuencia_generado': diagrama_secuencia_generado,
        'diagrama_entidad_relacion_generado': diagrama_entidad_relacion_generado,
        'ambos_diagramas_base_generados': ambos_diagramas_base_generados,
        'todos_diagramas_diseño': todos_diagramas_diseño_validos,
        'fases_desbloqueadas': fases_desbloqueadas,
        'pruebas_caja_negra_generadas': pruebas_caja_negra_generadas,
        'diagramas_c4_generados': diagramas_c4_generados
    })

# ===================== CREAR Y EDITA ARTEFACTOS =====================

@login_required
def crear_artefacto(request, proyecto_id):
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    titulo_default = request.GET.get('subartefacto', '')

    if request.method == 'POST':
        form = ArtefactoForm(request.POST)
        if form.is_valid():
            artefacto = form.save(commit=False)
            artefacto.proyecto = proyecto
            artefacto.generado_por_ia = True
            try:
                if artefacto.get_tipo_display() in ARTEFACTOS_TEXTO:
                    contenido = generar_subartefacto_con_prompt(
                        tipo=artefacto.get_tipo_display(),
                        nombre_proyecto=proyecto.nombre,
                        descripcion=proyecto.descripcion
                    )
                else:
                    contenido = generar_subartefacto_con_prompt(
                        tipo=artefacto.get_tipo_display(),
                        texto=proyecto.descripcion
                    )
                    contenido = limpiar_mermaid(contenido)
                artefacto.contenido = contenido
            except Exception as e:
                import traceback
                artefacto.contenido = f"[ERROR IA] {str(e)}\n{traceback.format_exc()}"
            artefacto.save()
            return redirect('detalle_proyecto', proyecto_id=proyecto.id) # type: ignore
    else:
        form = ArtefactoForm(initial={'titulo': titulo_default})
    
    return render(request, 'documentacion/crear_artefacto.html', {
        'form': form,
        'proyecto': proyecto
    })

@login_required
def editar_artefacto(request, artefacto_id):
    artefacto = get_object_or_404(Artefacto, id=artefacto_id, proyecto__propietario=request.user)
    proyecto = artefacto.proyecto

    if request.method == 'POST':
        form = ArtefactoForm(request.POST, instance=artefacto)
        regenerar = 'regenerar' in request.POST

        if form.is_valid():
            if regenerar:
                try:
                    artefacto.titulo = form.cleaned_data['titulo']
                    artefacto.tipo = form.cleaned_data['tipo'] 
                    
                    if artefacto.titulo.lower() == "historia de usuario":
                        contenido = generar_subartefacto_con_prompt(
                            tipo="Historia de Usuario",
                            nombre_proyecto=proyecto.nombre,
                            descripcion=proyecto.descripcion
                        )
                        artefacto.contenido = contenido
                        artefacto.generado_por_ia = True

                        try:
                            from core.ia import extraer_requisitos  
                            requisitos = extraer_requisitos(contenido)
                            artefacto.contexto = requisitos
                        except Exception as e:
                            artefacto.contexto = "[ERROR AL EXTRAER REQUISITOS]"
                    
                    # Especial para Requisitos: necesita la Historia de Usuario actual
                    elif artefacto.titulo.lower() == "requisitos":
                        # Buscar la Historia de Usuario del proyecto
                        artefactos = Artefacto.objects.filter(proyecto=proyecto)
                        hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
                        
                        if not hu:
                            hu = artefactos.filter(titulo__icontains="Historia").first()
                        
                        if hu and hu.contenido and hu.contenido.strip() != "":
                            # Pasar la Historia de Usuario completa al prompt
                            contenido = generar_subartefacto_con_prompt(
                                tipo="Requisitos",
                                texto=hu.contenido
                            )
                            artefacto.contenido = contenido
                            artefacto.generado_por_ia = True
                        else:
                            raise ValueError("No se encontró Historia de Usuario para regenerar Requisitos")
                    
                    # Especial para Diagrama de flujo: con contexto de requisitos
                    elif artefacto.titulo.lower() == "diagrama de flujo":
                        artefactos = Artefacto.objects.filter(proyecto=proyecto)
                        hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
                        
                        if not hu:
                            hu = artefactos.filter(titulo__icontains="Historia").first()
                        
                        if hu and hu.contenido and hu.contenido.strip() != "":
                            requisitos_art = artefactos.filter(titulo__iexact="Requisitos").first()
                            
                            if requisitos_art and requisitos_art.contenido:
                                # Regenerar diagrama con HU y Requisitos
                                contenido = generar_subartefacto_con_prompt(
                                    tipo="Diagrama de flujo",
                                    historia_usuario=hu.contenido,
                                    requisitos=requisitos_art.contenido
                                )
                                # Actualizar lista de RF relacionados
                                artefacto.requisitos_relacionados = extraer_rf_del_contenido(requisitos_art.contenido)
                            else:
                                # Si no hay requisitos, generar solo con HU
                                contenido = generar_subartefacto_con_prompt(
                                    tipo="Diagrama de flujo",
                                    historia_usuario=hu.contenido,
                                    requisitos="(Sin requisitos específicos)"
                                )
                                artefacto.requisitos_relacionados = []
                            
                            contenido = limpiar_mermaid(contenido)
                            artefacto.contenido = contenido
                            artefacto.generado_por_ia = True
                        else:
                            raise ValueError("No se encontró Historia de Usuario para regenerar Diagrama de Flujo")
                    
                    else:
                        contenido = generar_subartefacto_con_prompt(
                            tipo=artefacto.titulo,
                            texto=proyecto.descripcion
                        )
                        artefacto.contenido = limpiar_mermaid(contenido)
                        artefacto.generado_por_ia = True

                    messages.success(request, '♻️ Artefacto regenerado correctamente con IA.')

                except Exception as e:
                    import traceback
                    artefacto.contenido = f"[ERROR IA] {str(e)}\n{traceback.format_exc()}"
                    messages.error(request, '❌ Error al regenerar el contenido con IA.')
                
            else:
                
                artefacto = form.save(commit=False)
                messages.success(request, '💾 Artefacto actualizado correctamente.')

            artefacto.save()
            
            # Redirect inteligente según el tipo de artefacto
            if artefacto.titulo in ["Diagrama de Contexto C4", "Diagrama de Contenedor C4", "Diagrama de Componente C4", "Diagrama de Despliegue C4"]:
                return redirect('ver_diagramas_c4', proyecto_id=artefacto.proyecto.id) # pyright: ignore[reportAttributeAccessIssue]
            elif "Diagrama de flujo" in artefacto.titulo:
                return redirect('ver_diagramas_flujo', proyecto_id=artefacto.proyecto.id) # pyright: ignore[reportAttributeAccessIssue]
            elif "Diagrama de secuencia" in artefacto.titulo:
                return redirect('ver_diagramas_secuencia', proyecto_id=artefacto.proyecto.id) # pyright: ignore[reportAttributeAccessIssue]
            elif "Diagrama de Entidad-Relacion" in artefacto.titulo:
                return redirect('ver_diagrama_entidad_relacion', proyecto_id=artefacto.proyecto.id) # pyright: ignore[reportAttributeAccessIssue]
            elif "Requisitos" in artefacto.titulo:
                return redirect('ver_requisitos', proyecto_id=artefacto.proyecto.id) # pyright: ignore[reportAttributeAccessIssue]
            elif "Historia de Usuario" in artefacto.titulo:
                return redirect('ver_historias_usuario', artefacto_id=artefacto.id) # pyright: ignore[reportAttributeAccessIssue]
            else:
                return redirect('ver_artefacto', artefacto_id=artefacto.id) # pyright: ignore[reportAttributeAccessIssue]
        else:
            print("❌ Errores de validación:", form.errors) 
            messages.error(request, '❌ Corrige los errores en el formulario.')


    else:
        form = ArtefactoForm(instance=artefacto)

    return render(request, 'documentacion/editar_artefacto.html', {
        'form': form,
        'artefacto': artefacto
    })

# ===================== ELIMINAR ARTEFACTOS =====================
@login_required
def eliminar_artefacto(request, artefacto_id):
    artefacto = get_object_or_404(Artefacto, id=artefacto_id, proyecto__propietario=request.user)
    proyecto_id = artefacto.proyecto.id # pyright: ignore[reportAttributeAccessIssue]
    artefacto.delete()
    messages.success(request, "Artefacto eliminado correctamente.")
    return redirect('detalle_proyecto', proyecto_id=proyecto_id)

# ===================== VER ARTEFACTOS =====================

@login_required
def ver_artefacto(request, artefacto_id):
    artefacto = get_object_or_404(Artefacto, id=artefacto_id)
    is_mermaid = artefacto.titulo in ARTEFACTOS_MERMAID
    
    # Para mostrar Requisitos, necesitamos la Historia de Usuario
    hu = None
    hu_especifico = None  # Variable para filtrar requisitos por HU específica
    
    if artefacto.titulo == "Requisitos" or artefacto.titulo.lower() == "requisitos":
        hu = Artefacto.objects.filter(
            proyecto=artefacto.proyecto,
            titulo__iexact="Historia de Usuario"
        ).first()
        
        # Determinar si estamos viendo una HU específica
        hu_especifico = artefacto.historia_usuario_relacionada
    elif artefacto.titulo.startswith("Requisitos -"):
        # Para requisitos por HU: extraer la HU del título
        # Título es "Requisitos - HU1", así que extraemos "HU1"
        hu_especifico = artefacto.titulo.replace("Requisitos - ", "").strip()
        
        hu = Artefacto.objects.filter(
            proyecto=artefacto.proyecto,
            titulo__iexact="Historia de Usuario"
        ).first()
    
    if artefacto.titulo.lower() in PROMPTS and artefacto.titulo.lower() in ARTEFACTOS_MERMAID:
        try:
            texto_diagrama = artefacto.contexto if artefacto.contexto else artefacto.contenido
            prompt = PROMPTS[artefacto.titulo](texto_diagrama)
            mermaid_code = _generar_contenido(prompt)
        except Exception as e:
            mermaid_code = f"[ERROR AL GENERAR DIAGRAMA] {str(e)}"
    
    return render(request, 'documentacion/ver_artefacto.html', {
        'artefacto': artefacto,
        'is_mermaid': is_mermaid,
        'hu': hu,
        'hu_especifico': hu_especifico,
    })


@login_required
def ver_historias_usuario(request, artefacto_id):
    """Vista especializada para mostrar Historias de Usuario"""
    artefacto = get_object_or_404(Artefacto, id=artefacto_id, proyecto__propietario=request.user)
    proyecto = artefacto.proyecto
    
    # Verificar que sea un artefacto de Historia de Usuario
    if artefacto.titulo != "Historia de Usuario":
        return redirect('ver_artefacto', artefacto_id=artefacto_id)
    
    return render(request, 'documentacion/ver_historias_usuario.html', {
        'artefacto': artefacto,
        'proyecto': proyecto,
    })


@login_required
def ver_requisitos(request, proyecto_id):
    """
    Vista que muestra TODOS los requisitos generados para un proyecto (uno por HU).
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    # Obtener todos los requisitos de HU específicas
    requisitos = list(Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__startswith="Requisitos -"
    ))
    
    # Si no encuentra requisitos por HU, buscar el artefacto general
    if not requisitos:
        requisito_general = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__iexact="Requisitos"
        ).first()
        
        if requisito_general:
            return redirect('ver_artefacto', artefacto_id=requisito_general.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        messages.warning(request, "⚠️ No se han generado Requisitos aún.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    # Ordenar numéricamente por HU (HU1, HU2, ..., HU10, HU11, etc.)
    def extraer_numero_hu(requisito):
        hu_str = requisito.historia_usuario_relacionada or ""
        try:
            numero = int(hu_str.replace("HU", "").strip())
            return numero
        except (ValueError, AttributeError):
            return float('inf')  # Si no es HU, lo pone al final
    
    requisitos.sort(key=extraer_numero_hu)
    
    return render(request, 'documentacion/ver_requisitos.html', {
        'proyecto': proyecto,
        'requisitos': requisitos,
        'cantidad_requisitos': len(requisitos),
    })


@login_required
def eliminar_todos_requisitos(request, proyecto_id):
    """
    Vista para ELIMINAR todos los requisitos de un proyecto.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        requisitos = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Requisitos -"
        )
        
        cantidad = requisitos.count()
        requisitos.delete()
        
        messages.success(request, f"✅ Se eliminaron {cantidad} Requisitos correctamente")
        
    except Exception as e:
        messages.error(request, f"❌ Error al eliminar requisitos: {str(e)}")
    
    return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def ver_diagramas_flujo(request, proyecto_id):
    """
    Vista que muestra TODOS los diagramas de flujo generados para un proyecto.
    Se accede después de generar los diagramas la primera vez.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    # Obtener todos los diagramas de flujo
    diagramas = list(Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__startswith="Diagrama de flujo"
    ))
    
    if not diagramas:
        messages.warning(request, "⚠️ No se han generado Diagramas de Flujo aún.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    # Ordenar numéricamente por HU (HU1, HU2, ..., HU10, HU11, etc.)
    def extraer_numero_hu(diagrama):
        hu_str = diagrama.historia_usuario_relacionada or ""
        try:
            numero = int(hu_str.replace("HU", "").strip())
            return numero
        except (ValueError, AttributeError):
            return float('inf')  # Si no es HU, lo pone al final
    
    diagramas.sort(key=extraer_numero_hu)
    
    # Obtener artefactos de Requisitos para extraer descripciones
    requisitos_dict = {}
    artefactos = Artefacto.objects.filter(proyecto=proyecto)
    
    # Buscar tanto "Requisitos" como "Requisitos - HU#"
    requisitos_arts = artefactos.filter(titulo__in=["Requisitos"]) | artefactos.filter(titulo__startswith="Requisitos -")
    
    for req_art in requisitos_arts:
        # Extraer descripciones de RFs del contenido
        # Formato esperado: "RF1 [HU1] descripción" o "RF1: descripción"
        import re
        contenido = req_art.contenido or ""
        
        # Buscar patrones RF# seguidos de espacios, [HU#], y luego la descripción
        # Patrón: RF1 [HU1] El sistema debe...
        matches = re.finditer(r'(RF\d+)\s*(?:\[HU\d+\])?\s*(.+?)(?=\n(?:RF\d+|\Z))', contenido, re.DOTALL)
        for match in matches:
            rf_id = match.group(1).strip()
            rf_desc = match.group(2).strip()
            # Limpiar saltos de línea y espacios excesivos
            rf_desc = ' '.join(rf_desc.split())
            if rf_desc:
                requisitos_dict[rf_id] = rf_desc
    
    # Agregar a cada diagrama sus descripciones de RF
    for diagrama in diagramas:
        diagrama.rf_descriptions = {}  # pyright: ignore[reportAttributeAccessIssue]
        if diagrama.requisitos_relacionados:
            for rf in diagrama.requisitos_relacionados:
                diagrama.rf_descriptions[rf] = requisitos_dict.get(rf, "Sin descripción")  # pyright: ignore[reportAttributeAccessIssue]
    
    return render(request, 'documentacion/ver_diagramas_flujo.html', {
        'proyecto': proyecto,
        'diagramas': diagramas,
        'cantidad_diagramas': len(diagramas),
        'requisitos_dict': requisitos_dict,
    })


@login_required
def ver_diagramas_secuencia(request, proyecto_id):
    """
    Vista que muestra TODOS los diagramas de secuencia generados para un proyecto.
    Se accede después de generar los diagramas la primera vez.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    # Obtener todos los diagramas de secuencia
    diagramas = list(Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__startswith="Diagrama de secuencia"
    ))
    
    if not diagramas:
        messages.warning(request, "⚠️ No se han generado Diagramas de Secuencia aún.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    # Ordenar numéricamente por HU (HU1, HU2, ..., HU10, HU11, etc.)
    def extraer_numero_hu(diagrama):
        hu_str = diagrama.historia_usuario_relacionada or ""
        try:
            numero = int(hu_str.replace("HU", "").strip())
            return numero
        except (ValueError, AttributeError):
            return float('inf')  # Si no es HU, lo pone al final
    
    diagramas.sort(key=extraer_numero_hu)
    
    # Obtener artefactos de Requisitos para extraer descripciones
    requisitos_dict = {}
    artefactos = Artefacto.objects.filter(proyecto=proyecto)
    
    # Buscar tanto "Requisitos" como "Requisitos - HU#"
    requisitos_arts = artefactos.filter(titulo__in=["Requisitos"]) | artefactos.filter(titulo__startswith="Requisitos -")
    
    for req_art in requisitos_arts:
        # Extraer descripciones de RFs del contenido
        # Formato esperado: "RF1 [HU1] descripción"
        import re
        contenido = req_art.contenido or ""
        
        # Buscar patrones RF# seguidos de espacios, [HU#], y luego la descripción
        matches = re.finditer(r'(RF\d+)\s*(?:\[HU\d+\])?\s*(.+?)(?=\n(?:RF\d+|\Z))', contenido, re.DOTALL)
        for match in matches:
            rf_id = match.group(1).strip()
            rf_desc = match.group(2).strip()
            # Limpiar saltos de línea y espacios excesivos
            rf_desc = ' '.join(rf_desc.split())
            if rf_desc:
                requisitos_dict[rf_id] = rf_desc
    
    # Agregar a cada diagrama sus descripciones de RF
    for diagrama in diagramas:
        diagrama.rf_descriptions = {}  # pyright: ignore[reportAttributeAccessIssue]
        if diagrama.requisitos_relacionados:
            for rf in diagrama.requisitos_relacionados:
                diagrama.rf_descriptions[rf] = requisitos_dict.get(rf, "Sin descripción")  # pyright: ignore[reportAttributeAccessIssue]
    
    return render(request, 'documentacion/ver_diagramas_secuencia.html', {
        'proyecto': proyecto,
        'diagramas': diagramas,
        'cantidad_diagramas': len(diagramas),
        'requisitos_dict': requisitos_dict,
    })


@login_required
def ver_diagrama_entidad_relacion(request, proyecto_id):
    """
    Vista que muestra el Diagrama de Entidad-Relacion generado para un proyecto.
    Es un diagrama único que considera todo el contexto del proyecto.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    # Obtener el diagrama ER
    diagrama = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo="Diagrama de Entidad-Relacion"
    ).first()
    
    if not diagrama:
        messages.warning(request, "⚠️ No se ha generado el Diagrama de Entidad-Relacion aún.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    return render(request, 'documentacion/ver_diagrama_entidad_relacion.html', {
        'proyecto': proyecto,
        'diagrama': diagrama,
    })


@login_required
def regenerar_diagrama_entidad_relacion(request, proyecto_id):
    """
    Vista para REGENERAR el Diagrama de Entidad-Relacion con contexto actualizado.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        diagrama = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo="Diagrama de Entidad-Relacion"
        ).first()
        
        if not diagrama:
            messages.error(request, "❌ El Diagrama de Entidad-Relacion no existe")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        artefactos = Artefacto.objects.filter(proyecto=proyecto)
        hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
        
        if not hu:
            messages.error(request, "❌ No se encontró la Historia de Usuario")
            return redirect('ver_diagrama_entidad_relacion', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Buscar requisitos
        requisitos_art = artefactos.filter(
            titulo__in=["Requisitos"]
        ).first()
        
        if not requisitos_art:
            requisitos_art = artefactos.filter(
                titulo__startswith="Requisitos -"
            ).first()
        
        # Recopilar todos los diagramas de flujo
        diagramas_flujo = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de flujo"
        ).order_by('id')
        
        # Recopilar todos los diagramas de secuencia
        diagramas_secuencia = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de secuencia"
        ).order_by('id')
        
        # Construir contexto completo
        contexto_flujos = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_flujo]) if diagramas_flujo else "No hay diagramas de flujo"
        contexto_secuencias = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_secuencia]) if diagramas_secuencia else "No hay diagramas de secuencia"
        
        # Construir el contexto de requisitos
        requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos"
        
        # Construir el contexto de historias de usuario con diagramas
        historias_completo = f"""
{hu.contenido}

DIAGRAMAS DE FLUJO (Procesos del Sistema):
{contexto_flujos}

DIAGRAMAS DE SECUENCIA (Interacciones del Sistema):
{contexto_secuencias}
"""
        
        # DEBUG: Mostrar qué se está enviando a la IA (REGENERACIÓN)
        print(f"[DEBUG ER - REGEN] Regenerando Diagrama de Entidad-Relacion con contexto:")
        print(f"[DEBUG ER - REGEN] HU: {len(hu.contenido)} caracteres")
        print(f"[DEBUG ER - REGEN] Requisitos: {len(requisitos_texto)} caracteres")
        print(f"[DEBUG ER - REGEN] Diagramas de Flujo: {len(contexto_flujos)} caracteres ({len(list(diagramas_flujo))} diagramas)")
        print(f"[DEBUG ER - REGEN] Diagramas de Secuencia: {len(contexto_secuencias)} caracteres ({len(list(diagramas_secuencia))} diagramas)")
        print(f"[DEBUG ER - REGEN] Total: {len(historias_completo) + len(requisitos_texto)} caracteres")
        
        # Regenerar el diagrama ER con los parámetros correctos
        contenido_diagrama = generar_subartefacto_con_prompt(
            tipo="Diagrama de Entidad-Relacion",
            historias_usuario=historias_completo,
            requisitos=requisitos_texto
        )
        
        contenido_diagrama = limpiar_mermaid(contenido_diagrama)
        
        # Actualizar el diagrama existente
        diagrama.contenido = contenido_diagrama
        diagrama.save()
        
        messages.success(request, "✅ Diagrama de Entidad-Relacion regenerado exitosamente con contexto actualizado.")
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Regenerando diagrama ER: {str(e)}")
        print(traceback.format_exc())
        messages.error(request, f"❌ Error al regenerar: {str(e)}")
    
    return redirect('ver_diagrama_entidad_relacion', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def regenerar_diagramas_flujo(request, proyecto_id):
    """
    Vista para REGENERAR todos los diagramas de flujo de un proyecto.
    Solo accesible desde la vista ver_diagramas_flujo.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        artefactos = Artefacto.objects.filter(proyecto=proyecto)
        hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
        
        if not hu:
            messages.error(request, "❌ No se encontró la Historia de Usuario")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        requisitos_art = artefactos.filter(titulo__iexact="Requisitos").first()
        
        if not requisitos_art or not requisitos_art.contenido:
            messages.error(request, "❌ No se encontraron Requisitos para regenerar diagramas de flujo")
            return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Extraer todas las HU del contenido de Requisitos
        hu_list = extraer_historias_de_usuario(requisitos_art.contenido)
        
        if not hu_list:
            messages.error(request, "❌ No se encontraron Historias de Usuario en los Requisitos")
            return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        diagramas_regenerados = 0
        
        # Regenerar cada diagrama
        for hu_name in hu_list:
            try:
                diagrama_existente = Artefacto.objects.filter(
                    proyecto=proyecto,
                    titulo=f"Diagrama de flujo - {hu_name}"
                ).first()
                
                if not diagrama_existente:
                    continue
                
                # Buscar la HU en el contenido
                hu_pattern = f"{hu_name}:"
                
                # Extraer contenido de esa HU específica
                if hu_pattern in hu.contenido:
                    hu_inicio = hu.contenido.find(hu_pattern)
                    hu_siguiente = hu.contenido.find("\nHU", hu_inicio + 1)
                    if hu_siguiente == -1:
                        hu_contenido_especifico = hu.contenido[hu_inicio:]
                    else:
                        hu_contenido_especifico = hu.contenido[hu_inicio:hu_siguiente]
                else:
                    hu_contenido_especifico = hu_name
                
                # 🔑 IMPORTANTE: Extraer TODOS los RF asociados a esta HU
                # Buscar con múltiples formatos: HU1, HU01, HU001, etc.
                requisitos_especificos = []
                
                # Extraer número de HU (ej: HU1 -> 1, HU02 -> 2)
                hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
                
                for line in requisitos_art.contenido.split('\n'):
                    # Buscar múltiples formatos: [HU1], [HU01], [HU001], etc.
                    if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                        requisitos_especificos.append(line.strip())
                
                if not requisitos_especificos:
                    print(f"[DEBUG] No se encontraron RF para {hu_name} en regeneración")
                    print(f"[DEBUG] Buscando patrones: [{hu_name}], [HU0{hu_numero}], [HU{hu_numero}]")
                    continue
                
                requisitos_texto = "\n".join(requisitos_especificos)
                
                # Generar diagrama para esta HU específica
                contenido_diagrama = generar_subartefacto_con_prompt(
                    tipo="Diagrama de flujo",
                    historia_usuario=hu_contenido_especifico,
                    requisitos=requisitos_texto
                )
                
                contenido_diagrama = limpiar_mermaid(contenido_diagrama)
                
                # Extraer RF para guardar en relación
                rf_list = [rf.split()[0] for rf in requisitos_especificos if rf.split()]
                
                # Actualizar artefacto existente
                diagrama_existente.contenido = contenido_diagrama
                diagrama_existente.requisitos_relacionados = rf_list
                diagrama_existente.save()
                
                diagramas_regenerados += 1
                print(f"[DEBUG] Diagrama para {hu_name} regenerado")
                
            except Exception as e:
                print(f"[ERROR] Regenerando diagrama para {hu_name}: {str(e)}")
                continue
        
        messages.success(request, f"✅ Se regeneraron {diagramas_regenerados} Diagrama(s) de Flujo")
        
    except Exception as e:
        messages.error(request, f"❌ Error al regenerar: {str(e)}")
    
    return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


def eliminar_todos_diagramas_flujo(request, proyecto_id):
    """
    Vista para ELIMINAR todos los diagramas de flujo de un proyecto.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        diagramas = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de flujo"
        )
        
        cantidad = diagramas.count()
        diagramas.delete()
        
        messages.success(request, f"✅ Se eliminaron {cantidad} Diagrama(s) de Flujo correctamente")
        
    except Exception as e:
        messages.error(request, f"❌ Error al eliminar diagramas: {str(e)}")
    
    return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def eliminar_todos_diagramas_secuencia(request, proyecto_id):
    """
    Vista para ELIMINAR todos los diagramas de secuencia de un proyecto.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        diagramas = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de secuencia"
        )
        
        cantidad = diagramas.count()
        diagramas.delete()
        
        messages.success(request, f"✅ Se eliminaron {cantidad} Diagrama(s) de Secuencia correctamente")
        
    except Exception as e:
        messages.error(request, f"❌ Error al eliminar diagramas: {str(e)}")
    
    return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


def regenerar_diagrama_individual(request, diagrama_id):
    """
    Vista para REGENERAR UN SOLO diagrama de flujo con IA.
    """
    diagrama = get_object_or_404(Artefacto, id=diagrama_id)
    proyecto = diagrama.proyecto
    
    # Verificar que el usuario sea propietario del proyecto
    if proyecto.propietario != request.user:
        messages.error(request, "❌ No tienes permiso para regenerar este diagrama")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    try:
        hu_name = diagrama.historia_usuario_relacionada or ""
        
        artefactos = Artefacto.objects.filter(proyecto=proyecto)
        hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
        
        # Buscar requisitos (puede ser el general "Requisitos" o los por HU "Requisitos - HU#")
        requisitos_art = artefactos.filter(
            titulo__in=["Requisitos"]
        ).first()
        
        if not requisitos_art:
            # Si no está el general, buscar cualquiera de los por HU
            requisitos_art = artefactos.filter(
                titulo__startswith="Requisitos -"
            ).first()
        
        if not hu or not requisitos_art or not requisitos_art.contenido:
            messages.error(request, "❌ No se encontraron los datos necesarios para regenerar")
            return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Buscar contenido específico de esa HU
        hu_pattern = f"{hu_name}:"
        if hu_pattern in hu.contenido:
            hu_inicio = hu.contenido.find(hu_pattern)
            hu_siguiente = hu.contenido.find("\nHU", hu_inicio + 1)
            if hu_siguiente == -1:
                hu_contenido_especifico = hu.contenido[hu_inicio:]
            else:
                hu_contenido_especifico = hu.contenido[hu_inicio:hu_siguiente]
        else:
            hu_contenido_especifico = hu_name
        
        # Extraer RF específicos de esta HU
        requisitos_especificos = []
        hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
        
        for line in requisitos_art.contenido.split('\n'):
            if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                requisitos_especificos.append(line.strip())
        
        if not requisitos_especificos:
            messages.warning(request, f"⚠️ No se encontraron Requisitos para {hu_name}")
            return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Regenerar diagrama
        requisitos_texto = "\n".join(requisitos_especificos)
        
        contenido_diagrama = generar_subartefacto_con_prompt(
            tipo="Diagrama de flujo",
            historia_usuario=hu_contenido_especifico,
            requisitos=requisitos_texto
        )
        
        contenido_diagrama = limpiar_mermaid(contenido_diagrama)
        
        # Extraer RF para guardar
        rf_list = [rf.split()[0] for rf in requisitos_especificos if rf.split()]
        
        # Actualizar diagrama
        diagrama.contenido = contenido_diagrama
        diagrama.requisitos_relacionados = rf_list
        diagrama.save()
        
        messages.success(request, f"✅ Diagrama de {hu_name} regenerado exitosamente con IA")
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Regenerando diagrama individual: {str(e)}")
        print(traceback.format_exc())
        messages.error(request, f"❌ Error al regenerar diagrama: {str(e)}")
    
    return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def regenerar_diagrama_secuencia_individual(request, diagrama_id):
    """
    Vista para REGENERAR UN SOLO diagrama de secuencia con IA.
    """
    diagrama = get_object_or_404(Artefacto, id=diagrama_id)
    proyecto = diagrama.proyecto
    
    # Verificar que el usuario sea propietario del proyecto
    if proyecto.propietario != request.user:
        messages.error(request, "❌ No tienes permiso para regenerar este diagrama")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    try:
        hu_name = diagrama.historia_usuario_relacionada or ""
        
        artefactos = Artefacto.objects.filter(proyecto=proyecto)
        hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
        
        # Buscar requisitos (puede ser el general "Requisitos" o los por HU "Requisitos - HU#")
        requisitos_art = artefactos.filter(
            titulo__in=["Requisitos"]
        ).first()
        
        if not requisitos_art:
            # Si no está el general, buscar cualquiera de los por HU
            requisitos_art = artefactos.filter(
                titulo__startswith="Requisitos -"
            ).first()
        
        if not hu or not requisitos_art or not requisitos_art.contenido:
            messages.error(request, "❌ No se encontraron los datos necesarios para regenerar")
            return redirect('ver_diagramas_secuencia', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Buscar contenido específico de esa HU
        hu_pattern = f"{hu_name}:"
        if hu_pattern in hu.contenido:
            hu_inicio = hu.contenido.find(hu_pattern)
            hu_siguiente = hu.contenido.find("\nHU", hu_inicio + 1)
            if hu_siguiente == -1:
                hu_contenido_especifico = hu.contenido[hu_inicio:]
            else:
                hu_contenido_especifico = hu.contenido[hu_inicio:hu_siguiente]
        else:
            hu_contenido_especifico = hu_name
        
        # Extraer RF específicos de esta HU
        requisitos_especificos = []
        hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
        
        for line in requisitos_art.contenido.split('\n'):
            if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                requisitos_especificos.append(line.strip())
        
        if not requisitos_especificos:
            messages.warning(request, f"⚠️ No se encontraron Requisitos para {hu_name}")
            return redirect('ver_diagramas_secuencia', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Regenerar diagrama de secuencia
        requisitos_texto = "\n".join(requisitos_especificos)
        
        contenido_diagrama = generar_subartefacto_con_prompt(
            tipo="Diagrama de secuencia",
            historia_usuario=hu_contenido_especifico,
            requisitos=requisitos_texto
        )
        
        contenido_diagrama = limpiar_mermaid(contenido_diagrama)
        
        # Extraer RF para guardar
        rf_list = [rf.split()[0] for rf in requisitos_especificos if rf.split()]
        
        # Actualizar diagrama
        diagrama.contenido = contenido_diagrama
        diagrama.requisitos_relacionados = rf_list
        diagrama.save()
        
        messages.success(request, f"✅ Diagrama de Secuencia de {hu_name} regenerado exitosamente con IA")
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Regenerando diagrama de secuencia individual: {str(e)}")
        print(traceback.format_exc())
        messages.error(request, f"❌ Error al regenerar diagrama de secuencia: {str(e)}")
    
    return redirect('ver_diagramas_secuencia', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def regenerar_diagramas_secuencia(request, proyecto_id):
    """
    Vista para REGENERAR todos los diagramas de secuencia de un proyecto.
    Solo accesible desde la vista ver_diagramas_secuencia.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        artefactos = Artefacto.objects.filter(proyecto=proyecto)
        hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
        
        if not hu:
            messages.error(request, "❌ No se encontró la Historia de Usuario")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        requisitos_art = artefactos.filter(titulo__iexact="Requisitos").first()
        
        if not requisitos_art or not requisitos_art.contenido:
            messages.error(request, "❌ No se encontraron Requisitos para regenerar diagramas de secuencia")
            return redirect('ver_diagramas_secuencia', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Extraer todas las HU del contenido de Requisitos
        hu_list = extraer_historias_de_usuario(requisitos_art.contenido)
        
        if not hu_list:
            messages.error(request, "❌ No se encontraron Historias de Usuario en los Requisitos")
            return redirect('ver_diagramas_secuencia', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        diagramas_regenerados = 0
        
        # Regenerar cada diagrama
        for hu_name in hu_list:
            try:
                diagrama_existente = Artefacto.objects.filter(
                    proyecto=proyecto,
                    titulo=f"Diagrama de secuencia - {hu_name}"
                ).first()
                
                if not diagrama_existente:
                    continue
                
                # Buscar la HU en el contenido
                hu_pattern = f"{hu_name}:"
                
                # Extraer contenido de esa HU específica
                if hu_pattern in hu.contenido:
                    hu_inicio = hu.contenido.find(hu_pattern)
                    hu_siguiente = hu.contenido.find("\nHU", hu_inicio + 1)
                    if hu_siguiente == -1:
                        hu_contenido_especifico = hu.contenido[hu_inicio:]
                    else:
                        hu_contenido_especifico = hu.contenido[hu_inicio:hu_siguiente]
                else:
                    hu_contenido_especifico = hu_name
                
                # 🔑 IMPORTANTE: Extraer TODOS los RF asociados a esta HU
                # Buscar con múltiples formatos: HU1, HU01, HU001, etc.
                requisitos_especificos = []
                
                # Extraer número de HU (ej: HU1 -> 1, HU02 -> 2)
                hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
                
                for line in requisitos_art.contenido.split('\n'):
                    # Buscar múltiples formatos: [HU1], [HU01], [HU001], etc.
                    if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                        requisitos_especificos.append(line.strip())
                
                if not requisitos_especificos:
                    print(f"[DEBUG] No se encontraron RF para {hu_name} en regeneración de secuencias")
                    print(f"[DEBUG] Buscando patrones: [{hu_name}], [HU0{hu_numero}], [HU{hu_numero}]")
                    continue
                
                requisitos_texto = "\n".join(requisitos_especificos)
                
                # Generar diagrama para esta HU específica
                contenido_diagrama = generar_subartefacto_con_prompt(
                    tipo="Diagrama de secuencia",
                    historia_usuario=hu_contenido_especifico,
                    requisitos=requisitos_texto
                )
                
                contenido_diagrama = limpiar_mermaid(contenido_diagrama)
                
                # Extraer RF para guardar en relación
                rf_list = [rf.split()[0] for rf in requisitos_especificos if rf.split()]
                
                # Actualizar artefacto existente
                diagrama_existente.contenido = contenido_diagrama
                diagrama_existente.requisitos_relacionados = rf_list
                diagrama_existente.save()
                
                diagramas_regenerados += 1
                print(f"[DEBUG] Diagrama de secuencia para {hu_name} regenerado")
                
            except Exception as e:
                print(f"[ERROR] Regenerando diagrama de secuencia para {hu_name}: {str(e)}")
                continue
        
        messages.success(request, f"✅ Se regeneraron {diagramas_regenerados} Diagrama(s) de Secuencia")
        
    except Exception as e:
        messages.error(request, f"❌ Error al regenerar: {str(e)}")
    
    return redirect('ver_diagramas_secuencia', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]

# ===================== IA GENERACIÓN AUTOMÁTICA ARTEFACTOS Y SUBARTEFACTOS =====================

@login_required
def generar_artefacto(request, proyecto_id, subartefacto_nombre):
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    subartefacto = get_object_or_404(SubArtefacto, fase__proyecto=proyecto, nombre=subartefacto_nombre)

    if subartefacto.nombre not in ARTEFACTOS_VALIDOS:
        return JsonResponse({"error": "Tipo de artefacto inválido."}, status=400)
    
    # CASO ESPECIAL: Generar Historia de Usuario
    if subartefacto.nombre == "Historia de Usuario":
        # Primero verificar si ya existe
        hu_existente = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__iexact="Historia de Usuario"
        ).first()
        
        if hu_existente:
            # Si ya existe, solo redirigir a verla
            messages.info(request, "ℹ️ La Historia de Usuario ya existe.")
            return redirect('ver_historias_usuario', artefacto_id=hu_existente.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Si no existe, generarla
        try:
            contenido = generar_subartefacto_con_prompt(
                tipo="Historia de Usuario",
                nombre_proyecto=proyecto.nombre,
                descripcion=proyecto.descripcion
            )
            
            # Extraer requisitos automáticamente
            requisitos = ""
            try:
                requisitos = extraer_requisitos(contenido)
            except Exception as e:
                requisitos = "[ERROR AL EXTRAER REQUISITOS]"

            # Crear el artefacto
            artefacto = Artefacto.objects.create(
                proyecto=proyecto,
                titulo="Historia de Usuario",
                fase=subartefacto.fase,
                subartefacto=subartefacto,
                contenido=contenido,
                contexto=requisitos,
                generado_por_ia=True
            )

            messages.success(request, "✅ Historia de Usuario generada correctamente.")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]

        except Exception as e:
            import traceback
            messages.error(request, f"❌ Error al generar Historia de Usuario: {str(e)}")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]

    # PARA OTROS ARTEFACTOS: Buscar Historia de Usuario primero
    artefactos = Artefacto.objects.filter(proyecto=proyecto)
    hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
    
    # Si no la encuentra con iexact, intenta buscar por contains
    if not hu:
        hu = artefactos.filter(titulo__icontains="Historia").first()
    
    hu_con_contenido = hu and hu.contenido and hu.contenido.strip() != ""

    # Validar si es Requisitos: necesita Historia de Usuario
    if subartefacto.nombre == "Requisitos":
        if not hu_con_contenido:
            print(f"[DEBUG] No se encontró HU. Artefactos en DB: {list(artefactos.values_list('titulo', flat=True))}")
            messages.warning(request, "⚠️ Primero debes generar la Historia de Usuario antes de crear los Requisitos.")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]

    # Validar si es un diagrama: necesita Historia de Usuario
    if subartefacto.nombre not in ARTEFACTOS_TEXTO and not hu_con_contenido:
        messages.warning(request, "⚠️ Primero debes generar la Historia de Usuario antes de crear este tipo de artefacto.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]

    # ⚠️ ESPECIAL: Para "Diagrama de flujo" - solo generar si no existen
    if subartefacto.nombre == "Diagrama de flujo":
        # Verificar si ya existen diagramas de flujo para este proyecto
        diagramas_existentes = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de flujo"
        ).exists()
        
        if diagramas_existentes:
            # Si ya existen, simplemente ir a verlos (NO regenerar)
            messages.info(request, "ℹ️ Los Diagramas de Flujo ya fueron generados.")
            return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # MODO GENERACIÓN: Crear los diagramas por primera vez
        assert hu is not None, "Historia de Usuario no encontrada"
        
        # Buscar requisitos (puede ser el general "Requisitos" o los por HU "Requisitos - HU#")
        requisitos_art = artefactos.filter(
            titulo__in=["Requisitos"]
        ).first()
        
        if not requisitos_art:
            # Si no está el general, buscar cualquiera de los por HU
            requisitos_art = artefactos.filter(
                titulo__startswith="Requisitos -"
            ).first()
        
        if not requisitos_art or not requisitos_art.contenido:
            messages.error(request, "❌ No se encontraron Requisitos para generar diagramas de flujo")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Extraer todas las HU del contenido de Requisitos
        hu_list = extraer_historias_de_usuario(requisitos_art.contenido)
        
        if not hu_list:
            messages.error(request, "❌ No se encontraron Historias de Usuario en los Requisitos")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # Si llegó aquí, significa que ES la primera generación y continuará con el código de abajo
        # (la generación se hace en el bloque elif más abajo)
    
    # Verificar si ya existe el artefacto (excepto Diagrama de flujo que ya fue manejado)
    if subartefacto.nombre != "Diagrama de flujo":
        artefacto_existente = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo=subartefacto.nombre
        ).first()
        if artefacto_existente:
            if subartefacto.nombre == "Historia de Usuario":
                return redirect('ver_historias_usuario', artefacto_id=artefacto_existente.id)  # pyright: ignore[reportAttributeAccessIssue]
            else:
                return redirect('ver_artefacto', artefacto_id=artefacto_existente.id)  # pyright: ignore[reportAttributeAccessIssue]

    try:
        rf_list = []  # Inicializar lista de RF
        
        if subartefacto.nombre == "Requisitos":
            # Para Requisitos: usa el contenido de la Historia de Usuario
            assert hu is not None, "Historia de Usuario no encontrada"
            
            # PRIMERO: Generar el contenido general de Requisitos
            contenido_general = generar_subartefacto_con_prompt(
                tipo="Requisitos",
                texto=hu.contenido
            )
            
            # 🔑 NUEVO: Crear UN ARTEFACTO DE REQUISITOS POR CADA HU
            # Extraer todas las HU de los Requisitos generados
            hu_list = extraer_historias_de_usuario(contenido_general)
            
            requisitos_creados = 0
            
            if hu_list:
                # Crear requisitos filtrados por HU
                for hu_name in hu_list:
                    try:
                        # Extraer solo los RF de esta HU
                        hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
                        requisitos_especificos = []
                        
                        for line in contenido_general.split('\n'):
                            if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                                requisitos_especificos.append(line.strip())
                        
                        if requisitos_especificos:
                            requisitos_texto = "\n".join(requisitos_especificos)
                            rf_list = [rf.split()[0] for rf in requisitos_especificos if rf.split()]
                            
                            # Crear artefacto de Requisitos para esta HU específica
                            Artefacto.objects.create(
                                proyecto=proyecto,
                                fase=subartefacto.fase,
                                subartefacto=subartefacto,
                                titulo=f"Requisitos - {hu_name}",
                                contenido=contenido_general,  # Guardar el contenido general
                                requisitos_relacionados=rf_list,
                                historia_usuario_relacionada=hu_name,
                                generado_por_ia=True
                            )
                            
                            requisitos_creados += 1
                    except Exception as e:
                        print(f"[ERROR] Creando requisitos para {hu_name}: {str(e)}")
                        continue
                
                if requisitos_creados > 0:
                    messages.success(request, f"✅ Se generaron {requisitos_creados} Requisitos (uno por cada Historia de Usuario)")
                    return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
            
            # Si no se pudieron crear separados, crear uno general (fallback)
            contenido = contenido_general
            rf_list = []
        elif subartefacto.nombre in ARTEFACTOS_TEXTO:
            # Para otros textos: caja negra
            contenido = generar_subartefacto_con_prompt(
                tipo=subartefacto.nombre,
                nombre_proyecto=proyecto.nombre,
                descripcion=proyecto.descripcion
            )
        elif subartefacto.nombre == "Diagrama de flujo":
            # ✨ ESPECIAL: Generar UN DIAGRAMA POR CADA HISTORIA DE USUARIO
            # Primero verificar si ya existen
            diagramas_flujo_existentes = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__startswith="Diagrama de flujo"
            ).exists()
            
            if diagramas_flujo_existentes:
                # Si ya existen, solo redirigir a verlos
                messages.info(request, "ℹ️ Los Diagramas de Flujo ya existen.")
                return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
            
            assert hu is not None, "Historia de Usuario no encontrada"
            
            # Buscar requisitos (puede ser el general "Requisitos" o los por HU "Requisitos - HU#")
            requisitos_art = artefactos.filter(
                titulo__in=["Requisitos"]
            ).first()
            
            if not requisitos_art:
                # Si no está el general, buscar cualquiera de los por HU
                requisitos_art = artefactos.filter(
                    titulo__startswith="Requisitos -"
                ).first()
            
            if not requisitos_art or not requisitos_art.contenido:
                raise ValueError("No se encontraron Requisitos para generar diagramas de flujo")
            
            # 🔑 IMPORTANTE: Extraer HU DIRECTAMENTE de los Requisitos, no de la Historia de Usuario
            # Porque los Requisitos pueden tener HU que no están en la Historia de Usuario
            hu_list = extraer_historias_de_usuario(requisitos_art.contenido)
            
            if not hu_list:
                raise ValueError("No se encontraron Historias de Usuario en los Requisitos")
            
            diagramas_creados = 0
            
            # Crear UN DIAGRAMA por cada HU con TODOS sus RF
            for hu_name in hu_list:
                try:
                    # Buscar la HU en el contenido de Historia de Usuario
                    hu_pattern = f"{hu_name}:"
                    
                    # Extraer contenido de esa HU específica
                    if hu_pattern in hu.contenido:
                        hu_inicio = hu.contenido.find(hu_pattern)
                        hu_siguiente = hu.contenido.find("\nHU", hu_inicio + 1)
                        if hu_siguiente == -1:
                            hu_contenido_especifico = hu.contenido[hu_inicio:]
                        else:
                            hu_contenido_especifico = hu.contenido[hu_inicio:hu_siguiente]
                    else:
                        # Si no está en HU, usar solo el nombre de la HU
                        hu_contenido_especifico = hu_name
                    
                    # 🔑 IMPORTANTE: Extraer TODOS los RF asociados a esta HU específica
                    # Buscar con múltiples formatos: HU1, HU01, HU001, etc.
                    requisitos_especificos = []
                    
                    # Extraer número de HU (ej: HU1 -> 1, HU02 -> 2)
                    hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
                    
                    for line in requisitos_art.contenido.split('\n'):
                        # Buscar múltiples formatos: [HU1], [HU01], [HU001], etc.
                        if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                            requisitos_especificos.append(line.strip())
                    
                    if not requisitos_especificos:
                        print(f"[DEBUG] No se encontraron RF para {hu_name}")
                        print(f"[DEBUG] Buscando patrones: [{hu_name}], [HU0{hu_numero}], [HU{hu_numero}]")
                        print(f"[DEBUG] Primeras 500 caracteres de requisitos: {requisitos_art.contenido[:500]}")
                        continue
                    
                    # Construir texto con TODOS los requisitos
                    requisitos_texto = "\n".join(requisitos_especificos)
                    
                    print(f"[DEBUG] Generando diagrama para {hu_name} con {len(requisitos_especificos)} RF")
                    
                    # Generar UN DIAGRAMA que muestre el flujo de esta HU con sus RF
                    contenido_diagrama = generar_subartefacto_con_prompt(
                        tipo="Diagrama de flujo",
                        historia_usuario=hu_contenido_especifico,
                        requisitos=requisitos_texto
                    )
                    
                    contenido_diagrama = limpiar_mermaid(contenido_diagrama)
                    
                    # Extraer RF para guardar en relación
                    rf_list = [rf.split()[0] for rf in requisitos_especificos if rf.split()]
                    
                    # Crear UN artefacto por HU
                    Artefacto.objects.create(
                        proyecto=proyecto,
                        fase=subartefacto.fase,
                        subartefacto=subartefacto,
                        titulo=f"Diagrama de flujo - {hu_name}",
                        contenido=contenido_diagrama,
                        requisitos_relacionados=rf_list,
                        historia_usuario_relacionada=hu_name,
                        generado_por_ia=True
                    )
                    
                    diagramas_creados += 1
                    print(f"[DEBUG] Diagrama para {hu_name} creado exitosamente")
                    
                except Exception as e:
                    import traceback
                    print(f"[ERROR] Generando diagrama para {hu_name}: {str(e)}")
                    print(traceback.format_exc())
                    continue
            
            if diagramas_creados == 0:
                raise ValueError(f"No se pudieron crear diagramas. Se procesaron {len(hu_list)} HU pero ninguna tenía RF asociados")
            
            # Redireccionar a vista de diagramas
            messages.success(request, f"✅ Se generaron {diagramas_creados} Diagrama(s) de Flujo (uno por cada Historia de Usuario)")
            return redirect('ver_diagramas_flujo', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # ✨ ESPECIAL: Generar UN DIAGRAMA DE SECUENCIA POR CADA HISTORIA DE USUARIO
        elif subartefacto.nombre == "Diagrama de secuencia":
            # ✨ ESPECIAL: Generar UN DIAGRAMA POR CADA HISTORIA DE USUARIO
            # Primero verificar si ya existen
            diagramas_secuencia_existentes = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__startswith="Diagrama de secuencia"
            ).exists()
            
            if diagramas_secuencia_existentes:
                # Si ya existen, solo redirigir a verlos
                messages.info(request, "ℹ️ Los Diagramas de Secuencia ya existen.")
                return redirect('ver_diagramas_secuencia', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
            
            assert hu is not None, "Historia de Usuario no encontrada"
            
            # Buscar requisitos (puede ser el general "Requisitos" o los por HU "Requisitos - HU#")
            requisitos_art = artefactos.filter(
                titulo__in=["Requisitos"]
            ).first()
            
            if not requisitos_art:
                # Si no está el general, buscar cualquiera de los por HU
                requisitos_art = artefactos.filter(
                    titulo__startswith="Requisitos -"
                ).first()
            
            if not requisitos_art or not requisitos_art.contenido:
                raise ValueError("No se encontraron Requisitos para generar diagramas de secuencia")
            
            # 🔑 IMPORTANTE: Extraer HU DIRECTAMENTE de los Requisitos
            hu_list = extraer_historias_de_usuario(requisitos_art.contenido)
            
            if not hu_list:
                raise ValueError("No se encontraron Historias de Usuario en los Requisitos")
            
            diagramas_creados = 0
            
            # Crear UN DIAGRAMA DE SECUENCIA por cada HU con TODOS sus RF
            for hu_name in hu_list:
                try:
                    # Buscar la HU en el contenido de Historia de Usuario
                    hu_pattern = f"{hu_name}:"
                    
                    # Extraer contenido de esa HU específica
                    if hu_pattern in hu.contenido:
                        hu_inicio = hu.contenido.find(hu_pattern)
                        hu_siguiente = hu.contenido.find("\nHU", hu_inicio + 1)
                        if hu_siguiente == -1:
                            hu_contenido_especifico = hu.contenido[hu_inicio:]
                        else:
                            hu_contenido_especifico = hu.contenido[hu_inicio:hu_siguiente]
                    else:
                        # Si no está en HU, usar solo el nombre de la HU
                        hu_contenido_especifico = hu_name
                    
                    # 🔑 IMPORTANTE: Extraer TODOS los RF asociados a esta HU específica
                    requisitos_especificos = []
                    
                    # Extraer número de HU (ej: HU1 -> 1, HU02 -> 2)
                    hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
                    
                    for line in requisitos_art.contenido.split('\n'):
                        # Buscar múltiples formatos: [HU1], [HU01], [HU001], etc.
                        if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                            requisitos_especificos.append(line.strip())
                    
                    if not requisitos_especificos:
                        print(f"[DEBUG] No se encontraron RF para {hu_name}")
                        print(f"[DEBUG] Buscando patrones: [{hu_name}], [HU0{hu_numero}], [HU{hu_numero}]")
                        print(f"[DEBUG] Primeras 500 caracteres de requisitos: {requisitos_art.contenido[:500]}")
                        continue
                    
                    # Construir texto con TODOS los requisitos
                    requisitos_texto = "\n".join(requisitos_especificos)
                    
                    print(f"[DEBUG] Generando diagrama de secuencia para {hu_name} con {len(requisitos_especificos)} RF")
                    
                    # Generar UN DIAGRAMA DE SECUENCIA que muestre las interacciones de esta HU con sus RF
                    contenido_diagrama = generar_subartefacto_con_prompt(
                        tipo="Diagrama de secuencia",
                        historia_usuario=hu_contenido_especifico,
                        requisitos=requisitos_texto
                    )
                    
                    contenido_diagrama = limpiar_mermaid(contenido_diagrama)
                    
                    # Extraer RF para guardar en relación
                    rf_list = [rf.split()[0] for rf in requisitos_especificos if rf.split()]
                    
                    # Crear UN artefacto por HU
                    Artefacto.objects.create(
                        proyecto=proyecto,
                        fase=subartefacto.fase,
                        subartefacto=subartefacto,
                        titulo=f"Diagrama de secuencia - {hu_name}",
                        contenido=contenido_diagrama,
                        requisitos_relacionados=rf_list,
                        historia_usuario_relacionada=hu_name,
                        generado_por_ia=True
                    )
                    
                    diagramas_creados += 1
                    print(f"[DEBUG] Diagrama de secuencia para {hu_name} creado exitosamente")
                    
                except Exception as e:
                    import traceback
                    print(f"[ERROR] Generando diagrama de secuencia para {hu_name}: {str(e)}")
                    print(traceback.format_exc())
                    continue
            
            if diagramas_creados == 0:
                raise ValueError(f"No se pudieron crear diagramas de secuencia. Se procesaron {len(hu_list)} HU pero ninguna tenía RF asociados")
            
            # Redireccionar a vista de diagramas de secuencia
            messages.success(request, f"✅ Se generaron {diagramas_creados} Diagrama(s) de Secuencia (uno por cada Historia de Usuario)")
            return redirect('ver_diagramas_secuencia', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        elif subartefacto.nombre == "Diagrama de Entidad-Relacion":
            # ✨ ESPECIAL: UN SOLO DIAGRAMA ER con contexto completo del proyecto
            # Primero verificar si ya existe
            diagrama_er_existente = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo="Diagrama de Entidad-Relacion"
            ).first()
            
            if diagrama_er_existente:
                # Si ya existe, solo redirigir a verlo
                messages.info(request, "ℹ️ El Diagrama de Entidad-Relacion ya existe.")
                return redirect('ver_diagrama_entidad_relacion', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
            
            assert hu is not None, "Historia de Usuario no encontrada"
            
            # Buscar requisitos
            requisitos_art = artefactos.filter(
                titulo__in=["Requisitos"]
            ).first()
            
            if not requisitos_art:
                requisitos_art = artefactos.filter(
                    titulo__startswith="Requisitos -"
                ).first()
            
            # Recopilar todos los diagramas de flujo
            diagramas_flujo = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__startswith="Diagrama de flujo"
            ).order_by('id')
            
            # Recopilar todos los diagramas de secuencia
            diagramas_secuencia = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__startswith="Diagrama de secuencia"
            ).order_by('id')
            
            # Construir contexto completo
            contexto_flujos = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_flujo]) if diagramas_flujo else "No hay diagramas de flujo"
            contexto_secuencias = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_secuencia]) if diagramas_secuencia else "No hay diagramas de secuencia"
            
            # Construir el contexto de requisitos
            requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos"
            
            # Construir el contexto de historias de usuario con diagramas
            historias_completo = f"""
{hu.contenido}

DIAGRAMAS DE FLUJO (Procesos del Sistema):
{contexto_flujos}

DIAGRAMAS DE SECUENCIA (Interacciones del Sistema):
{contexto_secuencias}
"""
            
            # DEBUG: Mostrar qué se está enviando a la IA
            print(f"[DEBUG ER] Generando Diagrama de Entidad-Relacion con contexto:")
            print(f"[DEBUG ER] HU: {len(hu.contenido)} caracteres")
            print(f"[DEBUG ER] Requisitos: {len(requisitos_texto)} caracteres")
            print(f"[DEBUG ER] Diagramas de Flujo: {len(contexto_flujos)} caracteres ({len(list(diagramas_flujo))} diagramas)")
            print(f"[DEBUG ER] Diagramas de Secuencia: {len(contexto_secuencias)} caracteres ({len(list(diagramas_secuencia))} diagramas)")
            print(f"[DEBUG ER] Total: {len(historias_completo) + len(requisitos_texto)} caracteres")
            
            # Generar el diagrama ER con los parámetros correctos
            contenido_diagrama = generar_subartefacto_con_prompt(
                tipo="Diagrama de Entidad-Relacion",
                historias_usuario=historias_completo,
                requisitos=requisitos_texto
            )
            
            contenido_diagrama = limpiar_mermaid(contenido_diagrama)
            
            # Crear UN SOLO artefacto con el diagrama ER
            Artefacto.objects.create(
                proyecto=proyecto,
                fase=subartefacto.fase,
                subartefacto=subartefacto,
                titulo="Diagrama de Entidad-Relacion",
                contenido=contenido_diagrama,
                generado_por_ia=True
            )
            
            messages.success(request, "✅ Diagrama de Entidad-Relacion generado correctamente con contexto completo del proyecto.")
            return redirect('ver_diagrama_entidad_relacion', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        else:
            # ✨ ESPECIAL: Diagramas C4 - GENERAR TODOS LOS 4 JUNTOS
            if subartefacto.nombre in ["Diagrama de Contexto C4", "Diagrama de Contenedor C4", "Diagrama de Componente C4", "Diagrama de Despliegue C4"]:
                # Verificar si ya existen diagramas C4
                diagramas_c4_existentes = Artefacto.objects.filter(
                    proyecto=proyecto,
                    titulo__in=[
                        "Diagrama de Contexto C4",
                        "Diagrama de Contenedor C4",
                        "Diagrama de Componente C4",
                        "Diagrama de Despliegue C4"
                    ]
                ).exists()
                
                if diagramas_c4_existentes:
                    messages.info(request, "ℹ️ Los Diagramas C4 ya han sido generados.")
                    return redirect('ver_diagramas_c4', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
                
                assert hu is not None, "Historia de Usuario no encontrada"
                
                # Generar los 4 diagramas C4
                diagramas_c4_generados = 0
                
                try:
                    # ========== DIAGRAMA 1: CONTEXTO C4 ==========
                    requisitos_art = artefactos.filter(titulo__in=["Requisitos"]).first()
                    if not requisitos_art:
                        requisitos_art = artefactos.filter(titulo__startswith="Requisitos -").first()
                    
                    requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos disponibles"
                    
                    contexto_c4 = f"""HISTORIAS DE USUARIO:
{hu.contenido}

REQUISITOS FUNCIONALES:
{requisitos_texto}"""
                    
                    contenido_contexto = generar_subartefacto_con_prompt(
                        tipo="Diagrama de Contexto C4",
                        texto=contexto_c4
                    )
                    contenido_contexto = limpiar_mermaid(contenido_contexto)
                    
                    # Obtener subartefacto para Contexto C4
                    subartefacto_contexto = SubArtefacto.objects.get(nombre="Diagrama de Contexto C4", fase__proyecto=proyecto)
                    
                    Artefacto.objects.create(
                        proyecto=proyecto,
                        fase=subartefacto_contexto.fase,
                        subartefacto=subartefacto_contexto,
                        titulo="Diagrama de Contexto C4",
                        contenido=contenido_contexto,
                        requisitos_relacionados=[],
                        generado_por_ia=True
                    )
                    diagramas_c4_generados += 1
                    
                    # ========== DIAGRAMA 2: CONTENEDOR C4 ==========
                    diagramas_flujo = Artefacto.objects.filter(
                        proyecto=proyecto,
                        titulo__startswith="Diagrama de flujo"
                    ).order_by('id')
                    
                    contexto_flujos = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_flujo]) if diagramas_flujo else "No hay diagramas de flujo"
                    
                    contenido_contenedor = generar_subartefacto_con_prompt(
                        tipo="Diagrama de Contenedor C4",
                        requisitos=requisitos_texto,
                        diagramas_flujo=contexto_flujos
                    )
                    contenido_contenedor = limpiar_mermaid(contenido_contenedor)
                    
                    subartefacto_contenedor = SubArtefacto.objects.get(nombre="Diagrama de Contenedor C4", fase__proyecto=proyecto)
                    
                    Artefacto.objects.create(
                        proyecto=proyecto,
                        fase=subartefacto_contenedor.fase,
                        subartefacto=subartefacto_contenedor,
                        titulo="Diagrama de Contenedor C4",
                        contenido=contenido_contenedor,
                        requisitos_relacionados=[],
                        generado_por_ia=True
                    )
                    diagramas_c4_generados += 1
                    
                    # ========== DIAGRAMA 3: COMPONENTE C4 ==========
                    diagramas_secuencia = Artefacto.objects.filter(
                        proyecto=proyecto,
                        titulo__startswith="Diagrama de secuencia"
                    ).order_by('id')
                    
                    contexto_secuencias = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_secuencia]) if diagramas_secuencia else "No hay diagramas de secuencia"
                    
                    diagrama_er = Artefacto.objects.filter(
                        proyecto=proyecto,
                        titulo="Diagrama de Entidad-Relacion"
                    ).first()
                    
                    contexto_er = diagrama_er.contenido if diagrama_er else "No hay Diagrama de Entidad-Relacion"
                    
                    contenido_componente = generar_subartefacto_con_prompt(
                        tipo="Diagrama de Componente C4",
                        diagramas_secuencia=contexto_secuencias,
                        diagrama_er=contexto_er
                    )
                    contenido_componente = limpiar_mermaid(contenido_componente)
                    
                    subartefacto_componente = SubArtefacto.objects.get(nombre="Diagrama de Componente C4", fase__proyecto=proyecto)
                    
                    Artefacto.objects.create(
                        proyecto=proyecto,
                        fase=subartefacto_componente.fase,
                        subartefacto=subartefacto_componente,
                        titulo="Diagrama de Componente C4",
                        contenido=contenido_componente,
                        requisitos_relacionados=[],
                        generado_por_ia=True
                    )
                    diagramas_c4_generados += 1
                    
                    # ========== DIAGRAMA 4: DESPLIEGUE C4 ==========
                    contexto_despliegue = f"""HISTORIAS DE USUARIO:
{hu.contenido}

REQUISITOS FUNCIONALES:
{requisitos_texto}

NOTAS: Basado en los requisitos anteriores, diseña la infraestructura de despliegue necesaria."""
                    
                    contenido_despliegue = generar_subartefacto_con_prompt(
                        tipo="Diagrama de Despliegue C4",
                        texto=contexto_despliegue
                    )
                    contenido_despliegue = limpiar_mermaid(contenido_despliegue)
                    
                    subartefacto_despliegue = SubArtefacto.objects.get(nombre="Diagrama de Despliegue C4", fase__proyecto=proyecto)
                    
                    Artefacto.objects.create(
                        proyecto=proyecto,
                        fase=subartefacto_despliegue.fase,
                        subartefacto=subartefacto_despliegue,
                        titulo="Diagrama de Despliegue C4",
                        contenido=contenido_despliegue,
                        requisitos_relacionados=[],
                        generado_por_ia=True
                    )
                    diagramas_c4_generados += 1
                    
                    messages.success(request, f"✅ Se generaron {diagramas_c4_generados} Diagrama(s) C4 correctamente (Contexto, Contenedor, Componente, Despliegue)")
                    return redirect('ver_diagramas_c4', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
                
                except SubArtefacto.DoesNotExist as e:
                    print(f"[ERROR] SubArtefacto no encontrado: {str(e)}")
                    messages.error(request, f"❌ Error: Subartefacto no encontrado")
                    return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
                
                except Exception as e:
                    print(f"[ERROR] Generando diagramas C4: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    messages.error(request, f"❌ Error al generar diagramas C4: {str(e)}")
                    return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
            
            else:
                # Para otros diagramas: usa Historia de Usuario
                assert hu is not None, "Historia de Usuario no encontrada"
                texto_diagrama = hu.contexto if hu.contexto else hu.contenido
                contenido = generar_subartefacto_con_prompt(
                    tipo=subartefacto.nombre,
                    texto=texto_diagrama
                )
            
            contenido = limpiar_mermaid(contenido)

    except Exception as e:
        import traceback
        contenido = f"[ERROR IA] {str(e)}\n{traceback.format_exc()}"
        rf_list = []

    artefacto = Artefacto.objects.create(
        proyecto=proyecto,
        fase=subartefacto.fase,
        subartefacto=subartefacto,
        titulo=subartefacto.nombre,
        contenido=contenido,
        requisitos_relacionados=rf_list,
        generado_por_ia=True
    )

    messages.success(request, f"✅ {subartefacto.nombre} generado correctamente.")
    return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]

@login_required
def generar_subartefacto_modal(request, proyecto_id):
    subartefacto_nombre = request.GET.get("subartefacto", "")
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)

    try:
        if subartefacto_nombre in ARTEFACTOS_TEXTO:
            contenido = generar_subartefacto_con_prompt(
                tipo=subartefacto_nombre,
                nombre_proyecto=proyecto.nombre,
                descripcion=proyecto.descripcion
            )
        else:
            contenido = generar_subartefacto_con_prompt(
                tipo=subartefacto_nombre,
                texto=proyecto.descripcion
            )
            contenido = limpiar_mermaid(contenido)

        tipo = "mermaid" if subartefacto_nombre in ARTEFACTOS_MERMAID else "texto"
    except Exception as e:
        import traceback
        contenido = f"[ERROR IA] {str(e)}\n{traceback.format_exc()}"
        tipo = "error"

    return JsonResponse({
        "tipo": tipo,
        "contenido": contenido,
        "titulo": subartefacto_nombre
    })

# ===================== DESCARGAR_ DIAGRAMA =====================

@login_required
def descargar_diagrama(request, artefacto_id):
    artefacto = get_object_or_404(Artefacto, id=artefacto_id, proyecto__propietario=request.user)
    
    # Aceptar cualquier diagrama que comience con "Diagrama"
    if not artefacto.titulo.startswith("Diagrama"):
        return HttpResponse("Este artefacto no es un diagrama válido para descarga.", status=400)

    filename = f"{artefacto.titulo.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mmd"
    response = HttpResponse(artefacto.contenido, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# ===================== LOGIN =====================

def check_username(request):
    username = request.GET.get('username')
    if not username:
        return JsonResponse({'error': 'Username no proporcionado'}, status=400)
    
    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'available': not exists})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
        else:
            messages.error(request, "⚠️ Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def password_reset_request(request):
    """Vista para solicitar el restablecimiento de contraseña"""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                user = User.objects.get(username=username)
                security_questions = SecurityQuestions.objects.get(user=user)
                request.session['reset_user_id'] = str(user.pk)
                request.session['questions'] = {
                    'pregunta1': dict(SecurityQuestions.PREGUNTAS_CHOICES).get(security_questions.pregunta1),
                    'pregunta2': dict(SecurityQuestions.PREGUNTAS_CHOICES).get(security_questions.pregunta2),
                    'pregunta3': dict(SecurityQuestions.PREGUNTAS_CHOICES).get(security_questions.pregunta3)
                }
                return redirect('password_reset_verify')
            except (User.DoesNotExist, SecurityQuestions.DoesNotExist):
                messages.error(request, "Usuario no encontrado o no tiene preguntas de seguridad configuradas.")
    else:
        form = PasswordResetRequestForm()
    return render(request, 'registration/password_reset_request.html', {'form': form})

def password_reset_verify(request):
    """Vista para verificar respuestas de seguridad"""
    if 'reset_user_id' not in request.session:
        return redirect('password_reset_request')

    try:
        user = User.objects.get(pk=request.session['reset_user_id'])
        security_questions = SecurityQuestions.objects.get(user=user)
        questions = request.session.get('questions', {})

        if request.method == 'POST':
            form = SecurityAnswersForm(request.POST)
            if form.is_valid():
                from .utils import verificar_respuesta
                if (verificar_respuesta(form.cleaned_data['respuesta1'], security_questions.respuesta1) and
                    verificar_respuesta(form.cleaned_data['respuesta2'], security_questions.respuesta2) and
                    verificar_respuesta(form.cleaned_data['respuesta3'], security_questions.respuesta3)):
                    return redirect('password_reset_confirm')
                else:
                    messages.error(request, "Las respuestas no coinciden con las registradas.")
        else:
            form = SecurityAnswersForm()

        return render(request, 'registration/password_reset_verify.html', {
            'form': form,
            'questions': questions
        })
    except (User.DoesNotExist, SecurityQuestions.DoesNotExist, ValueError):
        messages.error(request, "Error al verificar el usuario.")
        return redirect('password_reset_request')

def password_reset_confirm(request):
    """Vista para establecer nueva contraseña"""
    if 'reset_user_id' not in request.session:
        return redirect('password_reset_request')

    try:
        user = User.objects.get(pk=request.session['reset_user_id'])

        if request.method == 'POST':
            form = NewPasswordForm(request.POST)
            if form.is_valid():
                user.set_password(form.cleaned_data['password1'])
                user.save()
                # Limpiar la sesión
                request.session.flush()
                messages.success(request, "Tu contraseña ha sido actualizada correctamente.")
                return redirect('login')
        else:
            form = NewPasswordForm()

        return render(request, 'registration/password_reset_confirm.html', {'form': form})
    except (User.DoesNotExist, ValueError):
        messages.error(request, "Error al verificar el usuario.")
        return redirect('password_reset_request')


# ===================== PRUEBAS DE CAJA NEGRA =====================

@login_required
def generar_pruebas_caja_negra(request, proyecto_id):
    """
    Vista para generar pruebas de caja negra basadas en Historias de Usuario.
    Una prueba por cada HU, que cubre todos sus Requisitos Funcionales asociados.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        # 1. Obtener Historias de Usuario
        hu_art = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__iexact="Historia de Usuario"
        ).first()
        
        if not hu_art or not hu_art.contenido:
            messages.error(request, "❌ No se encontraron Historias de Usuario")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # 2. Obtener Requisitos
        requisitos_art = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__in=["Requisitos"]
        ).first()
        
        if not requisitos_art:
            requisitos_art = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__startswith="Requisitos -"
            ).first()
        
        if not requisitos_art or not requisitos_art.contenido:
            messages.error(request, "❌ No se encontraron Requisitos")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # 3. Obtener Diagrama de Flujo
        diagrama_flujo = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de flujo"
        ).first()
        
        if not diagrama_flujo:
            messages.error(request, "❌ No se encontraron Diagramas de Flujo")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # 4. Extraer lista de HU del contenido de Requisitos
        hu_list = extraer_historias_de_usuario(requisitos_art.contenido)
        
        if not hu_list:
            messages.error(request, "❌ No se encontraron Historias de Usuario en los Requisitos")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        # 5. Eliminar pruebas anteriores si existen
        PruebacajaNegra.objects.filter(proyecto=proyecto).delete()
        
        # 6. Generar una prueba por cada HU
        pruebas_creadas = 0
        
        for hu_num, hu_name in enumerate(hu_list, 1):
            try:
                # Extraer número de HU (ej: HU1 -> 1, HU02 -> 2)
                hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
                
                # Buscar TODOS los RF asociados a esta HU específica
                requisitos_especificos = []
                
                for line in requisitos_art.contenido.split('\n'):
                    # Buscar múltiples formatos: [HU1], [HU01], [HU001], etc.
                    if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                        requisitos_especificos.append(line.strip())
                
                if not requisitos_especificos:
                    print(f"[DEBUG] No se encontraron RF para {hu_name}, saltando...")
                    continue
                
                # Construir texto con TODOS los requisitos de esta HU
                rfs_texto = "\n".join(requisitos_especificos)
                
                # Extraer contenido de esa HU específica de Historia de Usuario
                hu_pattern = f"{hu_name}:"
                hu_descripcion = hu_name  # Default
                if hu_pattern in hu_art.contenido:
                    hu_inicio = hu_art.contenido.find(hu_pattern)
                    # Extraer la primera línea después del nombre (la descripción)
                    hu_linea_inicio = hu_inicio + len(hu_pattern)
                    hu_linea_fin = hu_art.contenido.find("\n", hu_linea_inicio)
                    if hu_linea_fin == -1:
                        hu_descripcion = hu_art.contenido[hu_linea_inicio:].strip()
                    else:
                        hu_descripcion = hu_art.contenido[hu_linea_inicio:hu_linea_fin].strip()
                
                # Para la IA, usar todo el contenido de la HU
                hu_pattern = f"{hu_name}:"
                if hu_pattern in hu_art.contenido:
                    hu_inicio = hu_art.contenido.find(hu_pattern)
                    hu_siguiente = hu_art.contenido.find("\nHU", hu_inicio + 1)
                    if hu_siguiente == -1:
                        hu_contenido_especifico = hu_art.contenido[hu_inicio:]
                    else:
                        hu_contenido_especifico = hu_art.contenido[hu_inicio:hu_siguiente]
                else:
                    hu_contenido_especifico = hu_name
                
                # Generar contenido de la prueba usando IA
                contenido_prueba = generar_subartefacto_con_prompt(
                    tipo="caja_negra",
                    requisito_funcional=rfs_texto,
                    diagrama_flujo=diagrama_flujo.contenido if diagrama_flujo else None,
                    historia_usuario=hu_contenido_especifico
                )
                
                # Parsear el contenido generado
                objetivo = ""
                entrada = ""
                procedimiento = ""
                resultado = ""
                
                lines = contenido_prueba.split('\n')
                current_section = None
                
                for line in lines:
                    line_stripped = line.strip()
                    
                    # Detectar secciones por sus encabezados
                    if line_stripped == 'OBJETIVO:':
                        current_section = 'objetivo'
                    elif line_stripped == 'DATOS DE ENTRADA:':
                        current_section = 'entrada'
                    elif 'PROCEDIMIENTO' in line_stripped or 'PASOS' in line_stripped:
                        current_section = 'procedimiento'
                    elif line_stripped == 'RESULTADO ESPERADO:':
                        current_section = 'resultado'
                    elif current_section and line_stripped:
                        # Agregar contenido a la sección actual
                        if current_section == 'objetivo':
                            objetivo += (line_stripped if not objetivo else " " + line_stripped)
                        elif current_section == 'entrada':
                            entrada += (line_stripped if not entrada else ", " + line_stripped)
                        elif current_section == 'procedimiento':
                            procedimiento += ("\n" + line_stripped if procedimiento else line_stripped)
                        elif current_section == 'resultado':
                            resultado += (line_stripped if not resultado else " " + line_stripped)
                
                # Extraer lista de RFs con sus descripciones para esta HU
                rf_dict = {}
                for rf_line in requisitos_especificos:
                    rf_match = re.search(r'(RF\d+)', rf_line)
                    if rf_match:
                        rf_id = rf_match.group(1)
                        # Extraer descripción (todo después del ":")
                        descripcion_match = re.search(r'RF\d+:\s*(.+)', rf_line)
                        descripcion = descripcion_match.group(1) if descripcion_match else rf_line
                        # Limpiar tags [HU#] de la descripción
                        descripcion = re.sub(r'\s*\[HU\d+\]\s*', '', descripcion)
                        # Limpiar RF# redundante al inicio (ej: "RF1El sistema..." o "RF1 El sistema...")
                        descripcion = re.sub(rf'^{re.escape(rf_id)}\s*', '', descripcion)
                        rf_dict[rf_id] = descripcion.strip()
                
                # Crear la prueba de caja negra (una por HU)
                prueba = PruebacajaNegra.objects.create(
                    proyecto=proyecto,
                    requisito_id=hu_name,  # Identificador es la HU
                    numero_prueba=hu_num,
                    descripcion_requisito=hu_descripcion[:500],  # Descripción de la HU
                    historia_usuario_relacionada=hu_name,
                    objetivo_prueba=objetivo.strip(),
                    datos_entrada=entrada.strip(),
                    procedimiento=procedimiento.strip(),
                    resultado_esperado=resultado.strip(),
                    generado_por_ia=True
                )
                
                # Guardar RFs relacionados como JSON con sus descripciones
                if rf_dict:
                    prueba.requisitos_relacionados = rf_dict
                    prueba.save()
                
                pruebas_creadas += 1
                print(f"[DEBUG] Prueba para {hu_name} creada exitosamente")
                
            except Exception as e:
                print(f"[ERROR] Generando prueba para {hu_name}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue
        
        if pruebas_creadas == 0:
            messages.error(request, "❌ No se pudieron generar pruebas de caja negra")
            return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
        
        messages.success(request, f"✅ Se generaron {pruebas_creadas} Prueba(s) de Caja Negra (una por cada Historia de Usuario)")
        return redirect('ver_pruebas_caja_negra', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    except Exception as e:
        import traceback
        print(f"[ERROR] En generar_pruebas_caja_negra: {str(e)}")
        print(traceback.format_exc())
        messages.error(request, f"❌ Error al generar pruebas: {str(e)}")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def ver_pruebas_caja_negra(request, proyecto_id):
    """
    Vista para ver y editar las pruebas de caja negra generadas.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    pruebas = PruebacajaNegra.objects.filter(proyecto=proyecto).order_by('numero_prueba')
    
    return render(request, 'documentacion/ver_pruebas_caja_negra.html', {
        'proyecto': proyecto,
        'pruebas': pruebas,
        'cantidad_pruebas': pruebas.count()
    })


@login_required
@require_POST
def actualizar_prueba_caja_negra(request, prueba_id):
    """
    AJAX endpoint para actualizar una prueba de caja negra.
    """
    try:
        prueba = get_object_or_404(PruebacajaNegra, id=prueba_id, proyecto__propietario=request.user)
        
        # Actualizar campos
        if 'resultado_obtenido' in request.POST:
            prueba.resultado_obtenido = request.POST.get('resultado_obtenido', '')
        
        if 'estado' in request.POST:
            estado = request.POST.get('estado', '')
            if estado in ['PENDIENTE', 'EN_EJECUCION', 'FINALIZADO']:
                prueba.estado = estado
        
        if 'resultado_final' in request.POST:
            resultado = request.POST.get('resultado_final', '')
            if resultado in ['APTO', 'NO_APTO', 'PENDIENTE']:
                prueba.resultado_final = resultado
        
        if 'observaciones' in request.POST:
            prueba.observaciones = request.POST.get('observaciones', '')
        
        prueba.save()
        
        return JsonResponse({'status': 'success', 'message': 'Prueba actualizada correctamente'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def eliminar_todas_pruebas_caja_negra(request, proyecto_id):
    """
    Vista para eliminar todas las pruebas de caja negra de un proyecto.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        PruebacajaNegra.objects.filter(proyecto=proyecto).delete()
        messages.success(request, "✅ Todas las pruebas de caja negra han sido eliminadas")
    except Exception as e:
        messages.error(request, f"❌ Error al eliminar pruebas: {str(e)}")
    
    return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def regenerar_pruebas_caja_negra(request, proyecto_id):
    """
    Vista para regenerar todas las pruebas de caja negra de un proyecto.
    Elimina las anteriores y genera nuevas.
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    try:
        # Eliminar pruebas anteriores
        PruebacajaNegra.objects.filter(proyecto=proyecto).delete()
        
        # Redirigir a generar nuevas pruebas
        return redirect('generar_pruebas_caja_negra', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    except Exception as e:
        messages.error(request, f"❌ Error al regenerar pruebas: {str(e)}")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def regenerar_prueba_caja_negra_individual(request, prueba_id):
    """
    AJAX endpoint para regenerar una prueba de caja negra individual.
    """
    import json
    try:
        prueba = get_object_or_404(PruebacajaNegra, id=prueba_id, proyecto__propietario=request.user)
        proyecto = prueba.proyecto
        
        # Obtener artefactos necesarios con las búsquedas correctas
        hu_art = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__iexact="Historia de Usuario"
        ).first()
        
        requisitos_art = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__in=["Requisitos"]
        ).first()
        
        if not requisitos_art:
            requisitos_art = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__startswith="Requisitos -"
            ).first()
        
        diagrama_flujo = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__startswith="Diagrama de flujo"
        ).first()
        
        if not all([requisitos_art, hu_art]):
            return JsonResponse({'status': 'error', 'message': 'Artefactos necesarios no encontrados'}, status=400)
        
        hu_name = prueba.requisito_id  # Ej: HU1
        
        # Buscar TODOS los RF asociados a esta HU
        requisitos_especificos = []
        hu_numero = hu_name.replace("HU", "").lstrip("0") or "0"
        
        if requisitos_art and requisitos_art.contenido:  # pyright: ignore[reportOptionalMemberAccess]
            for line in requisitos_art.contenido.split('\n'):
                if line.strip().startswith("RF") and (f"[{hu_name}]" in line or f"[HU0{hu_numero}]" in line or f"[HU{hu_numero}]" in line):
                    requisitos_especificos.append(line.strip())
        
        if not requisitos_especificos:
            return JsonResponse({'status': 'error', 'message': f'No se encontraron RF para {hu_name}'}, status=400)
        
        # Construir texto con requisitos
        rfs_texto = "\n".join(requisitos_especificos)
        
        # Extraer descripción de la HU
        hu_pattern = f"{hu_name}:"
        hu_descripcion = hu_name
        if hu_pattern in hu_art.contenido:  # pyright: ignore[reportOptionalMemberAccess]
            hu_inicio = hu_art.contenido.find(hu_pattern)  # pyright: ignore[reportOptionalMemberAccess]
            hu_linea_inicio = hu_inicio + len(hu_pattern)
            hu_linea_fin = hu_art.contenido.find("\n", hu_linea_inicio)  # pyright: ignore[reportOptionalMemberAccess]
            if hu_linea_fin == -1:
                hu_descripcion = hu_art.contenido[hu_linea_inicio:].strip() # pyright: ignore[reportOptionalMemberAccess]
            else:
                hu_descripcion = hu_art.contenido[hu_linea_inicio:hu_linea_fin].strip()  # pyright: ignore[reportOptionalMemberAccess]
        
        # Para la IA, usar todo el contenido de la HU
        hu_contenido_especifico = hu_name
        if hu_pattern in hu_art.contenido:  # pyright: ignore[reportOptionalMemberAccess]
            hu_inicio = hu_art.contenido.find(hu_pattern) # pyright: ignore[reportOptionalMemberAccess]
            hu_siguiente = hu_art.contenido.find("\nHU", hu_inicio + 1) # pyright: ignore[reportOptionalMemberAccess]
            if hu_siguiente == -1:
                hu_contenido_especifico = hu_art.contenido[hu_inicio:] # pyright: ignore[reportOptionalMemberAccess]
            else:
                hu_contenido_especifico = hu_art.contenido[hu_inicio:hu_siguiente] # pyright: ignore[reportOptionalMemberAccess]
        
        # Generar contenido usando IA
        contenido_prueba = generar_subartefacto_con_prompt(
            tipo="caja_negra",
            requisito_funcional=rfs_texto,
            diagrama_flujo=diagrama_flujo.contenido if diagrama_flujo else None,
            historia_usuario=hu_contenido_especifico
        )
        
        # Parsear contenido (mismo algoritmo que en generar_pruebas_caja_negra)
        objetivo = ""
        entrada = ""
        procedimiento = ""
        resultado = ""
        
        lines = contenido_prueba.split('\n')
        current_section = None
        
        for line in lines:
            line_stripped = line.strip()
            
            if line_stripped == 'OBJETIVO:':
                current_section = 'objetivo'
            elif line_stripped == 'DATOS DE ENTRADA:':
                current_section = 'entrada'
            elif 'PROCEDIMIENTO' in line_stripped or 'PASOS' in line_stripped:
                current_section = 'procedimiento'
            elif line_stripped == 'RESULTADO ESPERADO:':
                current_section = 'resultado'
            elif current_section and line_stripped:
                if current_section == 'objetivo':
                    objetivo += (line_stripped if not objetivo else " " + line_stripped)
                elif current_section == 'entrada':
                    entrada += (line_stripped if not entrada else ", " + line_stripped)
                elif current_section == 'procedimiento':
                    procedimiento += ("\n" + line_stripped if procedimiento else line_stripped)
                elif current_section == 'resultado':
                    resultado += (line_stripped if not resultado else " " + line_stripped)
        
        # Extraer lista de RFs con sus descripciones
        rf_dict = {}
        for rf_line in requisitos_especificos:
            rf_match = re.search(r'(RF\d+)', rf_line)
            if rf_match:
                rf_id = rf_match.group(1)
                descripcion_match = re.search(r'RF\d+:\s*(.+)', rf_line)
                descripcion = descripcion_match.group(1) if descripcion_match else rf_line
                descripcion = re.sub(r'\s*\[HU\d+\]\s*', '', descripcion)
                descripcion = re.sub(rf'^{re.escape(rf_id)}\s*', '', descripcion)
                rf_dict[rf_id] = descripcion.strip()
        
        # Actualizar prueba existente
        prueba.descripcion_requisito = hu_descripcion[:500]
        prueba.objetivo_prueba = objetivo.strip()
        prueba.datos_entrada = entrada.strip()
        prueba.procedimiento = procedimiento.strip()
        prueba.resultado_esperado = resultado.strip()
        prueba.generado_por_ia = True
        
        if rf_dict:
            prueba.requisitos_relacionados = rf_dict
        
        prueba.save()
        
        return JsonResponse({
            'status': 'success',
            'message': '✅ Prueba regenerada correctamente',
            'prueba_id': prueba.id  # pyright: ignore[reportAttributeAccessIssue]
        })
    
    except Exception as e:
        print(f"[ERROR] Regenerando prueba {prueba_id}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=400)


# ===================== VER DIAGRAMAS C4 =====================

@login_required
def ver_diagramas_c4(request, proyecto_id):
    """
    Vista que muestra TODOS los diagramas C4 (4 niveles) en una sola página.
    Nivel 1: Contexto
    Nivel 2: Contenedor
    Nivel 3: Componente
    Nivel 4: Despliegue
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    # Buscar cada diagrama C4 por su nombre exacto
    diagrama_contexto = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo="Diagrama de Contexto C4"
    ).first()
    
    diagrama_contenedor = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo="Diagrama de Contenedor C4"
    ).first()
    
    diagrama_componente = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo="Diagrama de Componente C4"
    ).first()
    
    diagrama_despliegue = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo="Diagrama de Despliegue C4"
    ).first()
    
    # Contar cuántos se han generado
    diagramas_generados = sum([
        1 if diagrama_contexto else 0,
        1 if diagrama_contenedor else 0,
        1 if diagrama_componente else 0,
        1 if diagrama_despliegue else 0
    ])
    
    if diagramas_generados == 0:
        messages.warning(request, "⚠️ No se han generado Diagramas C4 aún.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    context = {
        'proyecto': proyecto,
        'diagrama_contexto': diagrama_contexto,
        'diagrama_contenedor': diagrama_contenedor,
        'diagrama_componente': diagrama_componente,
        'diagrama_despliegue': diagrama_despliegue,
        'diagramas_count': diagramas_generados
    }
    
    return render(request, 'documentacion/ver_diagramas_c4.html', context)


@login_required
def regenerar_diagramas_c4(request, proyecto_id):
    """
    Regenera TODOS los diagramas C4 (4 niveles).
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    # Buscar todos los diagramas C4 existentes
    diagramas_c4 = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__in=[
            "Diagrama de Contexto C4",
            "Diagrama de Contenedor C4",
            "Diagrama de Componente C4",
            "Diagrama de Despliegue C4"
        ]
    )
    
    if not diagramas_c4.exists():
        messages.warning(request, "⚠️ No hay diagramas C4 para regenerar.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    try:
        regenerados = 0
        for diagrama in diagramas_c4:
            # Obtener el subartefacto correspondiente
            subartefacto = diagrama.subartefacto
            hu = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__iexact="Historia de Usuario"
            ).first()
            
            artefactos = Artefacto.objects.filter(proyecto=proyecto)
            
            # Regenerar según el tipo
            if diagrama.titulo == "Diagrama de Contexto C4":
                requisitos_art = artefactos.filter(titulo__in=["Requisitos"]).first()
                if not requisitos_art:
                    requisitos_art = artefactos.filter(titulo__startswith="Requisitos -").first()
                
                requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos"
                contexto_c4 = f"""HISTORIAS DE USUARIO:
{hu.contenido if hu else 'No disponible'}

REQUISITOS FUNCIONALES:
{requisitos_texto}"""
                
                contenido = generar_subartefacto_con_prompt(
                    tipo=diagrama.titulo,
                    texto=contexto_c4
                )
            
            elif diagrama.titulo == "Diagrama de Contenedor C4":
                requisitos_art = artefactos.filter(titulo__in=["Requisitos"]).first()
                if not requisitos_art:
                    requisitos_art = artefactos.filter(titulo__startswith="Requisitos -").first()
                
                requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos"
                diagramas_flujo = Artefacto.objects.filter(
                    proyecto=proyecto,
                    titulo__startswith="Diagrama de flujo"
                ).order_by('id')
                
                contexto_flujos = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_flujo]) if diagramas_flujo else "No hay diagramas"
                
                contenido = generar_subartefacto_con_prompt(
                    tipo=diagrama.titulo,
                    requisitos=requisitos_texto,
                    diagramas_flujo=contexto_flujos
                )
            
            elif diagrama.titulo == "Diagrama de Componente C4":
                diagramas_secuencia = Artefacto.objects.filter(
                    proyecto=proyecto,
                    titulo__startswith="Diagrama de secuencia"
                ).order_by('id')
                
                contexto_secuencias = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_secuencia]) if diagramas_secuencia else "No hay diagramas"
                
                diagrama_er = Artefacto.objects.filter(
                    proyecto=proyecto,
                    titulo="Diagrama de Entidad-Relacion"
                ).first()
                
                contexto_er = diagrama_er.contenido if diagrama_er else "No disponible"
                
                contenido = generar_subartefacto_con_prompt(
                    tipo=diagrama.titulo,
                    diagramas_secuencia=contexto_secuencias,
                    diagrama_er=contexto_er
                )
            
            elif diagrama.titulo == "Diagrama de Despliegue C4":
                requisitos_art = artefactos.filter(titulo__in=["Requisitos"]).first()
                if not requisitos_art:
                    requisitos_art = artefactos.filter(titulo__startswith="Requisitos -").first()
                
                requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos"
                
                contexto_c4 = f"""HISTORIAS DE USUARIO:
{hu.contenido if hu else 'No disponible'}

REQUISITOS FUNCIONALES:
{requisitos_texto}

NOTAS: Basado en los requisitos anteriores, diseña la infraestructura de despliegue necesaria."""
                
                contenido = generar_subartefacto_con_prompt(
                    tipo=diagrama.titulo,
                    texto=contexto_c4
                )
            
            contenido = limpiar_mermaid(contenido)
            diagrama.contenido = contenido
            diagrama.save()
            regenerados += 1
        
        messages.success(request, f"✅ Se regeneraron {regenerados} Diagrama(s) C4 correctamente")
        return redirect('ver_diagramas_c4', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    except Exception as e:
        print(f"[ERROR] Regenerando diagramas C4: {str(e)}")
        import traceback
        print(traceback.format_exc())
        messages.error(request, f"❌ Error al regenerar: {str(e)}")
        return redirect('ver_diagramas_c4', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def eliminar_todos_diagramas_c4(request, proyecto_id):
    """
    Elimina TODOS los diagramas C4 (4 niveles).
    """
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    
    # Buscar todos los diagramas C4 existentes
    diagramas_c4 = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo__in=[
            "Diagrama de Contexto C4",
            "Diagrama de Contenedor C4",
            "Diagrama de Componente C4",
            "Diagrama de Despliegue C4"
        ]
    )
    
    cantidad = diagramas_c4.count()
    
    if cantidad == 0:
        messages.warning(request, "⚠️ No hay diagramas C4 para eliminar.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    try:
        diagramas_c4.delete()
        messages.success(request, f"✅ Se eliminaron {cantidad} Diagrama(s) C4 correctamente")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    except Exception as e:
        print(f"[ERROR] Eliminando diagramas C4: {str(e)}")
        messages.error(request, f"❌ Error al eliminar: {str(e)}")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]


@login_required
def regenerar_diagrama_c4_individual(request, artefacto_id):
    """
    Regenera un diagrama C4 individual (Contexto, Contenedor, Componente o Despliegue).
    """
    diagrama = get_object_or_404(Artefacto, id=artefacto_id)
    proyecto = diagrama.proyecto
    
    # Verificar permisos
    if proyecto.propietario != request.user:  # pyright: ignore[reportAttributeAccessIssue]
        return HttpResponse("Acceso denegado", status=403)
    
    try:
        artefactos = Artefacto.objects.filter(proyecto=proyecto)
        hu = Artefacto.objects.filter(
            proyecto=proyecto,
            titulo__iexact="Historia de Usuario"
        ).first()
        
        # Regenerar según el tipo de diagrama C4
        if diagrama.titulo == "Diagrama de Contexto C4":
            requisitos_art = artefactos.filter(titulo__in=["Requisitos"]).first()
            if not requisitos_art:
                requisitos_art = artefactos.filter(titulo__startswith="Requisitos -").first()
            
            requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos"
            contexto_c4 = f"""HISTORIAS DE USUARIO:
{hu.contenido if hu else 'No disponible'}

REQUISITOS FUNCIONALES:
{requisitos_texto}"""
            
            contenido = generar_subartefacto_con_prompt(
                tipo=diagrama.titulo,
                texto=contexto_c4
            )
        
        elif diagrama.titulo == "Diagrama de Contenedor C4":
            requisitos_art = artefactos.filter(titulo__in=["Requisitos"]).first()
            if not requisitos_art:
                requisitos_art = artefactos.filter(titulo__startswith="Requisitos -").first()
            
            requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos"
            diagramas_flujo = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__startswith="Diagrama de flujo"
            ).order_by('id')
            
            contexto_flujos = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_flujo]) if diagramas_flujo else "No hay diagramas"
            
            contenido = generar_subartefacto_con_prompt(
                tipo=diagrama.titulo,
                requisitos=requisitos_texto,
                diagramas_flujo=contexto_flujos
            )
        
        elif diagrama.titulo == "Diagrama de Componente C4":
            diagramas_secuencia = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo__startswith="Diagrama de secuencia"
            ).order_by('id')
            
            contexto_secuencias = "\n---\n".join([f"## {d.titulo}\n{d.contenido}" for d in diagramas_secuencia]) if diagramas_secuencia else "No hay diagramas"
            
            diagrama_er = Artefacto.objects.filter(
                proyecto=proyecto,
                titulo="Diagrama de Entidad-Relacion"
            ).first()
            
            contexto_er = diagrama_er.contenido if diagrama_er else "No disponible"
            
            contenido = generar_subartefacto_con_prompt(
                tipo=diagrama.titulo,
                diagramas_secuencia=contexto_secuencias,
                diagrama_er=contexto_er
            )
        
        elif diagrama.titulo == "Diagrama de Despliegue C4":
            requisitos_art = artefactos.filter(titulo__in=["Requisitos"]).first()
            if not requisitos_art:
                requisitos_art = artefactos.filter(titulo__startswith="Requisitos -").first()
            
            requisitos_texto = requisitos_art.contenido if requisitos_art else "No hay requisitos"
            
            contexto_c4 = f"""HISTORIAS DE USUARIO:
{hu.contenido if hu else 'No disponible'}

REQUISITOS FUNCIONALES:
{requisitos_texto}

NOTAS: Basado en los requisitos anteriores, diseña la infraestructura de despliegue necesaria."""
            
            contenido = generar_subartefacto_con_prompt(
                tipo=diagrama.titulo,
                texto=contexto_c4
            )
        
        else:
            raise ValueError(f"Tipo de diagrama C4 no reconocido: {diagrama.titulo}")
        
        contenido = limpiar_mermaid(contenido)
        diagrama.contenido = contenido
        diagrama.save()
        
        messages.success(request, f"✅ {diagrama.titulo} regenerado correctamente")
        return redirect('ver_diagramas_c4', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
    
    except Exception as e:
        print(f"[ERROR] Regenerando diagrama C4 {artefacto_id}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        messages.error(request, f"❌ Error al regenerar: {str(e)}")
        return redirect('ver_diagramas_c4', proyecto_id=proyecto.id)  # pyright: ignore[reportAttributeAccessIssue]
