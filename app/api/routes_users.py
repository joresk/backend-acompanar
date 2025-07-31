from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.db.session import get_db
from app.api.deps import get_current_token
from app.core import auth
from app.crud import crud_user
from uuid import uuid4
from app.schemas.token import Token
from datetime import timedelta
from app.schemas.auth import AnonymousLoginRequest

router = APIRouter()

# Rutas que aceptan anónimos (usando payload)
@router.get("/public-info")
def public_info(token_data: dict = Depends(get_current_token)):
    if token_data.get("is_anonymous"):
        return {"msg": "Bienvenido, usuario anónimo"}
    return {"msg": f"Hola, usuario {token_data['sub']}"}

# Rutas que solo usuarios registrados pueden acceder
@router.get("/protected", response_model=UserOut)
def protected_route(
    token_data: dict = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    # Solo usuarios no anónimos
    if token_data.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado para usuarios anónimos"
        )
    user_id = token_data.get("sub")
    user = crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return user

# ----------- Ping para test -----------
@router.get("/ping")
def ping():
    return {"status": "ok"}

# ----------- Registro -----------
@router.post("/register", response_model=UserOut)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    if not user_in.is_anonymous and not user_in.email:
        raise HTTPException(status_code=400, detail="Se requiere email para registro no anónimo.")
    if user_in.email:
        existing = crud_user.get_user_by_email(db, user_in.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email ya registrado.")
    new_user = crud_user.create_user(db, user_in)
    return new_user

# ----------- Login tradicional -----------
@router.post("/login")
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, login_data)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = auth.create_user_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

# ----------- Login anónimo -----------
@router.post("/anonymous", response_model=Token)
def anonymous_login(
    req: AnonymousLoginRequest
):
    anon_id = str(uuid4())
    expires = timedelta(hours=24)
    payload = {
        "sub": anon_id,
        "is_anonymous": True,
        "gender": req.gender,
        "device_os": req.device_info.os,
        "device_model": req.device_info.model,
    }
    if req.device_info.latitude is not None and req.device_info.longitude is not None:
        payload.update({"lat": req.device_info.latitude, "lon": req.device_info.longitude})
    token = auth.create_access_token(data=payload, expires_delta=expires)
    return {"access_token": token, "token_type": "bearer"}

# ----------- Completar registro anónimo -----------
@router.post("/complete", response_model=Token)
def complete_registration(
    user_in: UserCreate,
    token_data: dict = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    if not token_data.get("is_anonymous"):
        raise HTTPException(status_code=400, detail="No es una sesión anónima")
    new_user = crud_user.create_user(db, user_in)
    token = auth.create_user_token({"sub": str(new_user.id)})
    return {"access_token": token, "token_type": "bearer"}
