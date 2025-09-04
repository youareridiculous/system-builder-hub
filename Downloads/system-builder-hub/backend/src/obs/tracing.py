"""
OpenTelemetry tracing for SBH
"""
import os
from typing import Optional

def setup_tracing():
    """Setup OpenTelemetry tracing if configured"""
    otel_endpoint = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT')
    service_name = os.environ.get('OTEL_SERVICE_NAME', 'sbh')
    
    if not otel_endpoint:
        return None
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        
        # Create tracer provider
        provider = TracerProvider()
        
        # Create OTLP exporter
        otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
        
        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Get tracer
        tracer = trace.get_tracer(service_name)
        
        return tracer
        
    except ImportError:
        # OpenTelemetry not available
        return None
    except Exception as e:
        # Log error but don't fail
        print(f"Failed to setup OpenTelemetry tracing: {e}")
        return None

def get_tracer():
    """Get OpenTelemetry tracer if available"""
    try:
        from opentelemetry import trace
        return trace.get_tracer("sbh")
    except ImportError:
        return None

def trace_function(name: str):
    """Decorator to trace function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer:
                with tracer.start_as_current_span(name):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator

def trace_span(name: str):
    """Context manager for tracing spans"""
    class TraceSpan:
        def __init__(self, name):
            self.name = name
            self.tracer = get_tracer()
        
        def __enter__(self):
            if self.tracer:
                self.span = self.tracer.start_span(self.name)
                return self.span
            return None
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if hasattr(self, 'span'):
                self.span.end()
    
    return TraceSpan(name)
