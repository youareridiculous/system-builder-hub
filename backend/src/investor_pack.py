#!/usr/bin/env python3
"""
P40: Investor Pack Generator
Generate comprehensive investor packs with financial models, risk assessments, and data room access.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import tempfile
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app, send_file
from flask_cors import cross_origin

# Import infrastructure components
from config import config
from metrics import metrics
from feature_flags import flag_required
from idempotency import idempotent, require_idempotency_key
from trace_context import get_current_trace
from costs import cost_accounted, log_with_redaction
from multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Create blueprint
investor_pack_bp = Blueprint('investor_pack', __name__, url_prefix='/api/investor')

# Data Models
class PackStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class FinancialModelType(Enum):
    REVENUE_PROJECTION = "revenue_projection"
    CASH_FLOW = "cash_flow"
    UNIT_ECONOMICS = "unit_economics"
    VALUATION = "valuation"

@dataclass
class InvestorPack:
    id: str
    tenant_id: str
    system_id: str
    version: str
    summary_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class FinancialModel:
    id: str
    pack_id: str
    model_type: FinancialModelType
    assumptions_json: Dict[str, Any]
    projections_json: Dict[str, Any]
    created_at: datetime

class InvestorPackService:
    """Service for investor pack generation and management"""
    
    def __init__(self):
        self._init_database()
        self.financial_templates = self._load_financial_templates()
    
    def _init_database(self):
        """Initialize investor pack database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create investor_packs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS investor_packs (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        summary_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create financial_models table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS financial_models (
                        id TEXT PRIMARY KEY,
                        pack_id TEXT NOT NULL,
                        model_type TEXT NOT NULL,
                        assumptions_json TEXT NOT NULL,
                        projections_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (pack_id) REFERENCES investor_packs (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Investor pack database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize investor pack database: {e}")
    
    def _load_financial_templates(self) -> Dict[str, Any]:
        """Load financial modeling templates"""
        return {
            'saas': {
                'revenue_drivers': ['Monthly Recurring Revenue', 'Annual Recurring Revenue', 'Customer Lifetime Value'],
                'cost_structure': ['Customer Acquisition Cost', 'Cost of Goods Sold', 'Operating Expenses'],
                'growth_assumptions': ['Customer Growth Rate', 'Revenue Growth Rate', 'Churn Rate']
            },
            'marketplace': {
                'revenue_drivers': ['Transaction Volume', 'Commission Rate', 'Subscription Revenue'],
                'cost_structure': ['Payment Processing', 'Customer Support', 'Platform Development'],
                'growth_assumptions': ['User Growth Rate', 'Transaction Growth Rate', 'Market Penetration']
            },
            'enterprise': {
                'revenue_drivers': ['License Revenue', 'Professional Services', 'Maintenance Revenue'],
                'cost_structure': ['Sales and Marketing', 'Research and Development', 'General and Administrative'],
                'growth_assumptions': ['Market Expansion', 'Product Development', 'Customer Retention']
            }
        }
    
    def generate_investor_pack(self, system_id: str, tenant_id: str, 
                              custom_data: Optional[Dict[str, Any]] = None) -> Optional[InvestorPack]:
        """Generate comprehensive investor pack for system"""
        try:
            pack_id = f"pack_{int(time.time())}"
            version = "1.0.0"
            now = datetime.now()
            
            # Analyze system and generate pack content
            pack_content = self._analyze_system_and_generate_pack(system_id, custom_data)
            
            pack = InvestorPack(
                id=pack_id,
                tenant_id=tenant_id,
                system_id=system_id,
                version=version,
                summary_json=pack_content,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO investor_packs 
                    (id, tenant_id, system_id, version, summary_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pack.id,
                    pack.tenant_id,
                    pack.system_id,
                    pack.version,
                    json.dumps(pack.summary_json),
                    pack.created_at.isoformat(),
                    json.dumps(pack.metadata)
                ))
                conn.commit()
            
            # Generate financial models
            self._generate_financial_models(pack_id, pack_content)
            
            # Update metrics
            metrics.increment_counter('sbh_investor_pack_generate_total', {'tenant_id': tenant_id})
            
            logger.info(f"Generated investor pack: {pack_id}")
            return pack
            
        except Exception as e:
            logger.error(f"Failed to generate investor pack: {e}")
            return None
    
    def _analyze_system_and_generate_pack(self, system_id: str, custom_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze system and generate investor pack content"""
        # TODO: Integrate with actual system analysis
        # For now, generate mock pack content
        
        pack_content = {
            'executive_summary': {
                'company_overview': 'AI-powered automation platform for enterprise operations',
                'problem_solved': 'Manual processes costing businesses $2.7T annually',
                'solution': 'Intelligent automation platform reducing costs by 40%',
                'market_opportunity': '$50B TAM, $5B SAM, $500M SOM',
                'traction': '500+ customers, $10M ARR, 300% YoY growth',
                'team': '25 employees, 3 co-founders with 15+ years experience',
                'funding_ask': '$10M Series A for market expansion'
            },
            'market_analysis': {
                'market_size': {
                    'tam': 50000000000,
                    'sam': 5000000000,
                    'som': 500000000
                },
                'growth_rate': '15% CAGR',
                'key_drivers': ['Digital transformation', 'Cost pressure', 'AI adoption'],
                'competitive_landscape': {
                    'direct_competitors': ['UiPath', 'Automation Anywhere', 'Blue Prism'],
                    'competitive_advantage': 'AI-first approach, faster implementation, lower cost'
                }
            },
            'business_model': {
                'revenue_model': 'SaaS subscription with usage-based pricing',
                'pricing': {
                    'starter': 99,
                    'professional': 299,
                    'enterprise': 999
                },
                'customer_segments': ['Mid-market (100-1000 employees)', 'Enterprise (1000+ employees)'],
                'sales_motion': 'Product-led growth with enterprise sales overlay'
            },
            'traction_metrics': {
                'customers': 500,
                'arr': 10000000,
                'growth_rate': 300,
                'churn_rate': 5,
                'cac': 5000,
                'ltv': 50000,
                'ltv_cac_ratio': 10
            },
            'team': {
                'founders': [
                    {'name': 'CEO', 'background': 'Ex-Google, Stanford MBA'},
                    {'name': 'CTO', 'background': 'Ex-Microsoft, PhD AI'},
                    {'name': 'CPO', 'background': 'Ex-Salesforce, Product expert'}
                ],
                'employees': 25,
                'key_hires': ['VP Sales', 'VP Engineering', 'VP Marketing']
            },
            'financial_highlights': {
                'current_arr': 10000000,
                'projected_arr_12m': 30000000,
                'projected_arr_24m': 75000000,
                'burn_rate': 500000,
                'runway_months': 20,
                'unit_economics': 'Profitable at scale'
            },
            'use_of_funds': {
                'sales_marketing': 4000000,
                'product_development': 3000000,
                'operations': 2000000,
                'working_capital': 1000000
            },
            'risk_factors': [
                'Market competition intensifying',
                'Economic downturn affecting sales',
                'Talent acquisition challenges',
                'Regulatory changes in target markets'
            ]
        }
        
        if custom_data:
            pack_content['custom_data'] = custom_data
        
        return pack_content
    
    def _generate_financial_models(self, pack_id: str, pack_content: Dict[str, Any]):
        """Generate financial models for investor pack"""
        try:
            models = [
                self._create_revenue_projection_model(pack_id, pack_content),
                self._create_cash_flow_model(pack_id, pack_content),
                self._create_unit_economics_model(pack_id, pack_content),
                self._create_valuation_model(pack_id, pack_content)
            ]
            
            for model in models:
                if model:
                    self._save_financial_model(model)
                    
        except Exception as e:
            logger.error(f"Failed to generate financial models: {e}")
    
    def _create_revenue_projection_model(self, pack_id: str, pack_content: Dict[str, Any]) -> Optional[FinancialModel]:
        """Create revenue projection model"""
        try:
            model_id = f"model_{int(time.time())}"
            now = datetime.now()
            
            # Extract data from pack content
            current_arr = pack_content['financial_highlights']['current_arr']
            growth_rate = pack_content['traction_metrics']['growth_rate'] / 100
            
            # Generate 5-year projection
            projections = {}
            assumptions = {
                'starting_arr': current_arr,
                'growth_rate': growth_rate,
                'churn_rate': pack_content['traction_metrics']['churn_rate'] / 100,
                'expansion_rate': 0.15  # 15% expansion revenue
            }
            
            for year in range(1, 6):
                if year == 1:
                    projections[f'year_{year}'] = current_arr * (1 + growth_rate)
                else:
                    # Decay growth rate by 20% each year
                    decayed_growth = growth_rate * (0.8 ** (year - 1))
                    projections[f'year_{year}'] = projections[f'year_{year-1}'] * (1 + decayed_growth)
            
            return FinancialModel(
                id=model_id,
                pack_id=pack_id,
                model_type=FinancialModelType.REVENUE_PROJECTION,
                assumptions_json=assumptions,
                projections_json=projections,
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create revenue projection model: {e}")
            return None
    
    def _create_cash_flow_model(self, pack_id: str, pack_content: Dict[str, Any]) -> Optional[FinancialModel]:
        """Create cash flow model"""
        try:
            model_id = f"model_{int(time.time())}"
            now = datetime.now()
            
            assumptions = {
                'starting_cash': 2000000,
                'burn_rate': pack_content['financial_highlights']['burn_rate'],
                'funding_rounds': [
                    {'amount': 10000000, 'month': 0},
                    {'amount': 25000000, 'month': 18},
                    {'amount': 50000000, 'month': 36}
                ]
            }
            
            projections = {
                'monthly_burn': pack_content['financial_highlights']['burn_rate'],
                'runway_months': pack_content['financial_highlights']['runway_months'],
                'break_even_month': 24
            }
            
            return FinancialModel(
                id=model_id,
                pack_id=pack_id,
                model_type=FinancialModelType.CASH_FLOW,
                assumptions_json=assumptions,
                projections_json=projections,
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create cash flow model: {e}")
            return None
    
    def _create_unit_economics_model(self, pack_id: str, pack_content: Dict[str, Any]) -> Optional[FinancialModel]:
        """Create unit economics model"""
        try:
            model_id = f"model_{int(time.time())}"
            now = datetime.now()
            
            assumptions = {
                'cac': pack_content['traction_metrics']['cac'],
                'ltv': pack_content['traction_metrics']['ltv'],
                'payback_period': 12,  # months
                'gross_margin': 0.85,  # 85%
                'net_margin': 0.25     # 25%
            }
            
            projections = {
                'ltv_cac_ratio': pack_content['traction_metrics']['ltv_cac_ratio'],
                'payback_period_months': 12,
                'gross_margin': 0.85,
                'net_margin': 0.25,
                'contribution_margin': 0.60
            }
            
            return FinancialModel(
                id=model_id,
                pack_id=pack_id,
                model_type=FinancialModelType.UNIT_ECONOMICS,
                assumptions_json=assumptions,
                projections_json=projections,
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create unit economics model: {e}")
            return None
    
    def _create_valuation_model(self, pack_id: str, pack_content: Dict[str, Any]) -> Optional[FinancialModel]:
        """Create valuation model"""
        try:
            model_id = f"model_{int(time.time())}"
            now = datetime.now()
            
            # Simple DCF-based valuation
            current_arr = pack_content['financial_highlights']['current_arr']
            projected_arr_24m = pack_content['financial_highlights']['projected_arr_24m']
            
            assumptions = {
                'revenue_multiple': 15,  # 15x ARR multiple
                'discount_rate': 0.25,   # 25% discount rate
                'terminal_growth': 0.05  # 5% terminal growth
            }
            
            projections = {
                'current_valuation': current_arr * 15,
                'projected_valuation_24m': projected_arr_24m * 15,
                'implied_valuation': (current_arr + projected_arr_24m) / 2 * 15
            }
            
            return FinancialModel(
                id=model_id,
                pack_id=pack_id,
                model_type=FinancialModelType.VALUATION,
                assumptions_json=assumptions,
                projections_json=projections,
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create valuation model: {e}")
            return None
    
    def _save_financial_model(self, model: FinancialModel):
        """Save financial model to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO financial_models 
                    (id, pack_id, model_type, assumptions_json, projections_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    model.id,
                    model.pack_id,
                    model.model_type.value,
                    json.dumps(model.assumptions_json),
                    json.dumps(model.projections_json),
                    model.created_at.isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save financial model: {e}")
    
    def get_investor_pack(self, pack_id: str, tenant_id: str) -> Optional[InvestorPack]:
        """Get investor pack by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, system_id, version, summary_json, created_at, metadata
                    FROM investor_packs 
                    WHERE id = ? AND tenant_id = ?
                ''', (pack_id, tenant_id))
                row = cursor.fetchone()
                
                if row:
                    return InvestorPack(
                        id=row[0],
                        tenant_id=row[1],
                        system_id=row[2],
                        version=row[3],
                        summary_json=json.loads(row[4]),
                        created_at=datetime.fromisoformat(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get investor pack: {e}")
            return None
    
    def get_financial_models(self, pack_id: str, tenant_id: str) -> List[FinancialModel]:
        """Get financial models for investor pack"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Verify pack belongs to tenant
                cursor.execute('''
                    SELECT id FROM investor_packs WHERE id = ? AND tenant_id = ?
                ''', (pack_id, tenant_id))
                if not cursor.fetchone():
                    return []
                
                cursor.execute('''
                    SELECT id, pack_id, model_type, assumptions_json, projections_json, created_at
                    FROM financial_models 
                    WHERE pack_id = ?
                    ORDER BY created_at DESC
                ''', (pack_id,))
                
                models = []
                for row in cursor.fetchall():
                    models.append(FinancialModel(
                        id=row[0],
                        pack_id=row[1],
                        model_type=FinancialModelType(row[2]),
                        assumptions_json=json.loads(row[3]),
                        projections_json=json.loads(row[4]),
                        created_at=datetime.fromisoformat(row[5])
                    ))
                
                return models
                
        except Exception as e:
            logger.error(f"Failed to get financial models: {e}")
            return []
    
    def export_investor_pack(self, pack_id: str, tenant_id: str, format_type: str = 'pdf') -> Optional[str]:
        """Export investor pack in specified format"""
        try:
            # Get pack and models
            pack = self.get_investor_pack(pack_id, tenant_id)
            if not pack:
                return None
            
            models = self.get_financial_models(pack_id, tenant_id)
            
            # Create export file
            export_path = self._create_export_file(pack, models, format_type)
            
            if export_path:
                # Update metrics
                file_size = os.path.getsize(export_path)
                metrics.increment_counter('sbh_investor_export_bytes_total', {'format': format_type, 'bytes': file_size})
                
                return export_path
            return None
            
        except Exception as e:
            logger.error(f"Failed to export investor pack: {e}")
            return None
    
    def _create_export_file(self, pack: InvestorPack, models: List[FinancialModel], format_type: str) -> Optional[str]:
        """Create export file for investor pack"""
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=f'.{format_type}', 
                delete=False
            )
            
            if format_type == 'json':
                # Export as JSON
                export_data = {
                    'pack': asdict(pack),
                    'financial_models': [asdict(m) for m in models],
                    'exported_at': datetime.now().isoformat()
                }
                json.dump(export_data, temp_file, indent=2)
            
            elif format_type == 'md':
                # Export as Markdown
                content = self._generate_markdown_export(pack, models)
                temp_file.write(content)
            
            else:
                # Default to JSON
                export_data = {
                    'pack': asdict(pack),
                    'financial_models': [asdict(m) for m in models],
                    'exported_at': datetime.now().isoformat()
                }
                json.dump(export_data, temp_file, indent=2)
            
            temp_file.close()
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Failed to create export file: {e}")
            return None
    
    def _generate_markdown_export(self, pack: InvestorPack, models: List[FinancialModel]) -> str:
        """Generate Markdown export content"""
        content = f"""# Investor Pack - {pack.system_id}

## Executive Summary

### Company Overview
{pack.summary_json['executive_summary']['company_overview']}

### Problem Solved
{pack.summary_json['executive_summary']['problem_solved']}

### Solution
{pack.summary_json['executive_summary']['solution']}

### Market Opportunity
- TAM: ${pack.summary_json['market_analysis']['market_size']['tam']:,}
- SAM: ${pack.summary_json['market_analysis']['market_size']['sam']:,}
- SOM: ${pack.summary_json['market_analysis']['market_size']['som']:,}

### Traction
- Customers: {pack.summary_json['traction_metrics']['customers']:,}
- ARR: ${pack.summary_json['traction_metrics']['arr']:,}
- Growth Rate: {pack.summary_json['traction_metrics']['growth_rate']}% YoY

### Funding Ask
{pack.summary_json['executive_summary']['funding_ask']}

## Financial Models

"""
        
        for model in models:
            content += f"### {model.model_type.value.replace('_', ' ').title()}\n\n"
            content += f"**Assumptions:**\n"
            for key, value in model.assumptions_json.items():
                content += f"- {key}: {value}\n"
            content += f"\n**Projections:**\n"
            for key, value in model.projections_json.items():
                content += f"- {key}: {value}\n"
            content += "\n"
        
        return content

# Initialize service
investor_pack_service = InvestorPackService()

# API Routes
@investor_pack_bp.route('/pack/generate', methods=['POST'])
@cross_origin()
@flag_required('investor_pack')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def generate_investor_pack():
    """Generate investor pack for system"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        custom_data = data.get('custom_data')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        pack = investor_pack_service.generate_investor_pack(system_id, tenant_id, custom_data)
        
        if not pack:
            return jsonify({'error': 'Failed to generate investor pack'}), 500
        
        return jsonify({
            'success': True,
            'pack_id': pack.id,
            'pack': asdict(pack)
        })
        
    except Exception as e:
        logger.error(f"Generate investor pack error: {e}")
        return jsonify({'error': str(e)}), 500

@investor_pack_bp.route('/pack/<pack_id>', methods=['GET'])
@cross_origin()
@flag_required('investor_pack')
@require_tenant_context
def get_investor_pack(pack_id):
    """Get investor pack by ID"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        pack = investor_pack_service.get_investor_pack(pack_id, tenant_id)
        
        if not pack:
            return jsonify({'error': 'Investor pack not found'}), 404
        
        # Get financial models
        models = investor_pack_service.get_financial_models(pack_id, tenant_id)
        
        return jsonify({
            'success': True,
            'pack': asdict(pack),
            'financial_models': [asdict(m) for m in models]
        })
        
    except Exception as e:
        logger.error(f"Get investor pack error: {e}")
        return jsonify({'error': str(e)}), 500

@investor_pack_bp.route('/pack/export', methods=['POST'])
@cross_origin()
@flag_required('investor_pack')
@require_tenant_context
@cost_accounted("api", "operation")
def export_investor_pack():
    """Export investor pack"""
    try:
        data = request.get_json()
        pack_id = data.get('pack_id')
        format_type = data.get('format', 'json')
        
        if not pack_id:
            return jsonify({'error': 'pack_id is required'}), 400
        
        if format_type not in ['json', 'md', 'pdf']:
            return jsonify({'error': 'Invalid format. Supported: json, md, pdf'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        export_path = investor_pack_service.export_investor_pack(pack_id, tenant_id, format_type)
        
        if not export_path:
            return jsonify({'error': 'Failed to export investor pack'}), 500
        
        return jsonify({
            'success': True,
            'download_url': f"/api/investor/pack/download/{pack_id}?format={format_type}",
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Export investor pack error: {e}")
        return jsonify({'error': str(e)}), 500

@investor_pack_bp.route('/pack/download/<pack_id>', methods=['GET'])
@cross_origin()
@flag_required('investor_pack')
def download_investor_pack(pack_id):
    """Download exported investor pack"""
    try:
        format_type = request.args.get('format', 'json')
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        export_path = investor_pack_service.export_investor_pack(pack_id, tenant_id, format_type)
        
        if not export_path:
            return jsonify({'error': 'Export not found'}), 404
        
        return send_file(
            export_path,
            as_attachment=True,
            download_name=f"investor_pack_{pack_id}.{format_type}"
        )
        
    except Exception as e:
        logger.error(f"Download investor pack error: {e}")
        return jsonify({'error': str(e)}), 500
