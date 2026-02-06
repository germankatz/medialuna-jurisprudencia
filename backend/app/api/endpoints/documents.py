"""
Endpoints para gestión de documentos.

Principio SRP: Este router solo maneja operaciones CRUD de documentos.
El procesamiento (indexación) se delega al servicio de ingest.
"""
import os
import logging
import unicodedata
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Document, Origen
from app.schemas.document import DocumentResponse, DocumentListResponse, DocumentUpdateOrigen
from app.services.vector_store import delete_document_chunks, cleanup_orphan_chunks
from app.services.content_extractor import ContentExtractor
from app.core.config import PERSIST_DIR, UPLOAD_DIR
from llama_index.core import SimpleDirectoryReader

logger = logging.getLogger(__name__)

router = APIRouter()


def normalize_text(text: str) -> str:
    """
    Normaliza texto removiendo acentos/tildes y convirtiendo a minúsculas.
    
    Ejemplos:
        - "Rocío" -> "rocio"
        - "María José" -> "maria jose"
        - "ÑOÑO" -> "nono"
    """
    if not text:
        return ""
    # Descomponer caracteres unicode (ej: é -> e + acento combinante)
    normalized = unicodedata.normalize('NFD', text)
    # Remover marcas de combinación (acentos, tildes, etc.)
    without_accents = ''.join(
        char for char in normalized 
        if unicodedata.category(char) != 'Mn'
    )
    return without_accents.lower()


def create_unaccent_expression(column):
    """
    Crea una expresión SQL para normalizar texto en PostgreSQL.
    Usa translate() para reemplazar caracteres acentuados por sus equivalentes sin acento.
    """
    # Mapeo de caracteres acentuados a sin acento
    accented = "áéíóúàèìòùäëïöüâêîôûãõñÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÂÊÎÔÛÃÕÑ"
    unaccented = "aeiouaeiouaeiouaeiouaonAEIOUAEIOUAEIOUAEIOUAON"
    
    return func.lower(func.translate(column, accented, unaccented))


