"""
Plugin database client (read-only)
"""
import logging
from typing import Dict, Any, List, Optional
from src.database import db_session

logger = logging.getLogger(__name__)

class DBClient:
    """Plugin database client (read-only)"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def query(self, table: str, filters: Optional[Dict[str, Any]] = None, 
              limit: int = 100) -> List[Dict[str, Any]]:
        """Query table (read-only)"""
        try:
            with db_session() as session:
                # In a real implementation, this would use proper table mapping
                # For now, return mock data
                
                if table == 'users':
                    return [
                        {
                            'id': 'user-1',
                            'email': 'user@example.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'role': 'user'
                        }
                    ]
                elif table == 'projects':
                    return [
                        {
                            'id': 'project-1',
                            'name': 'Test Project',
                            'description': 'A test project',
                            'status': 'active'
                        }
                    ]
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error querying table {table}: {e}")
            return []
    
    def get_by_id(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get record by ID"""
        try:
            results = self.query(table, {'id': record_id}, limit=1)
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error getting record from {table}: {e}")
            return None
    
    def count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in table"""
        try:
            results = self.query(table, filters)
            return len(results)
            
        except Exception as e:
            logger.error(f"Error counting records in {table}: {e}")
            return 0
