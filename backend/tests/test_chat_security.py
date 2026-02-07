import sys
import os
import pytest
import logging
from unittest.mock import MagicMock

# Ensure backend is in python path
sys.path.insert(0, os.path.abspath("backend"))

# Mock dependencies before import
# We mock modules that are hard to install or configure in this isolated test environment
sys.modules["app.services.vector_store"] = MagicMock()
sys.modules["app.db.database"] = MagicMock()
sys.modules["app.db.models"] = MagicMock()

# Setup specific mock attributes needed for import
sys.modules["app.services.vector_store"].get_index = MagicMock()
sys.modules["app.db.database"].get_db = MagicMock()

class MockDocument:
    pass
class MockOrigen:
    pass

sys.modules["app.db.models"].Document = MockDocument
sys.modules["app.db.models"].Origen = MockOrigen

# Now import the module under test
from app.api.endpoints import chat

@pytest.mark.asyncio
async def test_chat_logging_security(caplog):
    """
    Verify that sensitive query information is not logged.
    """
    sensitive_data = "SENSITIVE_DATA_PASSWORD_123"
    request = chat.ChatRequest(query=f"Hello {sensitive_data}")

    # Configure logging capture
    caplog.set_level(logging.INFO, logger="app.api.endpoints.chat")

    try:
        # Call the function
        # We expect it to fail or succeed depending on mocks, but logging happens early
        await chat.chat(request, db=MagicMock())
    except Exception:
        # Ignore errors from mocks execution
        pass

    # Check logs
    assert "Procesando consulta" in caplog.text, "Expected log message 'Procesando consulta' not found"
    assert sensitive_data not in caplog.text, "SECURITY VULNERABILITY: Sensitive data found in logs!"
