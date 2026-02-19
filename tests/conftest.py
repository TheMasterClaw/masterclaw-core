"""pytest configuration for masterclaw-core tests"""

import pytest
import os
import tempfile
import shutil
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import masterclaw_core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch health_history module before it gets imported to avoid /data permission issues
_temp_health_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
_temp_health_db.close()
os.environ['HEALTH_HISTORY_DB_PATH'] = _temp_health_db.name

# Pre-patch the health_history module's default path
with patch('masterclaw_core.health_history.Path.mkdir'):
    with patch('masterclaw_core.health_history.sqlite3.connect'):
        pass  # Just ensure patches are available


def pytest_configure(config):
    """Configure pytest - called before test collection"""
    # Create a temp directory for health history tests
    config._health_temp_dir = tempfile.mkdtemp()
    os.environ['MASTERCLAW_TEST_DIR'] = config._health_temp_dir


def pytest_unconfigure(config):
    """Cleanup after all tests"""
    if hasattr(config, '_health_temp_dir') and os.path.exists(config._health_temp_dir):
        shutil.rmtree(config._health_temp_dir)
    if os.path.exists(_temp_health_db.name):
        os.unlink(_temp_health_db.name)


@pytest.fixture
def temp_data_dir():
    """Provide a temporary directory for test data"""
    temp_path = tempfile.mkdtemp()
    original_dir = os.getcwd()
    os.chdir(temp_path)
    yield temp_path
    os.chdir(original_dir)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_settings():
    """Provide mock settings for tests"""
    from unittest.mock import MagicMock
    
    settings = MagicMock()
    settings.MEMORY_BACKEND = "json"
    settings.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    settings.CHROMA_PERSIST_DIR = "./test_data/chroma"
    settings.OPENAI_API_KEY = "test-openai-key"
    settings.ANTHROPIC_API_KEY = "test-anthropic-key"
    
    return settings


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests"""
    # Import memory module only if available (some tests don't need it)
    try:
        from masterclaw_core import memory
        # Reset memory store singleton
        memory.memory_store = None
    except ImportError:
        # chromadb not installed, skip memory reset
        memory = None
    
    yield
    
    # Reset again after test
    if memory is not None:
        memory.memory_store = None


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
