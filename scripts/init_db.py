#!/usr/bin/env python3
"""
Script para inicializar estados en la base de datos
NOTA: Las tablas ya existen según v3.1.sql
Este script solo agrega datos iniciales si no existen
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_estados_peticiones(db: Session):
    """Inicializar estados de peticiones si no existen"""
    
    # Verificar si ya hay estados
    result = db.execute(text("SELECT COUNT(*) FROM estados_peticiones"))
    count = result.scalar()
    
    if count > 0:
        logger.info(f"✅ Ya existen {count} estados de peticiones")
        return
    
    # Insertar estados básicos
    estados = [
        ('pendiente', 'Petición pendiente de atención'),
        ('atendida', 'Petición atendida exitosamente'),
        ('en_proceso', 'Petición en proceso de atención'),
        ('cancelada', 'Petición cancelada'),
        ('error', 'Error al procesar petición')
    ]
    
    for code, descripcion in estados:
        db.execute(
            text("INSERT INTO estados_peticiones (code, descripcion) VALUES (:code, :desc)"),
            {"code": code, "desc": descripcion}
        )
    
    db.commit()
    logger.info(f"✅ Insertados {len(estados)} estados de peticiones")

def verify_extensions(db: Session):
    """Verificar que las extensiones necesarias están instaladas"""
    
    extensions = ['uuid-ossp', 'pgcrypto']
    
    for ext in extensions:
        result = db.execute(
            text("SELECT COUNT(*) FROM pg_extension WHERE extname = :ext"),
            {"ext": ext}
        )
        if result.scalar() == 0:
            logger.warning(f"⚠️ Extensión {ext} no encontrada. Instalando...")
            try:
                db.execute(text(f"CREATE EXTENSION IF NOT EXISTS \"{ext}\""))
                db.commit()
                logger.info(f"✅ Extensión {ext} instalada")
            except Exception as e:
                logger.error(f"❌ Error instalando {ext}: {e}")

def create_test_user(db: Session):
    """Crear usuario de prueba si no existe"""
    
    from app.models.user import User
    from app.core.security import get_password_hash
    
    # Verificar si existe usuario de prueba
    result = db.execute(
        text("SELECT COUNT(*) FROM usuarios WHERE email = :email"),
        {"email": "test@acompaniar.com"}
    )
    
    if result.scalar() > 0:
        logger.info("✅ Usuario de prueba ya existe")
        return
    
    # Crear usuario
    db.execute(
        text("""
            INSERT INTO usuarios (
                full_name, email, hashed_password, phone,
                is_anonymous, is_active, genero
            ) VALUES (
                :full_name, :email, :password, :phone,
                false, true, 'Otro'
            )
        """),
        {
            "full_name": "Usuario Prueba",
            "email": "test@acompaniar.com",
            "password": get_password_hash("Test123!"),
            "phone": "3815551234"
        }
    )
    db.commit()
    logger.info("✅ Usuario de prueba creado: test@acompaniar.com / Test123!")
    
    # Agregar contactos de prueba al usuario
    result = db.execute(
        text("SELECT id FROM usuarios WHERE email = 'test@acompaniar.com'")
    )
    user_id = result.scalar()
    
    if user_id:
        # Agregar 2 contactos de ejemplo
        contacts = [
            ("María García", "3815551111"),
            ("Juan Pérez", "3815552222")
        ]
        
        for nombre, telefono in contacts:
            db.execute(
                text("""
                    INSERT INTO contactos (usuario_id, nombre, telefono)
                    VALUES (:user_id, :nombre, :telefono)
                """),
                {"user_id": user_id, "nombre": nombre, "telefono": telefono}
            )
        
        db.commit()
        logger.info("✅ Contactos de prueba agregados")

def init_db():
    """Inicializar base de datos"""
    
    # Crear engine
    engine = create_engine(settings.DATABASE_URL)
    
    # Crear sesión
    db = Session(engine)
    
    try:
        logger.info("🔧 Iniciando configuración de base de datos...")
        
        # Verificar extensiones
        verify_extensions(db)
        
        # Inicializar estados
        init_estados_peticiones(db)
        
        # Crear usuario de prueba
        create_test_user(db)
        
        logger.info("\n" + "="*50)
        logger.info("🎉 Base de datos configurada correctamente!")
        logger.info("="*50)
        logger.info("\n📝 Credenciales de prueba:")
        logger.info("   Usuario: test@acompaniar.com")
        logger.info("   Contraseña: Test123!")
        logger.info("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error al inicializar BD: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()