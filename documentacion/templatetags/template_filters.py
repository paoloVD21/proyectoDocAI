from django import template
import re

register = template.Library()

@register.filter(name='parse_historias')
def parse_historias(texto):
    """Procesa el texto de historias de usuario"""
    try:
        historias = []
        if not texto:
            return historias

        # Separar por historias de usuario
        historias_texto = re.split(r'(?=HU\d+[:\s]+)', texto)
        if len(historias_texto) <= 1:
            return historias

        # Procesar cada historia
        for historia_texto in historias_texto[1:]:  # Ignorar el primer split vacío
            # Buscar patrones "Como... Quiero... Para..."
            patron = r'HU\d+[:\s]+Como\s+(.*?)\s+Quiero\s+(.*?)\s+Para\s+(.*?)(?:\s*Criterios:|$)'
            match = re.search(patron, historia_texto, re.DOTALL | re.IGNORECASE)
            
            if match:
                historia = {
                    'como': match.group(1).strip(),
                    'quiero': match.group(2).strip(),
                    'para': match.group(3).strip(),
                    'criterios': []
                }
                
                # Buscar criterios de aceptación
                patron_criterios = r'Criterios:\s*(.*?)(?=(?:\s*HU\d+|$))'
                match_criterios = re.search(patron_criterios, historia_texto, re.DOTALL | re.IGNORECASE)
                
                if match_criterios:
                    criterios_texto = match_criterios.group(1)
                    # Dividir los criterios por puntos o números
                    criterios = re.findall(r'(?:^|\n)\s*(?:\d+[).]\s*|[-•]\s*|\*\s*)?([^.\n]+(?:\.[^.\n]+)*)', criterios_texto)
                    historia['criterios'] = [criterio.strip() for criterio in criterios if criterio.strip()]
                
                historias.append(historia)
        
        return historias
    except Exception as e:
        print(f"Error al procesar historias de usuario: {str(e)}")
        return []

@register.filter
def split_requisitos(texto):
    """Divide el texto de requisitos en una lista"""
    if not texto:
        return []
        
    # Dividir por líneas y limpiar
    requisitos = [req.strip() for req in texto.split('\n') if req.strip()]
    return requisitos
