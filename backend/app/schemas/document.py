"""
Schemas Pydantic para documentos.

Principio ISP: Schemas separados para diferentes operaciones
(crear, respuesta, listado) para no exponer campos innecesarios.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.origin import OrigenResponse


class DocumentBase(BaseModel):
    """Schema base con campos comunes."""
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del documento")


class DocumentCreate(DocumentBase):
    """
    Schema para crear un documento.
    
    Se usa internamente al procesar el upload.
    """
    original_filename: str = Field(..., description="Nombre original del archivo")
    file_path: str = Field(..., description="Ruta al archivo en el sistema")
    file_size: Optional[int] = Field(None, description="Tamaño en bytes")
    chunks_count: int = Field(default=0, description="Cantidad de chunks creados")


class DocumentResponse(BaseModel):
    """
    Schema para respuesta de un documento individual.

    Expone solo los campos necesarios para el frontend.
    """
    id: int = Field(..., description="ID único del documento")
    name: str = Field(..., description="Nombre del documento")
    caratula: Optional[str] = Field(None, description="Carátula extraída del documento")
    search_content: Optional[str] = Field(None, description="Contenido procesado para búsqueda tradicional")
    original_filename: str = Field(..., description="Nombre original del archivo")
    file_size: Optional[int] = Field(None, description="Tamaño en bytes")
    chunks_count: int = Field(..., description="Cantidad de chunks indexados")
    origen: Optional[OrigenResponse] = Field(None, description="Origen/categoría del documento")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """
    Schema para listado de documentos.
    
    Incluye metadatos de paginación para futuras mejoras.
    """
    documents: List[DocumentResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total de documentos")


class DocumentUploadResponse(BaseModel):
    """
    Schema para respuesta de upload exitoso.
    """
    id: int = Field(..., description="ID del documento creado")
    filename: str = Field(..., description="Nombre del archivo")
    status: str = Field(..., description="Estado del procesamiento")
    chunks_created: int = Field(..., description="Cantidad de chunks creados")


class DocumentUpdateOrigen(BaseModel):
    """
    Schema para actualizar el origen de un documento.
    """
    origen_id: int = Field(..., description="ID del nuevo origen")
