from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import create_access_token as _create_token, verify_password
from datetime import timedelta
from app.schemas.user import UserLogin
from app.crud import crud_user

ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ---------- Login tradicional ----------

def authenticate_user(db: Session, login_data: UserLogin):
    user = crud_user.get_user_by_email(db, login_data.email)
    if not user or not verify_password(login_data.password, user.hashed_password):
        return None
    return user

# ---------- Login anónimo ----------

def anonymous_login(db: Session):
    # Podés extender esto con lógica basada en device_id o similar
    from app.schemas.user import UserCreate
    new_user = UserCreate(is_anonymous=True)
    return crud_user.create_user(db, new_user)

# ---------- Generar JWT ----------

def create_user_token(data: dict):
    # reutiliza la función de security con el tiempo por defecto
    return _create_token(data)
