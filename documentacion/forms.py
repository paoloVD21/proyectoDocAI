import re
from django import forms
from .models import Project, Artefacto
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

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

# Función para detectar contenido repetitivo o no coherente
def texto_no_coherente(texto: str) -> bool:
    texto = texto.lower().strip()
    if len(set(texto)) <= 3:
        return True
    if re.fullmatch(r'[\W\d_]+', texto):  # Solo símbolos o números
        return True
    if re.fullmatch(r'([a-zA-ZñÑ])\1{3,}', texto):  # Letras repetidas muchas veces
        return True
    if texto in ['...', 'aaa', 'asdf', 'qwerty', '1234','p2.lk.l.', '1.2125gggg..g.g.gy.1',
                 '1234568894..dfae3245',
                 r'[xyz],[^xyz],.,\d,\D,\w,\W,\s,\S,\t,\r,\n,', 
                 r'\v,\f,[\b],\0,,,,,\cX\xhh\uhhhh\u{hhhh}x|y',
                 r'^, $,\b,\B,x(?=y),x(?!y),(?<=y)x, (?<!y)x',
                 r'(x),(?<Name>x),,,(?:x)\n\k<Name>',
                 r'x*, x+,x?,,,x{n}x{n,}x{n,m}']:
        return True
    return False
#============= restricciones para nombre y descripcion del proyecto ==========
def texto_coherente(texto: str) -> bool:
    """
    Valida si un texto es mínimamente coherente:
    - Al menos 3 palabras con más de 2 letras.
    - No contiene repeticiones absurdas.
    - No usa caracteres incoherentes.
    """
    texto = texto.strip()

    if len(texto) < 10:
        return False

    palabras = texto.split()
    palabras_validas = [p for p in palabras if len(p) >= 3 and p.isalpha()]
    if len(palabras_validas) < 3:
        return False

    # Evita repeticiones absurdas tipo "aaa", "1111", etc.
    if re.search(r'(.)\1{3,}', texto.lower()):
        return False

    # Evita símbolos seguidos o solo símbolos
    if re.search(r'[\.\,\{\}\[\]\|\\\/]{3,}', texto):
        return False
    
    return True

# ===== creacion y editar proyecto ============
class ProjectForm(forms.ModelForm):
    """
    Formulario para crear o editar un proyecto.
    """
    nombre = forms.CharField(
        label='Nombre del Proyecto',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el nombre del proyecto'
        })
    )

    descripcion = forms.CharField(
        label='Descripción',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Ingrese una breve descripción del proyecto'
        })
    )

    class Meta:
        model = Project
        fields = ['nombre', 'descripcion']

# ===== validadcion proyecto ============
    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()

        if len(nombre) < 8:
            raise forms.ValidationError("El nombre debe tener al menos 8 caracteres.")
        if not re.match(r'^[A-Za-z0-9ÁÉÍÓÚáéíóúñÑ\s.,()-]+$', nombre):
            raise forms.ValidationError("El nombre contiene caracteres inválidos.")
        if not texto_coherente(nombre):
            raise forms.ValidationError("El nombre debe ser una frase coherente y significativa.")
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()

        if len(descripcion) < 15:
            raise forms.ValidationError("La descripción debe tener al menos 15 caracteres.")
        if not texto_coherente(descripcion):
            raise forms.ValidationError("La descripción debe tener sentido y estar bien redactada.")
        return descripcion

# ===== creacion y editar artefacto ============
class ArtefactoForm(forms.ModelForm):
    """
    Formulario para crear o editar un artefacto.
    """
    tipo = forms.ChoiceField(
        label='Tipo de Artefacto',
        choices=Artefacto.TIPO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )

    titulo = forms.CharField(
        label='Título del Artefacto',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly' 
        })
    )

    contenido = forms.CharField(
        label='Contenido',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Contenido generado o ingresado manualmente'
        })
    )

    class Meta:
        model = Artefacto
        fields = ['titulo', 'tipo', 'contenido']

