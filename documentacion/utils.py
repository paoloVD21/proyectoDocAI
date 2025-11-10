from django.contrib.auth.hashers import make_password, check_password
from typing import Optional

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