"""
Endpoint para ingesta de documentos PDF.

Principio SRP: Este endpoint coordina el flujo de upload:
1. Validación del archivo
2. Guardado permanente
3. Registro en PostgreSQL
4. Indexación en ChromaDB
"""
import os
import logging
import tempfile
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import Document, Origen
from app.services.ingest_service import IngestService, extract_caratula
from app.services.vector_store import ensure_cosine_collection
from app.schemas.document import DocumentUploadResponse
from llama_index.core import SimpleDirectoryReader

logger = logging.getLogger(__name__)

router = APIRouter()


class ExtractCaratulaResponse(BaseModel):
    """Response schema for caratula extraction."""
    caratula: Optional[str] = None
    filename: str


@router.post("/extract-caratula", response_model=ExtractCaratulaResponse)
async def extract_caratula_from_pdf(
    file: UploadFile = File(...)
):
    """
    Extrae la carátula de un PDF sin procesarlo completamente.

    Útil para clasificación previa a la subida.

    Args:
        file: Archivo PDF.

    Returns:
        ExtractCaratulaResponse: Carátula extraída (o None si no se encuentra).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo no proporcionado")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

    tmp_path = None
    try:
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="El archivo está vacío")
            tmp.write(content)
            tmp_path = tmp.name

        # Cargar y extraer texto de primeras páginas
        documents = SimpleDirectoryReader(input_files=[tmp_path]).load_data()

        caratula = None
        if documents:
            first_pages_text = ' '.join([
                doc.text for doc in documents[:3] if doc.text
            ])
            caratula = extract_caratula(first_pages_text)

        return ExtractCaratulaResponse(
            caratula=caratula,
            filename=file.filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extrayendo carátula: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error extrayendo carátula: {str(e)}"
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    origen_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Recibe un archivo PDF, lo guarda, registra en BD e indexa en ChromaDB.
    
    Flujo:
    1. Valida que sea un PDF válido
    2. Guarda temporalmente para validación
    3. Guarda permanentemente en /uploads
    4. Crea registro en PostgreSQL
    5. Procesa e indexa en ChromaDB
    6. Actualiza registro con cantidad de chunks
    
    Args:
        file: Archivo PDF subido.
        origen_id: ID del origen/categoría del documento (opcional).
        db: Sesión de base de datos.

    Returns:
        DocumentUploadResponse: ID, filename, status y chunks_created.

    Raises:
        HTTPException: Si el archivo no es PDF o hay error en el procesamiento.
    """
    # Validar origen_id si se proporciona
    if origen_id is not None:
        result = await db.execute(
            select(Origen).where(Origen.id == origen_id, Origen.activo == True)
        )
        origen = result.scalar_one_or_none()
        if origen is None:
            raise HTTPException(
                status_code=400,
                detail=f"Origen con ID {origen_id} no existe o no está activo"
            )

    # Validar que sea un PDF
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo no proporcionado")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Solo se permiten archivos PDF"
        )
    
    tmp_path = None
    permanent_path = None
    document = None
    
    try:
        logger.info(f"Recibiendo archivo: {file.filename}")
        
        # Guardar archivo temporal para validación
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="El archivo está vacío")
            
            tmp.write(content)
            tmp_path = tmp.name
        
        logger.info(f"Archivo guardado temporalmente: {tmp_path}")
        
        # Inicializar servicio
        service = IngestService()
        
        # Guardar archivo permanentemente
        permanent_path, file_size = service.save_file(tmp_path, file.filename)
        
        # Crear nombre descriptivo (sin extensión)
        doc_name = os.path.splitext(file.filename)[0]
        
        # Crear registro en base de datos
        document = Document(
            name=doc_name,
            original_filename=file.filename,
            file_path=permanent_path,
            file_size=file_size,
            chunks_count=0,
            origen_id=origen_id
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        logger.info(f"Documento registrado en BD: id={document.id}")
        
        # Procesar e indexar en ChromaDB (ahora async para extracción con LLM)
        result = await service.process_pdf(
            permanent_path, 
            document_id=document.id,
            original_filename=file.filename
        )
        
        # Actualizar cantidad de chunks, carátula y contenido buscable
        document.chunks_count = result["chunks_created"]
        if result.get("caratula"):
            document.caratula = result["caratula"]
        if result.get("search_content"):
            document.search_content = result["search_content"]
        await db.commit()
        
        logger.info(f"Archivo procesado exitosamente: {result['chunks_created']} chunks")
        
        return DocumentUploadResponse(
            id=document.id,
            filename=file.filename,
            status="Procesado con éxito",
            chunks_created=result["chunks_created"]
        )
        
    except HTTPException:
        # Si hubo error después de guardar permanentemente, limpiar
        if permanent_path and os.path.exists(permanent_path):
            try:
                os.remove(permanent_path)
            except:
                pass
        raise
    except Exception as e:
        logger.error(f"Error procesando archivo: {str(e)}")
        # Limpiar archivo permanente si se guardó
        if permanent_path and os.path.exists(permanent_path):
            try:
                os.remove(permanent_path)
            except:
                pass
        # Eliminar registro de BD si se creó
        if document and document.id:
            try:
                await db.delete(document)
                await db.commit()
            except:
                pass
        raise HTTPException(
            status_code=500, 
            detail=f"Error procesando archivo: {str(e)}"
        )
    finally:
        # Limpiar archivo temporal
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.info("Archivo temporal eliminado")
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal: {str(e)}")


class ReindexResponse(BaseModel):
    """Response schema for reindex operation."""
    status: str
    migrated: bool
    documents_processed: int
    total_chunks: int
    errors: list


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_all_documents(db: AsyncSession = Depends(get_db)):
    """
    Re-indexa todos los documentos en ChromaDB.

    Migra la colección a distancia coseno si es necesario, luego
    re-procesa todos los PDFs registrados en la BD con los nuevos
    parámetros de chunking.
    """
    try:
        # Paso 1: Migrar colección a coseno si usa L2
        migrated = ensure_cosine_collection()

        # Paso 2: Re-procesar todos los documentos
        result = await db.execute(select(Document))
        documents = result.scalars().all()

        service = IngestService()
        processed = 0
        total_chunks = 0
        errors = []

        for doc in documents:
            if not doc.file_path or not os.path.exists(doc.file_path):
                errors.append(f"Doc {doc.id} ({doc.name}): archivo no encontrado en {doc.file_path}")
                continue

            try:
                ingest_result = await service.process_pdf(
                    doc.file_path,
                    document_id=doc.id,
                    original_filename=doc.original_filename
                )
                doc.chunks_count = ingest_result["chunks_created"]
                if ingest_result.get("caratula"):
                    doc.caratula = ingest_result["caratula"]
                if ingest_result.get("search_content"):
                    doc.search_content = ingest_result["search_content"]
                total_chunks += ingest_result["chunks_created"]
                processed += 1
                logger.info(f"Re-indexado doc {doc.id}: {ingest_result['chunks_created']} chunks")
            except Exception as e:
                errors.append(f"Doc {doc.id} ({doc.name}): {str(e)}")
                logger.error(f"Error re-indexando doc {doc.id}: {str(e)}")

        await db.commit()

        return ReindexResponse(
            status="completed",
            migrated=migrated,
            documents_processed=processed,
            total_chunks=total_chunks,
            errors=errors
        )

    except Exception as e:
        logger.error(f"Error en re-indexación: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en re-indexación: {str(e)}")