# ===== validadcion artefacto ============
    def clean_titulo(self):
        titulo = self.cleaned_data['titulo'].strip()
        if not re.match(r'^[A-Za-z0-9ÁÉÍÓÚáéíóúñÑ\s.,()-]{3,100}$', titulo):
            raise ValidationError("El título contiene caracteres no válidos.")
        if texto_no_coherente(titulo):
            raise ValidationError("El título no es coherente o tiene patrones repetitivos.")
        return titulo

    def clean_contenido(self):
        contenido = self.cleaned_data['contenido'].strip()
        if len(contenido) < 10:
            raise ValidationError("El contenido es demasiado corto.")
        titulo = self.cleaned_data.get('titulo', '')
        if titulo not in ARTEFACTOS_MERMAID and texto_no_coherente(contenido):
            raise ValidationError("El contenido no parece tener sentido o está mal estructurado.")
        return contenido

    def clean_tipo(self):
        """
        Asigna automáticamente el tipo de artefacto basado en el título.
        """
        titulo = self.cleaned_data.get('titulo', '').lower()

        if titulo in ("historia de usuario", "requisitos"):
            return 'AREQ'
        elif titulo == "diagrama de flujo":
            return 'DEVS'
        elif titulo in ("caja negra", "smoke"):
            return 'PRUE'
        elif titulo in ("diagrama de clases", "diagrama de entidad-relacion"):
            return 'DISE'
        elif titulo in ("diagrama de secuencia", "diagrama de estado"):
            return 'DEVS'
        elif titulo in ("diagrama de c4-contexto", "diagrama de c4-contenedor", "diagrama de c4-implementación"):
            return 'DESP'
        else:
            raise ValidationError("Título no reconocido para asignar tipo automáticamente.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            self.fields['titulo'].disabled = True
            self.fields['tipo'].disabled = True  

            titulo = self.instance.titulo.lower()
            if titulo in ("historia de usuario", "requisitos"):
                self.initial['tipo'] = 'AREQ'
            elif titulo == "diagrama de flujo":
                self.initial['tipo'] = 'DEVS'
            elif titulo in ("caja negra", "smoke"):
                self.initial['tipo'] = 'PRUE'
            elif titulo in ("diagrama de clases", "diagrama de entidad-relacion"):
                self.initial['tipo'] = 'DISE'
            elif titulo in ("diagrama de secuencia", "diagrama de estado"):
                self.initial['tipo'] = 'DEVS'
            elif titulo in ("diagrama de c4-contexto", "diagrama de c4-contenedor", "diagrama de c4-implementación"):
                self.initial['tipo'] = 'DESP'

# ===== registarse  y loguearse  ============
class CustomUserCreationForm(UserCreationForm):
    """
    Formulario personalizado de registro de usuario con campo de email obligatorio.
    """
    username = forms.CharField(
        label='Nombre de usuario',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese un nombre de usuario'
        })
    )
            
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )

    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña'
        })
    )

    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme su contraseña'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    # ===== validadcion registro ============
    def clean_username(self):
        username = self.cleaned_data['username']
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            raise ValidationError("Debe contener solo letras, números o guion bajo, entre 3 y 20 caracteres.")
        if texto_no_coherente(username):
            raise ValidationError("El usuario no es coherente o tiene patrones repetitivos.")
        return username


    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        # Verificar formato general válido
        if not re.match(r'^[\w\.-]+@[a-zA-Z]+\.[a-z]{2,}(?:\.[a-z]{2,})?$', email):
            raise ValidationError("Formato de correo inválido.")

        dominio = email.split('@')[1]
        nombre_dominio = dominio.split('.')[0]

        if re.fullmatch(r'(.)\1{2,}', nombre_dominio):
            raise ValidationError("El dominio no parece real. Usa uno válido como gmail.com o outlook.com.")

        if len(nombre_dominio) < 4 or not any(letra in nombre_dominio for letra in 'aeiou'):
            raise ValidationError("El dominio debe ser coherente y reconocible.")

        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$'
        if not password or not re.match(pattern, password):
            raise ValidationError("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un símbolo.")
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if not password1 or not password2:
            raise ValidationError("Ambas contraseñas son requeridas.")
        if password1 != password2:
            raise ValidationError("Las contraseñas no coinciden.")
        return password2