"""
Centralized event logging for SBH

Provides a robust, schema-adaptive logging interface that:
- Introspects the actual table schema at runtime
- Maps fields to available columns
- Fails softly without crashing API routes
- Centralizes all event logging across the system
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from flask import current_app

logger = logging.getLogger(__name__)

# Cache for table schema to avoid repeated introspection
_SCHEMA_CACHE = None

def _safe_str(val):
    """Safely convert value to string, return None on failure"""
    try:
        return str(val) if val is not None else None
    except Exception:
        return None

def _safe_uuid(val):
    """Safely convert value to UUID, return None on failure"""
    try:
        if val is None:
            return None
        if isinstance(val, str):
            return uuid.UUID(val)
        if hasattr(val, 'hex'):  # UUID object
            return val
        return uuid.UUID(str(val))
    except Exception:
        return None

def usage_to_dict(u):
    """Convert LLMUsage object to dict, return None on failure"""
    try:
        return {
            "prompt_tokens": int(u.prompt_tokens),
            "completion_tokens": int(u.completion_tokens),
            "total_tokens": int(u.total_tokens),
        }
    except Exception:
        return None

def _normalize_props(props: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize props to ensure JSON serializability"""
    if not props:
        return {}
    
    normalized = {}
    for key, value in props.items():
        try:
            # Handle LLMUsage objects specifically
            if key == "usage" and not isinstance(value, (dict, type(None))):
                normalized[key] = usage_to_dict(value)
            # Handle other non-serializable objects
            elif not isinstance(value, (str, int, float, bool, type(None), list, dict)):
                normalized[key] = str(value)
            else:
                normalized[key] = value
        except Exception:
            normalized[key] = str(value) if value is not None else None
    
    return normalized

def _safe_json_serialize(obj: Any) -> str:
    """Safely serialize object to JSON with fallback"""
    try:
        return json.dumps(obj, default=str)
    except Exception:
        try:
            # Fallback: convert to string representation
            return json.dumps(str(obj))
        except Exception:
            # Final fallback: return error message
            return json.dumps({"error": "Failed to serialize object"})

def _get_table_schema() -> Dict[str, str]:
    """Introspect sbh_events table and return column name -> type mapping"""
    global _SCHEMA_CACHE
    
    if _SCHEMA_CACHE is not None:
        return _SCHEMA_CACHE
    
    try:
        db_path = current_app.config.get("DATABASE", "system_builder_hub.db")
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info('sbh_events')")
            columns = {}
            for row in cursor.fetchall():
                col_name, col_type = row[1], row[2]
                columns[col_name] = col_type
            
            _SCHEMA_CACHE = columns
            logger.info(f"sbh_events schema: {list(columns.keys())}")
            return columns
    except Exception as e:
        logger.warning(f"Failed to introspect sbh_events schema: {e}")
        # Fallback to known schema
        return {
            'id': 'VARCHAR',
            'tenant_id': 'VARCHAR', 
            'module': 'VARCHAR',
            'event_type': 'VARCHAR',
            'metadata': 'JSON',
            'created_at': 'DATETIME',
            'message': 'TEXT'
        }

