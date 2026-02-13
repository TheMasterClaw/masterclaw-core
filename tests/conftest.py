"""pytest configuration for masterclaw-core tests"""

import pytest
import os
import tempfile
import shutil
import sys

# Add the parent directory to the path so we can import masterclaw_core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    from masterclaw_core import memory
    
    # Reset memory store singleton
    memory.memory_store = None
    
    yield
    
    # Reset again after test
    memory.memory_store = None


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
