from django.shortcuts import render, redirect, get_object_or_404 # pyright: ignore[reportMissingModuleSource]
from django.contrib.auth.decorators import login_required # pyright: ignore[reportMissingModuleSource]
from django.contrib.auth import authenticate,login, logout # pyright: ignore[reportMissingModuleSource]
from django.views.decorators.http import require_POST # pyright: ignore[reportMissingModuleSource]
from django.http import JsonResponse, HttpResponse # pyright: ignore[reportMissingModuleSource]
from django.contrib.auth.forms import AuthenticationForm # pyright: ignore[reportMissingModuleSource]
from django.contrib import messages # pyright: ignore[reportMissingModuleSource]
from .models import Project, Artefacto, Fase, SubArtefacto
from .forms import ProjectForm, ArtefactoForm, CustomUserCreationForm
from core.ia import generar_subartefacto_con_prompt, extraer_requisitos, _generar_contenido, PROMPTS
import datetime

# ===== TIPOS DE ARTEFACTOS DEFINIDOS DIRECTAMENTE =====

ARTEFACTOS_TEXTO = [
    "Historia de Usuario",
    "caja negra",
    "smoke"
]

ARTEFACTOS_MERMAID = [
    "Diagrama de flujo",
    "Diagrama de clases",
    "Diagrama de Entidad-Relacion",
    "Diagrama de secuencia",
    "Diagrama de estado",
    "Diagrama de C4-contexto",
    "Diagrama de C4-contenedor",
    "Diagrama de C4-implementación"
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
                "Análisis Requisitos": ["Historia de Usuario", "Diagrama de flujo"],
                "Diseño": ["Diagrama de clases", "Diagrama de Entidad-Relacion"],
                "Desarrollo": ["Diagrama de secuencia", "Diagrama de estado"],
                "Pruebas": ["caja negra", "smoke"],
                "Despliegue": ["Diagrama de C4-contexto", "Diagrama de C4-contenedor","Diagrama de C4-implementación" ] #se creo 3 botones C4
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
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()

            # Autenticar con username y password1 para obtener el backend
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1']
            )
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "No se pudo iniciar sesión automáticamente. Intenta iniciar sesión manualmente.")
                return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})

def cerrar_sesion(request):
    logout(request)
    return redirect('home')

# ===================== DETALLE PROYECTO =====================

@login_required
def detalle_proyecto(request, proyecto_id):
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    orden_deseado = [
        "Análisis Requisitos",
        "Diseño",
        "Desarrollo",
        "Pruebas",
        "Despliegue"
    ]
    
    # Obtener las fases usando el manager de Fase directamente
    fases_queryset = Fase.objects.filter(proyecto=proyecto).select_related('proyecto').prefetch_related('subartefactos')
    fases = sorted(fases_queryset, key=lambda f: orden_deseado.index(f.nombre) if f.nombre in orden_deseado else 999)

    orden_subartefactos = {
        "Análisis Requisitos": ["Historia de Usuario", "Diagrama de flujo"],
        "Diseño": ["Diagrama de clases", "Diagrama de Entidad-Relacion"],
        "Desarrollo": ["Diagrama de secuencia", "Diagrama de estado"],
        "Pruebas": ["caja negra", "smoke"],
        "Despliegue": ["Diagrama de C4-contexto", "Diagrama de C4-contenedor", "Diagrama de C4-implementación"]
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
    
    return render(request, 'documentacion/detalle_proyecto.html', {
        'proyecto': proyecto,
        'fases': fases,
        'artefactos': artefactos,
        'hu_con_requisitos': hu_con_requisitos
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
    })

# ===================== IA GENERACIÓN AUTOMÁTICA ARTEFACTOS Y SUBARTEFACTOS =====================

@login_required
def generar_artefacto(request, proyecto_id, subartefacto_nombre):
    proyecto = get_object_or_404(Project, id=proyecto_id, propietario=request.user)
    subartefacto = get_object_or_404(SubArtefacto, fase__proyecto=proyecto, nombre=subartefacto_nombre)

    if subartefacto.nombre not in ARTEFACTOS_VALIDOS:
        return JsonResponse({"error": "Tipo de artefacto inválido."}, status=400)
    
    artefactos = Artefacto.objects.filter(proyecto=proyecto)
    hu = artefactos.filter(titulo__iexact="Historia de Usuario").first()
    hu_con_requisitos = hu and hu.contexto and hu.contexto.strip() != ""

    if subartefacto.nombre not in ARTEFACTOS_TEXTO and not hu_con_requisitos:
        messages.warning(request, "⚠️ Primero debes generar la Historia de Usuario con requisitos antes de crear este tipo de artefacto.")
        return redirect('detalle_proyecto', proyecto_id=proyecto.id) # pyright: ignore[reportAttributeAccessIssue]

    artefacto_existente = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo=subartefacto.nombre
    ).first()
    if artefacto_existente:
        return redirect('ver_artefacto', artefacto_id=artefacto_existente.id) # pyright: ignore[reportAttributeAccessIssue]

    try:
        if subartefacto.nombre in ARTEFACTOS_TEXTO:
            contenido = generar_subartefacto_con_prompt(
                tipo=subartefacto.nombre,
                nombre_proyecto=proyecto.nombre,
                descripcion=proyecto.descripcion
            )
        
        else:
            
            contenido = generar_subartefacto_con_prompt(
                tipo=subartefacto.nombre,
                texto=proyecto.descripcion
            )
            contenido = limpiar_mermaid(contenido)

    except Exception as e:
        import traceback
        contenido = f"[ERROR IA] {str(e)}\n{traceback.format_exc()}"

    artefacto = Artefacto.objects.create(
        proyecto=proyecto,
        fase=subartefacto.fase,
        subartefacto=subartefacto,
        titulo=subartefacto.nombre,
        contenido=contenido,
        generado_por_ia=True
    )

    if artefacto.titulo.lower() == "historia de usuario":
            contenido = generar_subartefacto_con_prompt(
                tipo="Historia de Usuario",
                nombre_proyecto=proyecto.nombre,
                descripcion=proyecto.descripcion
            )

            artefacto.contenido = contenido
            artefacto.generado_por_ia = True

            try:
                requisitos = extraer_requisitos(contenido)
                artefacto.contexto = requisitos
            except Exception as e:
                artefacto.contexto = "[ERROR AL EXTRAER REQUISITOS]"

            artefacto.save()
            messages.success(request, "Historia de Usuario generada con requisitos.")
            return redirect('ver_artefacto', artefacto.id) # pyright: ignore[reportAttributeAccessIssue]

    return redirect('ver_artefacto', artefacto_id=artefacto.id) # pyright: ignore[reportAttributeAccessIssue]

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
    
    diagramas_validos = [
        "Diagrama de flujo",
        "Diagrama de clases",
        "Diagrama de Entidad-Relacion",
        "Diagrama de secuencia",
        "Diagrama de estado",
        "Diagrama de C4-contexto",
        "Diagrama de C4-contenedor",
        "Diagrama de C4-implementación"
    ]
    if artefacto.titulo not in diagramas_validos:
        return HttpResponse("Este artefacto no es un diagrama válido para descarga.", status=400)

    filename = f"{artefacto.titulo.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mmd"
    response = HttpResponse(artefacto.contenido, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# ===================== LOGIN =====================

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
