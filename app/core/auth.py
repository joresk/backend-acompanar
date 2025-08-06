from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import create_access_token, verify_password
from datetime import timedelta
from app.schemas.auth import LoginWithDeviceRequest
from app.crud import crud_user
from typing import Optional
import secrets
import string

ACCESS_TOKEN_EXPIRE_MINUTES = 30
ANONYMOUS_TOKEN_EXPIRE_HOURS = 24

def authenticate_user(db: Session, login_data: LoginWithDeviceRequest) -> Optional[User]:
    """Autentica usuario y actualiza información del dispositivo"""
    user = crud_user.get_user_by_email(db, login_data.email)
    if not user or not verify_password(login_data.password, user.hashed_password):
        return None
    
    # Actualizar IP del dispositivo
    if login_data.device_info and login_data.device_info.ipAddress:
        crud_user.update_user_device_info(db, user, login_data.device_info.ipAddress)
    
    return user

def create_user_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Genera un JWT para usuarios registrados"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(data=data, expires_delta=expires_delta)

def create_anonymous_token(data: dict) -> str:
    """Genera un JWT para usuarios anónimos con mayor duración"""
    expires_delta = timedelta(hours=ANONYMOUS_TOKEN_EXPIRE_HOURS)
    return create_access_token(data=data, expires_delta=expires_delta)

def generate_temp_password(length: int = 12) -> str:
    """Genera una contraseña temporal para recuperación"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))