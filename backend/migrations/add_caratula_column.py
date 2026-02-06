"""
Script de migración para agregar la columna 'caratula' a la tabla documents.

Ejecutar con: python -m migrations.add_caratula_column
"""
import asyncio
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine


async def migrate():
    """Agrega la columna caratula a la tabla documents si no existe."""
    async with engine.begin() as conn:
        # Verificar si la columna ya existe
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'caratula'
        """))
        
        if result.fetchone() is None:
            print("Agregando columna 'caratula' a la tabla 'documents'...")
            await conn.execute(text("""
                ALTER TABLE documents 
                ADD COLUMN caratula VARCHAR(500) NULL
            """))
            print("Columna 'caratula' agregada exitosamente.")
        else:
            print("La columna 'caratula' ya existe.")


if __name__ == "__main__":
    asyncio.run(migrate())
