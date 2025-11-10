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
from .models import Project, Artefacto, Fase, SubArtefacto, SecurityQuestions
from .forms import (ProjectForm, ArtefactoForm, CustomUserCreationForm, SecurityQuestionsForm,
                   PasswordResetRequestForm, SecurityAnswersForm, NewPasswordForm)
from core.ia import generar_subartefacto_con_prompt, extraer_requisitos, _generar_contenido, PROMPTS
import datetime

# ===== TIPOS DE ARTEFACTOS DEFINIDOS DIRECTAMENTE =====

ARTEFACTOS_TEXTO = [
    "Historia de Usuario",
    "Requisitos",
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
                "Análisis": ["Historia de Usuario", "Requisitos"],
                "Diseño": ["Diagrama de flujo", "Diagrama de secuencia", "Diagrama de clases", "Diagrama de Entidad-Relacion"],
                "Pruebas": ["caja negra", "smoke"],
                "Despliegue": ["Diagrama de C4-contexto", "Diagrama de C4-contenedor", "Diagrama de C4-implementación"]
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
        "Diseño": ["Diagrama de flujo", "Diagrama de secuencia", "Diagrama de clases", "Diagrama de Entidad-Relacion"],
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
    
    # Verificar si ya se generaron los requisitos
    requisitos_generados = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo="Requisitos"
    ).exists()
    
    return render(request, 'documentacion/detalle_proyecto.html', {
        'proyecto': proyecto,
        'fases': fases,
        'artefactos': artefactos,
        'caso_uso_con_requisitos': hu_con_requisitos,
        'requisitos_generados': requisitos_generados
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
    
    # Para mostrar Requisitos, necesitamos la Historia de Usuario
    hu = None
    if artefacto.titulo == "Requisitos" or artefacto.titulo.lower() == "requisitos":
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
    })

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
            return redirect('ver_artefacto', artefacto_id=hu_existente.id)  # pyright: ignore[reportAttributeAccessIssue]
        
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
            return redirect('ver_artefacto', artefacto_id=artefacto.id)  # pyright: ignore[reportAttributeAccessIssue]

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

    # Verificar si ya existe el artefacto
    artefacto_existente = Artefacto.objects.filter(
        proyecto=proyecto,
        titulo=subartefacto.nombre
    ).first()
    if artefacto_existente:
        return redirect('ver_artefacto', artefacto_id=artefacto_existente.id)  # pyright: ignore[reportAttributeAccessIssue]

    try:
        if subartefacto.nombre == "Requisitos":
            # Para Requisitos: usa el contenido de la Historia de Usuario
            assert hu is not None, "Historia de Usuario no encontrada"
            contenido = generar_subartefacto_con_prompt(
                tipo="Requisitos",
                texto=hu.contenido
            )
        elif subartefacto.nombre in ARTEFACTOS_TEXTO:
            # Para otros textos: caja negra, smoke
            contenido = generar_subartefacto_con_prompt(
                tipo=subartefacto.nombre,
                nombre_proyecto=proyecto.nombre,
                descripcion=proyecto.descripcion
            )
        else:
            # Para diagramas: usa Historia de Usuario
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

    artefacto = Artefacto.objects.create(
        proyecto=proyecto,
        fase=subartefacto.fase,
        subartefacto=subartefacto,
        titulo=subartefacto.nombre,
        contenido=contenido,
        generado_por_ia=True
    )

    messages.success(request, f"✅ {subartefacto.nombre} generado correctamente.")
    return redirect('ver_artefacto', artefacto_id=artefacto.id)  # pyright: ignore[reportAttributeAccessIssue]

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
