from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.centro import (
    CentroCreate, 
    CentroUpdate, 
    CentroWithDetails, 
    CentroListResponse,
    CategoriaOut
)
from app.crud.crud_centro import crud_centro

router = APIRouter()

# Función helper para verificar si es admin
def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Verificar que el usuario sea administrador"""
    admin_emails = ["admin@acompanar.com", "admin@example.com", "jorgeluisres@gmail.com"]
    
    if current_user.email not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    return current_user

@router.get("/", response_model=CentroListResponse)
def get_centros(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    categoria: Optional[str] = None,
    search: Optional[str] = None
):
    """Obtener lista de centros con filtros (público)"""
    centros = crud_centro.get_multi_with_details(
        db, 
        skip=skip, 
        limit=limit,
        categoria_code=categoria,
        search=search
    )
    
    return CentroListResponse(
        centros=centros,
        total=len(centros),
        page=(skip // limit) + 1,
        per_page=limit
    )

@router.get("/categorias", response_model=List[CategoriaOut])
def get_categorias(db: Session = Depends(get_db)):
    """Obtener todas las categorías disponibles"""
    return crud_centro.get_all_categorias(db)

@router.get("/stats")
def get_centro_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Obtener estadísticas de centros (solo admin)"""
    stats = crud_centro.count_by_categoria(db)
    total = sum(stats.values())
    
    return {
        "total_centros": total,
        "por_categoria": stats
    }
#búsqueda por proximidad
@router.get("/cercanos", response_model=List[CentroWithDetails])
def get_centros_cercanos(
    db: Session = Depends(get_db),
    # 1. Cambiamos de float obligatorio a str opcional para soportar los nulos de n8n
    lat: Optional[str] = Query(None, description="Latitud"),
    lon: Optional[str] = Query(None, description="Longitud"),
    radius: float = Query(10, ge=1, le=100, description="Radio en kilómetros"),
    limit: int = Query(20, ge=1, le=50)
):
    """Obtener centros cercanos a una ubicación"""
    
    # 2. Atrapamos cualquier formato vacío o nulo que envíe n8n si el GPS estaba apagado
    if not lat or not lon or lat.lower() == "null" or lon.lower() == "null" or lat == "" or lon == "":
        return [] # Devolvemos lista vacía para que LangChain/n8n no colapse
        
    try:
        # 3. Convertimos a número flotante de forma segura
        lat_float = float(lat)
        lon_float = float(lon)
    except ValueError:
        return [] # Si llega basura en el texto, también devolvemos vacío

    # 4. Buscamos normalmente en la base de datos
    centros = crud_centro.get_by_proximity(
        db, 
        lat=lat_float, 
        lon=lon_float, 
        radius_km=radius,
        limit=limit
    )
    return centros
# Endpoint para obtener detalles de un centro específico
@router.get("/{centro_id}", response_model=CentroWithDetails)
def get_centro(
    centro_id: UUID,
    db: Session = Depends(get_db)
):
    """Obtener información detallada de un centro"""
    centro = crud_centro.get_with_details(db, id=centro_id)
    if not centro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Centro no encontrado"
        )
    return centro

@router.post("/", response_model=CentroWithDetails, status_code=status.HTTP_201_CREATED)
def create_centro(
    *,
    db: Session = Depends(get_db),
    centro_in: CentroCreate,
    admin: User = Depends(get_admin_user)
):
    """Crear nuevo centro (solo admin)"""
    try:
        centro = crud_centro.create_with_details(db, obj_in=centro_in)
        return centro
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al crear centro: {str(e)}"
        )

@router.put("/{centro_id}", response_model=CentroWithDetails)
def update_centro(
    *,
    db: Session = Depends(get_db),
    centro_id: UUID,
    centro_in: CentroUpdate,
    admin: User = Depends(get_admin_user)
):
    """Actualizar centro existente (solo admin)"""
    centro = crud_centro.get(db, id=centro_id)
    if not centro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Centro no encontrado"
        )
    
    try:
        centro = crud_centro.update(db, db_obj=centro, obj_in=centro_in)
        return centro
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al actualizar centro: {str(e)}"
        )

@router.delete("/{centro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_centro(
    *,
    db: Session = Depends(get_db),
    centro_id: UUID,
    admin: User = Depends(get_admin_user)
):
    """Eliminar un centro (solo admin)"""
    success = crud_centro.delete(db, id=centro_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Centro no encontrado"
        )
    return {"message": "Centro eliminado exitosamente"}

# Endpoint para registrar que un usuario consultó un centro (para estadísticas de popularidad)
@router.post("/{centro_id}/view", status_code=status.HTTP_204_NO_CONTENT)
def register_centro_view(
    *,
    db: Session = Depends(get_db),
    centro_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Registrar que un usuario consultó un centro"""
    centro = crud_centro.get(db, id=centro_id)
    if not centro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Centro no encontrado"
        )
    
    crud_centro.register_view(db, centro_id=centro_id, user_id=current_user.id)
    return None

@router.get("/populares", response_model=List[CentroWithDetails])
def get_centros_populares(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """Obtener los centros más consultados"""
    centros = crud_centro.get_populares(db, limit=limit)
    return centros
