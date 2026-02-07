import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings, ALLOWED_ORIGINS  # Aplica Settings de LlamaIndex
from app.api.endpoints import chat, ingest, documents, origins, classify
from app.db.database import init_db

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    
    - Al iniciar: Crea las tablas de la base de datos.
    - Al cerrar: Limpia recursos si es necesario.
    """
    logger.info("Inicializando base de datos...")
    await init_db()
    logger.info("Base de datos inicializada correctamente")
    yield
    logger.info("Cerrando aplicación...")


app = FastAPI(
    title="Sistema RAG Jurisprudencia",
    description="API para consulta de jurisprudencia usando RAG con LlamaIndex",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(origins.router, prefix="/api/origins", tags=["origins"])
app.include_router(classify.router, prefix="/api/classify", tags=["classify"])


@app.get("/")
def root():
    """Endpoint de health check."""
    return {"status": "ok", "message": "Sistema RAG activo"}
