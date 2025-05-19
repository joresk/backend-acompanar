from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.db.session import get_db
from app.api.deps import get_current_token, get_current_user
from app.core import auth
from app.crud import crud_user
from fastapi import APIRouter
from uuid import uuid4
from app.schemas.token import Token
from app.core.auth import create_user_token


router = APIRouter()

#Rutas que aceptan anónimos (usando payload)
@router.get("/public-info")
def public_info(token_data: dict = Depends(get_current_token)):
    if token_data.get("is_anonymous"):
        return {"msg": "Bienvenido, usuario anónimo"}
    else:
        return {"msg": f"Hola, usuario {token_data['sub']}"}

#Rutas que solo usuarios registrados pueden acceder
@router.get("/protected", response_model=UserOut)
def protected_route(user = Depends(get_current_user)):
    # user es un objeto User de la base
    return user

# ----------- Ping para test -----------

@router.get("/ping")
def ping():
    return {"status": "ok"}

# ----------- Registro -----------

@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    print("📥 Intentando registrar:", user_in)
    
    if not user_in.is_anonymous and not user_in.email:
        raise HTTPException(status_code=400, detail="Se requiere email para registro no anónimo.")
    
    if user_in.email:
        existing_user = crud_user.get_user_by_email(db, user_in.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email ya registrado.")

    new_user = crud_user.create_user(db, user_in)
    print("✅ Usuario creado:", new_user)
    return new_user

# ----------- Login tradicional -----------

@router.post("/login")
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, login_data)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    # ← aquí paso un dict, no el User completo
    token = auth.create_user_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

# ----------- Login anónimo -----------

@router.post("/anonymous", response_model=Token)
def anonymous_login():
    #Genera un JWT para sesión anónima sin tocar la base de datos.    
    # 1. Creamos un UUID para identificar la sesión
    anon_id = str(uuid4())
    # 2. Generamos el token incluyendo is_anonymous=True
    token = create_user_token({"sub": anon_id, "is_anonymous": True})
    # 3. Devolvemos el esquema Token { access_token, token_type }
    return {"access_token": token, "token_type": "bearer"}

@router.post("/complete", response_model=Token)
def complete_registration(user_in: UserCreate,
                        token_data: dict = Depends(get_current_token),
                        db: Session = Depends(get_db)):
    # Sólo si venís de sesión anónima
    if not token_data.get("is_anonymous"):
        raise HTTPException(status_code=400, detail="No es una sesión anónima")
    # Crea el usuario real en BD
    new_user = crud_user.create_user(db, user_in)
    # Genera token definitivo
    token = create_user_token({"sub": str(new_user.id)})
    return {"access_token": token, "token_type": "bearer"}