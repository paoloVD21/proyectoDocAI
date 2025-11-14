from django.contrib.auth.hashers import make_password, check_password
from typing import Optional
import re

def hash_respuesta(respuesta: Optional[str]) -> Optional[str]:
    """
    Hashea la respuesta de seguridad usando el mismo algoritmo que Django usa para contraseñas
    Args:
        respuesta: La respuesta a hashear
    Returns:
        str: La respuesta hasheada o None si la entrada es None
    """
    if not respuesta:
        return None
    return make_password(respuesta.lower())

def verificar_respuesta(respuesta, respuesta_hasheada):
    """
    Verifica si la respuesta coincide con el hash almacenado
    """
    if not respuesta or not respuesta_hasheada:
        return False
    return check_password(respuesta.lower(), respuesta_hasheada)

def parse_historias_desde_texto(texto):
    """
    Procesa el texto de historias de usuario y devuelve una lista de diccionarios parseados.
    Mismo funcionamiento que el filtro de template parse_historias.
    """
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