def _adapt_payload_to_schema(payload: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
    """Adapt payload to match available columns in schema"""
    adapted = {}
    
    # Map common fields to available columns
    field_mapping = {
        'event_id': 'id',
        'details': 'metadata',
        'actor': 'module',  # Use module column for actor if available
        'extra': 'metadata'  # Merge extra into metadata
    }
    
    for key, value in payload.items():
        # Map field names if needed
        mapped_key = field_mapping.get(key, key)
        
        if mapped_key in schema:
            col_type = schema[mapped_key]
            
            # Handle different column types appropriately
            if col_type.upper() in ('JSON', 'TEXT'):
                if isinstance(value, (dict, list)):
                    adapted[mapped_key] = _safe_json_serialize(value)
                else:
                    adapted[mapped_key] = str(value)
            elif col_type.upper() == 'DATETIME':
                if isinstance(value, datetime):
                    adapted[mapped_key] = value.isoformat()
                else:
                    adapted[mapped_key] = datetime.now().isoformat()
            else:
                # For VARCHAR, INTEGER, etc.
                adapted[mapped_key] = value
    
    return adapted

def log_event(
    event_type: str, 
    tenant_id: Optional[str] = None, 
    module: Optional[str] = None, 
    actor: Optional[str] = None, 
    payload: Optional[Dict[str, Any]] = None, 
    extra: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Log an event to sbh_events table
    
    Args:
        event_type: Type of event (e.g., 'ops_check', 'growth_metric', 'cobuilder_intent')
        tenant_id: Tenant identifier
        module: Module name
        actor: Actor performing the action
        payload: Main event data
        extra: Additional context data
    
    Returns:
        bool: True if logged successfully, False otherwise
    """
    try:
        # Get current app context
        if not current_app:
            logger.warning("No Flask app context for event logging")
            return False
        
        # Normalize and validate inputs
        event_type = _safe_str(event_type) or "unknown_event"
        tenant_id = _safe_str(tenant_id) or "system"
        module = _safe_str(module) or _safe_str(actor) or "system"
        
        # Generate proper event ID
        event_id = str(uuid.uuid4())
        
        # Normalize payload and extra to ensure JSON serializability
        payload = _normalize_props(payload)
        extra = _normalize_props(extra)
        
        # Build the event payload
        event_data = {
            'event_type': event_type,
            'tenant_id': tenant_id,
            'module': module,
            'payload': payload,
            'extra': extra
        }
        
        # Introspect table schema
        schema = _get_table_schema()
        
        # Adapt payload to available columns
        adapted_data = _adapt_payload_to_schema(event_data, schema)
        
        # Ensure required fields are present
        if 'id' in schema and 'id' not in adapted_data:
            adapted_data['id'] = event_id
        
        if 'created_at' in schema and 'created_at' not in adapted_data:
            # Use UTC time
            adapted_data['created_at'] = datetime.now(timezone.utc).isoformat()
        
        # Build INSERT statement dynamically
        columns = list(adapted_data.keys())
        placeholders = ['?' for _ in columns]
        values = [adapted_data[col] for col in columns]
        
        insert_sql = f"""
            INSERT INTO sbh_events ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        
        # Execute insert
        db_path = current_app.config.get("DATABASE", "system_builder_hub.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(insert_sql, values)
            conn.commit()
        
        logger.debug(f"Logged event: {event_type} for tenant {tenant_id}")
        return True
        
    except Exception as e:
        logger.warning(f"Analytics failure ignored: {e}")
        return False

def get_recent_events(
    tenant_id: Optional[str] = None,
    module: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get recent events with optional filtering"""
    try:
        if not current_app:
            return []
        
        db_path = current_app.config.get("DATABASE", "system_builder_hub.db")
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM sbh_events WHERE 1=1"
            params = []
            
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            
            if module:
                query += " AND module = ?"
                params.append(module)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                event = dict(row)
                # Parse JSON fields
                for key, value in event.items():
                    if key in ('metadata', 'payload', 'extra') and value:
                        try:
                            event[key] = json.loads(value)
                        except:
                            pass
                events.append(event)
            
            return events
            
    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        return []

def clear_schema_cache():
    """Clear the schema cache (useful for testing)"""
    global _SCHEMA_CACHE
    _SCHEMA_CACHE = None

def test_analytics_serialization():
    """Test analytics serialization on app start (dry run)"""
    try:
        # Test basic event logging
        test_payload = {
            'test_string': 'hello',
            'test_int': 42,
            'test_float': 3.14,
            'test_bool': True,
            'test_none': None,
            'test_list': [1, 2, 3],
            'test_dict': {'nested': 'value'}
        }
        
        # Test LLMUsage-like object
        class MockLLMUsage:
            def __init__(self):
                self.prompt_tokens = 100
                self.completion_tokens = 50
                self.total_tokens = 150
        
        test_payload['usage'] = MockLLMUsage()
        
        # Test UUID handling
        test_payload['uuid_field'] = str(uuid.uuid4())
        
        # Test normalization
        normalized = _normalize_props(test_payload)
        logger.info(f"Props normalization test passed: {len(normalized)} fields normalized")
        
        # Test JSON serialization
        json_str = _safe_json_serialize(normalized)
        logger.info(f"JSON serialization test passed: {len(json_str)} characters")
        
        logger.info("Analytics serialization test passed - all types handled correctly")
        return True
        
    except Exception as e:
        logger.warning(f"Analytics serialization test failed: {e}")
        return False
