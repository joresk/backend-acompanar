from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.schemas.user import UserOut, UserUpdate
from app.models.user import User
from app.crud import crud_user

router = APIRouter()

# ----------- Perfil del usuario autenticado -----------

@router.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# ----------- Actualizar usuario autenticado -----------

@router.put("/me", response_model=UserOut)
def update_user_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated_user = crud_user.update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return updated_user

# ----------- Eliminar usuario autenticado -----------

@router.delete("/me", response_model=UserOut)
def deactivate_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = crud_user.delete_user(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# ----------- Listar usuarios (opcional, futuro uso admin) -----------

@router.get("/", response_model=list[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud_user.get_users(db, skip=skip, limit=limit)
