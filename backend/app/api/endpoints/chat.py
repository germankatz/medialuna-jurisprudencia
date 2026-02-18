import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from llama_index.core.postprocessor import SimilarityPostprocessor

from app.services.vector_store import get_index
from app.db.database import get_db
from app.db.models import Document

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Configuración RAG ---
# Cantidad de chunks a recuperar del vector store por consulta.
# Con documentos legales extensos, 10 chunks proveen contexto suficiente
# sin saturar la ventana de contexto del LLM.
SIMILARITY_TOP_K = 10

# Umbral mínimo de relevancia para que un chunk llegue al LLM.
# Se aplica ANTES de la generación, no después. Chunks por debajo
# de este score se descartan y el LLM nunca los ve.
# Con distancia coseno + math.exp(-d), documentos relevantes dan ~0.60-0.95.
MIN_RELEVANCE_THRESHOLD = 0.55

# Umbral para mostrar fuentes en la UI. Más alto que el del LLM
# para que solo se muestren documentos con relevancia clara.
MIN_SOURCE_DISPLAY_THRESHOLD = 0.60

# Frases que indican que el LLM no encontró información suficiente.
# Si la respuesta contiene alguna de estas, no se adjuntan fuentes.
NO_INFO_PHRASES = [
    "no encontré información",
    "no encontre informacion",
    "no cuento con información",
    "no cuento con informacion",
    "no hay información suficiente",
    "no hay informacion suficiente",
    "no dispongo de información",
    "no se encuentra en los documentos",
    "no se encuentra en el contexto",
]

# --- System prompt ---
# Diseñado para: (1) anclar respuestas al contexto, (2) prevenir alucinaciones,
# (3) mantener respuestas en español, (4) dar instrucciones claras sobre qué
# hacer cuando no hay información suficiente.
SYSTEM_PROMPT = """\
Eres un asistente experto en jurisprudencia argentina.

REGLAS ESTRICTAS:
1. Respondé ÚNICAMENTE basándote en el contexto proporcionado. No inventes, supongas ni completes información que no esté en los documentos.
2. Si la información no está en el contexto o es insuficiente para responder, decilo explícitamente: "No encontré información suficiente en los documentos cargados para responder esta pregunta."
3. Siempre respondé en español, sin importar el idioma de la pregunta.
4. Cuando cites información de los documentos, indicá de qué documento proviene si es posible.
5. Sé preciso y profesional. En materia jurídica, la exactitud es fundamental: no parafrasees normas ni holdings de manera que altere su sentido.
6. Si una pregunta es ambigua, pedí aclaración antes de responder.
"""

# Template de contexto en español (reemplaza el default en inglés de LlamaIndex)
CONTEXT_TEMPLATE = """\
A continuación se presenta información de contexto extraída de documentos jurídicos relevantes.
--------------------
{context_str}
--------------------
Utilizá esta información de contexto para responder la consulta del usuario. \
Si la respuesta no se encuentra en el contexto, indicalo explícitamente.\
"""


# --- Modelos de request/response ---

class MessageItem(BaseModel):
    """Un mensaje individual del historial de conversación."""
    role: str  # 'user' o 'assistant'
    content: str


class ChatRequest(BaseModel):
    """Modelo de solicitud de chat."""
    query: str
    history: Optional[List[MessageItem]] = None


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


# --- Endpoint ---

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Endpoint de chat usando RAG con contexto.

    Utiliza el índice vectorial para recuperar contexto relevante
    y genera respuestas con el LLM configurado (Ollama).

    Soporta historial de conversación enviado desde el frontend
    para mantener coherencia entre turnos.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")

    try:
        logger.info(f"Procesando consulta: {request.query[:100]}...")

        # Obtener índice vectorial
        index = get_index()

        # Crear chat engine con:
        # - similarity_top_k=10: recuperar 10 chunks (no 2)
        # - SimilarityPostprocessor: filtrar chunks irrelevantes ANTES del LLM
        # - context_template en español
        # - system_prompt con instrucciones anti-alucinación
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            system_prompt=SYSTEM_PROMPT,
            context_template=CONTEXT_TEMPLATE,
            similarity_top_k=SIMILARITY_TOP_K,
            node_postprocessors=[
                SimilarityPostprocessor(similarity_cutoff=MIN_RELEVANCE_THRESHOLD)
            ],
        )

        # Construir mensajes previos del historial (si los hay) para dar
        # continuidad a la conversación. LlamaIndex ContextChatEngine
        # acepta chat_history como parámetro.
        from llama_index.core.llms import ChatMessage, MessageRole

        chat_history = []
        if request.history:
            for msg in request.history:
                role = MessageRole.USER if msg.role == "user" else MessageRole.ASSISTANT
                chat_history.append(ChatMessage(role=role, content=msg.content))

        # Ejecutar consulta con historial
        if chat_history:
            response = chat_engine.chat(request.query, chat_history=chat_history)
        else:
            response = chat_engine.chat(request.query)

        # Manejar respuesta vacía (puede pasar si el postprocessor filtra
        # todos los chunks y el synthesizer no tiene contexto para generar)
        response_text = str(response).strip()
        if not response_text or response_text.lower() == "empty response":
            response_text = "No encontré información suficiente en los documentos cargados para responder esta pregunta."
            logger.warning("Respuesta vacía del LLM - posiblemente todos los chunks fueron filtrados por baja relevancia")
        response_lower = response_text.lower()
        llm_found_no_info = any(phrase in response_lower for phrase in NO_INFO_PHRASES)

        # Extraer fuentes, deduplicando por document_id y quedándose con el mejor score
        best_chunks: Dict[int, tuple] = {}

        if not llm_found_no_info and hasattr(response, 'source_nodes') and response.source_nodes:
            for node in response.source_nodes:
                score = getattr(node, 'score', 0) or 0
                # Solo incluir fuentes que superen el umbral de display
                if score < MIN_SOURCE_DISPLAY_THRESHOLD:
                    continue
                doc_id = node.metadata.get('document_id') if hasattr(node, 'metadata') else None
                if doc_id:
                    if doc_id not in best_chunks or score > best_chunks[doc_id][1]:
                        best_chunks[doc_id] = (node, score)

        # Obtener información de documentos de la BD
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
            document_info = {
                doc.id: {
                    'name': doc.caratula or doc.name,
                    'origen': doc.origen
                }
                for doc in documents
            }

        # Construir lista de fuentes
        sources = []
        for doc_id, (node, score) in best_chunks.items():
            doc_data = document_info.get(doc_id, {})
            doc_name = doc_data.get('name') if isinstance(doc_data, dict) else doc_data
            doc_origen = doc_data.get('origen') if isinstance(doc_data, dict) else None

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

        if llm_found_no_info:
            logger.info("LLM indicó que no encontró información - fuentes suprimidas")
        else:
            logger.info(f"Respuesta generada con {len(sources)} fuentes (de {len(response.source_nodes) if hasattr(response, 'source_nodes') and response.source_nodes else 0} chunks recuperados)")

        return ChatResponse(
            response=response_text,
            sources=sources,
        )

    except Exception as e:
        logger.error(f"Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")
