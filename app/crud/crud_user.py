from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


# -------- Obtener usuarios --------

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()

# -------- Crear usuario --------

def create_user(db: Session, user: UserCreate):
    # ——— Reglas de contraseña ———
    if user.password:
        # Si envían contraseña, siempre la hasheamos
        hashed_password = get_password_hash(user.password)
    else:
        # Si no envían contraseña, SÓLO está permitido para cuentas anónimas
        if not user.is_anonymous:
            raise ValueError("Se requiere contraseña para usuarios no anónimos.")
        hashed_password = None

    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_anonymous=user.is_anonymous,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# -------- Actualizar usuario anónimo (para completar registro) --------

def update_anonymous_user(db: Session, user: User, email: str, password: str):
    user.email = email
    user.hashed_password = get_password_hash(password)
    user.is_anonymous = False
    db.commit()
    db.refresh(user)
    return user

# -------- Actualizar usuario genérico --------

def update_user(db: Session, user_id: int, user_update: UserUpdate):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    for field, value in user_update.dict(exclude_unset=True).items():
        if field == "password" and value:
            db_user.hashed_password = get_password_hash(value)
        else:
            setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user

# -------- Eliminar usuario --------

def delete_user(db: Session, user_id: int) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
