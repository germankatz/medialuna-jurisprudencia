"""
Script de migración para agregar la columna 'search_content' a la tabla documents.

Esta columna almacena información procesada de los chunks del documento
para permitir búsquedas tradicionales (LIKE, full-text) sin usar el LLM.

Contenido típico:
- Materia/rama del derecho
- Nombres de partes, jueces, abogados
- Códigos de expediente, fechas
- Resumen breve del documento

Ejecutar con: python -m migrations.add_search_content_column
"""
import asyncio
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine


async def migrate():
    """Agrega la columna search_content a la tabla documents si no existe."""
    async with engine.begin() as conn:
        # Verificar si la columna ya existe
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'search_content'
        """))
        
        if result.fetchone() is None:
            print("Agregando columna 'search_content' a la tabla 'documents'...")
            await conn.execute(text("""
                ALTER TABLE documents 
                ADD COLUMN search_content TEXT NULL
            """))
            print("Columna 'search_content' agregada exitosamente.")
        else:
            print("La columna 'search_content' ya existe.")


if __name__ == "__main__":
    asyncio.run(migrate())
