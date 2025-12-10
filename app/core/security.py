import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

load_dotenv()

# Variables de entorno
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# Eliminamos passlib y CryptContext porque causan conflicto con bcrypt moderno.
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------- Contraseñas ----------

def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro para la contraseña.
    Se trunca a 72 caracteres para evitar limitaciones de Bcrypt.
    """
    # 1. Truncar contraseña
    short_pwd = password[:72]
    # 2. Convertir a bytes (utf-8)
    pwd_bytes = short_pwd.encode('utf-8')
    # 3. Generar salt y hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    # 4. Retornar como string para guardar en BD
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si la contraseña coincide con el hash.
    """
    # 1. Truncar contraseña entrante
    short_pwd = plain_password[:72]
    # 2. Convertir a bytes
    pwd_bytes = short_pwd.encode('utf-8')
    # 3. Asegurar que el hash almacenado sea bytes (si viene de BD puede ser str)
    if isinstance(hashed_password, str):
        hash_bytes = hashed_password.encode('utf-8')
    else:
        hash_bytes = hashed_password
    
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        # Si el hash tiene formato inválido, retornamos False en lugar de error 500
        return False

# ---------- JWT Tokens (Sin cambios) ----------

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None