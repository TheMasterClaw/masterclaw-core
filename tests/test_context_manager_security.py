"""
Security tests for context_manager path validation.

These tests verify that the context_manager properly validates file paths
to prevent path traversal attacks.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from masterclaw_core.context_manager import ContextManager, get_context_manager, reset_context_manager


class TestContextManagerPathSecurity:
    """Test path traversal protection in ContextManager"""
    
    @pytest.fixture
    def temp_context_dir(self):
        """Create a temporary context directory with test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_dir = Path(tmpdir) / "context"
            context_dir.mkdir()
            
            # Create test context files
            (context_dir / "projects.md").write_text("# Projects\n\n## Test Project\nStatus: active\n")
            (context_dir / "goals.md").write_text("# Goals\n\n## Test Goal\nStatus: active\n")
            (context_dir / "people.md").write_text("# People\n\n## Test Person\nRole: developer\n")
            (context_dir / "knowledge.md").write_text("# Knowledge\n\n## Topic\nContent: test\n")
            (context_dir / "preferences.md").write_text("# Preferences\n\n## Item\nValue: test\n")
            
            yield context_dir
    
    @pytest.fixture
    def context_manager(self, temp_context_dir):
        """Create a ContextManager with temp directory"""
        reset_context_manager()
        cm = ContextManager(context_dir=str(temp_context_dir))
        yield cm
        reset_context_manager()
    
    def test_read_valid_file(self, context_manager):
        """Should read valid context files successfully"""
        content = context_manager._read_file('projects.md')
        assert content is not None
        assert '# Projects' in content
    
    def test_read_file_path_traversal_blocked(self, context_manager, temp_context_dir):
        """Should block path traversal attempts"""
        # Create a file outside the context directory
        outside_file = temp_context_dir.parent / "secret.txt"
        outside_file.write_text("secret data")
        
        # Attempt to read it via path traversal
        content = context_manager._read_file('../secret.txt')
        assert content is None
    
    def test_read_file_absolute_path_blocked(self, context_manager):
        """Should block absolute paths"""
        content = context_manager._read_file('/etc/passwd')
        assert content is None
    
    def test_read_file_null_byte_blocked(self, context_manager):
        """Should block paths with null bytes"""
        content = context_manager._read_file('file.txt\x00.md')
        assert content is None
    
    def test_read_file_command_injection_blocked(self, context_manager):
        """Should block paths with command injection characters"""
        content = context_manager._read_file('file.txt; rm -rf /')
        assert content is None
    
    def test_read_file_url_encoded_traversal_blocked(self, context_manager):
        """Should block URL-encoded path traversal"""
        content = context_manager._read_file('%2e%2e/%2fetc/passwd')
        assert content is None
    
    def test_read_file_double_traversal_blocked(self, context_manager):
        """Should block double path traversal attempts"""
        content = context_manager._read_file('....//....//etc/passwd')
        assert content is None
    
    def test_read_file_nonexistent_file(self, context_manager):
        """Should return None for non-existent files (not raise exception)"""
        content = context_manager._read_file('nonexistent.md')
        assert content is None
    
    def test_get_projects_with_security(self, context_manager):
        """get_projects should work normally with security in place"""
        projects = context_manager.get_projects()
        assert isinstance(projects, list)
    
    def test_get_goals_with_security(self, context_manager):
        """get_goals should work normally with security in place"""
        goals = context_manager.get_goals()
        assert isinstance(goals, list)
    
    def test_get_people_with_security(self, context_manager):
        """get_people should work normally with security in place"""
        people = context_manager.get_people()
        assert isinstance(people, list)
    
    def test_get_knowledge_with_security(self, context_manager):
        """get_knowledge should work normally with security in place"""
        knowledge = context_manager.get_knowledge()
        assert isinstance(knowledge, list)
    
    def test_get_preferences_with_security(self, context_manager):
        """get_preferences should work normally with security in place"""
        prefs = context_manager.get_preferences()
        assert isinstance(prefs, list)
    
    @pytest.mark.parametrize("attack_path", [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "....//....//etc/passwd",
        "..%2f..%2fetc/passwd",
        "/etc/passwd",
        "C:\\Windows\\System32",
        "file.txt; rm -rf /",
        "file.txt|cat /etc/passwd",
        "file.txt`whoami`",
        "file.txt$(id)",
        "file\x00.txt",
        "../.env",
        "../../config/secrets.yaml",
    ])
    def test_various_attack_vectors_blocked(self, context_manager, attack_path):
        """Test that various attack vectors are all blocked"""
        content = context_manager._read_file(attack_path)
        assert content is None, f"Attack path should be blocked: {attack_path}"


class TestContextManagerSecurityLogging:
    """Test security logging in ContextManager"""
    
    @pytest.fixture
    def temp_context_dir(self):
        """Create a temporary context directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_dir = Path(tmpdir) / "context"
            context_dir.mkdir()
            (context_dir / "projects.md").write_text("# Projects\n")
            yield context_dir
    
    def test_security_warning_logged_on_traversal_attempt(self, temp_context_dir, caplog):
        """Should log security warning when path traversal is attempted"""
        import logging
        
        reset_context_manager()
        cm = ContextManager(context_dir=str(temp_context_dir))
        
        with caplog.at_level(logging.WARNING):
            cm._read_file('../../../etc/passwd')
        
        # Check that a security warning was logged
        security_logs = [r for r in caplog.records if 'Security' in r.message or 'security' in r.message.lower()]
        assert len(security_logs) > 0, "Expected security warning to be logged"
        
        reset_context_manager()


class TestContextManagerEdgeCases:
    """Test edge cases for security"""
    
    @pytest.fixture
    def temp_context_dir(self):
        """Create a temporary context directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_dir = Path(tmpdir) / "context"
            context_dir.mkdir()
            (context_dir / "projects.md").write_text("# Projects\n")
            yield context_dir
    
    def test_empty_filename(self, temp_context_dir):
        """Should handle empty filename gracefully"""
        reset_context_manager()
        cm = ContextManager(context_dir=str(temp_context_dir))
        
        content = cm._read_file('')
        assert content is None
        
        reset_context_manager()
    
    def test_whitespace_only_filename(self, temp_context_dir):
        """Should handle whitespace-only filename gracefully"""
        reset_context_manager()
        cm = ContextManager(context_dir=str(temp_context_dir))
        
        content = cm._read_file('   ')
        assert content is None
        
        reset_context_manager()
    
    def test_very_long_filename(self, temp_context_dir):
        """Should handle very long filename gracefully"""
        reset_context_manager()
        cm = ContextManager(context_dir=str(temp_context_dir))
        
        long_filename = 'a' * 5000
        content = cm._read_file(long_filename)
        assert content is None
        
        reset_context_manager()
