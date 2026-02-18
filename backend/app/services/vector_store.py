import os
import logging
import chromadb
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from app.core.config import PERSIST_DIR

logger = logging.getLogger(__name__)

# Nombre de la colección y métrica de distancia.
# IMPORTANTE: Usar cosine porque BGE-M3 genera embeddings normalizados
# y LlamaIndex calcula scores con math.exp(-distance), fórmula diseñada
# para distancia coseno (rango 0-2), NO para L2 (rango 0-infinito).
# Con L2, los scores quedaban artificialmente bajos (~35-39%).
COLLECTION_NAME = "jurisprudencia"
COLLECTION_METADATA = {"hnsw:space": "cosine"}


def get_chroma_collection():
    """
    Obtiene la colección de ChromaDB para operaciones directas.

    Returns:
        chromadb.Collection: Colección de ChromaDB.
    """
    db = chromadb.PersistentClient(path=PERSIST_DIR)
    return db.get_or_create_collection(COLLECTION_NAME, metadata=COLLECTION_METADATA)


def delete_document_chunks(document_id: int) -> int:
    """
    Elimina todos los chunks de un documento del vector store.
    
    Args:
        document_id: ID del documento cuyos chunks se eliminarán.
        
    Returns:
        int: Número de chunks eliminados.
    """
    try:
        collection = get_chroma_collection()
        
        # Primero obtener los IDs de los chunks con este document_id
        results = collection.get(
            where={"document_id": document_id},
            include=[]  # Solo necesitamos los IDs
        )
        
        chunk_ids = results.get("ids", [])
        chunks_count = len(chunk_ids)
        
        if chunks_count > 0:
            # Eliminar los chunks por sus IDs
            collection.delete(ids=chunk_ids)
            logger.info(f"Eliminados {chunks_count} chunks del documento {document_id}")
        else:
            logger.info(f"No se encontraron chunks para el documento {document_id}")
        
        return chunks_count
        
    except Exception as e:
        logger.error(f"Error eliminando chunks del documento {document_id}: {str(e)}")
        raise


def cleanup_orphan_chunks(valid_document_ids: list) -> dict:
    """
    Elimina chunks huérfanos que pertenecen a documentos que ya no existen.
    
    Args:
        valid_document_ids: Lista de IDs de documentos que existen en la BD.
        
    Returns:
        dict: Información sobre los chunks eliminados.
    """
    try:
        collection = get_chroma_collection()
        
        # Obtener todos los document_ids únicos en ChromaDB
        all_results = collection.get(include=["metadatas"])
        
        orphan_doc_ids = set()
        orphan_chunk_ids = []
        
        for i, metadata in enumerate(all_results.get("metadatas", [])):
            if metadata:
                doc_id = metadata.get("document_id")
                if doc_id is not None and doc_id not in valid_document_ids:
                    orphan_doc_ids.add(doc_id)
                    orphan_chunk_ids.append(all_results["ids"][i])
        
        chunks_deleted = len(orphan_chunk_ids)
        
        if chunks_deleted > 0:
            collection.delete(ids=orphan_chunk_ids)
            logger.info(f"Limpieza: eliminados {chunks_deleted} chunks huérfanos de documentos {orphan_doc_ids}")
        else:
            logger.info("Limpieza: no se encontraron chunks huérfanos")
        
        return {
            "chunks_deleted": chunks_deleted,
            "orphan_document_ids": list(orphan_doc_ids)
        }
        
    except Exception as e:
        logger.error(f"Error limpiando chunks huérfanos: {str(e)}")
        raise


def ensure_cosine_collection():
    """
    Verifica que la colección use distancia coseno. Si usa L2 (default viejo),
    la elimina para que se recree con coseno en la próxima operación.

    Returns:
        bool: True si se migró (la colección fue eliminada), False si ya estaba bien.
    """
    try:
        db = chromadb.PersistentClient(path=PERSIST_DIR)
        existing_collections = db.list_collections()

        # Buscar nuestra colección
        for col in existing_collections:
            if col.name == COLLECTION_NAME:
                # Verificar la métrica actual
                metadata = col.metadata or {}
                space = metadata.get("hnsw:space", "l2")
                if space != "cosine":
                    logger.warning(
                        f"Colección '{COLLECTION_NAME}' usa métrica '{space}' "
                        f"(se requiere 'cosine'). Eliminando para recrear..."
                    )
                    db.delete_collection(COLLECTION_NAME)
                    # También limpiar docstore de LlamaIndex
                    docstore_path = os.path.join(PERSIST_DIR, "docstore.json")
                    if os.path.exists(docstore_path):
                        os.remove(docstore_path)
                        logger.info("docstore.json eliminado")
                    return True
                else:
                    logger.info(f"Colección '{COLLECTION_NAME}' ya usa métrica cosine")
                    return False

        # No existe, se creará con cosine al primer uso
        return False

    except Exception as e:
        logger.error(f"Error verificando métrica de colección: {str(e)}")
        return False


def get_index() -> VectorStoreIndex:
    """
    Obtiene o crea el índice vectorial con ChromaDB persistente.
    
    Returns:
        VectorStoreIndex: Índice vectorial listo para usar.
    
    Raises:
        Exception: Si hay error al conectar con ChromaDB o crear el índice.
    """
    try:
        # Conectar a ChromaDB persistente
        db = chromadb.PersistentClient(path=PERSIST_DIR)
        chroma_collection = db.get_or_create_collection(
            COLLECTION_NAME, metadata=COLLECTION_METADATA
        )
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        # Verificar si existe docstore.json (indica que LlamaIndex ya persistió el índice)
        docstore_path = os.path.join(PERSIST_DIR, "docstore.json")
        
        if os.path.exists(docstore_path):
            # Cargar índice existente con todos los componentes persistidos
            logger.info(f"Cargando índice existente desde {PERSIST_DIR}")
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=PERSIST_DIR
            )
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context
            )
        else:
            # Crear índice nuevo (ChromaDB puede existir pero sin docstore de LlamaIndex)
            logger.info(f"Creando nuevo índice en {PERSIST_DIR}")
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_documents(
                [], 
                storage_context=storage_context
            )
            # Persistir para crear docstore.json y otros archivos de LlamaIndex
            storage_context.persist(persist_dir=PERSIST_DIR)
            logger.info(f"Índice inicializado y persistido en {PERSIST_DIR}")
        
        return index
        
    except Exception as e:
        logger.error(f"Error al obtener índice: {str(e)}")
        raise
