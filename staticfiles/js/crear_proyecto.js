document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('projectForm');
    const nextBtn = document.getElementById('nextStep');
    const prevBtn = document.getElementById('prevStep');
    const submitBtn = document.getElementById('submitBtn');
    const progressBar = document.querySelector('.progress-bar');
    
    let currentStep = 1;
    const totalSteps = 3;
    const sections = document.querySelectorAll('.form-section');

    // Inicializar tooltips de Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Objeto para almacenar los datos de usuarios
    let usuariosData = {};

    // Función para actualizar la barra de progreso
    function updateProgress() {
        const progress = (currentStep / totalSteps) * 100;
        progressBar.style.width = `${progress}%`;
    }

    // Función para validar un paso específico
    function validateStep(step) {
        const section = document.querySelector(`[data-step="${step}"]`);
        const inputs = section.querySelectorAll('input, textarea');
        let isValid = true;
        let firstInvalidInput = null;

        inputs.forEach(input => {
            // Remover mensajes de error previos
            const existingError = input.parentElement.querySelector('.validation-error');
            if (existingError) {
                existingError.remove();
            }
            input.classList.remove('is-invalid');

            if (input.type !== 'hidden' && input.required && !input.value.trim()) {
                isValid = false;
                input.classList.add('is-invalid');
                
                // Crear mensaje de error
                const errorDiv = document.createElement('div');
                errorDiv.className = 'validation-error text-danger mt-1 small';
                errorDiv.textContent = 'Este campo es requerido';
                input.parentElement.appendChild(errorDiv);

                if (!firstInvalidInput) {
                    firstInvalidInput = input;
                }
            }
        });

        // Si es el paso 2, validar que haya al menos un usuario
        if (step === 2) {
            const usuariosList = document.getElementById('usuarios-list');
            if (!usuariosList.children.length) {
                isValid = false;
                const usuarioInput = document.querySelector('.usuario-input');
                usuarioInput.classList.add('is-invalid');
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'validation-error text-danger mt-1 small';
                errorDiv.textContent = 'Debe agregar al menos un usuario';
                usuarioInput.parentElement.parentElement.appendChild(errorDiv);
            }
        }

        if (!isValid && firstInvalidInput) {
            firstInvalidInput.focus();
        }

        return isValid;
    }

    // Función para mostrar el paso actual
    function showStep(step) {
        sections.forEach(section => {
            section.style.display = 'none';
        });
        document.querySelector(`[data-step="${step}"]`).style.display = 'block';
        
        updateProgress();
        
        // Actualizar visibilidad de botones
        prevBtn.style.display = step > 1 ? 'block' : 'none';
        nextBtn.style.display = step < totalSteps ? 'block' : 'none';
        submitBtn.style.display = step === totalSteps ? 'block' : 'none';
    }

    // Agregar nuevo usuario
    document.querySelector('.add-usuario-btn').addEventListener('click', function() {
        const usuarioInput = document.querySelector('.usuario-input');
        const usuario = usuarioInput.value.trim();
        
        if (usuario) {
            addUserToList(usuario);
            usuarioInput.value = '';
        }
    });

    // Función para agregar usuario a la lista
    function addUserToList(usuario) {
        const usuariosList = document.getElementById('usuarios-list');
        
        // Crear elemento para el usuario
        const userDiv = document.createElement('div');
        userDiv.className = 'user-section mt-4';
        userDiv.innerHTML = `
            <div class="user-header" style="display: flex; justify-content: space-between; align-items: center;">
                <h6 style="font-weight:800; margin: 0; text-transform: uppercase;"><i class="fas fa-user-circle" style="margin-right: 10px;"></i>${usuario}</h6>
                <button type="button" class="delete-user-btn" title="Eliminar usuario" aria-label="Eliminar usuario">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
            
            <div class="user-content">
                <div class="user-needs">
                    <label>Necesidades específicas del usuario</label>
                    <div class="input-group">
                        <input type="text" class="form-control need-input" placeholder="¿Qué necesita este usuario?" style="border: 2px solid #e2e8f0; border-radius: 0.5rem; padding: 0.75rem 1rem; font-size: 1rem; background-color: #f8fafc;">
                        <button type="button" class="btn btn-outline-primary add-need-btn">
                            <i class="fas fa-plus"></i> Agregar
                        </button>
                    </div>
                    <div class="needs-list list-group mt-3"></div>
                </div>
                
                <div class="user-processes">
                    <label>Procesos Principales</label>
                    <div class="input-group">
                        <input type="text" class="form-control process-input" placeholder="¿Qué proceso realiza este usuario?" style="border: 2px solid #e2e8f0; border-radius: 0.5rem; padding: 0.75rem 1rem; font-size: 1rem; background-color: #f8fafc;">
                        <button type="button" class="btn btn-outline-success add-process-btn">
                            <i class="fas fa-plus"></i> Agregar
                        </button>
                    </div>
                    <div class="processes-list list-group mt-3"></div>
                </div>
            </div>
        `;

        usuariosList.appendChild(userDiv);

        // Inicializar datos del usuario
        usuariosData[usuario] = {
            necesidades: [],
            procesos: []
        };

        // Agregar event listener para eliminar usuario
        const deleteBtn = userDiv.querySelector('.delete-user-btn');
        deleteBtn.addEventListener('click', () => {
            if (confirm(`¿Estás seguro que deseas eliminar el usuario "${usuario}" y todas sus necesidades y procesos?`)) {
                delete usuariosData[usuario];
                userDiv.remove();
                updateHiddenFields();

                // Verificar si no hay usuarios y mostrar mensaje de validación
                if (Object.keys(usuariosData).length === 0) {
                    const usuarioInput = document.querySelector('.usuario-input');
                    usuarioInput.classList.add('is-invalid');
                    
                    const existingError = usuarioInput.parentElement.parentElement.querySelector('.validation-error');
                    if (!existingError) {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'validation-error text-danger mt-1 small';
                        errorDiv.textContent = 'Debe agregar al menos un usuario';
                        usuarioInput.parentElement.parentElement.appendChild(errorDiv);
                    }
                }
            }
        });

        // Agregar event listeners para necesidades y procesos
        const needInput = userDiv.querySelector('.need-input');
        const needBtn = userDiv.querySelector('.add-need-btn');
        const needsList = userDiv.querySelector('.needs-list');
        
        const processInput = userDiv.querySelector('.process-input');
        const processBtn = userDiv.querySelector('.add-process-btn');
        const processesList = userDiv.querySelector('.processes-list');

        needBtn.addEventListener('click', () => {
            const need = needInput.value.trim();
            if (need) {
                addNeed(usuario, need, needsList);
                needInput.value = '';
            }
        });

        processBtn.addEventListener('click', () => {
            const process = processInput.value.trim();
            if (process) {
                addProcess(usuario, process, processesList);
                processInput.value = '';
            }
        });

        updateHiddenFields();
    }

    // Funciones para agregar necesidades y procesos
    function addNeed(usuario, need, listElement) {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.style.borderLeft = '4px solid #4a90e2';
        li.style.marginBottom = '12px';
        li.style.borderRadius = '8px';
        li.style.padding = '12px 18px';
        li.style.backgroundColor = 'white';
        li.style.transition = 'all 0.3s ease';
        li.style.boxShadow = '0 2px 4px rgba(0,0,0,0.04)';
        li.innerHTML = `
            <span>${need}</span>
            <button type="button" class="btn btn-outline-danger">×</button>
        `;
        listElement.appendChild(li);
        
        usuariosData[usuario].necesidades.push(need);
        
        li.querySelector('button').addEventListener('click', () => {
            li.remove();
            usuariosData[usuario].necesidades = usuariosData[usuario].necesidades.filter(n => n !== need);
            updateHiddenFields();
        });

        updateHiddenFields();
    }

    function addProcess(usuario, process, listElement) {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.style.borderLeft = '4px solid #28a745';
        li.style.marginBottom = '12px';
        li.style.borderRadius = '8px';
        li.style.padding = '12px 18px';
        li.style.backgroundColor = 'white';
        li.style.transition = 'all 0.3s ease';
        li.style.boxShadow = '0 2px 4px rgba(0,0,0,0.04)';
        li.innerHTML = `
            <span>${process}</span>
            <button type="button" class="btn btn-outline-danger">×</button>
        `;
        listElement.appendChild(li);
        
        usuariosData[usuario].procesos.push(process);
        
        li.querySelector('button').addEventListener('click', () => {
            li.remove();
            usuariosData[usuario].procesos = usuariosData[usuario].procesos.filter(p => p !== process);
            updateHiddenFields();
        });

        updateHiddenFields();
    }

    // Función para actualizar los campos ocultos
    function updateHiddenFields() {
        const usuarios = Object.keys(usuariosData);
        document.getElementById('usuarios_finales_hidden').value = usuarios.join('\n');

        let necesidades = '';
        let procesos = '';

        usuarios.forEach(usuario => {
            if (usuariosData[usuario].necesidades.length > 0) {
                necesidades += `[${usuario}]\n${usuariosData[usuario].necesidades.join('\n')}\n\n`;
            }
            if (usuariosData[usuario].procesos.length > 0) {
                procesos += `[${usuario}]\n${usuariosData[usuario].procesos.join('\n')}\n\n`;
            }
        });

        document.getElementById('necesidades_usuarios_hidden').value = necesidades.trim();
        document.getElementById('procesos_principales_hidden').value = procesos.trim();
    }

    // Event listeners para navegación
    nextBtn.addEventListener('click', () => {
        if (currentStep < totalSteps && validateStep(currentStep)) {
            currentStep++;
            showStep(currentStep);
        }
    });

    prevBtn.addEventListener('click', () => {
        if (currentStep > 1) {
            currentStep--;
            showStep(currentStep);
        }
    });

    // Validación final al enviar el formulario
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validar el paso actual
        if (!validateStep(currentStep)) {
            return;
        }

        // Validar que haya al menos un usuario
        const usuariosList = document.getElementById('usuarios-list');
        if (!usuariosList.children.length) {
            alert('Debe agregar al menos un usuario antes de crear el proyecto');
            return;
        }

        // Validar que cada usuario tenga al menos una necesidad y una funcionalidad
        let isValid = true;
        const userSections = usuariosList.getElementsByClassName('user-section');
        
        for (const userSection of userSections) {
            const needsList = userSection.querySelector('.needs-list');
            const processesList = userSection.querySelector('.processes-list');
            const userName = userSection.querySelector('.user-header h6').textContent.replace('Usuario: ', '');

            if (!needsList.children.length) {
                alert(`El usuario "${userName}" debe tener al menos una necesidad`);
                isValid = false;
                break;
            }

            if (!processesList.children.length) {
                alert(`El usuario "${userName}" debe tener al menos un proceso principal`);
                isValid = false;
                break;
            }
        }

        if (isValid) {
            this.submit();
        }
    });

    // Mostrar el primer paso al cargar
    showStep(1);
});