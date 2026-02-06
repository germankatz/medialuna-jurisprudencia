"""
Script de migración para agregar índices de rendimiento a la tabla documents.

Estos índices optimizan:
- Ordenamiento por fecha de creación (created_at)
- Búsquedas por nombre y carátula usando trigrams (pg_trgm)

Ejecutar con: python -m migrations.add_performance_indexes
"""
import asyncio
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine


async def index_exists(conn, index_name: str) -> bool:
    """Verifica si un índice existe en la base de datos."""
    result = await conn.execute(text("""
        SELECT 1 FROM pg_indexes 
        WHERE indexname = :index_name
    """), {"index_name": index_name})
    return result.fetchone() is not None


async def migrate():
    """Agrega índices de rendimiento a la tabla documents."""
    async with engine.begin() as conn:
        print("Iniciando migración de índices de rendimiento...\n")
        
        # 1. Índice para ordenamiento por created_at DESC
        index_name = "idx_documents_created_at"
        if not await index_exists(conn, index_name):
            print(f"Creando índice '{index_name}'...")
            await conn.execute(text("""
                CREATE INDEX idx_documents_created_at 
                ON documents(created_at DESC)
            """))
            print(f"  -> Índice '{index_name}' creado exitosamente.")
        else:
            print(f"  -> Índice '{index_name}' ya existe, omitiendo.")
        
        # 2. Habilitar extensión pg_trgm para búsquedas con trigrams
        print("\nVerificando extensión pg_trgm...")
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            print("  -> Extensión pg_trgm habilitada.")
        except Exception as e:
            print(f"  -> Nota: No se pudo crear la extensión pg_trgm: {e}")
            print("     Los índices trigram requieren permisos de superusuario.")
            print("     Continuando sin índices trigram...")
            print("\nMigración completada (parcial).")
            return
        
        # 3. Índice GIN trigram para búsquedas en 'name'
        index_name = "idx_documents_name_trgm"
        if not await index_exists(conn, index_name):
            print(f"\nCreando índice '{index_name}'...")
            await conn.execute(text("""
                CREATE INDEX idx_documents_name_trgm 
                ON documents USING gin(name gin_trgm_ops)
            """))
            print(f"  -> Índice '{index_name}' creado exitosamente.")
        else:
            print(f"  -> Índice '{index_name}' ya existe, omitiendo.")
        
        # 4. Índice GIN trigram para búsquedas en 'caratula'
        index_name = "idx_documents_caratula_trgm"
        if not await index_exists(conn, index_name):
            print(f"\nCreando índice '{index_name}'...")
            await conn.execute(text("""
                CREATE INDEX idx_documents_caratula_trgm 
                ON documents USING gin(caratula gin_trgm_ops)
            """))
            print(f"  -> Índice '{index_name}' creado exitosamente.")
        else:
            print(f"  -> Índice '{index_name}' ya existe, omitiendo.")
        
        print("\n" + "="*50)
        print("Migración completada exitosamente.")
        print("="*50)
        print("\nÍndices creados:")
        print("  - idx_documents_created_at: Optimiza ORDER BY created_at DESC")
        print("  - idx_documents_name_trgm: Optimiza búsquedas LIKE en 'name'")
        print("  - idx_documents_caratula_trgm: Optimiza búsquedas LIKE en 'caratula'")


if __name__ == "__main__":
    asyncio.run(migrate())
