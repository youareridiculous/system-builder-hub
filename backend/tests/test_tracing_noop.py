#!/usr/bin/env python3
"""
Test OpenTelemetry tracing no-op functionality
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestTracingNoop(unittest.TestCase):
    """Test tracing no-op functionality"""
    
    def test_tracing_import_safe(self):
        """Test that tracing can be imported safely without OTEL env"""
        try:
            from obs.tracing import setup_tracing, get_tracer, trace_function, trace_span
            
            # Should not raise exceptions
            tracer = setup_tracing()
            self.assertIsNone(tracer)  # No OTEL endpoint configured
            
            tracer = get_tracer()
            self.assertIsNone(tracer)  # No tracer available
            
        except ImportError:
            self.skipTest("OpenTelemetry not available")
    
    def test_trace_function_decorator(self):
        """Test trace function decorator"""
        try:
            from obs.tracing import trace_function
            
            @trace_function("test_function")
            def test_func():
                return "test"
            
            # Should work without exceptions
            result = test_func()
            self.assertEqual(result, "test")
            
        except ImportError:
            self.skipTest("OpenTelemetry not available")
    
    def test_trace_span_context_manager(self):
        """Test trace span context manager"""
        try:
            from obs.tracing import trace_span
            
            with trace_span("test_span"):
                # Should work without exceptions
                pass
            
        except ImportError:
            self.skipTest("OpenTelemetry not available")

if __name__ == '__main__':
    unittest.main()
