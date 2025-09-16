#!/usr/bin/env python3
"""
Test script to debug the generator content issue
"""
import sys
import os
sys.path.append('src')

from cobuilder.generator import CoBuilderGenerator, LLMBuild

# Create a mock client that returns a known response
class MockClient:
    def __init__(self):
        self.chat = self.Chat()
    
    class Chat:
        def __init__(self):
            self.completions = self.Completions()
        
        class Completions:
            def create(self, **kwargs):
                # Return a mock response that should work
                class MockResponse:
                    def __init__(self):
                        self.choices = [self.Choice()]
                    
                    class Choice:
                        def __init__(self):
                            self.message = self.Message()
                        
                        class Message:
                            def __init__(self):
                                self.content = '''{
  "response": "Created Venture OS module with version info",
  "file": "src/venture_os/__init__.py",
  "diff": "--- /dev/null\\n+++ src/venture_os/__init__.py\\n@@ -0,0 +1,3 @@\\n+__version__ = \\"0.1.0\\"\\n\\n+# Venture OS - A modular operating system framework\\n",
  "content": "__version__ = \\"0.1.0\\"\\n\\n# Venture OS - A modular operating system framework\\n",
  "snippet": "print(__version__)"
}'''
                
                return MockResponse()

# Test the generator
print("Testing generator with mock client...")
client = MockClient()
gen = CoBuilderGenerator(client, "mock-model")

try:
    result = gen.apply_change(
        prompt="Create src/venture_os/__init__.py with __version__",
        tenant_id="test",
        request_id="test-123",
        deadline_ts=1000000.0
    )
    
    print(f"\n✅ Generation successful!")
    print(f"Response: {result.response}")
    print(f"File: {result.file}")
    print(f"Content length: {len(result.content) if result.content else 0}")
    print(f"Content preview: {repr(result.content[:100]) if result.content else None}")
    print(f"Diff length: {len(result.diff) if result.diff else 0}")
    print(f"Model: {result.model}")
    print(f"LLM generated: {result.llm_generated}")
    
except Exception as e:
    print(f"❌ Generation failed: {e}")
    import traceback
    traceback.print_exc()
