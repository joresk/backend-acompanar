from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User, GenderEnum
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.auth import AnonymousLoginRequest
from app.core.security import get_password_hash
from uuid import uuid4
from typing import Optional
import secrets

# -------- Obtener usuarios --------
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()

# -------- Crear usuario regular --------
def create_user(db: Session, user: UserCreate, ip_address: Optional[str] = None) -> User:
    # Validaciones
    if not user.is_anonymous and not user.email:
        raise ValueError("Se requiere email para usuarios no anónimos")
    
    if not user.is_anonymous and not user.password:
        raise ValueError("Se requiere contraseña para usuarios no anónimos")
    
    # Hash de contraseña si existe
    hashed_password = get_password_hash(user.password) if user.password else None
    
    # Mapear género del frontend al backend
    gender_map = {
        "MALE": GenderEnum.MASCULINO,
        "FEMALE": GenderEnum.FEMENINO,
        "OTHER": GenderEnum.OTRO
    }
    genero = gender_map.get(str(user.genero), GenderEnum.OTRO) if user.genero else GenderEnum.OTRO
    
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        phone=user.phone,
        is_active=True,
        is_anonymous=user.is_anonymous,
        genero=genero,
        ip_dispositivo=ip_address
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# -------- Crear usuario anónimo --------
def create_anonymous_user(
    db: Session, 
    request: AnonymousLoginRequest,
    ip_address: Optional[str] = None
) -> User:
    # Generar nombre único para usuario anónimo
    random_suffix = secrets.token_hex(4)
    full_name = f"Usuario Anónimo {random_suffix}"
    
    # Mapear género
    gender_map = {
        "MALE": GenderEnum.MASCULINO,
        "FEMALE": GenderEnum.FEMENINO,
        "OTHER": GenderEnum.OTRO
    }
    genero = gender_map.get(request.gender, GenderEnum.OTRO)
    
    db_user = User(
        full_name=full_name,
        is_anonymous=True,
        is_active=True,
        genero=genero,
        ip_dispositivo=ip_address or request.device_info.ipAddress
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# -------- Actualizar usuario --------
def update_user(db: Session, user_id: str, user_update: UserUpdate) -> Optional[User]:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    update_data = user_update.dict(exclude_unset=True)
    
    # Si hay nueva contraseña, hashearla
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        del update_data["password"]
    
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user

# -------- Eliminar usuario (soft delete) --------
def delete_user(db: Session, user_id: str) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user

# -------- Guardar información del dispositivo --------
def update_user_device_info(
    db: Session, 
    user: User, 
    ip_address: Optional[str] = None
) -> User:
    if ip_address:
        user.ip_dispositivo = ip_address
    db.commit()
    db.refresh(user)
    return user