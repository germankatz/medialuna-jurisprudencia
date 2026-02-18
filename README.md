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

## Parámetros del pipeline RAG

El sistema RAG tiene parámetros configurables que afectan la calidad de las respuestas del asistente. Están distribuidos en tres archivos del backend.

### LLM (`backend/app/core/config.py`)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `model` | `llama3` | Modelo de Ollama usado para generar respuestas. Puede cambiarse a `llama3.1`, `mistral`, etc. |
| `temperature` | `0.1` | Controla la aleatoriedad de las respuestas. Valores bajos (0.0-0.2) generan respuestas más deterministas y apegadas al contexto. Valores altos (0.7-1.0) generan respuestas más creativas pero menos precisas. Para uso jurídico se recomienda mantenerlo bajo. |
| `request_timeout` | `360.0` | Timeout en segundos para llamadas al LLM. Documentos largos pueden necesitar más tiempo. |

### Chunking semántico (`backend/app/services/ingest_service.py`)

Estos parámetros controlan cómo se dividen los documentos PDF en fragmentos para indexar. **Cambiar estos valores requiere re-ingestar los documentos** (reset + volver a subir, o usar `/api/ingest/reindex`).

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `buffer_size` | `2` | Cantidad de oraciones agrupadas para evaluar similitud semántica entre segmentos. Con 1, cada oración se compara individualmente (más granular, más cortes). Con 2-3, se evalúan grupos de oraciones (menos cortes, chunks más grandes). Para textos jurídicos que tienen argumentos extensos, 2 es un buen balance. |
| `breakpoint_percentile_threshold` | `92` | Percentil de disimilitud a partir del cual se crea un corte entre chunks. Con 80, cualquier diferencia semántica por encima del percentil 80 genera un corte (muchos chunks pequeños). Con 95 (default), solo diferencias muy marcadas generan cortes (pocos chunks grandes). El valor 92 produce chunks de tamaño medio, lo suficientemente grandes para contener argumentos legales completos sin ser demasiado extensos. |

### Retrieval y chat (`backend/app/api/endpoints/chat.py`)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `SIMILARITY_TOP_K` | `10` | Cantidad de chunks recuperados del vector store por consulta. Con 2 (default de LlamaIndex) el modelo tenía muy poco contexto. Con 10, se recuperan suficientes fragmentos para cubrir la mayoría de las consultas. Subir a 15-20 si se necesitan respuestas que crucen múltiples documentos, pero tener en cuenta que más chunks implica mayor consumo de la ventana de contexto del LLM. |
| `MIN_RELEVANCE_THRESHOLD` | `0.55` | Score mínimo de similitud coseno para que un chunk llegue al LLM. Los chunks con score menor son descartados **antes** de la generación. Bajarlo si el modelo dice "no encontré información" para consultas que deberían tener resultados. Subirlo si se filtran respuestas con información irrelevante. |
| `MIN_SOURCE_DISPLAY_THRESHOLD` | `0.60` | Score mínimo para mostrar un documento como fuente en la UI. Más alto que el umbral del LLM para que solo se muestren documentos con relevancia clara al usuario. |

### Vector store (`backend/app/services/vector_store.py`)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `COLLECTION_METADATA` | `{"hnsw:space": "cosine"}` | Métrica de distancia usada por ChromaDB. Debe ser `cosine` porque LlamaIndex calcula scores con `math.exp(-distance)`, fórmula diseñada para distancia coseno (0-2). Con `l2` (default de ChromaDB) los scores quedan artificialmente bajos (~35-39%). **Cambiar este valor requiere eliminar la colección y re-ingestar.** |

---

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
