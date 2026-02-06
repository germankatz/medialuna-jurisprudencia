"""
Endpoint para clasificación de documentos por origen usando IA.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from llama_index.core import Settings

from app.db.database import get_db
from app.db.models import Origen
from app.schemas.origin import (
    ClassifyRequest,
    ClassifyResponse,
    ClassifyBatchRequest,
    ClassifyBatchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Prompt para clasificación de documentos jurídicos
CLASSIFY_PROMPT = """Eres un asistente especializado en clasificar documentos jurídicos argentinos.

Dada la siguiente carátula de un documento jurídico, clasifícalo en UNA de las siguientes categorías:

CATEGORÍAS DISPONIBLES:
- cfcp: Sentencias de la Cámara Federal de Casación Penal
- civ_para: Sentencias civiles de la Cámara Federal de Paraná
- csjn_civ: Sentencias de la Corte Suprema de Justicia de la Nación - materia CIVIL
- csjn_pen: Sentencias de la Corte Suprema de Justicia de la Nación - materia PENAL
- pen_para: Sentencias penales de la Cámara Federal de Paraná
- sin_clasificar: Si no puedes determinar la categoría con certeza

INSTRUCCIONES:
1. Analiza el texto de la carátula buscando indicadores de jurisdicción y materia
2. Busca menciones a tribunales (CSJN, Cámara Federal, etc.)
3. Identifica la materia (civil, penal, laboral, etc.)
4. Si hay ambigüedad o no hay información suficiente, usa "sin_clasificar"

CARÁTULA A CLASIFICAR:
{caratula}

Responde ÚNICAMENTE con el código de la categoría (ej: cfcp, csjn_civ, sin_clasificar).
No agregues explicaciones ni texto adicional."""


async def get_origenes_map(db: AsyncSession) -> dict:
    """Obtiene un mapeo de código -> id de orígenes."""
    result = await db.execute(select(Origen).where(Origen.activo == True))
    origenes = result.scalars().all()
    return {o.codigo: o.id for o in origenes}


async def classify_caratula(caratula: str, origenes_map: dict) -> tuple[str, int]:
    """
    Clasifica una carátula usando el LLM.

    Args:
        caratula: Texto de la carátula a clasificar.
        origenes_map: Mapeo de código -> id de orígenes.

    Returns:
        tuple: (codigo_origen, id_origen)
    """
    try:
        prompt = CLASSIFY_PROMPT.format(caratula=caratula)
        response = await Settings.llm.acomplete(prompt)

        # Extraer código de la respuesta (limpiar espacios y convertir a minúsculas)
        codigo = response.text.strip().lower()

        # Validar que el código existe
        if codigo in origenes_map:
            return codigo, origenes_map[codigo]

        # Si el LLM devolvió algo inválido, usar sin_clasificar
        logger.warning(f"LLM devolvió código inválido: {codigo}")
        return 'sin_clasificar', origenes_map.get('sin_clasificar', 0)

    except Exception as e:
        logger.error(f"Error clasificando carátula: {str(e)}")
        return 'sin_clasificar', origenes_map.get('sin_clasificar', 0)


@router.post("/single", response_model=ClassifyResponse)
async def classify_single(
    request: ClassifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Clasifica una única carátula usando IA.

    Args:
        request: Solicitud con la carátula a clasificar.
        db: Sesión de base de datos.

    Returns:
        ClassifyResponse: Origen sugerido.
    """
    origenes_map = await get_origenes_map(db)

    if not origenes_map:
        raise HTTPException(
            status_code=500,
            detail="No hay orígenes configurados en el sistema"
        )

    codigo, origen_id = await classify_caratula(request.caratula, origenes_map)

    return ClassifyResponse(
        origen_codigo=codigo,
        origen_id=origen_id,
        confianza=None  # Por ahora no calculamos confianza
    )


@router.post("/batch", response_model=ClassifyBatchResponse)
async def classify_batch(
    request: ClassifyBatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Clasifica múltiples carátulas usando IA.

    Args:
        request: Solicitud con lista de items {id, caratula}.
        db: Sesión de base de datos.

    Returns:
        ClassifyBatchResponse: Lista de resultados.
    """
    origenes_map = await get_origenes_map(db)

    if not origenes_map:
        raise HTTPException(
            status_code=500,
            detail="No hay orígenes configurados en el sistema"
        )

    results = []
    for item in request.items:
        item_id = item.get('id')
        caratula = item.get('caratula', '')

        if not caratula:
            # Sin carátula, usar sin_clasificar
            codigo = 'sin_clasificar'
            origen_id = origenes_map.get('sin_clasificar', 0)
        else:
            codigo, origen_id = await classify_caratula(caratula, origenes_map)

        results.append({
            'id': item_id,
            'origen_codigo': codigo,
            'origen_id': origen_id
        })

    return ClassifyBatchResponse(results=results)
