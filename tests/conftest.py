import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Importar app y dependencias de tu proyecto
from app.main import app
from app.db.session import get_db

# Crear Base si existe o usar ejecución directa
# En este backend las tablas a veces se crean con SQL crudo (text) en las rutas, 
# por lo que el test client debe permitir eso.

# URL de la base de datos de test en memoria
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Crear engine para SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Crear una nueva conexión y sesión para cada test
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Importar los modelos para que Base los conozca
    from app.db.base import Base
    from app.models.user import User
    from app.models.perfil_seguridad import PerfilSeguridad
    
    # No usamos Base.metadata.create_all porque falla en SQLite por tipos nativos de Postgres (ej. INET, ENUM).
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE,
            hashed_password TEXT,
            phone TEXT,
            is_anonymous BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            genero TEXT DEFAULT 'Otro',
            ip_dispositivo TEXT,
            latitud_actual REAL,
            longitud_actual REAL,
            rol TEXT DEFAULT 'Victima'
        );
    """))
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS perfiles_seguridad (
            id TEXT PRIMARY KEY,
            usuario_id TEXT NOT NULL UNIQUE,
            nivel_riesgo INTEGER DEFAULT 1,
            notas_contexto TEXT,
            tipo_violencia TEXT,
            ultima_interaccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_checkin TIMESTAMP
        );
    """))
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS ubicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direccion TEXT,
            latitud REAL,
            longitud REAL
        );
    """))
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS peticiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id TEXT,
            ubicacion_id INTEGER,
            estado_code TEXT,
            mensaje TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS estados_peticiones (
            code TEXT PRIMARY KEY,
            descripcion TEXT NOT NULL
        );
    """))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    # Sobrescribir la dependencia get_db
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
