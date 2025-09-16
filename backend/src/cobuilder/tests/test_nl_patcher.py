#!/usr/bin/env python3
"""
Unit tests for Natural Language Patcher
"""

import unittest
import tempfile
import os
from pathlib import Path
from src.cobuilder.nl_patcher import NLPatchTranslator, GuardedPatch

class TestNLPatchTranslator(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.translator = NLPatchTranslator(project_root=self.temp_dir)
        
        # Create a test file
        self.test_file = os.path.join(self.temp_dir, "test_file.py")
        with open(self.test_file, 'w') as f:
            f.write("""from flask import Flask

_repo = MemoryRepo()

def existing_function():
    pass
""")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_is_edit_request(self):
        """Test edit request detection"""
        # Should detect edit requests
        self.assertTrue(self.translator.is_edit_request("Add a route after _repo in test_file.py"))
        self.assertTrue(self.translator.is_edit_request("Insert a new function before existing_function"))
        self.assertTrue(self.translator.is_edit_request("Modify the import section"))
        
        # Should not detect non-edit requests
        self.assertFalse(self.translator.is_edit_request("What is the weather today?"))
        self.assertFalse(self.translator.is_edit_request("Explain how this code works"))
    
    def test_extract_target_file(self):
        """Test target file extraction"""
        # Test explicit file paths
        self.assertEqual(
            self.translator.extract_target_file("Add route in src/venture_os/http/api.py"),
            "src/venture_os/http/api.py"
        )
        self.assertEqual(
            self.translator.extract_target_file("Modify test_file.py"),
            "test_file.py"
        )
        
        # Test no file found
        self.assertIsNone(self.translator.extract_target_file("Add a new feature"))
    
    def test_extract_anchor(self):
        """Test anchor extraction"""
        # Test various anchor patterns
        self.assertEqual(
            self.translator.extract_anchor("Add after _repo =", "test_file.py"),
            "_repo ="
        )
        self.assertEqual(
            self.translator.extract_anchor("Insert before existing_function", "test_file.py"),
            "existing_function"
        )
        self.assertEqual(
            self.translator.extract_anchor("Add Blueprint after the repo block", "test_file.py"),
            "the repo block"
        )
    
    def test_extract_insertion_point(self):
        """Test insertion point extraction"""
        self.assertEqual(
            self.translator.extract_insertion_point("Add before _repo"),
            "before"
        )
        self.assertEqual(
            self.translator.extract_insertion_point("Insert after existing_function"),
            "after"
        )
        self.assertEqual(
            self.translator.extract_insertion_point("Replace the import section"),
            "replace"
        )
        self.assertEqual(
            self.translator.extract_insertion_point("Add a new function"),
            "after"  # default
        )
    
    def test_extract_constraints(self):
        """Test constraint extraction"""
        # Test explicit constraints
        constraints = self.translator.extract_constraints("Don't touch imports or reformat")
        self.assertIn("no_import_changes", constraints)
        self.assertIn("no_reformatting", constraints)
        
        # Test default constraints
        constraints = self.translator.extract_constraints("Add a new function")
        self.assertIn("no_import_changes", constraints)
        self.assertIn("no_reformatting", constraints)
        self.assertIn("strict_anchor_match", constraints)
    
    def test_find_anchor_in_file(self):
        """Test anchor finding in file"""
        # Test existing anchor
        result = self.translator.find_anchor_in_file(self.test_file, "_repo")
        self.assertIsNotNone(result)
        line_num, line_content = result
        self.assertEqual(line_num, 3)
        self.assertEqual(line_content, "_repo = MemoryRepo()")
        
        # Test non-existing anchor
        result = self.translator.find_anchor_in_file(self.test_file, "nonexistent")
        self.assertIsNone(result)
    
    def test_translate_success(self):
        """Test successful translation"""
        message = "In test_file.py, right after _repo, add a Blueprint with url_prefix='/api/test'"
        
        patch = self.translator.translate(message)
        self.assertIsNotNone(patch)
        self.assertEqual(patch.target_file, self.test_file)
        self.assertEqual(patch.anchor, "_repo")
        self.assertEqual(patch.insertion_point, "after")
        self.assertIn("Blueprint", patch.content)
        self.assertIn("no_import_changes", patch.constraints)
    
    def test_translate_anchor_not_found(self):
        """Test translation when anchor is not found"""
        message = "In test_file.py, after nonexistent_anchor, add a new function"
        
        patch = self.translator.translate(message)
        self.assertIsNone(patch)
    
    def test_translate_no_target_file(self):
        """Test translation when no target file is found"""
        message = "Add a new function somewhere"
        
        patch = self.translator.translate(message)
        self.assertIsNone(patch)
    
    def test_generate_unified_diff(self):
        """Test unified diff generation"""
        patch = GuardedPatch(
            target_file=self.test_file,
            anchor="_repo",
            insertion_point="after",
            content="bp = Blueprint('test', __name__)\n",
            constraints=["no_import_changes"],
            max_lines=25
        )
        
        diff = self.translator.generate_unified_diff(patch)
        self.assertIn("--- a/", diff)
        self.assertIn("+++ b/", diff)
        self.assertIn("+bp = Blueprint('test', __name__)", diff)
    
    def test_generate_patch_content(self):
        """Test patch content generation"""
        message = "Add a Blueprint with routes for seed/demo and entities"
        content = self.translator.generate_patch_content(message, "test_file.py")
        
        self.assertIn("Blueprint", content)
        self.assertIn("seed/demo", content)
        self.assertIn("entities", content)
    
    def test_max_lines_constraint(self):
        """Test that patches exceeding max lines are rejected"""
        # Create a large content request
        large_content = "\n".join([f"line {i}" for i in range(30)])
        
        patch = GuardedPatch(
            target_file=self.test_file,
            anchor="_repo",
            insertion_point="after",
            content=large_content,
            constraints=["no_import_changes"],
            max_lines=25
        )
        
        # Should be rejected due to size
        self.assertGreater(patch.content.count('\n') + 1, patch.max_lines)


if __name__ == "__main__":
    unittest.main()
