"""
Script para insertar los orígenes iniciales en la base de datos.

Ejecutar con: python -m migrations.insert_origenes_iniciales
"""
import asyncio
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine


# Orígenes iniciales según el plan
ORIGENES_INICIALES = [
    ('cfcp', 'Sentencias cámara federal de casación penal', 'CFCP', '#DC2626'),
    ('civ_para', 'Sentencias civiles cámara federal de Paraná', 'CF Paraná Civil', '#2563EB'),
    ('csjn_civ', 'Sentencias corte suprema de justicia - CIVIL', 'CSJN Civil', '#7C3AED'),
    ('csjn_pen', 'Sentencias corte suprema de justicia - PENAL', 'CSJN Penal', '#DB2777'),
    ('pen_para', 'Sentencias penales cámara federal de Paraná', 'CF Paraná Penal', '#059669'),
    ('sin_clasificar', 'Sin clasificar', 'Sin clasificar', '#6B7280'),
]


async def insert_origenes():
    """Inserta los orígenes iniciales si no existen."""
    async with engine.begin() as conn:
        print("Verificando e insertando orígenes iniciales...")

        inserted = 0
        skipped = 0

        for codigo, nombre, abreviacion, color in ORIGENES_INICIALES:
            # Verificar si ya existe
            result = await conn.execute(text("""
                SELECT id FROM origenes WHERE codigo = :codigo
            """), {'codigo': codigo})

            if result.fetchone() is None:
                # Insertar
                await conn.execute(text("""
                    INSERT INTO origenes (codigo, nombre, abreviacion, color, activo, created_at)
                    VALUES (:codigo, :nombre, :abreviacion, :color, true, NOW())
                """), {
                    'codigo': codigo,
                    'nombre': nombre,
                    'abreviacion': abreviacion,
                    'color': color
                })
                print(f"  + Insertado: {codigo} ({abreviacion})")
                inserted += 1
            else:
                print(f"  - Ya existe: {codigo}")
                skipped += 1

        print(f"\nResumen: {inserted} insertados, {skipped} ya existían")


if __name__ == "__main__":
    asyncio.run(insert_origenes())
