window.DIAGRAMA_INFO = {
    proyecto: "",  // Se llenará dinámicamente
    titulo: "",    // Se llenará dinámicamente
    fecha: ""      // Se llenará dinámicamente
};

// ========================================
// Gestor profesional de Drag & Drop
// ========================================
if (!window.HistoriasDragDropManager) {
    class HistoriasDragDropManager {
        constructor(containerId = 'historias-lista') {
            this.container = document.getElementById(containerId);
            this.draggedElement = null;
            this.dropIndicator = null;
            this.placeholderHeight = 3; // Altura de la línea indicadora en px
            
            if (!this.container) return;
            
            this.init();
        }

        init() {
            this.createDropIndicator();
            this.attachContainerListeners();
        }

        createDropIndicator() {
            this.dropIndicator = document.createElement('div');
            this.dropIndicator.className = 'drop-line-indicator';
            this.container.appendChild(this.dropIndicator);
        }

        attachContainerListeners() {
            this.container.addEventListener('dragstart', (e) => this.onDragStart(e), true);
            this.container.addEventListener('dragover', (e) => this.onDragOver(e), true);
            this.container.addEventListener('drop', (e) => this.onDrop(e), true);
            this.container.addEventListener('dragend', (e) => this.onDragEnd(e), true);
            this.container.addEventListener('dragenter', (e) => this.onDragEnter(e), true);
            this.container.addEventListener('dragleave', (e) => this.onDragLeave(e), true);
        }

        onDragStart(e) {
            const item = e.target.closest('.historia-item');
            if (!item) return;
            
            this.draggedElement = item;
            item.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', item.innerHTML);
        }

        onDragOver(e) {
            e.preventDefault();
            e.stopPropagation();
            e.dataTransfer.dropEffect = 'move';
            
            if (!this.draggedElement) return;
            
            const targetItem = e.target.closest('.historia-item');
            
            if (targetItem && targetItem !== this.draggedElement) {
                this.updateDropIndicator(e, targetItem);
            }
        }

        onDragEnter(e) {
            e.preventDefault();
        }

        onDragLeave(e) {
            // Ocultar indicador solo si salimos del contenedor
            if (!this.container.contains(e.relatedTarget)) {
                this.hideDropIndicator();
            }
        }

        onDrop(e) {
            e.preventDefault();
            e.stopPropagation();

            if (!this.draggedElement) return;

            const targetItem = e.target.closest('.historia-item');
            
            if (targetItem && targetItem !== this.draggedElement) {
                const position = this.getDropPosition(e, targetItem);
                
                if (position === 'before') {
                    this.container.insertBefore(this.draggedElement, targetItem);
                } else {
                    this.container.insertBefore(this.draggedElement, targetItem.nextSibling);
                }
                
                this.updateHistoriaNumbers();
            }

            this.hideDropIndicator();
        }

        onDragEnd(e) {
            if (this.draggedElement) {
                this.draggedElement.classList.remove('dragging');
                this.draggedElement = null;
            }
            this.hideDropIndicator();
        }

        getDropPosition(e, targetItem) {
            const rect = targetItem.getBoundingClientRect();
            const midpoint = rect.height / 2;
            const cursorY = e.clientY - rect.top;
            
            return cursorY < midpoint ? 'before' : 'after';
        }

        updateDropIndicator(e, targetItem) {
            const rect = targetItem.getBoundingClientRect();
            const containerRect = this.container.getBoundingClientRect();
            const position = this.getDropPosition(e, targetItem);
            
            if (position === 'before') {
                const top = rect.top - containerRect.top;
                this.dropIndicator.style.top = top + 'px';
            } else {
                const top = rect.bottom - containerRect.top;
                this.dropIndicator.style.top = top + 'px';
            }
            
            this.dropIndicator.style.width = rect.width + 'px';
            this.dropIndicator.style.left = (rect.left - containerRect.left) + 'px';
            this.dropIndicator.style.display = 'block';
        }

        hideDropIndicator() {
            this.dropIndicator.style.display = 'none';
        }

        updateHistoriaNumbers() {
            const items = this.container.querySelectorAll('.historia-item');
            items.forEach((item, index) => {
                const numero = index + 1;
                item.dataset.historiaId = numero;
                const titleElement = item.querySelector('h6');
                if (titleElement) {
                    titleElement.textContent = `Historia de Usuario #${numero}`;
                }
            });
        }
    }
    
    window.HistoriasDragDropManager = HistoriasDragDropManager;
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('historias-lista')) {
        new window.HistoriasDragDropManager('historias-lista');
    }
});