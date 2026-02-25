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
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import AnonymousLoginRequest
from typing import List
from pydantic import BaseModel
from app.api import deps

router = APIRouter()

# ----------- Obtener datos del usuario actual -----------
@router.get("/me", response_model=UserOut)
def read_users_me(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener el perfil del usuario actual.
    """
    return current_user
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
# Endpoint para obtener profesionales de terreno disponibles para despacho
@router.get("/profesionales", response_model=List[UserOut])
def get_profesionales(
    db: Session = Depends(deps.get_db),
    # current_user: models.User = Depends(deps.get_current_active_user) # Comentado para facilitar pruebas
):
    """
    Obtiene la lista de usuarios con rol PROFESIONAL_TERRENO para el despacho
    """
    # Buscamos a los usuarios que tengan el rol correspondiente
    profesionales = db.query(User).filter(
        User.rol == "Profesional_Terreno",
        User.is_active == True
    ).all()
    
    return profesionales

# Esquema temporal para recibir el nuevo rol
class RoleUpdate(BaseModel):
    rol: str

# ----------- Panel de Administración (Gestión de Usuarios) -----------
@router.get("/", response_model=List[UserOut])
def get_all_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
    # token_data: dict = Depends(get_current_token) # Opcional: Proteger solo para admins
):
    """
    Obtiene la lista de todos los usuarios registrados en la plataforma.
    """
    return crud_user.get_users(db, skip=skip, limit=limit)
# Endpoint para actualizar el rol de un usuario (Ej: de Victima a Profesional_Terreno)
@router.put("/{user_id}/rol")
def update_role(
    user_id: str, 
    payload: RoleUpdate, 
    db: Session = Depends(get_db)
):
    """
    Actualiza el rol de un usuario (Ej: de 'Victima' a 'Profesional_Terreno').
    """
    updated_user = crud_user.update_user_role(db, user_id, payload.rol)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {"message": "Rol actualizado exitosamente", "rol": updated_user.rol}
