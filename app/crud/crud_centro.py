from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from uuid import UUID
from fastapi import HTTPException, status

# Asegúrate de importar el nuevo modelo de imagen
from app.models.centro import Centro, CategoriasCentros, CentroAyudaTelefono, CentroAyudaImagen
from app.models.ubicacion import Ubicacion
from app.schemas.centro import CentroCreate, CentroUpdate, CentroWithDetails

class CRUDCentro:
    
    def create_with_details(
        self, 
        db: Session, 
        *, 
        obj_in: CentroCreate
    ) -> Centro:
        """Crear centro con ubicación, teléfonos e imágenes"""
        
        # Crear ubicación primero
        ubicacion = Ubicacion(
            direccion=obj_in.ubicacion.direccion,
            latitud=obj_in.ubicacion.latitud,
            longitud=obj_in.ubicacion.longitud
        )
        db.add(ubicacion)
        db.flush()
        
        # Crear centro
        centro = Centro(
            nombre=obj_in.nombre,
            descripcion=obj_in.descripcion,
            ubicacion_id=ubicacion.id,
            categoria_code=obj_in.categoria_code
        )
        db.add(centro)
        db.flush()
        
        # Crear teléfonos
        for telefono in obj_in.telefonos:
            tel = CentroAyudaTelefono(
                centro_id=centro.id,
                telefono=telefono
            )
            db.add(tel)
        
        # --- NUEVO: Crear imágenes ---
        for url in obj_in.imagenes:
            img = CentroAyudaImagen(
                centro_id=centro.id,
                url_imagen=url
            )
            db.add(img)
            
        db.commit()
        db.refresh(centro)
        return self.get_with_details(db, id=centro.id)
    
    def get_with_details(self, db: Session, id: UUID) -> Optional[Centro]:
        """Obtener centro con todos sus detalles (incluyendo imágenes)"""
        return db.query(Centro)\
            .options(
                joinedload(Centro.ubicacion),
                joinedload(Centro.telefonos),
                joinedload(Centro.categoria),
                # --- NUEVO: Cargar imágenes relacionadas ---
                joinedload(Centro.imagenes)
            )\
            .filter(Centro.id == id)\
            .first()
    
    def get_multi_with_details(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        categoria_code: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Centro]:
        """Obtener lista de centros con filtros (incluyendo imágenes)"""
        query = db.query(Centro)\
            .options(
                joinedload(Centro.ubicacion),
                joinedload(Centro.telefonos),
                joinedload(Centro.categoria),
                # --- NUEVO: Cargar imágenes relacionadas ---
                joinedload(Centro.imagenes)
            )
        
        # Aplicar filtros
        if categoria_code:
            query = query.filter(Centro.categoria_code == categoria_code)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    Centro.nombre.ilike(search_filter),
                    Centro.descripcion.ilike(search_filter)
                )
            )
        
        return query.offset(skip).limit(limit).all()
    
    def update(
        self,
        db: Session,
        *,
        db_obj: Centro,
        obj_in: CentroUpdate
    ) -> Centro:
        """Actualizar centro y sus relaciones (incluyendo imágenes)"""
        
        # Actualizar campos básicos del centro
        update_data = obj_in.dict(exclude={'ubicacion', 'telefonos', 'imagenes'}, exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        # Actualizar ubicación si se proporciona
        if obj_in.ubicacion:
            # (El código existente para ubicación no necesita cambios)
            ubicacion = db.query(Ubicacion).filter(Ubicacion.id == db_obj.ubicacion_id).first()
            if ubicacion:
                ubicacion.direccion = obj_in.ubicacion.direccion
                ubicacion.latitud = obj_in.ubicacion.latitud
                ubicacion.longitud = obj_in.ubicacion.longitud
        
        # Actualizar teléfonos si se proporcionan
        if obj_in.telefonos is not None:
            # (El código existente para teléfonos no necesita cambios)
            db.query(CentroAyudaTelefono).filter(CentroAyudaTelefono.centro_id == db_obj.id).delete()
            for telefono in obj_in.telefonos:
                tel = CentroAyudaTelefono(centro_id=db_obj.id, telefono=telefono)
                db.add(tel)

        # --- NUEVO: Actualizar imágenes ---
        # La estrategia es simple: borrar las viejas y crear las nuevas.
        if obj_in.imagenes is not None:
            # 1. Eliminar imágenes existentes
            db.query(CentroAyudaImagen).filter(CentroAyudaImagen.centro_id == db_obj.id).delete()
            
            # 2. Crear las nuevas imágenes a partir de la lista de URLs
            for url in obj_in.imagenes:
                img = CentroAyudaImagen(
                    centro_id=db_obj.id,
                    url_imagen=url
                )
                db.add(img)

        db.commit()
        db.refresh(db_obj)
        return self.get_with_details(db, id=db_obj.id)
    
    # --- (Las funciones delete, get_all_categorias y count_by_categoria no necesitan cambios) ---
    def delete(self, db: Session, *, id: UUID) -> bool:
        """Eliminar centro (cascade eliminará teléfonos e imágenes)"""
        centro = db.query(Centro).filter(Centro.id == id).first()
        
        if not centro:
            return False
        
        # Eliminar ubicación asociada
        if centro.ubicacion_id:
            db.query(Ubicacion).filter(
                Ubicacion.id == centro.ubicacion_id
            ).delete()
        
        # Eliminar centro (teléfonos e imágenes se eliminan por cascade)
        db.delete(centro)
        db.commit()
        return True
    
    def get_all_categorias(self, db: Session) -> List[CategoriasCentros]:
        """Obtener todas las categorías disponibles"""
        return db.query(CategoriasCentros).all()
    
    def count_by_categoria(self, db: Session) -> Dict[str, int]:
        """Contar centros por categoría"""
        result = {}
        categorias = self.get_all_categorias(db)
        
        for cat in categorias:
            count = db.query(Centro).filter(
                Centro.categoria_code == cat.id
            ).count()
            result[cat.id] = count
        
        return result

crud_centro = CRUDCentro()