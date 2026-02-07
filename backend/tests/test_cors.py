import sys
import os
import types
from unittest.mock import MagicMock

# Set backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Helper to mock a module
def mock_module(name):
    if name not in sys.modules:
        sys.modules[name] = MagicMock()

# List of modules to mock
modules_to_mock = [
    "llama_index",
    "llama_index.core",
    "llama_index.core.node_parser",
    "llama_index.llms",
    "llama_index.llms.ollama",
    "llama_index.embeddings",
    "llama_index.embeddings.huggingface",
    "llama_index.vector_stores",
    "llama_index.vector_stores.chroma",
    "chromadb",
    "chromadb.config",
    "app.db.database", # Mock only the database connection module
]

# Apply mocks
for module in modules_to_mock:
    mock_module(module)

# Now import app
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_policy():
    """Verify that CORS policy is restrictive and allows specific origins."""

    # 1. Verify disallowed origin
    # Should NOT return Access-Control-Allow-Origin header
    response_evil = client.get("/", headers={"Origin": "http://evil.com"})
    assert response_evil.status_code == 200
    assert "access-control-allow-origin" not in response_evil.headers

    # 2. Verify allowed origin (default: http://localhost:5173)
    response_allowed = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert response_allowed.status_code == 200
    assert response_allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response_allowed.headers["access-control-allow-credentials"] == "true"
