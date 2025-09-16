"""
Integration smoke test for .env file creation in Pass-1 scaffold.
"""

import os
import tempfile
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cobuilder.generators.repo_scaffold import _create_env_files


def test_env_files_created_with_correct_paths():
    """Test that .env files are created with correct content and paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Capture log output
        import io
        from contextlib import redirect_stdout
        
        log_output = io.StringIO()
        
        # Run the env creation function with captured output
        with redirect_stdout(log_output):
            result = _create_env_files(temp_dir)
        
        logs = log_output.getvalue()
        
        # Check that both files were created
        assert result["root_env"]["status"] == "created"
        assert result["prisma_env"]["status"] == "created"
        
        # Check that files exist
        root_env_path = os.path.join(temp_dir, ".env")
        prisma_env_path = os.path.join(temp_dir, "prisma", ".env")
        
        assert os.path.exists(root_env_path), "Root .env file should exist"
        assert os.path.exists(prisma_env_path), "Prisma .env file should exist"
        
        # Check content
        with open(root_env_path, 'r') as f:
            root_content = f.read()
        assert 'DATABASE_URL="file:./apps/site/dev.db"' in root_content, "Root .env should contain correct DATABASE_URL"
        
        with open(prisma_env_path, 'r') as f:
            prisma_content = f.read()
        assert 'DATABASE_URL="file:../apps/site/dev.db"' in prisma_content, "Prisma .env should contain correct DATABASE_URL"
        
        # Check that logs contain absolute paths
        assert f"workspace_dir={os.path.abspath(temp_dir)}" in logs, "Logs should contain absolute workspace path"
        assert f"root_env_path={os.path.abspath(root_env_path)}" in logs, "Logs should contain absolute root .env path"
        assert f"prisma_env_path={os.path.abspath(prisma_env_path)}" in logs, "Logs should contain absolute prisma .env path"
        assert f".env: wrote -> {os.path.abspath(root_env_path)}" in logs, "Logs should show .env was written"
        assert f"prisma/.env: wrote -> {os.path.abspath(prisma_env_path)}" in logs, "Logs should show prisma/.env was written"


def test_env_files_idempotent():
    """Test that re-invoking scaffold doesn't overwrite existing .env files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # First run
        result1 = _create_env_files(temp_dir)
        assert result1["root_env"]["status"] == "created"
        assert result1["prisma_env"]["status"] == "created"
        
        # Capture content
        root_env_path = os.path.join(temp_dir, ".env")
        prisma_env_path = os.path.join(temp_dir, "prisma", ".env")
        
        with open(root_env_path, 'r') as f:
            original_root_content = f.read()
        with open(prisma_env_path, 'r') as f:
            original_prisma_content = f.read()
        
        # Second run
        import io
        from contextlib import redirect_stdout
        
        log_output = io.StringIO()
        with redirect_stdout(log_output):
            result2 = _create_env_files(temp_dir)
        
        logs = log_output.getvalue()
        
        # Should be marked as existing
        assert result2["root_env"]["status"] == "exists"
        assert result2["prisma_env"]["status"] == "exists"
        
        # Content should be unchanged
        with open(root_env_path, 'r') as f:
            new_root_content = f.read()
        with open(prisma_env_path, 'r') as f:
            new_prisma_content = f.read()
        
        assert new_root_content == original_root_content, "Root .env content should not change"
        assert new_prisma_content == original_prisma_content, "Prisma .env content should not change"
        
        # Logs should show skipping
        assert "exists, skipping" in logs, "Logs should show files were skipped"


if __name__ == "__main__":
    test_env_files_created_with_correct_paths()
    test_env_files_idempotent()
    print("✅ All Pass-1 smoke tests passed!")
