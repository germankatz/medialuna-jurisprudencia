# Sistema de Jurisprudencia

**Sistema RAG (Retrieval-Augmented Generation) para jurisprudencia argentina.**

Plataforma que permite cargar, organizar y consultar documentos jurídicos mediante inteligencia artificial. Subí fallos en PDF, buscalos por texto o por tribunal, y chateá con un asistente que responde en base al contenido real de los documentos.

---

## Funcionalidades

- **Carga de documentos** — Subí PDFs de sentencias y fallos. El sistema extrae automáticamente la carátula y genera chunks semánticos para búsqueda vectorial.
- **Búsqueda full-text** — Búsqueda por texto insensible a acentos y mayúsculas, con filtrado por origen/tribunal.
- **Chat RAG** — Chateá con un asistente de IA que responde usando el contenido de los documentos cargados como contexto.
- **Clasificación automática** — Clasificación de documentos por tribunal/origen usando IA.
- **Gestión de orígenes** — Administrá los tribunales y categorías (CSJN, Cámaras Federales, etc.) con códigos y colores.

## Stack técnico

| Capa | Tecnología |
|------|-----------|
| **Frontend** | Vue 3 (Composition API), Vite, Tailwind CSS, shadcn-vue |
| **Backend** | Python 3.9+, FastAPI, SQLAlchemy async |
| **Base de datos** | PostgreSQL (asyncpg) |
| **Vector store** | ChromaDB (persistente) |
| **Embeddings** | HuggingFace BAAI/bge-m3 (multilingüe, local) |
| **LLM** | Ollama con llama3 (local) |
| **Procesamiento PDF** | pypdf + SemanticSplitterNodeParser (LlamaIndex) |

---

## Requisitos previos

- **Python** 3.9+
- **Node.js** 18+
- **PostgreSQL** corriendo en `localhost:5432`
- **Ollama** instalado con el modelo `llama3` descargado:
  ```bash
  ollama pull llama3
  ```

## Instalación

### Base de datos

```bash
createdb jurisprudencia
```

### Backend

```bash
cd backend

# Entorno virtual
python -m venv venv
source venv/bin/activate

# Dependencias
pip install -r requirements.txt

# Configuración
cp .env.example .env
# Editá .env si necesitás cambiar la conexión a la DB
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

## Ejecución

### Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API queda disponible en `http://localhost:8000`. Documentación interactiva en `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm run dev
```

La app queda disponible en `http://localhost:5173`.

---

## Variables de entorno

### Backend (`backend/.env`)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Conexión a PostgreSQL | `postgresql+asyncpg://localhost:5432/jurisprudencia` |
| `UPLOAD_DIR` | Directorio de almacenamiento de PDFs | `./uploads` |
| `PERSIST_DIR` | Directorio de ChromaDB | `./chroma_db` |

### Frontend (`frontend/.env`)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `VITE_API_URL` | URL base de la API | `http://localhost:8000/api` |

---

## Estructura del proyecto

```
sistema-jurisprudencia/
├── backend/
│   ├── app/
│   │   ├── main.py                 # Entry point FastAPI
│   │   ├── api/endpoints/          # Rutas de la API
│   │   │   ├── chat.py             # Chat RAG
│   │   │   ├── documents.py        # CRUD documentos
│   │   │   ├── ingest.py           # Carga de PDFs
│   │   │   ├── origins.py          # CRUD orígenes
│   │   │   └── classify.py         # Clasificación con IA
│   │   ├── core/config.py          # Config de LlamaIndex, embeddings, LLM
│   │   ├── db/
│   │   │   ├── database.py         # Conexión async a PostgreSQL
│   │   │   └── models.py           # Modelos SQLAlchemy
│   │   ├── schemas/                # Schemas Pydantic
│   │   └── services/               # Lógica de negocio
│   │       ├── ingest_service.py   # Procesamiento de PDFs
│   │       ├── vector_store.py     # Operaciones ChromaDB
│   │       └── content_extractor.py
│   ├── uploads/                    # PDFs almacenados
│   ├── chroma_db/                  # Vector store persistente
│   ├── migrations/                 # Migraciones de esquema
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── App.vue                 # Layout principal con sidebar
        └── components/
            ├── documents/          # Vista de documentos
            ├── search/             # Búsqueda full-text
            ├── chat/               # Chat con IA
            ├── origins/            # Gestión de orígenes
            ├── classify/           # Clasificación automática
            └── ui/                 # Componentes shadcn-vue
```

## API

Endpoints principales:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/ingest/upload` | Subir PDF |
| `GET` | `/api/documents/` | Listar documentos |
| `GET` | `/api/documents/search?q=...` | Buscar documentos |
| `GET` | `/api/documents/{id}/preview` | Ver PDF |
| `POST` | `/api/chat/` | Chat RAG |
| `GET` | `/api/origins/` | Listar orígenes |
| `POST` | `/api/classify/single` | Clasificar documento |

Documentación completa disponible en `/docs` (Swagger UI) al correr el backend.
