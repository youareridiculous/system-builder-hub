#!/usr/bin/env python3
"""Direct test of the robust generator implementation"""

import os
import sys
import time
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_robust_generator():
    """Test the robust generator directly"""
    print("=== Testing Robust Generator Directly ===")
    
    try:
        from cobuilder.generator import CoBuilderGenerator, _extract_json_candidate, _coerce_llm_build_dict
        
        # Create a mock client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        Here's the file you requested:
        
        ```json
        {
            "file": "src/venture_os/__init__.py",
            "diff": "--- /dev/null\n+++ src/venture_os/__init__.py\n@@ -0,0 +1,3 @@\n+__version__ = '0.1.0'\n+\n+# Venture OS - A modern operating system framework\n",
            "content": "__version__ = '0.1.0'\\n\\n# Venture OS - A modern operating system framework\\n",
            "response": "Created Venture OS init file",
            "snippet": "print(__version__)"
        }
        ```
        '''
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test the JSON extraction helpers
        print("Testing JSON extraction helpers...")
        
        # Test _extract_json_candidate
        candidate = _extract_json_candidate(mock_response.choices[0].message.content)
        print(f"JSON candidate extracted: {candidate is not None}")
        if candidate:
            print(f"Keys found: {list(candidate.keys())}")
        
        # Test _coerce_llm_build_dict
        if candidate:
            coerced = _coerce_llm_build_dict(candidate)
            print(f"Coerced dict: {coerced}")
        
        # Test the generator
        print("\nTesting generator...")
        generator = CoBuilderGenerator(
            llm_client=mock_client,
            model_default="gpt-4o-mini"
        )
        
        # Test with JSON mode disabled
        os.environ['COBUILDER_USE_JSON_MODE'] = '0'
        
        result = generator.apply_change(
            prompt="Create src/venture_os/__init__.py with __version__",
            tenant_id="demo",
            request_id="test123",
            deadline_ts=time.time() + 60
        )
        
        print(f"Generation result:")
        print(f"  File: {result.file}")
        print(f"  Content length: {len(result.content)}")
        print(f"  Content: {repr(result.content[:100])}")
        print(f"  Diff length: {len(result.diff)}")
        
        if result.content and len(result.content.strip()) > 0:
            print("✅ SUCCESS: Content is present and non-empty")
        else:
            print("❌ FAILURE: Content is empty")
            
    except Exception as e:
        print(f"Error testing generator: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_robust_generator()
