#!/usr/bin/env python3
"""
Tests for directory creation and verification in full build
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.cobuilder.generators.repo_skeleton import RepoSkeletonGenerator, SkeletonConfig
from src.cobuilder.orchestrator import FullBuildOrchestrator, BuildStep, StepType


class TestDirectoryVerification(unittest.TestCase):
    """Test directory creation and verification"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = SkeletonConfig(project_root=self.temp_dir)
        self.generator = RepoSkeletonGenerator(self.config)
        self.orchestrator = FullBuildOrchestrator()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_directory_structure_success(self):
        """Test that directory creation succeeds and returns correct metadata"""
        build_id = "test_build_dir_123"
        
        with patch.dict(os.environ, {'COB_WORKSPACE': self.temp_dir}):
            result = self.generator.create_default_structure(build_id)
        
        # Check result structure
        self.assertTrue(result["success"])
        self.assertTrue(result["is_directory"])
        self.assertIn("studio/intake_editor", result["file"])
        
        # Check that the directory actually exists
        workspace_path = Path(self.temp_dir) / build_id
        self.assertTrue(workspace_path.exists())
        self.assertTrue(workspace_path.is_dir())
        
        studio_path = workspace_path / "studio"
        self.assertTrue(studio_path.exists())
        self.assertTrue(studio_path.is_dir())
        
        intake_editor_path = studio_path / "intake_editor"
        self.assertTrue(intake_editor_path.exists())
        self.assertTrue(intake_editor_path.is_dir())
    
    def test_directory_verification_passes(self):
        """Test that directory verification correctly identifies directories"""
        build_id = "test_build_verify_456"
        
        with patch.dict(os.environ, {'COB_WORKSPACE': self.temp_dir}):
            result = self.generator.create_default_structure(build_id)
        
        self.assertTrue(result["success"])
        
        # Create a mock step with directory result
        step = BuildStep(
            step_id="create_dir_test",
            step_type=StepType.PATCH,
            description="Test directory creation"
        )
        step.result = {
            "file": result["file"],
            "path": result["path"],
            "lines_changed": result["lines_changed"],
            "anchor_matched": result["anchor_matched"],
            "is_directory": result["is_directory"]
        }
        
        # Test verification
        verification_result = self.orchestrator._run_post_step_verification(step, "test_tenant", build_id)
        self.assertTrue(verification_result, "Directory verification should pass")
    
    def test_file_verification_passes(self):
        """Test that file verification correctly identifies files"""
        # Create a test file
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_file.write_text("Test content")
        
        # Create a mock step with file result
        step = BuildStep(
            step_id="create_file_test",
            step_type=StepType.PATCH,
            description="Test file creation"
        )
        step.result = {
            "file": str(test_file),
            "path": str(test_file),
            "lines_changed": 1,
            "anchor_matched": False,
            "is_directory": False
        }
        
        # Test verification
        verification_result = self.orchestrator._run_post_step_verification(step, "test_tenant", "test_build")
        self.assertTrue(verification_result, "File verification should pass")
    
    def test_verification_fails_for_missing_path(self):
        """Test that verification fails when path doesn't exist"""
        step = BuildStep(
            step_id="missing_path_test",
            step_type=StepType.PATCH,
            description="Test missing path"
        )
        step.result = {
            "file": "/nonexistent/path",
            "path": "/nonexistent/path",
            "lines_changed": 0,
            "anchor_matched": False,
            "is_directory": True
        }
        
        # Test verification
        verification_result = self.orchestrator._run_post_step_verification(step, "test_tenant", "test_build")
        self.assertFalse(verification_result, "Verification should fail for missing path")
    
    def test_verification_fails_for_wrong_type(self):
        """Test that verification fails when expecting directory but finding file"""
        # Create a test file
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_file.write_text("Test content")
        
        # Create a mock step expecting a directory but pointing to a file
        step = BuildStep(
            step_id="wrong_type_test",
            step_type=StepType.PATCH,
            description="Test wrong type"
        )
        step.result = {
            "file": str(test_file),
            "path": str(test_file),
            "lines_changed": 0,
            "anchor_matched": False,
            "is_directory": True  # Expecting directory but file exists
        }
        
        # Test verification
        verification_result = self.orchestrator._run_post_step_verification(step, "test_tenant", "test_build")
        self.assertFalse(verification_result, "Verification should fail for wrong type")
    
    def test_idempotent_directory_creation(self):
        """Test that creating the same directory structure twice is idempotent"""
        build_id = "test_build_idempotent_789"
        
        with patch.dict(os.environ, {'COB_WORKSPACE': self.temp_dir}):
            # Create structure first time
            result1 = self.generator.create_default_structure(build_id)
            self.assertTrue(result1["success"])
            
            # Create structure second time (should succeed)
            result2 = self.generator.create_default_structure(build_id)
            self.assertTrue(result2["success"])
            
            # Both should point to the same directory
            self.assertEqual(result1["file"], result2["file"])
            self.assertTrue(result1["is_directory"])
            self.assertTrue(result2["is_directory"])
    
    def test_verification_logs_to_build_registry(self):
        """Test that verification logs are properly recorded in build registry"""
        from src.cobuilder.persistent_registry import persistent_build_registry
        
        build_id = "test_build_logs_999"
        tenant_id = "test_tenant"
        
        # Create a test file
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_file.write_text("Test content")
        
        # Create a mock step with file result
        step = BuildStep(
            step_id="create_file_test",
            step_type=StepType.PATCH,
            description="Test file creation"
        )
        step.result = {
            "file": str(test_file),
            "path": str(test_file),
            "lines_changed": 1,
            "anchor_matched": False,
            "is_directory": False
        }
        
        # Create a build record
        from src.cobuilder.build_registry import BuildRecord
        build_record = BuildRecord(
            build_id=build_id,
            tenant_id=tenant_id,
            idempotency_key="test_key",
            started_at="2025-01-01T00:00:00Z",
            status="running"
        )
        persistent_build_registry.register_build(build_record)
        
        # Test verification
        verification_result = self.orchestrator._run_post_step_verification(step, tenant_id, build_id)
        self.assertTrue(verification_result, "File verification should pass")
        
        # Check that logs were recorded
        updated_record = persistent_build_registry.get_build(build_id, tenant_id)
        self.assertIsNotNone(updated_record)
        
        # Check for verification logs
        logs = list(updated_record.logs)
        verification_logs = [log for log in logs if "Verifying artifact:" in log or "[OK] Verified file:" in log]
        self.assertGreater(len(verification_logs), 0, "Verification logs should be recorded")


if __name__ == '__main__':
    unittest.main()
