import os
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

load_dotenv()

# Directorio de persistencia para ChromaDB
PERSIST_DIR = os.getenv("PERSIST_DIR", "./chroma_db")

# Directorio para guardar archivos PDF subidos
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# Dominios permitidos para CORS
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# Embeddings locales con HuggingFace (corre en Python/Mac M4)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

# LLM conecta a Ollama local
Settings.llm = Ollama(model="llama3", request_timeout=360.0)

settings = Settings
