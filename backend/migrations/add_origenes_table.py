"""
Script de migración para agregar la tabla 'origenes' y FK en documents.

Ejecutar con: python -m migrations.add_origenes_table
"""
import asyncio
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine


# Orígenes iniciales
ORIGENES_INICIALES = [
    ('cfcp', 'Sentencias cámara federal de casación penal', 'CFCP', '#DC2626'),
    ('civ_para', 'Sentencias civiles cámara federal de Paraná', 'CF Paraná Civil', '#2563EB'),
    ('csjn_civ', 'Sentencias corte suprema de justicia - CIVIL', 'CSJN Civil', '#7C3AED'),
    ('csjn_pen', 'Sentencias corte suprema de justicia - PENAL', 'CSJN Penal', '#DB2777'),
    ('pen_para', 'Sentencias penales cámara federal de Paraná', 'CF Paraná Penal', '#059669'),
    ('sin_clasificar', 'Sin clasificar', 'Sin clasificar', '#6B7280'),
]


async def migrate():
    """Crea la tabla origenes, inserta datos iniciales y agrega FK en documents."""
    async with engine.begin() as conn:
        # 1. Crear tabla origenes si no existe
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name = 'origenes'
        """))

        if result.fetchone() is None:
            print("Creando tabla 'origenes'...")
            await conn.execute(text("""
                CREATE TABLE origenes (
                    id SERIAL PRIMARY KEY,
                    codigo VARCHAR(20) UNIQUE NOT NULL,
                    nombre VARCHAR(255) NOT NULL,
                    abreviacion VARCHAR(50) NOT NULL,
                    color VARCHAR(7) NOT NULL,
                    activo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            print("Tabla 'origenes' creada exitosamente.")

            # Insertar orígenes iniciales
            print("Insertando orígenes iniciales...")
            for codigo, nombre, abreviacion, color in ORIGENES_INICIALES:
                await conn.execute(text("""
                    INSERT INTO origenes (codigo, nombre, abreviacion, color, created_at)
                    VALUES (:codigo, :nombre, :abreviacion, :color, NOW())
                """), {
                    'codigo': codigo,
                    'nombre': nombre,
                    'abreviacion': abreviacion,
                    'color': color
                })
            print(f"Insertados {len(ORIGENES_INICIALES)} orígenes.")
        else:
            print("La tabla 'origenes' ya existe.")

        # 2. Agregar columna origen_id a documents si no existe
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'documents' AND column_name = 'origen_id'
        """))

        if result.fetchone() is None:
            print("Agregando columna 'origen_id' a la tabla 'documents'...")
            await conn.execute(text("""
                ALTER TABLE documents
                ADD COLUMN origen_id INTEGER NULL REFERENCES origenes(id)
            """))
            print("Columna 'origen_id' agregada exitosamente.")

            # Crear índice
            print("Creando índice en documents.origen_id...")
            await conn.execute(text("""
                CREATE INDEX idx_documents_origen_id ON documents(origen_id)
            """))
            print("Índice creado exitosamente.")
        else:
            print("La columna 'origen_id' ya existe en 'documents'.")


if __name__ == "__main__":
    asyncio.run(migrate())
