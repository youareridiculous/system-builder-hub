#!/usr/bin/env python3
"""
Tests for repo skeleton workspace functionality
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.cobuilder.generators.repo_skeleton import RepoSkeletonGenerator, SkeletonConfig


class TestRepoSkeletonWorkspace(unittest.TestCase):
    """Test repo skeleton workspace creation"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = SkeletonConfig(project_root=self.temp_dir)
        self.generator = RepoSkeletonGenerator(self.config)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_default_structure_success(self):
        """Test successful creation of default directory structure"""
        build_id = "test_build_123"
        
        with patch.dict(os.environ, {'COB_WORKSPACE': self.temp_dir}):
            result = self.generator.create_default_structure(build_id)
        
        # Check result structure
        self.assertTrue(result["success"])
        self.assertIn("studio/intake_editor", result["file"])
        self.assertEqual(result["lines_changed"], 0)
        self.assertEqual(result["anchor_matched"], False)
        
        # Check that directories were created
        workspace_path = Path(self.temp_dir) / build_id
        self.assertTrue(workspace_path.exists())
        
        studio_path = workspace_path / "studio"
        self.assertTrue(studio_path.exists())
        
        intake_editor_path = studio_path / "intake_editor"
        self.assertTrue(intake_editor_path.exists())
        
        # Check that __init__.py files were created
        studio_init = studio_path / "__init__.py"
        self.assertTrue(studio_init.exists())
        
        intake_init = intake_editor_path / "__init__.py"
        self.assertTrue(intake_init.exists())
    
    def test_create_default_structure_idempotent(self):
        """Test that creating the same structure twice is idempotent"""
        build_id = "test_build_456"
        
        with patch.dict(os.environ, {'COB_WORKSPACE': self.temp_dir}):
            # Create structure first time
            result1 = self.generator.create_default_structure(build_id)
            self.assertTrue(result1["success"])
            
            # Create structure second time (should succeed)
            result2 = self.generator.create_default_structure(build_id)
            self.assertTrue(result2["success"])
            
            # Both should point to the same directory
            self.assertEqual(result1["file"], result2["file"])
    
    def test_create_default_structure_permission_error(self):
        """Test handling of permission errors"""
        build_id = "test_build_789"
        
        # Mock Path.mkdir to raise PermissionError
        with patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied")):
            result = self.generator.create_default_structure(build_id)
        
        # Should return failure with error message
        self.assertFalse(result["success"])
        self.assertIn("Permission denied", result["error"])
        self.assertEqual(result["file"], "")
        self.assertEqual(result["lines_changed"], 0)
    
    def test_safe_workspace_path_resolution(self):
        """Test that workspace path is resolved correctly"""
        build_id = "test_build_path"
        
        # Test with custom workspace
        custom_workspace = Path(self.temp_dir) / "custom_workspace"
        with patch.dict(os.environ, {'COB_WORKSPACE': str(custom_workspace)}):
            workspace = self.generator._get_safe_workspace(build_id)
        
        expected_path = custom_workspace / build_id
        self.assertEqual(workspace, expected_path)
        self.assertTrue(workspace.exists())
    
    def test_safe_workspace_default_fallback(self):
        """Test that workspace falls back to default when COB_WORKSPACE not set"""
        build_id = "test_build_default"
        
        # Remove COB_WORKSPACE from environment
        with patch.dict(os.environ, {}, clear=True):
            workspace = self.generator._get_safe_workspace(build_id)
        
        # Should use default workspace (backend/workspace)
        self.assertIn("workspace", str(workspace))
        self.assertTrue(workspace.exists())


if __name__ == '__main__':
    unittest.main()
