"""
Data Contracts (Cross-Module Interop)

Defines contract schema and registry for common interoperability between modules.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
import sqlite3
from contextlib import contextmanager

from src.events import log_event

logger = logging.getLogger(__name__)

class DataContract(ABC):
    """Abstract base class for data contracts"""
    
    def __init__(self, name: str, source_module: str, target_module: str):
        self.name = name
        self.source_module = source_module
        self.target_module = target_module
    
    @abstractmethod
    def validate(self, source_record: Dict[str, Any]) -> List[str]:
        """Validate source record for contract compliance"""
        pass
    
    @abstractmethod
    def transform(self, source_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform source record to target payload"""
        pass
    
    @abstractmethod
    def apply(self, db_path: str, payload: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Apply transformed payload to target module (idempotent upsert)"""
        pass

class ContactsSyncContract(DataContract):
    """Contract for syncing contacts between CRM and LMS"""
    
    def __init__(self):
        super().__init__("contacts_sync", "crm", "lms")
    
    def validate(self, source_record: Dict[str, Any]) -> List[str]:
        """Validate CRM contact record"""
        errors = []
        required_fields = ['id', 'email', 'first_name', 'last_name']
        
        for field in required_fields:
            if not source_record.get(field):
                errors.append(f"Missing required field: {field}")
        
        if source_record.get('email') and '@' not in str(source_record['email']):
            errors.append("Invalid email format")
        
        return errors
    
    def transform(self, source_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CRM contact to LMS student"""
        return {
            'student_id': f"crm_{source_record['id']}",
            'email': source_record['email'],
            'first_name': source_record.get('first_name', ''),
            'last_name': source_record.get('last_name', ''),
            'phone': source_record.get('phone', ''),
            'company': source_record.get('company', ''),
            'status': 'active',
            'enrollment_date': source_record.get('created_at'),
            'source_module': 'crm',
            'source_id': source_record['id']
        }
    
    def apply(self, db_path: str, payload: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Apply student record to LMS (idempotent upsert)"""
        try:
            with _get_db_connection(db_path) as conn:
                # Ensure students table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id TEXT UNIQUE NOT NULL,
                        email TEXT NOT NULL,
                        first_name TEXT,
                        last_name TEXT,
                        phone TEXT,
                        company TEXT,
                        status TEXT DEFAULT 'active',
                        enrollment_date TEXT,
                        source_module TEXT,
                        source_id TEXT,
                        tenant_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check if student exists
                cursor = conn.execute(
                    "SELECT id FROM students WHERE student_id = ? AND tenant_id = ?",
                    (payload['student_id'], tenant_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing student
                    conn.execute("""
                        UPDATE students SET
                            email = ?, first_name = ?, last_name = ?, phone = ?,
                            company = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE student_id = ? AND tenant_id = ?
                    """, (
                        payload['email'], payload['first_name'], payload['last_name'],
                        payload['phone'], payload['company'], payload['status'],
                        payload['student_id'], tenant_id
                    ))
                    action = 'updated'
                else:
                    # Insert new student
                    conn.execute("""
                        INSERT INTO students (
                            student_id, email, first_name, last_name, phone, company,
                            status, enrollment_date, source_module, source_id, tenant_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        payload['student_id'], payload['email'], payload['first_name'],
                        payload['last_name'], payload['phone'], payload['company'],
                        payload['status'], payload['enrollment_date'], payload['source_module'],
                        payload['source_id'], tenant_id
                    ))
                    action = 'created'
                
                conn.commit()
                
                return {
                    'success': True,
                    'action': action,
                    'student_id': payload['student_id'],
                    'tenant_id': tenant_id
                }
                
        except Exception as e:
            logger.error(f"Failed to apply contacts sync contract: {e}")
            return {
                'success': False,
                'error': str(e),
                'student_id': payload.get('student_id'),
                'tenant_id': tenant_id
            }

class OrdersToDealsContract(DataContract):
    """Contract for converting ERP orders to CRM deals"""
    
    def __init__(self):
        super().__init__("orders_to_deals", "erp", "crm")
    
    def validate(self, source_record: Dict[str, Any]) -> List[str]:
        """Validate ERP order record"""
        errors = []
        required_fields = ['id', 'customer_id', 'total_amount', 'status']
        
        for field in required_fields:
            if not source_record.get(field):
                errors.append(f"Missing required field: {field}")
        
        if source_record.get('total_amount') and float(source_record['total_amount']) <= 0:
            errors.append("Order amount must be positive")
        
        return errors
    
    def transform(self, source_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ERP order to CRM deal"""
        return {
            'deal_id': f"erp_{source_record['id']}",
            'title': f"Order #{source_record['id']}",
            'amount': source_record['total_amount'],
            'stage': 'closed_won' if source_record['status'] == 'completed' else 'prospecting',
            'customer_id': source_record['customer_id'],
            'close_date': source_record.get('completed_at'),
            'source_module': 'erp',
            'source_id': source_record['id'],
            'description': f"Order from ERP system: {source_record.get('notes', '')}"
        }
    
    def apply(self, db_path: str, payload: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Apply deal record to CRM (idempotent upsert)"""
        try:
            with _get_db_connection(db_path) as conn:
                # Ensure deals table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS deals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        deal_id TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        amount REAL,
                        stage TEXT DEFAULT 'prospecting',
                        customer_id TEXT,
                        close_date TEXT,
                        source_module TEXT,
                        source_id TEXT,
                        description TEXT,
                        tenant_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check if deal exists
                cursor = conn.execute(
                    "SELECT id FROM deals WHERE deal_id = ? AND tenant_id = ?",
                    (payload['deal_id'], tenant_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing deal
                    conn.execute("""
                        UPDATE deals SET
                            title = ?, amount = ?, stage = ?, customer_id = ?,
                            close_date = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE deal_id = ? AND tenant_id = ?
                    """, (
                        payload['title'], payload['amount'], payload['stage'],
                        payload['customer_id'], payload['close_date'], payload['description'],
                        payload['deal_id'], tenant_id
                    ))
                    action = 'updated'
                else:
                    # Insert new deal
                    conn.execute("""
                        INSERT INTO deals (
                            deal_id, title, amount, stage, customer_id, close_date,
                            source_module, source_id, description, tenant_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        payload['deal_id'], payload['title'], payload['amount'],
                        payload['stage'], payload['customer_id'], payload['close_date'],
                        payload['source_module'], payload['source_id'], payload['description'],
                        tenant_id
                    ))
                    action = 'created'
                
                conn.commit()
                
                return {
                    'success': True,
                    'action': action,
                    'deal_id': payload['deal_id'],
                    'tenant_id': tenant_id
                }
                
        except Exception as e:
            logger.error(f"Failed to apply orders to deals contract: {e}")
            return {
                'success': False,
                'error': str(e),
                'deal_id': payload.get('deal_id'),
                'tenant_id': tenant_id
            }

class ContractRegistry:
    """Registry for managing data contracts"""
    
    def __init__(self):
        self.contracts = {}
        self._register_default_contracts()
    
    def _register_default_contracts(self):
        """Register default contracts"""
        self.register(ContactsSyncContract())
        self.register(OrdersToDealsContract())
    
    def register(self, contract: DataContract):
        """Register a data contract"""
        self.contracts[contract.name] = contract
        logger.info(f"Registered data contract: {contract.name}")
    
    def get(self, name: str) -> Optional[DataContract]:
        """Get a contract by name"""
        return self.contracts.get(name)
    
    def list_contracts(self) -> List[Dict[str, Any]]:
        """List all registered contracts"""
        return [
            {
                'name': contract.name,
                'source_module': contract.source_module,
                'target_module': contract.target_module
            }
            for contract in self.contracts.values()
        ]
    
    def run_contract(self, contract_name: str, source_records: List[Dict[str, Any]], 
                    db_path: str, tenant_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """Run a data contract"""
        contract = self.get(contract_name)
        if not contract:
            return {
                'success': False,
                'error': f'Contract not found: {contract_name}'
            }
        
        results = {
            'contract_name': contract_name,
            'tenant_id': tenant_id,
            'dry_run': dry_run,
            'total_records': len(source_records),
            'validated': 0,
            'transformed': 0,
            'applied': 0,
            'errors': [],
            'details': []
        }
        
        for i, record in enumerate(source_records):
            try:
                # Validate
                validation_errors = contract.validate(record)
                if validation_errors:
                    results['errors'].append(f"Record {i}: {validation_errors}")
                    continue
                
                results['validated'] += 1
                
                # Transform
                payload = contract.transform(record)
                results['transformed'] += 1
                
                if not dry_run:
                    # Apply
                    apply_result = contract.apply(db_path, payload, tenant_id)
                    if apply_result['success']:
                        results['applied'] += 1
                        results['details'].append({
                            'record_index': i,
                            'action': apply_result['action'],
                            'target_id': apply_result.get('deal_id') or apply_result.get('student_id')
                        })
                    else:
                        results['errors'].append(f"Record {i}: {apply_result['error']}")
                else:
                    results['details'].append({
                        'record_index': i,
                        'action': 'dry_run',
                        'payload': payload
                    })
                
            except Exception as e:
                results['errors'].append(f"Record {i}: {str(e)}")
                logger.error(f"Contract execution failed for record {i}: {e}")
        
        # Log contract execution
        log_event(
            'contract_executed',
            tenant_id=tenant_id,
            module=f"{contract.source_module}_to_{contract.target_module}",
            payload={
                'contract_name': contract_name,
                'dry_run': dry_run,
                'total_records': results['total_records'],
                'applied': results['applied'],
                'errors_count': len(results['errors'])
            }
        )
        
        return results

@contextmanager
def _get_db_connection(db_path: str):
    """Get database connection with proper cleanup"""
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()
