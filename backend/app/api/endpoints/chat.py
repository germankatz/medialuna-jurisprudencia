import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sqlalchemy.orm import selectinload

from app.services.vector_store import get_index
from app.db.database import get_db
from app.db.models import Document, Origen

logger = logging.getLogger(__name__)

router = APIRouter()

# Umbral mínimo de relevancia para mostrar documentos relacionados (0.35 = 35%)
# Nota: Con embeddings BAAI/bge-m3, scores >= 0.35 indican relevancia semántica significativa
# Scores menores a 0.35 suelen ser coincidencias genéricas sin relación real con la consulta
MIN_RELEVANCE_THRESHOLD = 0.35


class ChatRequest(BaseModel):
    """Modelo de solicitud de chat."""
    query: str


class OrigenInfo(BaseModel):
    """Información del origen de un documento."""
    id: int
    codigo: str
    abreviacion: str
    color: str


class SourceInfo(BaseModel):
    """Información de una fuente citada."""
    text: str
    score: Optional[float] = None
    document_id: Optional[int] = None
    document_name: Optional[str] = None
    origen: Optional[OrigenInfo] = None


class ChatResponse(BaseModel):
    """Modelo de respuesta de chat."""
    response: str
    sources: List[SourceInfo] = []


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Endpoint de chat usando RAG con contexto.
    
    Utiliza el índice vectorial para recuperar contexto relevante
    y genera respuestas con el LLM configurado (Ollama llama3).
    
    Args:
        request: Solicitud con la consulta del usuario.
        db: Sesión de base de datos.
        
    Returns:
        ChatResponse: Respuesta generada y fuentes utilizadas.
        
    Raises:
        HTTPException: Si hay error en el procesamiento.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")
    
    try:
        logger.info("Procesando consulta...")
        
        # Obtener índice y crear chat engine en modo context
        index = get_index()
        
        # System prompt para asegurar respuestas en español
        system_prompt = """Eres un asistente experto en jurisprudencia argentina. 
IMPORTANTE: Siempre debes responder en español, sin importar el idioma en que te pregunten.
Tu rol es ayudar a los usuarios a entender documentos legales, fallos judiciales y normativas.
Responde de forma clara, precisa y profesional. Si citas fuentes, hazlo de manera ordenada."""
        
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            system_prompt=system_prompt
        )
        
        # Ejecutar consulta
        response = chat_engine.chat(request.query)
        
        # Extraer fuentes si existen, deduplicando por document_id y filtrando por relevancia
        sources = []
        best_chunks = {}  # {document_id: (node, score)} - mantener solo el mejor chunk por documento
        
        # Agrupar por document_id, manteniendo el chunk con mejor score
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for node in response.source_nodes:
                score = getattr(node, 'score', 0) or 0
                
                # Filtrar por umbral de relevancia
                if score < MIN_RELEVANCE_THRESHOLD:
                    logger.debug(f"Descartando chunk con score {score:.4f} (umbral: {MIN_RELEVANCE_THRESHOLD})")
                    continue
                
                doc_id = node.metadata.get('document_id') if hasattr(node, 'metadata') else None
                if doc_id:
                    # Solo mantener el chunk con mejor score por documento
                    if doc_id not in best_chunks or score > best_chunks[doc_id][1]:
                        best_chunks[doc_id] = (node, score)
        
        # Obtener información de documentos de la BD (carátula, nombre y origen)
        document_info = {}
        document_ids_to_fetch = set(best_chunks.keys())
        if document_ids_to_fetch:
            query = (
                select(Document)
                .options(selectinload(Document.origen))
                .where(Document.id.in_(list(document_ids_to_fetch)))
            )
            result = await db.execute(query)
            documents = result.scalars().all()
            # Almacenar nombre y origen
            document_info = {
                doc.id: {
                    'name': doc.caratula or doc.name,
                    'origen': doc.origen
                }
                for doc in documents
            }
        
        # Construir lista de fuentes desde los chunks deduplicados
        for doc_id, (node, score) in best_chunks.items():
            doc_data = document_info.get(doc_id, {})
            doc_name = doc_data.get('name') if isinstance(doc_data, dict) else doc_data
            doc_origen = doc_data.get('origen') if isinstance(doc_data, dict) else None

            # Construir info de origen si existe
            origen_info = None
            if doc_origen:
                origen_info = OrigenInfo(
                    id=doc_origen.id,
                    codigo=doc_origen.codigo,
                    abreviacion=doc_origen.abreviacion,
                    color=doc_origen.color
                )

            source_info = SourceInfo(
                text=node.text[:200] + "..." if len(node.text) > 200 else node.text,
                score=score,
                document_id=doc_id,
                document_name=doc_name,
                origen=origen_info
            )
            sources.append(source_info)
        
        # Ordenar por score descendente
        sources.sort(key=lambda x: x.score or 0, reverse=True)
        
        logger.info(f"Respuesta generada con {len(sources)} fuentes")
        
        return ChatResponse(
            response=str(response),
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")