@router.get("/search", response_model=DocumentListResponse)
async def search_documents(
    q: str,
    skip: int = 0,
    limit: int = 50,
    origen_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Busca documentos por texto en nombre, carátula y contenido buscable.

    Características:
    - Ignora tildes/acentos (ej: "rocio" encuentra "Rocío")
    - Busca TODAS las palabras individualmente (ej: "rocio miguel" encuentra
      documentos que contengan ambas palabras aunque no estén juntas)
    - Case-insensitive
    - Filtrado opcional por origen

    Args:
        q: Texto a buscar (mínimo 2 caracteres).
        skip: Cantidad de documentos a saltar (offset).
        limit: Cantidad máxima de documentos a retornar (max 50).
        origen_id: ID del origen para filtrar (opcional).
        db: Sesión de base de datos.

    Returns:
        DocumentListResponse: Lista de documentos que coinciden.
    """
    if len(q.strip()) < 2:
        raise HTTPException(
            status_code=400, 
            detail="La búsqueda debe tener al menos 2 caracteres"
        )
    
    try:
        # Normalizar el término de búsqueda y dividir en palabras
        normalized_query = normalize_text(q)
        words = [word.strip() for word in normalized_query.split() if len(word.strip()) >= 2]
        
        if not words:
            raise HTTPException(
                status_code=400, 
                detail="La búsqueda debe contener al menos una palabra de 2+ caracteres"
            )
        
        # Crear condiciones: cada palabra debe estar en al menos uno de los campos
        word_conditions = []
        for word in words:
            search_term = f"%{word}%"
            # Cada palabra debe encontrarse en alguno de los campos (OR entre campos)
            word_condition = or_(
                create_unaccent_expression(Document.name).like(search_term),
                create_unaccent_expression(Document.caratula).like(search_term),
                create_unaccent_expression(Document.search_content).like(search_term),
                create_unaccent_expression(Document.original_filename).like(search_term)
            )
            word_conditions.append(word_condition)
        
        # TODAS las palabras deben estar presentes (AND entre palabras)
        combined_condition = and_(*word_conditions) if len(word_conditions) > 1 else word_conditions[0]

        # Agregar filtro por origen si se especificó
        if origen_id is not None:
            combined_condition = and_(combined_condition, Document.origen_id == origen_id)

        # Query base con la condición combinada
        base_query = select(Document).where(combined_condition)
        
        # Obtener total de resultados
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Obtener documentos con origen
        query = (
            base_query
            .options(selectinload(Document.origen))
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(min(limit, 50))  # Limitar a 50 máximo
        )
        result = await db.execute(query)
        documents = result.scalars().all()

        logger.info(f"Búsqueda '{q}' (palabras: {words}): {total} resultados encontrados")
        
        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en búsqueda de documentos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al buscar documentos")


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos los documentos con paginación opcional.
    
    Args:
        skip: Cantidad de documentos a saltar (offset).
        limit: Cantidad máxima de documentos a retornar.
        db: Sesión de base de datos.
        
    Returns:
        DocumentListResponse: Lista de documentos y total.
    """
    try:
        # Obtener total
        count_query = select(func.count()).select_from(Document)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Obtener documentos ordenados por fecha de creación (más recientes primero)
        query = (
            select(Document)
            .options(selectinload(Document.origen))
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        documents = result.scalars().all()

        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total
        )
    except Exception as e:
        logger.error(f"Error listando documentos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener documentos")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene un documento por su ID.
    
    Args:
        document_id: ID del documento.
        db: Sesión de base de datos.
        
    Returns:
        DocumentResponse: Datos del documento.
        
    Raises:
        HTTPException: 404 si no existe el documento.
    """
    query = (
        select(Document)
        .options(selectinload(Document.origen))
        .where(Document.id == document_id)
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return DocumentResponse.model_validate(document)


@router.put("/{document_id}/origen", response_model=DocumentResponse)
async def update_document_origen(
    document_id: int,
    update_data: DocumentUpdateOrigen,
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza el origen de un documento.

    Args:
        document_id: ID del documento a actualizar.
        update_data: Datos con el nuevo origen_id.
        db: Sesión de base de datos.

    Returns:
        DocumentResponse: Documento actualizado.

    Raises:
        HTTPException: 404 si no existe el documento o el origen.
    """
    # Verificar que el documento existe
    query = (
        select(Document)
        .options(selectinload(Document.origen))
        .where(Document.id == document_id)
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Verificar que el nuevo origen existe
    origen_query = select(Origen).where(Origen.id == update_data.origen_id)
    origen_result = await db.execute(origen_query)
    origen = origen_result.scalar_one_or_none()

    if not origen:
        raise HTTPException(status_code=404, detail="Origen no encontrado")

    # Actualizar el origen
    document.origen_id = update_data.origen_id
    await db.commit()
    await db.refresh(document)

    logger.info(f"Documento {document_id} actualizado con origen {update_data.origen_id}")

    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un documento, su archivo asociado y sus chunks del vector store.

    Args:
        document_id: ID del documento a eliminar.
        db: Sesión de base de datos.

    Returns:
        dict: Confirmación de eliminación con cantidad de chunks eliminados.

    Raises:
        HTTPException: 404 si no existe el documento.
    """
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Eliminar chunks del vector store (ChromaDB)
    chunks_deleted = 0
    try:
        chunks_deleted = delete_document_chunks(document_id)
        logger.info(f"Chunks eliminados del vector store: {chunks_deleted}")
    except Exception as e:
        logger.error(f"Error eliminando chunks: {str(e)}")
        # Continuar con la eliminación aunque falle la limpieza de chunks

    # Eliminar archivo físico si existe
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
            logger.info(f"Archivo eliminado: {document.file_path}")
        except OSError as e:
            logger.warning(f"No se pudo eliminar archivo: {str(e)}")

    # Eliminar de la base de datos
    await db.delete(document)
    await db.commit()

    logger.info(f"Documento eliminado: id={document_id}")

    return {
        "message": "Documento eliminado correctamente",
        "id": document_id,
        "chunks_deleted": chunks_deleted
    }


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Sirve el archivo PDF para visualización inline (en el navegador).
    
    A diferencia de /download, este endpoint no fuerza la descarga,
    permitiendo que el navegador muestre el PDF en un iframe o visor.
    
    Args:
        document_id: ID del documento.
        db: Sesión de base de datos.
        
    Returns:
        FileResponse: Archivo PDF para visualizar inline.
        
    Raises:
        HTTPException: 404 si no existe el documento o el archivo.
    """
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor")
    
    # Usar headers para indicar visualización inline en vez de descarga
    return FileResponse(
        path=document.file_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"{document.original_filename}\""
        }
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Descarga el archivo PDF original de un documento.
    
    Args:
        document_id: ID del documento.
        db: Sesión de base de datos.
        
    Returns:
        FileResponse: Archivo PDF para descargar.
        
    Raises:
        HTTPException: 404 si no existe el documento o el archivo.
    """
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor")
    
    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type="application/pdf"
    )


@router.post("/{document_id}/reprocess-search")
async def reprocess_document_search(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocesa un documento para extraer/actualizar su contenido buscable.
    
    Útil para documentos que se subieron antes de implementar esta funcionalidad
    o que necesitan actualizar su información de búsqueda.
    
    Args:
        document_id: ID del documento a reprocesar.
        db: Sesión de base de datos.
        
    Returns:
        dict: Información sobre el reprocesamiento.
    """
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado")
    
    try:
        # Cargar documento para obtener texto
        documents = SimpleDirectoryReader(input_files=[document.file_path]).load_data()
        
        if not documents:
            raise HTTPException(status_code=400, detail="No se pudo leer el documento")
        
        # Obtener textos de todas las páginas como chunks
        chunk_texts = [doc.text for doc in documents if doc.text]
        
        # Extraer texto completo para búsqueda
        extractor = ContentExtractor()
        search_content = extractor.extract_searchable_content(
            chunks=chunk_texts,
            caratula=document.caratula,
            filename=document.original_filename
        )
        
        # Actualizar documento
        document.search_content = search_content
        await db.commit()
        
        logger.info(f"Documento {document_id} reprocesado: {len(search_content) if search_content else 0} caracteres")
        
        return {
            "message": "Documento reprocesado correctamente",
            "id": document_id,
            "search_content_length": len(search_content) if search_content else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocesando documento {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reprocesando: {str(e)}")


@router.post("/reprocess-all-search")
async def reprocess_all_documents_search(
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocesa TODOS los documentos que no tienen contenido buscable.
    
    ADVERTENCIA: Este proceso puede tomar mucho tiempo si hay muchos documentos.
    
    Returns:
        dict: Resumen del reprocesamiento.
    """
    try:
        # Obtener documentos sin search_content
        query = select(Document).where(
            (Document.search_content == None) | (Document.search_content == "")
        )
        result = await db.execute(query)
        documents = result.scalars().all()
        
        if not documents:
            return {
                "message": "No hay documentos para reprocesar",
                "processed": 0,
                "failed": 0
            }
        
        extractor = ContentExtractor()
        processed = 0
        failed = 0
        failed_ids = []
        
        for document in documents:
            try:
                if not document.file_path or not os.path.exists(document.file_path):
                    failed += 1
                    failed_ids.append(document.id)
                    continue
                
                # Cargar documento
                docs = SimpleDirectoryReader(input_files=[document.file_path]).load_data()
                
                if not docs:
                    failed += 1
                    failed_ids.append(document.id)
                    continue
                
                # Obtener textos
                chunk_texts = [doc.text for doc in docs if doc.text]
                
                # Extraer texto completo
                search_content = extractor.extract_searchable_content(
                    chunks=chunk_texts,
                    caratula=document.caratula,
                    filename=document.original_filename
                )
                
                document.search_content = search_content
                processed += 1
                
                logger.info(f"Reprocesado documento {document.id}")
                
            except Exception as e:
                logger.error(f"Error reprocesando documento {document.id}: {str(e)}")
                failed += 1
                failed_ids.append(document.id)
        
        await db.commit()
        
        return {
            "message": "Reprocesamiento completado",
            "processed": processed,
            "failed": failed,
            "failed_ids": failed_ids if failed_ids else None
        }
        
    except Exception as e:
        logger.error(f"Error en reprocesamiento masivo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/cleanup-vectors")
async def cleanup_vector_store(db: AsyncSession = Depends(get_db)):
    """
    Limpia chunks huérfanos del vector store.

    Elimina del ChromaDB todos los chunks que pertenecen a documentos
    que ya no existen en la base de datos PostgreSQL.

    Returns:
        dict: Información sobre los chunks eliminados.
    """
    try:
        # Obtener IDs de todos los documentos existentes en PostgreSQL
        query = select(Document.id)
        result = await db.execute(query)
        valid_ids = [row[0] for row in result.fetchall()]

        # Limpiar chunks huérfanos
        cleanup_result = cleanup_orphan_chunks(valid_ids)

        logger.info(f"Limpieza de vector store completada: {cleanup_result}")

        return {
            "message": "Limpieza completada",
            "chunks_deleted": cleanup_result["chunks_deleted"],
            "orphan_document_ids": cleanup_result["orphan_document_ids"]
        }
    except Exception as e:
        logger.error(f"Error en limpieza de vector store: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en limpieza: {str(e)}")


@router.post("/reset-all")
async def reset_all_data(db: AsyncSession = Depends(get_db)):
    """
    ELIMINA TODOS LOS DATOS DEL SISTEMA.

    Esta operación es IRREVERSIBLE y elimina:
    - Todos los documentos de la base de datos PostgreSQL
    - Toda la memoria vectorial (ChromaDB)
    - Todos los archivos PDF del directorio de uploads
    - Todos los archivos de índice de LlamaIndex

    ADVERTENCIA: Esta acción no se puede deshacer.

    Returns:
        dict: Resumen de los datos eliminados.
    """
    try:
        deleted_count = 0
        deleted_files = 0
        errors = []

        # 1. Contar y eliminar documentos de PostgreSQL
        query = select(func.count()).select_from(Document)
        result = await db.execute(query)
        deleted_count = result.scalar() or 0

        # Eliminar todos los documentos
        if deleted_count > 0:
            delete_query = select(Document)
            result = await db.execute(delete_query)
            documents = result.scalars().all()

            for document in documents:
                await db.delete(document)

            await db.commit()
            logger.info(f"Eliminados {deleted_count} documentos de PostgreSQL")

        # 2. Eliminar directorio completo de ChromaDB
        if os.path.exists(PERSIST_DIR):
            try:
                shutil.rmtree(PERSIST_DIR)
                logger.info(f"Directorio de ChromaDB eliminado: {PERSIST_DIR}")
                # Recrear el directorio vacío
                os.makedirs(PERSIST_DIR, exist_ok=True)
                # Forzar reinicio de uvicorn tocando este archivo (para reinicializar ChromaDB)
                os.utime(__file__, None)
            except Exception as e:
                error_msg = f"Error eliminando ChromaDB: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # 3. Eliminar todos los archivos PDF del directorio de uploads
        if os.path.exists(UPLOAD_DIR):
            try:
                for filename in os.listdir(UPLOAD_DIR):
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_files += 1
                logger.info(f"Eliminados {deleted_files} archivos del directorio de uploads")
            except Exception as e:
                error_msg = f"Error eliminando archivos: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.warning(f"RESET COMPLETO DEL SISTEMA: {deleted_count} documentos, {deleted_files} archivos")

        return {
            "message": "Sistema reiniciado completamente",
            "documents_deleted": deleted_count,
            "files_deleted": deleted_files,
            "vector_store_reset": True,
            "errors": errors if errors else None
        }

    except Exception as e:
        logger.error(f"Error crítico en reset del sistema: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en reset del sistema: {str(e)}")
