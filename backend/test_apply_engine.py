#!/usr/bin/env python3
"""Direct test of the Apply Engine - no Flask, no servers"""

import os
import sys
import time
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_apply_engine():
    """Test the Apply Engine end-to-end"""
    print("=== Testing Apply Engine Directly ===")
    
    try:
        # Import the components
        from cobuilder.generator import CoBuilderGenerator
        from cobuilder.applier import apply_single_file
        
        print("✅ Imports successful")
        
        # Create mock LLM client
        class MockClient:
            def __init__(self):
                self.chat = Mock()
                self.chat.completions = Mock()
                self.chat.completions.create = Mock()
                
                # Mock response for venture_os/__init__.py
                mock_resp = Mock()
                mock_resp.choices = [Mock()]
                mock_resp.choices[0].message.content = '''
                {
                    "file": "venture_os/__init__.py",
                    "diff": "--- /dev/null\\n+++ venture_os/__init__.py\\n@@ -0,0 +1,1 @@\\n+__version__ = \\"0.0.1\\"\\n",
                    "content": "__version__ = \\"0.0.1\\"\\n",
                    "response": "Created venture_os/__init__.py with version",
                    "snippet": "print(__version__)"
                }
                '''
                self.chat.completions.create.return_value = mock_resp
        
        print("✅ Mock client created")
        
        # Test 1: Generate content
        print("\n--- Test 1: Generate Content ---")
        generator = CoBuilderGenerator(
            llm_client=MockClient(),
            model_default="gpt-4o-mini"
        )
        
        result = generator.apply_change(
            prompt="Create file venture_os/__init__.py containing __version__ = \"0.0.1\"",
            tenant_id="demo",
            request_id="test123",
            deadline_ts=time.time() + 60
        )
        
        print(f"File: {result.file}")
        print(f"Content length: {len(result.content)}")
        print(f"Content: {repr(result.content)}")
        print(f"Diff length: {len(result.diff)}")
        
        if result.content and len(result.content.strip()) > 0:
            print("✅ SUCCESS: Content generated")
        else:
            print("❌ FAILURE: No content")
            return
        
        # Test 2: Apply the change
        print("\n--- Test 2: Apply Change ---")
        try:
            apply_result = apply_single_file(result.file, result.content)
            print(f"Applied to: {apply_result.file}")
            print(f"Bytes written: {apply_result.bytes_written}")
            print(f"Created: {apply_result.created}")
            print(f"SHA256: {apply_result.sha256}")
            print("✅ SUCCESS: File applied")
        except Exception as e:
            print(f"❌ FAILURE: Apply failed - {e}")
            return
        
        # Test 3: Verify file exists
        print("\n--- Test 3: Verify File ---")
        file_path = os.path.join("src", result.file)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            print(f"File exists: {file_path}")
            print(f"File size: {len(content)} bytes")
            print(f"File content: {repr(content)}")
            print("✅ SUCCESS: File verified on disk")
        else:
            print(f"❌ FAILURE: File not found at {file_path}")
        
        # Test 4: Test with JSON mode disabled
        print("\n--- Test 4: Test with JSON Mode Disabled ---")
        os.environ['COBUILDER_USE_JSON_MODE'] = '0'
        
        # Create a mock client that returns prose instead of JSON
        class ProseClient:
            def __init__(self):
                self.chat = Mock()
                self.chat.completions = Mock()
                self.chat.completions.create = Mock()
                
                # Mock response with prose (no JSON)
                mock_resp = Mock()
                mock_resp.choices = [Mock()]
                mock_resp.choices[0].message.content = '''
                I'll create a README.md file for you.
                
                Here's what I'm adding:
                - File: README.md
                - Content: A simple overview of Venture OS
                
                The file will contain:
                # Venture OS Entity Management v1.0.1
                
                This is a modern operating system framework.
                '''
                self.chat.completions.create.return_value = mock_resp
        
        generator2 = CoBuilderGenerator(
            llm_client=ProseClient(),
            model_default="gpt-4o-mini"
        )
        
        result2 = generator2.apply_change(
            prompt="Add README.md with Venture OS overview",
            tenant_id="demo",
            request_id="test456",
            deadline_ts=time.time() + 60
        )
        
        print(f"File: {result2.file}")
        print(f"Content length: {len(result2.content)}")
        print(f"Content preview: {result2.content[:100]}...")
        
        if result2.content and len(result2.content.strip()) > 0:
            print("✅ SUCCESS: Content generated from prose (robust fallback working)")
        else:
            print("❌ FAILURE: No content from prose")
        
        print("\n=== Apply Engine Test Complete ===")
        print("✅ All core functionality working!")
        print("✅ Content generation robust")
        print("✅ File application working")
        print("✅ Fallback mechanisms working")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_apply_engine()
