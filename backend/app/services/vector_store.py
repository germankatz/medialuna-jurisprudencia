import os
import logging
import chromadb
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from app.core.config import PERSIST_DIR

logger = logging.getLogger(__name__)

# Variable global para almacenar el cliente de ChromaDB (Singleton)
_chroma_client = None


def get_chroma_client():
    """
    Obtiene o crea el cliente persistente de ChromaDB como Singleton.

    Returns:
        chromadb.PersistentClient: Cliente de ChromaDB.
    """
    global _chroma_client
    if _chroma_client is None:
        logger.info(f"Inicializando cliente ChromaDB en {PERSIST_DIR}")
        _chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
    return _chroma_client


def get_chroma_collection():
    """
    Obtiene la colección de ChromaDB para operaciones directas.
    
    Returns:
        chromadb.Collection: Colección de ChromaDB.
    """
    db = get_chroma_client()
    return db.get_or_create_collection("jurisprudencia")


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


def get_index() -> VectorStoreIndex:
    """
    Obtiene o crea el índice vectorial con ChromaDB persistente.
    
    Returns:
        VectorStoreIndex: Índice vectorial listo para usar.
    
    Raises:
        Exception: Si hay error al conectar con ChromaDB o crear el índice.
    """
    try:
        # Obtener colección usando el cliente singleton
        chroma_collection = get_chroma_collection()
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
