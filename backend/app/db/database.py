"""
Configuración de la conexión a PostgreSQL usando SQLAlchemy async.

Principio SRP: Este módulo solo se encarga de la configuración
y gestión de la conexión a la base de datos.
"""
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

load_dotenv()

# URL de conexión a PostgreSQL (async)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://localhost:5432/jurisprudencia"
)

# Motor async de SQLAlchemy
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # True para debug SQL
    pool_pre_ping=True,  # Verificar conexiones antes de usar
    pool_size=5,
    max_overflow=10
)

# Session factory async
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Base para los modelos
Base = declarative_base()


async def get_db():
    """
    Dependency injection para obtener una sesión de base de datos.
    
    Uso en FastAPI:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    
    Yields:
        AsyncSession: Sesión de base de datos.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    
    Llamar al iniciar la aplicación.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
