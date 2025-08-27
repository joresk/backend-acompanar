from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut
from app.schemas.auth import (
    AnonymousLoginRequest, 
    LoginWithDeviceRequest,
    RecoverPasswordRequest,
    RecoverPasswordResponse
)
from app.schemas.token import Token
from app.db.session import get_db
from app.api.deps import get_current_token
from app.core import auth
from app.crud import crud_user
from app.core.security import get_password_hash
from datetime import timedelta
from typing import Optional
from app.schemas.user import AuthResponseWithUserInfo


router = APIRouter()

# ----------- Login tradicional con dispositivo -----------
@router.post("/login", response_model=AuthResponseWithUserInfo)
def login(
    req: LoginWithDeviceRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login con email/password y guarda info del dispositivo"""
    # Autenticar usuario
    user = auth.authenticate_user(db, req)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    # Crear token con información extendida
    expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "is_anonymous": False,
        "device_id": req.device_info.deviceId,
        "first_access": req.device_info.firstAccessDate,
    }
    
    # Agregar ubicación si existe
    if req.device_info.location:
        payload.update({
            "city": req.device_info.location.city,
            "country": req.device_info.location.country,
            "lat": req.device_info.location.latitude,
            "lon": req.device_info.location.longitude,
        })
    
    token = auth.create_user_token(data=payload, expires_delta=expires)
    
    userinfo = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_anonymous": False,
        "phone": user.phone,
        "genero": user.genero
    }
    return {
        "access_token": token, 
        "token_type": "bearer",
        "user_info": userinfo  # AGREGAR ESTA LÍNEA
    }

# ----------- Login anónimo -----------
@router.post("/anonymous", response_model=AuthResponseWithUserInfo)
def anonymous_login(
    req: AnonymousLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login anónimo que crea un usuario temporal en BD"""
    try:
        # FIX: Obtener IP real del cliente
        # Primero intentar desde headers (si hay proxy/nginx)
        client_ip = (
            request.headers.get("X-Forwarded-For") or
            request.headers.get("X-Real-IP") or
            (request.client.host if request.client else None)
        )
        
        # Si viene de Android emulador, la IP será 10.0.2.2
        # Si viene de localhost, será 127.0.0.1
        # Usar la IP del device_info si está disponible
        final_ip = client_ip or req.device_info.ipAddress or "0.0.0.0"
        
        print(f"IP detectada - Client: {client_ip}, Device: {req.device_info.ipAddress}, Final: {final_ip}")
        print(f"Gender recibido: {req.gender}")
        
        # Crear usuario anónimo en BD
        anon_user = crud_user.create_anonymous_user(
            db=db,
            request=req,
            ip_address=final_ip
        )
        
        print(f"Usuario anónimo creado: ID={anon_user.id}, Género={anon_user.genero}")
        
        # Crear token
        payload = {
            "sub": str(anon_user.id),
            "is_anonymous": True,
            "gender": req.gender,  # Mantener el original para el token
            "device_id": req.device_info.deviceId,
            "first_access": req.device_info.firstAccessDate,
        }
        
        # Agregar ubicación si existe
        if req.device_info.location:
            payload.update({
                "city": req.device_info.location.city,
                "country": req.device_info.location.country,
                "lat": req.device_info.location.latitude,
                "lon": req.device_info.location.longitude,
            })
        
        token = auth.create_anonymous_token(data=payload)
        user_info = {
        "id": str(anon_user.id),
        "email": None,
        "full_name": "Usuario Anónimo",
        "is_anonymous": True,
        "phone": None,
        "genero": req.gender
        }
    
        return {
            "access_token": token, 
            "token_type": "bearer", 
            "user_info": user_info
        }
        
    except Exception as e:
        print(f"Error en login anónimo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar login anónimo: {str(e)}"
        )

# ----------- Registro -----------
@router.post("/register", response_model=UserOut)
def register(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Registro de nuevo usuario"""
    # Verificar si el email ya existe
    if user_in.email:
        existing = crud_user.get_user_by_email(db, user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
    
    # Obtener IP del cliente
    client_ip = request.client.host if request.client else None
    
    # Crear usuario
    try:
        new_user = crud_user.create_user(
            db=db, 
            user=user_in,
            ip_address=client_ip
        )
        return new_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ----------- Recuperar contraseña -----------
@router.post("/recover-password", response_model=RecoverPasswordResponse)
def recover_password(
    req: RecoverPasswordRequest,
    db: Session = Depends(get_db)
):
    """Envía instrucciones para recuperar contraseña"""
    user = crud_user.get_user_by_email(db, req.email)
    
    # Por seguridad, siempre devolver éxito aunque el email no exista
    if not user:
        return RecoverPasswordResponse(
            message="Si el email existe, recibirás instrucciones para recuperar tu contraseña",
            success=True
        )
    
    # Generar contraseña temporal
    temp_password = auth.generate_temp_password()
    
    # Actualizar contraseña en BD
    user.hashed_password = get_password_hash(temp_password)
    db.commit()
    
    # TODO: Implementar envío de email real
    # Por ahora, solo logueamos (en producción NUNCA hacer esto)
    print(f"Contraseña temporal para {user.email}: {temp_password}")
    
    return RecoverPasswordResponse(
        message="Se han enviado las instrucciones a tu email",
        success=True
    )

# ----------- Ruta protegida de prueba -----------
@router.get("/protected", response_model=UserOut)
def protected_route(
    token_data: dict = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    """Ruta protegida que requiere autenticación"""
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

# ----------- Completar registro desde anónimo -----------
@router.post("/complete-registration", response_model=Token)
def complete_registration(
    user_data: UserCreate,
    token_data: dict = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    """Convierte una cuenta anónima en cuenta registrada"""
    if not token_data.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta función es solo para usuarios anónimos"
        )
    
    # Obtener usuario anónimo actual
    anon_user_id = token_data.get("sub")
    anon_user = crud_user.get_user(db, anon_user_id)
    
    if not anon_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario anónimo no encontrado"
        )
    
    # Verificar que el email no exista
    if crud_user.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Actualizar usuario anónimo a registrado
    anon_user.email = user_data.email
    anon_user.full_name = user_data.full_name
    anon_user.hashed_password = get_password_hash(user_data.password)
    anon_user.phone = user_data.phone
    anon_user.is_anonymous = False
    
    db.commit()
    db.refresh(anon_user)
    
    # Generar nuevo token
    payload = {
        "sub": str(anon_user.id),
        "email": anon_user.email,
        "is_anonymous": False
    }
    token = auth.create_user_token(data=payload)
    
    return {"access_token": token, "token_type": "bearer"}