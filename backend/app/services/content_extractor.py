"""
Servicio para extraer contenido buscable de documentos jurídicos.

Almacena el texto completo del documento en PostgreSQL para 
búsquedas full-text tradicionales (sin LLM).
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ContentExtractor:
    """
    Extrae el texto completo del documento para búsquedas full-text.
    
    Enfoque simple y eficiente:
    - Guarda TODO el texto del documento
    - PostgreSQL comprime automáticamente con TOAST
    - Permite búsquedas ILIKE o full-text search nativo
    """
    
    def extract_searchable_content(
        self, 
        chunks: List[str], 
        caratula: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Extrae el texto completo del documento para búsqueda.
        
        Args:
            chunks: Lista de textos (páginas/chunks) del documento.
            caratula: Carátula del documento.
            filename: Nombre del archivo original.
            
        Returns:
            Texto completo del documento, preparado para búsqueda.
        """
        if not chunks:
            return None
        
        parts = []
        
        # Incluir metadatos al inicio para búsqueda rápida
        if filename:
            parts.append(f"ARCHIVO: {filename}")
        
        if caratula:
            parts.append(f"CARATULA: {caratula}")
        
        # Separador
        if parts:
            parts.append("---")
        
        # Agregar todo el texto del documento
        full_text = '\n\n'.join(chunks)
        parts.append(full_text)
        
        result = '\n'.join(parts)
        
        logger.info(f"Texto extraído: {len(result)} caracteres ({len(result)/1024:.1f} KB)")
        
        return result
