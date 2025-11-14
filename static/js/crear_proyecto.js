document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('projectForm');
    const usuarioInput = document.querySelector('.usuario-input');
    const addUsuarioBtn = document.querySelector('.add-usuario-btn');
    const usuariosList = document.getElementById('usuarios-list');
    const submitBtn = document.getElementById('submitBtn');
    let usuariosData = {};

    function showInputError(input, message) {
        input.classList.add('is-invalid');
        const existingError = input.parentElement.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        input.parentElement.appendChild(errorDiv);
    }

    // Add user functionality
    addUsuarioBtn.addEventListener('click', function() {
        const usuario = usuarioInput.value.trim();
        if (!usuario) {
            showInputError(usuarioInput, 'Por favor ingrese un nombre de usuario');
            return;
        }

        if (usuariosData[usuario]) {
            showInputError(usuarioInput, 'Este usuario ya existe');
            return;
        }

        addUserToList(usuario);
        // Limpiar completamente el input y darle foco
        usuarioInput.value = '';
        usuarioInput.classList.remove('is-invalid');
        usuarioInput.classList.remove('is-valid');
        setTimeout(() => usuarioInput.focus(), 100);
    });

    function addUserToList(usuario) {
        const userDiv = document.createElement('div');
        userDiv.className = 'user-section mt-4 border rounded p-3';
        userDiv.innerHTML = `
            <div class="user-header d-flex justify-content-between align-items-center mb-3">
                <h6 class="m-0 text-uppercase fw-bold">
                    <i class="fas fa-user-circle me-2"></i>${usuario}
                </h6>
                <button type="button" class="btn btn-outline-danger btn-sm delete-user-btn">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
            <div class="user-content">
                <div class="user-needs mb-3">
                    <label>Necesidades específicas</label>
                    <div class="input-group mb-2">
                        <input type="text" class="form-control need-input" placeholder="¿Qué necesita este usuario?">
                        <button type="button" class="btn btn-outline-primary add-need-btn">
                            <i class="fas fa-plus"></i> Agregar
                        </button>
                    </div>
                    <div class="needs-list list-group"></div>
                </div>

            </div>
        `;

        usuariosList.appendChild(userDiv);
        usuariosData[usuario] = { necesidades: [] };

        // Add needs functionality
        const needInput = userDiv.querySelector('.need-input');
        const addNeedBtn = userDiv.querySelector('.add-need-btn');
        const needsList = userDiv.querySelector('.needs-list');

        addNeedBtn.addEventListener('click', function() {
            const need = needInput.value.trim();
            if (!need) {
                showInputError(needInput, 'Por favor ingrese una necesidad');
                return;
            }
            addNeed(usuario, need, needsList);
            // Limpiar el input de necesidad y remover clases de validación
            needInput.value = '';
            needInput.classList.remove('is-invalid');
            needInput.classList.remove('is-valid');
            needInput.focus();
        });

        // Delete user functionality
        userDiv.querySelector('.delete-user-btn').addEventListener('click', function() {
            if (confirm('¿Está seguro de eliminar este usuario?')) {
                delete usuariosData[usuario];
                userDiv.remove();
                updateHiddenFields();
            }
        });

        updateHiddenFields();
    }

    function addNeed(usuario, need, listElement) {
        // Validar y limpiar la entrada
        need = need.trim();
        if (!need) return;

        const li = document.createElement('div');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `
            <span>${need}</span>
            <button type="button" class="btn btn-outline-danger btn-sm">×</button>
        `;

        listElement.appendChild(li);
        usuariosData[usuario].necesidades.push(need);

        li.querySelector('button').addEventListener('click', function() {
            li.remove();
            usuariosData[usuario].necesidades = usuariosData[usuario].necesidades.filter(n => n !== need);
            updateHiddenFields();
        });

        updateHiddenFields();
    }

    function updateHiddenFields() {
        const usuarios = Object.keys(usuariosData);
        
        // Guardar usuarios y necesidades en un texto comprensible
        let usuariosNecesidades = '';
        for (const usuario of usuarios) {
            usuariosNecesidades += `${usuario}:\n`;
            if (usuariosData[usuario].necesidades.length > 0) {
                usuariosNecesidades += usuariosData[usuario].necesidades.map(n => `  - ${n}`).join('\n');
            }
            usuariosNecesidades += '\n\n';
        }

        const hiddenField = document.getElementById('id_usuarios_necesidades');
        if (hiddenField) {
            hiddenField.value = usuariosNecesidades.trim();
        }
    }

    // Form submission with validation
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Validar todos los campos requeridos del formulario
        let isValid = true;
        let firstInvalidInput = null;

        // 1. Validar campos básicos del proyecto
        const requiredInputs = form.querySelectorAll('input[required], textarea[required]');
        requiredInputs.forEach(input => {
            if (input.type !== 'hidden' && !input.value.trim()) {
                showInputError(input, 'Este campo es obligatorio');
                isValid = false;
                if (!firstInvalidInput) firstInvalidInput = input;
            } else {
                input.classList.remove('is-invalid');
            }
        });

        // 2. Validar que haya al menos un usuario
        const usuarios = Object.keys(usuariosData);
        if (usuarios.length === 0) {
            showInputError(usuarioInput, 'Debe agregar al menos un usuario');
            isValid = false;
            if (!firstInvalidInput) firstInvalidInput = usuarioInput;
        }

        // 3. Validar datos de cada usuario
        let usuariosValidos = true;
        let mensajesError = [];

        for (const usuario of usuarios) {
            if (usuariosData[usuario].necesidades.length === 0) {
                mensajesError.push(`El usuario "${usuario}" debe tener al menos una necesidad`);
                usuariosValidos = false;
            }
        }

        if (!usuariosValidos) {
            alert(mensajesError.join('\n'));
            isValid = false;
        }

        // Si hay errores, enfocar el primer campo inválido
        if (!isValid) {
            if (firstInvalidInput) {
                firstInvalidInput.focus();
            }
            return;
        }

        // 4. Si todo es válido, actualizar campos ocultos y enviar
        try {
            updateHiddenFields();
            setTimeout(() => {
                form.submit();
            }, 100);
        } catch (error) {
            console.error('Error al enviar el formulario:', error);
            alert('Hubo un error al enviar el formulario. Por favor, inténtelo de nuevo.');
        }
    });
});