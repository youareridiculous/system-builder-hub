"""
Dependency health check module with unified schema and required vs optional handling
"""
import importlib
import os
import sys
from typing import Dict, List, Any

# Required dependencies for core functionality
REQUIRED_DEPS_DEV = [
    "flask", "flask_cors", "sqlalchemy", "alembic", "cryptography",
    "requests", "werkzeug", "jwt", "prometheus_client"
]

# Optional dependencies for enhanced functionality
OPTIONAL_DEPS = [
    "redis", "rq", "flask_session", "flask_limiter", "gunicorn", "opentelemetry",
    "sentry_sdk", "structlog", "boto3", "moto", "dns", "psycopg2", "bcrypt", "jinja2", "click"
]

# Package name mappings for import detection
PACKAGE_MAPPINGS = {
    "jwt": "PyJWT",
    "dns": "dnspython",
    "opentelemetry": "opentelemetry-sdk"
}

def _is_development_environment() -> bool:
    """Check if we're in a development environment."""
    env_vars = ["FLASK_ENV", "SBH_ENV", "ENVIRONMENT"]
    for var in env_vars:
        value = os.environ.get(var, "").lower()
        if value in {"development", "dev", "testing", "staging"}:
            return True
    return False

def _is_sqlite_database() -> bool:
    """Check if we're using SQLite database."""
    database_url = os.environ.get("DATABASE_URL", "")
    return database_url.startswith("sqlite://") or not database_url

def _check_module_availability(module_name: str) -> bool:
    """Check if a module is available for import."""
    try:
        # Handle special cases for submodules
        if module_name == "jwt":
            importlib.import_module("jwt")
        elif module_name == "dns":
            importlib.import_module("dns")
        elif module_name == "opentelemetry":
            importlib.import_module("opentelemetry")
        else:
            importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def collect_dependency_status(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Collect comprehensive dependency status.
    
    Args:
        config: Optional configuration dict (currently unused but kept for future extensibility)
    
    Returns:
        Dict with dependency status information
    """
    if config is None:
        config = {}
    
    is_dev = _is_development_environment()
    is_sqlite = _is_sqlite_database()
    
    # Determine required dependencies based on environment
    required_deps = REQUIRED_DEPS_DEV.copy()
    
    # In production with PostgreSQL, psycopg2 becomes required
    if not is_dev and not is_sqlite:
        if "psycopg2" not in required_deps:
            required_deps.append("psycopg2")
    
    # Check all dependencies
    required_missing = []
    optional_missing = []
    summary = {}
    
    # Check required dependencies
    for dep in required_deps:
        present = _check_module_availability(dep)
        summary[dep] = {"present": present, "required": True}
        if not present:
            required_missing.append(dep)
    
    # Check optional dependencies
    for dep in OPTIONAL_DEPS:
        present = _check_module_availability(dep)
        summary[dep] = {"present": present, "required": False}
        if not present:
            optional_missing.append(dep)
    
    # Determine overall dependency status
    deps_ok = len(required_missing) == 0
    
    return {
        "deps": deps_ok,
        "required_missing": required_missing,
        "optional_missing": optional_missing,
        "summary": summary,
        "environment": {
            "is_development": is_dev,
            "is_sqlite": is_sqlite,
            "required_count": len(required_deps),
            "optional_count": len(OPTIONAL_DEPS)
        }
    }

def check_dependencies() -> List[str]:
    """
    Legacy function for backward compatibility.
    Returns list of missing required dependencies.
    """
    status = collect_dependency_status()
    return status["required_missing"]

def get_dependency_status() -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Returns dependency status for readiness endpoint.
    """
    status = collect_dependency_status()
    return {
        'deps': status['deps'],
        'missing_deps': status['required_missing'],
        'optional_missing': status['optional_missing'],
        'total_deps': status['environment']['required_count'] + status['environment']['optional_count'],
        'available_deps': len([s for s in status['summary'].values() if s['present']])
    }

def print_dependency_error(missing_deps: List[str]) -> None:
    """Print a clear error message for missing dependencies."""
    if not missing_deps:
        return
    
    print("❌ Missing required dependencies:")
    for dep in missing_deps:
        package_name = PACKAGE_MAPPINGS.get(dep, dep)
        print(f"   - {package_name}")
    print("\n🔧 To fix, run:")
    print("   pip install -r requirements.txt")
    print("\n💡 If using a virtual environment:")
    print("   python3 -m venv .venv")
    print("   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate")
    print("   pip install -r requirements.txt")
    print("\n🔍 To check dependencies:")
    print("   python -m src.cli check")
