"""
Ecosystem Orchestrator (System Provision & Sync)

Provides orchestration for provisioning multi-module systems and running workflows.
"""

import logging
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from src.events import log_event
from .blueprints import SystemBlueprint, get_blueprint
from .contracts import ContractRegistry

logger = logging.getLogger(__name__)

class EcosystemOrchestrator:
    """Orchestrates multi-module system operations"""
    
    def __init__(self):
        self.contract_registry = ContractRegistry()
        self.db_path = "system_builder_hub.db"
    
    def provision_system(self, blueprint_name: str, tenant_id: str) -> Dict[str, Any]:
        """Provision a complete system based on blueprint"""
        try:
            blueprint = get_blueprint(blueprint_name)
            if not blueprint:
                return {
                    'success': False,
                    'error': f'Blueprint not found: {blueprint_name}'
                }
            
            logger.info(f"Provisioning system {blueprint_name} for tenant {tenant_id}")
            
            results = {
                'system_name': blueprint_name,
                'tenant_id': tenant_id,
                'timestamp': datetime.now().isoformat(),
                'modules': [],
                'contracts': [],
                'workflows': [],
                'demo_data_seeded': False
            }
            
            # Provision each module (idempotent)
            for module_name in blueprint.modules:
                module_result = self._provision_module(module_name, tenant_id)
                results['modules'].append(module_result)
            
            # Seed cross-module demo data if empty
            if self._should_seed_demo_data(tenant_id):
                demo_result = self._seed_cross_module_demo_data(blueprint, tenant_id)
                results['demo_data_seeded'] = demo_result['success']
                if demo_result['success']:
                    results['demo_data_summary'] = demo_result['summary']
            
            # Log system provisioning
            log_event(
                'system_provisioned',
                tenant_id=tenant_id,
                module=blueprint_name,
                payload={
                    'blueprint_name': blueprint_name,
                    'modules_count': len(blueprint.modules),
                    'contracts_count': len(blueprint.contracts),
                    'workflows_count': len(blueprint.workflows),
                    'demo_data_seeded': results['demo_data_seeded']
                }
            )
            
            return {
                'success': True,
                'data': results
            }
            
        except Exception as e:
            logger.error(f"System provisioning failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _provision_module(self, module_name: str, tenant_id: str) -> Dict[str, Any]:
        """Provision a single module (idempotent)"""
        try:
            # Check if module is already provisioned
            if self._is_module_provisioned(module_name, tenant_id):
                return {
                    'module': module_name,
                    'status': 'already_provisioned',
                    'tenant_id': tenant_id
                }
            
            # For now, we'll just mark modules as provisioned
            # In a real implementation, this would call the marketplace provision API
            self._mark_module_provisioned(module_name, tenant_id)
            
            return {
                'module': module_name,
                'status': 'provisioned',
                'tenant_id': tenant_id
            }
            
        except Exception as e:
            logger.error(f"Module provisioning failed for {module_name}: {e}")
            return {
                'module': module_name,
                'status': 'failed',
                'error': str(e),
                'tenant_id': tenant_id
            }
    
    def _is_module_provisioned(self, module_name: str, tenant_id: str) -> bool:
        """Check if a module is already provisioned for a tenant"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS provisioned_modules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        module_name TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        provisioned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(module_name, tenant_id)
                    )
                """)
                
                cursor = conn.execute(
                    "SELECT id FROM provisioned_modules WHERE module_name = ? AND tenant_id = ?",
                    (module_name, tenant_id)
                )
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Failed to check module provisioning status: {e}")
            return False
    
    def _mark_module_provisioned(self, module_name: str, tenant_id: str):
        """Mark a module as provisioned for a tenant"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO provisioned_modules (module_name, tenant_id)
                    VALUES (?, ?)
                """, (module_name, tenant_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to mark module as provisioned: {e}")
    
    def _should_seed_demo_data(self, tenant_id: str) -> bool:
        """Check if demo data should be seeded"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if any cross-module data exists
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM students WHERE tenant_id = ? AND source_module != 'lms'
                    UNION ALL
                    SELECT COUNT(*) FROM deals WHERE tenant_id = ? AND source_module != 'crm'
                """, (tenant_id, tenant_id))
                
                counts = cursor.fetchall()
                total_existing = sum(count[0] for count in counts if count[0] is not None)
                
                return total_existing == 0
                
        except Exception as e:
            logger.error(f"Failed to check demo data status: {e}")
            return True
    
    def _seed_cross_module_demo_data(self, blueprint: SystemBlueprint, tenant_id: str) -> Dict[str, Any]:
        """Seed cross-module demo data"""
        try:
            logger.info(f"Seeding cross-module demo data for tenant {tenant_id}")
            
            # Create sample CRM contacts
            crm_contacts = [
                {
                    'id': 'crm_001',
                    'email': 'john.doe@example.com',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'phone': '+1-555-0101',
                    'company': 'Acme Corp',
                    'created_at': datetime.now().isoformat()
                },
                {
                    'id': 'crm_002',
                    'email': 'jane.smith@example.com',
                    'first_name': 'Jane',
                    'last_name': 'Smith',
                    'phone': '+1-555-0102',
                    'company': 'TechStart Inc',
                    'created_at': datetime.now().isoformat()
                }
            ]
            
            # Create sample ERP orders
            erp_orders = [
                {
                    'id': 'erp_001',
                    'customer_id': 'crm_001',
                    'total_amount': 2999.99,
                    'status': 'completed',
                    'notes': 'Premium software license',
                    'completed_at': datetime.now().isoformat()
                },
                {
                    'id': 'erp_002',
                    'customer_id': 'crm_002',
                    'total_amount': 1499.99,
                    'status': 'pending',
                    'notes': 'Consulting services',
                    'completed_at': None
                }
            ]
            
            # Store demo data in ecosystem tables
            self._store_demo_data('crm_contacts', crm_contacts, tenant_id)
            self._store_demo_data('erp_orders', erp_orders, tenant_id)
            
            return {
                'success': True,
                'summary': {
                    'crm_contacts': len(crm_contacts),
                    'erp_orders': len(erp_orders),
                    'tenant_id': tenant_id
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to seed demo data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _store_demo_data(self, data_type: str, records: List[Dict[str, Any]], tenant_id: str):
        """Store demo data in ecosystem tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if data_type == 'crm_contacts':
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS crm_contacts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            contact_id TEXT UNIQUE NOT NULL,
                            email TEXT NOT NULL,
                            first_name TEXT,
                            last_name TEXT,
                            phone TEXT,
                            company TEXT,
                            created_at TEXT,
                            tenant_id TEXT NOT NULL
                        )
                    """)
                    
                    for record in records:
                        conn.execute("""
                            INSERT OR IGNORE INTO crm_contacts 
                            (contact_id, email, first_name, last_name, phone, company, created_at, tenant_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record['id'], record['email'], record['first_name'],
                            record['last_name'], record['phone'], record['company'],
                            record['created_at'], tenant_id
                        ))
                
                elif data_type == 'erp_orders':
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS erp_orders (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            order_id TEXT UNIQUE NOT NULL,
                            customer_id TEXT NOT NULL,
                            total_amount REAL,
                            status TEXT,
                            notes TEXT,
                            completed_at TEXT,
                            tenant_id TEXT NOT NULL
                        )
                    """)
                    
                    for record in records:
                        conn.execute("""
                            INSERT OR IGNORE INTO erp_orders 
                            (order_id, customer_id, total_amount, status, notes, completed_at, tenant_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record['id'], record['customer_id'], record['total_amount'],
                            record['status'], record['notes'], record['completed_at'], tenant_id
                        ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store demo data {data_type}: {e}")
    
    def run_contract(self, contract_name: str, tenant_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """Run a data contract for a tenant"""
        try:
            contract = self.contract_registry.get(contract_name)
            if not contract:
                return {
                    'success': False,
                    'error': f'Contract not found: {contract_name}'
                }
            
            # Get source data based on contract type
            source_records = self._get_source_records(contract, tenant_id)
            
            if not source_records:
                return {
                    'success': False,
                    'error': f'No source data found for contract {contract_name}'
                }
            
            # Run the contract
            result = self.contract_registry.run_contract(
                contract_name, source_records, self.db_path, tenant_id, dry_run
            )
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Contract execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_source_records(self, contract, tenant_id: str) -> List[Dict[str, Any]]:
        """Get source records for a contract"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if contract.source_module == 'crm':
                    cursor = conn.execute(
                        "SELECT * FROM crm_contacts WHERE tenant_id = ?",
                        (tenant_id,)
                    )
                    rows = cursor.fetchall()
                    return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
                
                elif contract.source_module == 'erp':
                    cursor = conn.execute(
                        "SELECT * FROM erp_orders WHERE tenant_id = ?",
                        (tenant_id,)
                    )
                    rows = cursor.fetchall()
                    return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
                
                else:
                    logger.warning(f"Unknown source module: {contract.source_module}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get source records: {e}")
            return []
    
    def run_workflow(self, workflow_name: str, tenant_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """Run a predefined workflow"""
        try:
            logger.info(f"Running workflow {workflow_name} for tenant {tenant_id}")
            
            if workflow_name == 'lead_to_cash':
                return self._run_lead_to_cash_workflow(tenant_id, dry_run)
            elif workflow_name == 'new_customer_360':
                return self._run_new_customer_360_workflow(tenant_id, dry_run)
            else:
                return {
                    'success': False,
                    'error': f'Unknown workflow: {workflow_name}'
                }
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _run_lead_to_cash_workflow(self, tenant_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """Run lead to cash workflow: CRM lead → ERP order"""
        try:
            # Get CRM leads
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM crm_contacts WHERE tenant_id = ? AND company LIKE '%Corp%'
                """, (tenant_id,))
                rows = cursor.fetchall()
                leads = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
            
            if not leads:
                return {
                    'success': True,
                    'workflow': 'lead_to_cash',
                    'tenant_id': tenant_id,
                    'dry_run': dry_run,
                    'message': 'No qualifying leads found',
                    'results': []
                }
            
            results = []
            for lead in leads:
                # Create ERP order from lead
                order_data = {
                    'id': f"order_from_lead_{lead['contact_id']}",
                    'customer_id': lead['contact_id'],
                    'total_amount': 1999.99,  # Default order value
                    'status': 'pending',
                    'notes': f'Generated from CRM lead: {lead["first_name"]} {lead["last_name"]}',
                    'completed_at': None
                }
                
                if not dry_run:
                    # Store the order
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("""
                            INSERT OR IGNORE INTO erp_orders 
                            (order_id, customer_id, total_amount, status, notes, completed_at, tenant_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            order_data['id'], order_data['customer_id'], order_data['total_amount'],
                            order_data['status'], order_data['notes'], order_data['completed_at'], tenant_id
                        ))
                        conn.commit()
                
                results.append({
                    'lead_id': lead['contact_id'],
                    'lead_name': f"{lead['first_name']} {lead['last_name']}",
                    'order_id': order_data['id'],
                    'action': 'dry_run' if dry_run else 'created'
                })
            
            # Log workflow execution
            log_event(
                'workflow_executed',
                tenant_id=tenant_id,
                module='ecosystem',
                payload={
                    'workflow_name': 'lead_to_cash',
                    'dry_run': dry_run,
                    'leads_processed': len(leads),
                    'orders_created': len([r for r in results if r['action'] == 'created'])
                }
            )
            
            return {
                'success': True,
                'workflow': 'lead_to_cash',
                'tenant_id': tenant_id,
                'dry_run': dry_run,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Lead to cash workflow failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _run_new_customer_360_workflow(self, tenant_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """Run new customer 360 workflow: stitch CRM+ERP+LMS profile"""
        try:
            # Get new customers (contacts created in last 24 hours)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM crm_contacts WHERE tenant_id = ? 
                    AND created_at > datetime('now', '-1 day')
                """, (tenant_id,))
                rows = cursor.fetchall()
                new_customers = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
            
            if not new_customers:
                return {
                    'success': True,
                    'workflow': 'new_customer_360',
                    'tenant_id': tenant_id,
                    'dry_run': dry_run,
                    'message': 'No new customers in last 24 hours',
                    'results': []
                }
            
            results = []
            for customer in new_customers:
                # Create unified customer profile
                profile = {
                    'customer_id': customer['contact_id'],
                    'name': f"{customer['first_name']} {customer['last_name']}",
                    'email': customer['email'],
                    'company': customer['company'],
                    'modules': ['crm'],
                    'created_at': customer['created_at']
                }
                
                # Check if customer exists in other modules
                if not dry_run:
                    # Sync to LMS (via contract)
                    lms_result = self.run_contract('contacts_sync', tenant_id, dry_run=False)
                    if lms_result['success']:
                        profile['modules'].append('lms')
                    
                    # Create welcome order in ERP
                    with sqlite3.connect(self.db_path) as conn:
                        order_id = f"welcome_{customer['contact_id']}"
                        conn.execute("""
                            INSERT OR IGNORE INTO erp_orders 
                            (order_id, customer_id, total_amount, status, notes, completed_at, tenant_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            order_id, customer['contact_id'], 99.99, 'completed',
                            'Welcome package', datetime.now().isoformat(), tenant_id
                        ))
                        conn.commit()
                        profile['modules'].append('erp')
                
                results.append({
                    'customer_id': customer['contact_id'],
                    'profile': profile,
                    'action': 'dry_run' if dry_run else 'profile_created'
                })
            
            # Log workflow execution
            log_event(
                'workflow_executed',
                tenant_id=tenant_id,
                module='ecosystem',
                payload={
                    'workflow_name': 'new_customer_360',
                    'dry_run': dry_run,
                    'customers_processed': len(new_customers),
                    'profiles_created': len([r for r in results if r['action'] == 'profile_created'])
                }
            )
            
            return {
                'success': True,
                'workflow': 'new_customer_360',
                'tenant_id': tenant_id,
                'dry_run': dry_run,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"New customer 360 workflow failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
