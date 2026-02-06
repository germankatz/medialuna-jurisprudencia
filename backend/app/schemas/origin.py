"""
Schemas Pydantic para orígenes de documentos.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OrigenResponse(BaseModel):
    """
    Schema para respuesta de un origen.

    Expone los campos necesarios para el frontend.
    """
    id: int = Field(..., description="ID único del origen")
    codigo: str = Field(..., description="Código corto del origen")
    nombre: str = Field(..., description="Nombre completo del origen")
    abreviacion: str = Field(..., description="Abreviación para mostrar")
    color: str = Field(..., description="Color hexadecimal (#RRGGBB)")
    activo: bool = Field(True, description="Si el origen está activo")

    model_config = {"from_attributes": True}


class OrigenListResponse(BaseModel):
    """
    Schema para listado de orígenes.
    """
    origins: list[OrigenResponse] = Field(default_factory=list)


class ClassifyRequest(BaseModel):
    """
    Schema para solicitud de clasificación de una carátula.
    """
    caratula: str = Field(..., min_length=1, description="Carátula a clasificar")


class ClassifyResponse(BaseModel):
    """
    Schema para respuesta de clasificación.
    """
    origen_codigo: str = Field(..., description="Código del origen sugerido")
    origen_id: int = Field(..., description="ID del origen sugerido")
    confianza: Optional[float] = Field(None, description="Nivel de confianza (0-1)")


class ClassifyBatchRequest(BaseModel):
    """
    Schema para clasificación por lotes.
    """
    items: list[dict] = Field(..., description="Lista de {id, caratula}")


class ClassifyBatchResponse(BaseModel):
    """
    Schema para respuesta de clasificación por lotes.
    """
    results: list[dict] = Field(..., description="Lista de {id, origen_codigo, origen_id}")
