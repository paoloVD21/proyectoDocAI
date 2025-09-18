window.DIAGRAMA_INFO = {
    proyecto: "",  // Se llenará dinámicamente
    titulo: "",    // Se llenará dinámicamente
    fecha: ""      // Se llenará dinámicamente
};

// Funcionalidad de arrastrar y soltar
document.addEventListener('DOMContentLoaded', function() {
    const historiasLista = document.getElementById('historias-lista');
    let draggedItem = null;

    // Aplicar eventos a cada historia
    document.querySelectorAll('.historia-item').forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
    });

    function handleDragStart(e) {
        draggedItem = this;
        this.style.opacity = '0.4';
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this.dataset.historiaId);
    }

    function handleDragEnd(e) {
        this.style.opacity = '1';
        document.querySelectorAll('.historia-item').forEach(item => {
            item.classList.remove('drag-over');
        });
    }

    function handleDragOver(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    }

    function handleDrop(e) {
        e.preventDefault();
        if (this === draggedItem) return;

        const draggedId = parseInt(draggedItem.dataset.historiaId);
        const dropId = parseInt(this.dataset.historiaId);
        
        if (dropId > draggedId) {
            this.parentNode.insertBefore(draggedItem, this.nextSibling);
        } else {
            this.parentNode.insertBefore(draggedItem, this);
        }

        // Actualizar los números de las historias
        actualizarNumerosHistorias();
    }

    function actualizarNumerosHistorias() {
        document.querySelectorAll('.historia-item').forEach((item, index) => {
            item.dataset.historiaId = index + 1;
            item.querySelector('h6').textContent = `Historia de Usuario #${index + 1}`;
        });
    }
});