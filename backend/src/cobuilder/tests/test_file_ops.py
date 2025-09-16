"""
Tests for file operations helper.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.cobuilder.generators.file_ops import ensure_parents, write_file


class TestFileOps(unittest.TestCase):
    """Test file operations helper functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: os.system(f"rm -rf {self.temp_dir}"))
    
    def test_ensure_parents_creates_directories(self):
        """Test that ensure_parents creates parent directories."""
        nested_path = os.path.join(self.temp_dir, "level1", "level2", "file.txt")
        
        # Should not exist initially
        self.assertFalse(os.path.exists(os.path.dirname(nested_path)))
        
        # Create parents
        ensure_parents(nested_path)
        
        # Should exist now
        self.assertTrue(os.path.exists(os.path.dirname(nested_path)))
        self.assertTrue(os.path.isdir(os.path.dirname(nested_path)))
    
    def test_ensure_parents_handles_existing_directories(self):
        """Test that ensure_parents handles existing directories gracefully."""
        existing_dir = os.path.join(self.temp_dir, "existing")
        os.makedirs(existing_dir)
        
        # Should not raise an exception
        ensure_parents(os.path.join(existing_dir, "file.txt"))
        
        # Directory should still exist
        self.assertTrue(os.path.exists(existing_dir))
    
    def test_write_file_creates_file_with_content(self):
        """Test that write_file creates a file with the specified content."""
        test_path = os.path.join(self.temp_dir, "test_file.txt")
        test_content = "Hello, World!\nThis is a test file.\n"
        
        result = write_file(test_path, test_content)
        
        # Check file was created
        self.assertTrue(os.path.exists(test_path))
        self.assertTrue(os.path.isfile(test_path))
        
        # Check content
        with open(test_path, 'r', encoding='utf-8') as f:
            actual_content = f.read()
        self.assertEqual(actual_content, test_content)
        
        # Check metadata
        self.assertEqual(result["path"], test_path)
        self.assertFalse(result["is_directory"])
        self.assertEqual(result["lines_changed"], 2)
        self.assertIsInstance(result["sha256"], str)
        self.assertEqual(len(result["sha256"]), 64)  # SHA256 hex length
    
    def test_write_file_creates_parent_directories(self):
        """Test that write_file creates parent directories automatically."""
        nested_path = os.path.join(self.temp_dir, "level1", "level2", "nested_file.txt")
        test_content = "Nested file content"
        
        # Parent directories should not exist initially
        self.assertFalse(os.path.exists(os.path.dirname(nested_path)))
        
        result = write_file(nested_path, test_content)
        
        # File and parents should exist now
        self.assertTrue(os.path.exists(nested_path))
        self.assertTrue(os.path.isfile(nested_path))
        
        # Check content
        with open(nested_path, 'r', encoding='utf-8') as f:
            actual_content = f.read()
        self.assertEqual(actual_content, test_content)
    
    def test_write_file_idempotent_no_overwrite(self):
        """Test that write_file with overwrite=False is idempotent."""
        test_path = os.path.join(self.temp_dir, "idempotent_file.txt")
        original_content = "Original content\nLine 2"
        
        # Write file first time
        result1 = write_file(test_path, original_content)
        
        # Write again with overwrite=False
        new_content = "This should not be written"
        result2 = write_file(test_path, new_content, overwrite=False)
        
        # Content should be unchanged
        with open(test_path, 'r', encoding='utf-8') as f:
            actual_content = f.read()
        self.assertEqual(actual_content, original_content)
        
        # Second result should show no changes
        self.assertEqual(result2["lines_changed"], 0)
        self.assertEqual(result1["sha256"], result2["sha256"])
    
    def test_write_file_overwrite_default_behavior(self):
        """Test that write_file overwrites by default."""
        test_path = os.path.join(self.temp_dir, "overwrite_file.txt")
        original_content = "Original content"
        new_content = "New content"
        
        # Write file first time
        write_file(test_path, original_content)
        
        # Write again (default overwrite=True)
        result = write_file(test_path, new_content)
        
        # Content should be updated
        with open(test_path, 'r', encoding='utf-8') as f:
            actual_content = f.read()
        self.assertEqual(actual_content, new_content)
        
        # Result should show changes
        self.assertEqual(result["lines_changed"], 1)
    
    def test_write_file_sha256_consistency(self):
        """Test that SHA256 is computed correctly and consistently."""
        test_path = os.path.join(self.temp_dir, "sha_test.txt")
        test_content = "Test content for SHA256"
        
        result = write_file(test_path, test_content)
        
        # Verify SHA256 matches what we expect
        import hashlib
        expected_sha = hashlib.sha256(test_content.encode('utf-8')).hexdigest()
        self.assertEqual(result["sha256"], expected_sha)
    
    def test_write_file_handles_unicode(self):
        """Test that write_file handles Unicode content correctly."""
        test_path = os.path.join(self.temp_dir, "unicode_test.txt")
        unicode_content = "Hello 世界! 🌍\nUnicode test: café, naïve, résumé"
        
        result = write_file(test_path, unicode_content)
        
        # Check file was created and content is correct
        self.assertTrue(os.path.exists(test_path))
        with open(test_path, 'r', encoding='utf-8') as f:
            actual_content = f.read()
        self.assertEqual(actual_content, unicode_content)
        
        # Check metadata
        self.assertEqual(result["lines_changed"], 2)
        self.assertIsInstance(result["sha256"], str)


if __name__ == '__main__':
    unittest.main()
