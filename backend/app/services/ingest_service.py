"""
Servicio para procesar e indexar documentos PDF.

Principio SRP: Este servicio solo se encarga del procesamiento
y indexación de documentos. La persistencia en BD se maneja
en el endpoint.
"""
import os
import re
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional
from llama_index.core import SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SemanticSplitterNodeParser
from app.services.vector_store import get_index
from app.services.content_extractor import ContentExtractor
from app.core.config import PERSIST_DIR, UPLOAD_DIR

logger = logging.getLogger(__name__)


def extract_caratula(text: str) -> Optional[str]:
    """
    Extrae la carátula de un documento jurídico argentino.
    
    Busca patrones comunes como:
    - "Autos: ..." o "Autos caratulados: ..."
    - "Causa: ..." o "Causa n°: ..."
    - "En los autos: ..."
    - Patrón típico: "Nombre c/ Nombre s/ tipo"
    
    Args:
        text: Texto extraído del PDF (primeras páginas).
        
    Returns:
        Carátula extraída o None si no se encuentra.
    """
    if not text:
        return None
    
    # Normalizar espacios y saltos de línea
    text = ' '.join(text.split())
    
    # Patrones para buscar carátulas en documentos jurídicos argentinos
    patterns = [
        # "Autos: XXX" o "Autos caratulados: XXX"
        r'[Aa]utos(?:\s+caratulados)?[\s:]+["\']?([^"\']+?(?:c[/.]|contra)\s+.+?(?:s[/.]|sobre)\s+[^"\']+?)["\']?(?:\s*[-–—]|\s*\(|\s*$|\.)',
        
        # "Causa: XXX" o "Causa n°: XXX"
        r'[Cc]ausa(?:\s+[Nn][°º]?\s*[\d/\-]+)?[\s:]+["\']?([^"\']+?(?:c[/.]|contra)\s+.+?(?:s[/.]|sobre)\s+[^"\']+?)["\']?(?:\s*[-–—]|\s*\(|\s*$|\.)',
        
        # "En los autos: XXX"
        r'[Ee]n\s+los\s+autos[\s:]+["\']?([^"\']+?(?:c[/.]|contra)\s+.+?(?:s[/.]|sobre)\s+[^"\']+?)["\']?(?:\s*[-–—]|\s*\(|\s*$|\.)',
        
        # "Expte. N°: XXX - Carátula: YYY" 
        r'[Cc]ar[áa]tula[\s:]+["\']?([^"\']+?(?:c[/.]|contra)\s+.+?(?:s[/.]|sobre)\s+[^"\']+?)["\']?(?:\s*[-–—]|\s*\(|\s*$|\.)',
        
        # Patrón general: "NOMBRE c/ NOMBRE s/ TIPO"
        r'"([A-ZÁÉÍÓÚÑ][^"]+?(?:c[/.]|contra)\s+[^"]+?(?:s[/.]|sobre)\s+[^"]+?)"',
        
        # Buscar en comillas simples
        r"'([A-ZÁÉÍÓÚÑ][^']+?(?:c[/.]|contra)\s+[^']+?(?:s[/.]|sobre)\s+[^']+?)'",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            caratula = match.group(1).strip()
            # Limpiar la carátula
            caratula = re.sub(r'\s+', ' ', caratula)
            # Limitar longitud
            if len(caratula) > 400:
                caratula = caratula[:400] + "..."
            if len(caratula) > 10:  # Evitar matches muy cortos
                logger.info(f"Carátula extraída: {caratula[:100]}...")
                return caratula
    
    # Si no encontramos un patrón específico, buscar cualquier texto con "c/" y "s/"
    simple_pattern = r'([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s,\.]+?(?:c[/.]|contra)\s+[A-Za-záéíóúñÁÉÍÓÚÑ\s,\.]+?(?:s[/.]|sobre)\s+[a-záéíóúñ\s]+)'
    match = re.search(simple_pattern, text)
    if match:
        caratula = match.group(1).strip()
        caratula = re.sub(r'\s+', ' ', caratula)
        if 20 < len(caratula) < 400:
            logger.info(f"Carátula extraída (patrón simple): {caratula[:100]}...")
            return caratula
    
    logger.info("No se pudo extraer carátula del documento")
    return None


class IngestService:
    """
    Servicio para procesar e indexar documentos PDF.
    
    Utiliza SemanticSplitterNodeParser para dividir documentos
    en chunks semánticamente coherentes.
    """
    
    def __init__(self):
        """
        Inicializa el servicio con el splitter semántico y extractor de contenido.
        
        CRITICO: buffer_size=1 y breakpoint_percentile_threshold=80
        para separar correctamente las sentencias jurídicas.
        """
        self.splitter = SemanticSplitterNodeParser(
            buffer_size=1,
            breakpoint_percentile_threshold=80,
            embed_model=Settings.embed_model
        )
        self.content_extractor = ContentExtractor()
        # Asegurar que existe el directorio de uploads
        Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    
    def save_file(self, temp_path: str, original_filename: str) -> tuple[str, int]:
        """
        Guarda un archivo temporal de forma permanente.
        
        Args:
            temp_path: Ruta al archivo temporal.
            original_filename: Nombre original del archivo.
            
        Returns:
            tuple: (ruta_permanente, tamaño_en_bytes)
        """
        # Generar nombre único para evitar colisiones
        file_extension = Path(original_filename).suffix
        unique_name = f"{uuid.uuid4().hex}{file_extension}"
        permanent_path = os.path.join(UPLOAD_DIR, unique_name)
        
        # Copiar archivo a ubicación permanente
        shutil.copy2(temp_path, permanent_path)
        
        # Obtener tamaño
        file_size = os.path.getsize(permanent_path)
        
        logger.info(f"Archivo guardado: {permanent_path} ({file_size} bytes)")
        
        return permanent_path, file_size
    
    async def process_pdf(self, file_path: str, document_id: int = None, original_filename: str = None) -> dict:
        """
        Procesa un PDF y lo indexa en ChromaDB.
        
        Args:
            file_path: Ruta al archivo PDF a procesar.
            document_id: ID del documento en PostgreSQL (para metadatos).
            original_filename: Nombre original del archivo (para incluir en búsqueda).
            
        Returns:
            dict: Resultado con chunks_created, status, caratula y search_content.
            
        Raises:
            Exception: Si hay error al procesar el documento.
        """
        try:
            logger.info(f"Procesando PDF: {file_path}")
            
            # Cargar documento
            documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
            logger.info(f"Documento cargado: {len(documents)} páginas")
            
            # Extraer carátula del texto de las primeras páginas
            caratula = None
            if documents:
                # Concatenar texto de las primeras 3 páginas para buscar carátula
                first_pages_text = ' '.join([
                    doc.text for doc in documents[:3] if doc.text
                ])
                caratula = extract_caratula(first_pages_text)
            
            # Agregar metadatos del documento a cada página
            if document_id:
                for doc in documents:
                    doc.metadata["document_id"] = document_id
            
            # Aplicar chunking semántico
            nodes = self.splitter.get_nodes_from_documents(documents)
            logger.info(f"Chunks creados: {len(nodes)}")
            
            # Extraer texto completo para búsqueda (sin LLM, solo texto)
            search_content = None
            try:
                # Usar texto de las páginas originales (no chunks) para búsqueda
                page_texts = [doc.text for doc in documents if doc.text]
                search_content = self.content_extractor.extract_searchable_content(
                    chunks=page_texts,
                    caratula=caratula,
                    filename=original_filename
                )
                logger.info(f"Texto extraído para búsqueda: {len(search_content) if search_content else 0} caracteres")
            except Exception as e:
                logger.warning(f"Error extrayendo texto (continuando sin él): {str(e)}")
            
            # Obtener índice e insertar nodos
            index = get_index()
            index.insert_nodes(nodes)
            
            # Persistir cambios en disco
            index.storage_context.persist(persist_dir=PERSIST_DIR)
            logger.info("Índice persistido correctamente")
            
            return {
                "chunks_created": len(nodes),
                "status": "success",
                "caratula": caratula,
                "search_content": search_content
            }
            
        except Exception as e:
            logger.error(f"Error procesando PDF: {str(e)}")
            raise
