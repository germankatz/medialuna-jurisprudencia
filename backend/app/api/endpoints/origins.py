"""
Endpoint para gestión de orígenes de documentos.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import Optional

from app.db.database import get_db
from app.db.models import Origen, Document
from app.schemas.origin import OrigenResponse, OrigenListResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class OrigenCreate(BaseModel):
    """Schema para crear un origen."""
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=255)
    abreviacion: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$')


class OrigenUpdate(BaseModel):
    """Schema para actualizar un origen."""
    codigo: Optional[str] = Field(None, min_length=1, max_length=20)
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    abreviacion: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    activo: Optional[bool] = None


@router.get("", response_model=OrigenListResponse)
async def get_origins(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene la lista de orígenes.

    Args:
        include_inactive: Si es True, incluye orígenes inactivos.

    Returns:
        OrigenListResponse: Lista de orígenes.
    """
    query = select(Origen)
    if not include_inactive:
        query = query.where(Origen.activo == True)
    query = query.order_by(Origen.nombre)

    result = await db.execute(query)
    origenes = result.scalars().all()

    return OrigenListResponse(
        origins=[OrigenResponse.model_validate(o) for o in origenes]
    )


@router.get("/{origen_id}", response_model=OrigenResponse)
async def get_origin(
    origen_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene un origen por su ID.

    Args:
        origen_id: ID del origen.

    Returns:
        OrigenResponse: Datos del origen.
    """
    result = await db.execute(
        select(Origen).where(Origen.id == origen_id)
    )
    origen = result.scalar_one_or_none()

    if not origen:
        raise HTTPException(status_code=404, detail="Origen no encontrado")

    return OrigenResponse.model_validate(origen)


@router.post("", response_model=OrigenResponse)
async def create_origin(
    data: OrigenCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo origen.

    Args:
        data: Datos del origen a crear.

    Returns:
        OrigenResponse: Origen creado.
    """
    # Verificar que el código no exista
    existing = await db.execute(
        select(Origen).where(Origen.codigo == data.codigo)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un origen con el código '{data.codigo}'"
        )

    origen = Origen(
        codigo=data.codigo,
        nombre=data.nombre,
        abreviacion=data.abreviacion,
        color=data.color,
        activo=True
    )

    db.add(origen)
    await db.commit()
    await db.refresh(origen)

    logger.info(f"Origen creado: {origen.codigo}")

    return OrigenResponse.model_validate(origen)


@router.put("/{origen_id}", response_model=OrigenResponse)
async def update_origin(
    origen_id: int,
    data: OrigenUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza un origen existente.

    Args:
        origen_id: ID del origen a actualizar.
        data: Datos a actualizar.

    Returns:
        OrigenResponse: Origen actualizado.
    """
    result = await db.execute(
        select(Origen).where(Origen.id == origen_id)
    )
    origen = result.scalar_one_or_none()

    if not origen:
        raise HTTPException(status_code=404, detail="Origen no encontrado")

    # Verificar código único si se está cambiando
    if data.codigo and data.codigo != origen.codigo:
        existing = await db.execute(
            select(Origen).where(Origen.codigo == data.codigo)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un origen con el código '{data.codigo}'"
            )

    # Actualizar campos proporcionados
    if data.codigo is not None:
        origen.codigo = data.codigo
    if data.nombre is not None:
        origen.nombre = data.nombre
    if data.abreviacion is not None:
        origen.abreviacion = data.abreviacion
    if data.color is not None:
        origen.color = data.color
    if data.activo is not None:
        origen.activo = data.activo

    await db.commit()
    await db.refresh(origen)

    logger.info(f"Origen actualizado: {origen.codigo}")

    return OrigenResponse.model_validate(origen)


@router.delete("/{origen_id}")
async def delete_origin(
    origen_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un origen (solo si no tiene documentos asociados).

    Args:
        origen_id: ID del origen a eliminar.

    Returns:
        dict: Confirmación de eliminación.
    """
    result = await db.execute(
        select(Origen).where(Origen.id == origen_id)
    )
    origen = result.scalar_one_or_none()

    if not origen:
        raise HTTPException(status_code=404, detail="Origen no encontrado")

    # Verificar si tiene documentos asociados
    doc_count = await db.execute(
        select(func.count()).select_from(Document).where(Document.origen_id == origen_id)
    )
    count = doc_count.scalar() or 0

    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {count} documento(s) asociado(s). Desactívelo en su lugar."
        )

    await db.delete(origen)
    await db.commit()

    logger.info(f"Origen eliminado: {origen.codigo}")

    return {"message": "Origen eliminado correctamente", "id": origen_id}
