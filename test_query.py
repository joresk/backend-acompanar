import asyncio
from sqlalchemy.orm import Session, joinedload
from app.db.session import SessionLocal
from app.models.peticion import Peticion

def test_query():
    db = SessionLocal()
    try:
        peticiones = db.query(Peticion).options(
            joinedload(Peticion.ubicacion),
            joinedload(Peticion.usuario)
        ).filter(
            Peticion.estado_code.in_(["pendiente", "en_triaje"]), 
            Peticion.contacto_id == None
        ).all()
        print(f"Total peticiones activas: {len(peticiones)}")
        for p in peticiones:
            is_anon = p.usuario.is_anonymous if p.usuario else False
            nombre = p.usuario.full_name if p.usuario else "Desconocido"
            telefono = p.usuario.phone if p.usuario else None
            direccion = p.ubicacion.direccion if p.ubicacion else "Desconocida"
            print(f"ID: {p.id}, Nombre: {nombre}, Tel: {telefono}, Dir: {direccion}, Anon: {is_anon}")
    finally:
        db.close()

if __name__ == "__main__":
    test_query()
