from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any, Optional
from app.core.security import decode_access_token
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.crud import crud_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_token_data(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Decodifica y valida el token JWT"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

def get_current_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Obtiene los datos del token actual"""
    return get_token_data(token)

def get_current_user(
    payload: Dict[str, Any] = Depends(get_token_data),
    db: Session = Depends(get_db)
) -> User:
    """Obtiene el usuario actual (no anónimos)"""
    if payload.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere usuario registrado"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    user = crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    return user

def get_current_user_optional(
    payload: Dict[str, Any] = Depends(get_token_data),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Obtiene el usuario actual (permite anónimos)"""
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = crud_user.get_user(db, user_id)
    return user if user and user.is_active else None