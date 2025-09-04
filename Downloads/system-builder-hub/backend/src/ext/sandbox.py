"""
Plugin sandbox for safe execution
"""
import time
import signal
import logging
import threading
from typing import Any, Dict, Optional, Callable
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class SandboxError(Exception):
    """Sandbox execution error"""
    pass

class TimeoutError(SandboxError):
    """Execution timeout error"""
    pass

class MemoryError(SandboxError):
    """Memory limit exceeded error"""
    pass

class ForbiddenImportError(SandboxError):
    """Forbidden import error"""
    pass

class PluginSandbox:
    """Sandbox for safe plugin execution"""
    
    def __init__(self, timeout_seconds: int = 5, memory_limit_mb: int = 100):
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        
        # Allowed imports
        self.allowed_imports = {
            'json', 'datetime', 'time', 'uuid', 'hashlib', 'base64',
            'urllib.parse', 'collections', 'itertools', 'functools',
            're', 'math', 'random', 'string'
        }
    
    @contextmanager
    def execute(self, func: Callable, *args, **kwargs):
        """Execute function in sandbox"""
        try:
            # Set up timeout
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            # Create thread for execution
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            
            # Wait for completion or timeout
            thread.join(timeout=self.timeout_seconds)
            
            if thread.is_alive():
                # Timeout occurred
                raise TimeoutError(f"Execution timed out after {self.timeout_seconds} seconds")
            
            if exception[0]:
                raise exception[0]
            
            yield result[0]
            
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            raise
    
    def validate_imports(self, code: str) -> bool:
        """Validate that code doesn't contain forbidden imports"""
        try:
            forbidden_imports = [
                'import os', 'import sys', 'import subprocess',
                'from os import', 'from sys import', 'from subprocess import',
                '__import__', 'eval', 'exec', 'compile'
            ]
            
            for forbidden_import in forbidden_imports:
                if forbidden_import in code:
                    logger.warning(f"Forbidden import found: {forbidden_import}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating imports: {e}")
            return False
    
    def check_memory_usage(self) -> bool:
        """Check if memory usage is within limits"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.memory_limit_mb:
                logger.warning(f"Memory usage {memory_mb:.2f}MB exceeds limit {self.memory_limit_mb}MB")
                return False
            
            return True
            
        except ImportError:
            # psutil not available, skip memory check
            return True
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
            return True
    
    def capture_output(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Capture stdout/stderr from function execution"""
        import io
        import sys
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            with self.execute(func, *args, **kwargs) as result:
                return {
                    'result': result,
                    'stdout': stdout_capture.getvalue(),
                    'stderr': stderr_capture.getvalue(),
                    'success': True
                }
                
        except Exception as e:
            return {
                'result': None,
                'stdout': stdout_capture.getvalue(),
                'stderr': stderr_capture.getvalue(),
                'error': str(e),
                'success': False
            }
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def execute_with_limits(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Execute function with all safety limits"""
        try:
            # Check memory before execution
            if not self.check_memory_usage():
                raise MemoryError("Memory usage exceeds limits")
            
            # Execute with timeout and output capture
            result = self.capture_output(func, *args, **kwargs)
            
            # Check memory after execution
            if not self.check_memory_usage():
                raise MemoryError("Memory usage exceeded limits during execution")
            
            return result
            
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return {
                'result': None,
                'stdout': '',
                'stderr': '',
                'error': str(e),
                'success': False
            }

# Global sandbox instance
plugin_sandbox = PluginSandbox()
