$(document).ready(function() {
    // Configuración de los pasos
    const steps = {
        1: ['nombre', 'descripcion', 'objetivo_principal'],
        2: ['usuarios_finales', 'necesidades_usuarios'],
        3: ['reglas_restricciones']
    };

    let currentStep = 1;
    const totalSteps = Object.keys(steps).length;

    // Función para mostrar solo los campos del paso actual
    function showCurrentStep() {
        // Ocultar todos los campos
        Object.values(steps).flat().forEach(fieldName => {
            $(`[name="${fieldName}"]`).closest('.form-group').hide();
        });

        // Mostrar solo los campos del paso actual
        steps[currentStep].forEach(fieldName => {
            $(`[name="${fieldName}"]`).closest('.form-group').fadeIn(300);
        });

        // Actualizar título del paso
        const titles = {
            1: '📋 Información Básica del Proyecto',
            2: '👥 Usuarios y Necesidades',
            3: '🔄 Reglas y Restricciones'
        };
        $('.step-title').text(titles[currentStep]);

        // Actualizar progreso
        updateProgress();
        updateButtons();
        updateStepIndicators();
    }

    // Actualizar la barra de progreso
    function updateProgress() {
        const progress = ((currentStep - 1) * 100) / (totalSteps - 1);
        $('.progress-bar').css('width', progress + '%');
    }

    // Actualizar la visibilidad de los botones
    function updateButtons() {
        $('#prevStep').toggle(currentStep > 1);
        $('#nextStep').toggle(currentStep < totalSteps);
        $('#submitBtn').toggle(currentStep === totalSteps);
    }

    // Actualizar los indicadores de paso
    function updateStepIndicators() {
        $('.wizard-step').each(function(index) {
            $(this)
                .toggleClass('active', index + 1 === currentStep)
                .toggleClass('completed', index + 1 < currentStep);
        });
    }

    // Validar campos del paso actual
    function validateCurrentStep() {
        let isValid = true;
        const currentFields = steps[currentStep];

        currentFields.forEach(fieldName => {
            const $field = $(`[name="${fieldName}"]`);
            if ($field.prop('required') && !$field.val().trim()) {
                isValid = false;
                $field.addClass('is-invalid');
                
                // Agregar mensaje de error si no existe
                if (!$field.next('.invalid-feedback').length) {
                    $field.after('<div class="invalid-feedback">Este campo es obligatorio</div>');
                }
            } else {
                $field.removeClass('is-invalid');
                $field.next('.invalid-feedback').remove();
            }
        });

        return isValid;
    }

    // Inicializar tooltips
    $('[data-bs-toggle="tooltip"]').tooltip({
        template: '<div class="tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner bg-info"></div></div>'
    });

    // Eventos de navegación
    $('#nextStep').click(function() {
        if (validateCurrentStep() && currentStep < totalSteps) {
            currentStep++;
            showCurrentStep();
        }
    });

    $('#prevStep').click(function() {
        if (currentStep > 1) {
            currentStep--;
            showCurrentStep();
        }
    });

    // Manejo de campos dinámicos para usuarios_finales
    $(document).on('click', '.add-field-btn', function() {
        const $container = $(this).closest('.dynamic-field-container');
        const $newGroup = $container.find('.dynamic-field-group').first().clone();
        $newGroup.find('input').val('');
        
        const $removeBtn = $('<button type="button" class="btn btn-link text-danger remove-field-btn">❌</button>');
        $newGroup.append($removeBtn);
        $container.append($newGroup);
    });

    $(document).on('click', '.remove-field-btn', function() {
        $(this).closest('.dynamic-field-group').fadeOut(200, function() {
            $(this).remove();
        });
    });

    // Validación antes de enviar el formulario
    $('#projectForm').on('submit', function(e) {
        e.preventDefault();
        
        // Recopilar todos los valores de campos dinámicos
        const usuariosFinales = [];
        $('.dynamic-field-container[data-field-name="usuarios_finales"] input').each(function() {
            const valor = $(this).val().trim();
            if (valor) {
                usuariosFinales.push(valor);
            }
        });

        // Agregar los valores como campo oculto
        const $hiddenInput = $('<input>')
            .attr({
                type: 'hidden',
                name: 'usuarios_finales_list',
                value: JSON.stringify(usuariosFinales)
            });
        
        $(this).append($hiddenInput);
        this.submit();
    });

    // Inicializar el primer paso
    showCurrentStep();
});