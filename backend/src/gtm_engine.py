#!/usr/bin/env python3
"""
P39: GTM Engine (Market Strategy Factory)
Generate go-to-market strategies, personas, messaging, pricing, and launch plans for systems.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app
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
gtm_engine_bp = Blueprint('gtm_engine', __name__, url_prefix='/api/gtm')

# Data Models
class GTMPlanStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    LAUNCHED = "launched"
    ARCHIVED = "archived"

class AssetKind(Enum):
    PERSONA = "persona"
    MESSAGING = "messaging"
    PRICING = "pricing"
    LAUNCH_PLAN = "launch_plan"
    GROWTH_PLAYBOOK = "growth_playbook"
    MARKET_RESEARCH = "market_research"

@dataclass
class GTMPlan:
    id: str
    tenant_id: str
    system_id: str
    version: int
    summary_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class GTMAsset:
    id: str
    plan_id: str
    kind: AssetKind
    content_md: str
    meta_json: Dict[str, Any]
    created_at: datetime

@dataclass
class GTMMetric:
    id: str
    plan_id: str
    kpi: str
    value: float
    timestamp: datetime

class GTMEngineService:
    """Service for GTM strategy generation and management"""
    
    def __init__(self):
        self._init_database()
        self.market_templates = self._load_market_templates()
    
    def _init_database(self):
        """Initialize GTM engine database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create gtm_plans table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS gtm_plans (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        summary_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create gtm_assets table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS gtm_assets (
                        id TEXT PRIMARY KEY,
                        plan_id TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        content_md TEXT NOT NULL,
                        meta_json TEXT,
                        created_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (plan_id) REFERENCES gtm_plans (id)
                    )
                ''')
                
                # Create gtm_metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS gtm_metrics (
                        id TEXT PRIMARY KEY,
                        plan_id TEXT NOT NULL,
                        kpi TEXT NOT NULL,
                        value REAL NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        FOREIGN KEY (plan_id) REFERENCES gtm_plans (id)
                    )
                ''')
                
                conn.commit()
                logger.info("GTM engine database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize GTM engine database: {e}")
    
    def _load_market_templates(self) -> Dict[str, Any]:
        """Load market strategy templates"""
        return {
            'b2b_saas': {
                'personas': ['Decision Maker', 'End User', 'Champion', 'Economic Buyer'],
                'messaging_frameworks': ['Problem-Agitate-Solution', 'Before-After-Bridge'],
                'pricing_models': ['Per User', 'Per Feature', 'Tiered', 'Usage-Based'],
                'launch_channels': ['Content Marketing', 'Sales Outreach', 'Partnerships', 'Events']
            },
            'b2c_app': {
                'personas': ['Early Adopter', 'Mainstream User', 'Power User', 'Casual User'],
                'messaging_frameworks': ['Benefit-Focused', 'Social Proof', 'Urgency'],
                'pricing_models': ['Freemium', 'Subscription', 'One-Time', 'In-App Purchases'],
                'launch_channels': ['App Stores', 'Social Media', 'Influencers', 'PR']
            },
            'enterprise': {
                'personas': ['C-Suite', 'IT Director', 'Department Head', 'End User'],
                'messaging_frameworks': ['ROI-Focused', 'Risk Mitigation', 'Competitive Advantage'],
                'pricing_models': ['Enterprise License', 'Annual Contract', 'Custom Pricing'],
                'launch_channels': ['Direct Sales', 'Partners', 'Industry Events', 'Thought Leadership']
            }
        }
    
    def generate_gtm_plan(self, system_id: str, tenant_id: str, goals: Optional[Dict[str, Any]] = None) -> Optional[GTMPlan]:
        """Generate a comprehensive GTM plan for a system"""
        try:
            plan_id = f"gtm_{int(time.time())}"
            version = 1
            now = datetime.now()
            
            # Analyze system and generate strategy
            strategy = self._analyze_system_and_generate_strategy(system_id, goals)
            
            plan = GTMPlan(
                id=plan_id,
                tenant_id=tenant_id,
                system_id=system_id,
                version=version,
                summary_json=strategy,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gtm_plans 
                    (id, tenant_id, system_id, version, summary_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    plan.id,
                    plan.tenant_id,
                    plan.system_id,
                    plan.version,
                    json.dumps(plan.summary_json),
                    plan.created_at.isoformat(),
                    json.dumps(plan.metadata)
                ))
                conn.commit()
            
            # Generate GTM assets
            self._generate_gtm_assets(plan_id, strategy)
            
            # Initialize KPIs
            self._initialize_kpis(plan_id)
            
            # Update metrics
            metrics.increment_counter('sbh_gtm_generate_total', {'tenant_id': tenant_id})
            
            logger.info(f"Generated GTM plan: {plan_id}")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to generate GTM plan: {e}")
            return None
    
    def _analyze_system_and_generate_strategy(self, system_id: str, goals: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze system and generate GTM strategy"""
        # TODO: Integrate with actual system analysis
        # For now, generate mock strategy based on system type
        
        strategy = {
            'market_category': 'b2b_saas',
            'target_market': {
                'size': 'Mid-market (100-1000 employees)',
                'industries': ['Technology', 'Finance', 'Healthcare'],
                'geographies': ['North America', 'Europe']
            },
            'competitive_landscape': {
                'direct_competitors': ['Competitor A', 'Competitor B'],
                'indirect_competitors': ['Alternative Solution 1', 'Alternative Solution 2'],
                'differentiation': 'AI-powered automation with enterprise-grade security'
            },
            'value_proposition': {
                'primary': 'Streamline operations and reduce costs by 40%',
                'secondary': 'Improve team productivity and decision-making',
                'emotional': 'Peace of mind with reliable, secure automation'
            },
            'pricing_strategy': {
                'model': 'Tiered subscription',
                'tiers': [
                    {'name': 'Starter', 'price': 99, 'features': ['Basic features', '5 users']},
                    {'name': 'Professional', 'price': 299, 'features': ['Advanced features', '25 users']},
                    {'name': 'Enterprise', 'price': 999, 'features': ['All features', 'Unlimited users']}
                ]
            },
            'launch_strategy': {
                'timeline': 'Q2 2024',
                'channels': ['Content marketing', 'Sales outreach', 'Partnerships'],
                'budget': 50000,
                'success_metrics': ['MRR', 'Customer acquisition cost', 'Churn rate']
            }
        }
        
        if goals:
            strategy['custom_goals'] = goals
        
        return strategy
    
    def _generate_gtm_assets(self, plan_id: str, strategy: Dict[str, Any]):
        """Generate GTM assets based on strategy"""
        try:
            assets = [
                self._create_persona_asset(plan_id, strategy),
                self._create_messaging_asset(plan_id, strategy),
                self._create_pricing_asset(plan_id, strategy),
                self._create_launch_plan_asset(plan_id, strategy),
                self._create_growth_playbook_asset(plan_id, strategy)
            ]
            
            for asset in assets:
                if asset:
                    self._save_gtm_asset(asset)
                    
        except Exception as e:
            logger.error(f"Failed to generate GTM assets: {e}")
    
    def _create_persona_asset(self, plan_id: str, strategy: Dict[str, Any]) -> Optional[GTMAsset]:
        """Create persona asset"""
        try:
            asset_id = f"asset_{int(time.time())}"
            now = datetime.now()
            
            content = f"""# Target Personas

## Primary Persona: Decision Maker
- **Role**: VP/Director of Operations
- **Company Size**: 100-1000 employees
- **Pain Points**: 
  - Manual processes slowing down operations
  - High operational costs
  - Difficulty scaling with growth
- **Goals**: Streamline operations, reduce costs, improve efficiency
- **Buying Criteria**: ROI, ease of implementation, vendor reputation

## Secondary Persona: End User
- **Role**: Operations Manager
- **Pain Points**: 
  - Repetitive manual tasks
  - Data entry errors
  - Lack of real-time insights
- **Goals**: Automate routine tasks, get better insights, improve accuracy
- **Adoption Drivers**: Ease of use, immediate value, training support

## Champion Persona: IT Manager
- **Role**: IT Director/Manager
- **Pain Points**: 
  - Integration complexity
  - Security concerns
  - Maintenance overhead
- **Goals**: Seamless integration, robust security, minimal maintenance
- **Technical Criteria**: API availability, security certifications, support quality
"""
            
            return GTMAsset(
                id=asset_id,
                plan_id=plan_id,
                kind=AssetKind.PERSONA,
                content_md=content,
                meta_json={'persona_count': 3},
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create persona asset: {e}")
            return None
    
    def _create_messaging_asset(self, plan_id: str, strategy: Dict[str, Any]) -> Optional[GTMAsset]:
        """Create messaging asset"""
        try:
            asset_id = f"asset_{int(time.time())}"
            now = datetime.now()
            
            content = f"""# Messaging Framework

## Primary Message
**Transform your operations with AI-powered automation that reduces costs by 40% while improving accuracy and speed.**

## Problem Statement
Manual processes are killing your productivity and costing you money. Your team spends countless hours on repetitive tasks, making errors, and struggling to scale with growth.

## Solution Statement
Our AI-powered platform automates your most time-consuming operations, eliminating errors and freeing your team to focus on strategic work.

## Key Benefits
- **40% cost reduction** through automation
- **99.9% accuracy** with AI-powered validation
- **10x faster** processing times
- **Real-time insights** for better decision-making

## Proof Points
- Trusted by 500+ companies
- 4.8/5 customer satisfaction rating
- 30-day implementation timeline
- 24/7 expert support

## Call to Action
Start your transformation today with a free 30-day trial.
"""
            
            return GTMAsset(
                id=asset_id,
                plan_id=plan_id,
                kind=AssetKind.MESSAGING,
                content_md=content,
                meta_json={'message_framework': 'Problem-Agitate-Solution'},
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create messaging asset: {e}")
            return None
    
    def _create_pricing_asset(self, plan_id: str, strategy: Dict[str, Any]) -> Optional[GTMAsset]:
        """Create pricing asset"""
        try:
            asset_id = f"asset_{int(time.time())}"
            now = datetime.now()
            
            content = f"""# Pricing Strategy

## Pricing Model: Tiered Subscription

### Starter Plan - $99/month
**Perfect for small teams getting started**
- Up to 5 users
- Basic automation features
- Email support
- Standard integrations
- Monthly billing

### Professional Plan - $299/month
**For growing teams that need more power**
- Up to 25 users
- Advanced automation features
- Priority support
- Custom integrations
- API access
- Monthly or annual billing (save 20%)

### Enterprise Plan - $999/month
**For large organizations with complex needs**
- Unlimited users
- All features included
- Dedicated support manager
- Custom development
- SLA guarantees
- Annual billing only

## Pricing Psychology
- **Anchoring**: Enterprise plan makes Professional look affordable
- **Value perception**: Clear ROI justification for each tier
- **Flexibility**: Monthly options for testing, annual for commitment
- **Transparency**: No hidden fees or setup costs

## Competitive Positioning
- 20% below market average for comparable features
- Premium positioning justified by AI capabilities
- Enterprise pricing competitive with legacy solutions
"""
            
            return GTMAsset(
                id=asset_id,
                plan_id=plan_id,
                kind=AssetKind.PRICING,
                content_md=content,
                meta_json={'pricing_model': 'Tiered Subscription'},
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create pricing asset: {e}")
            return None
    
    def _create_launch_plan_asset(self, plan_id: str, strategy: Dict[str, Any]) -> Optional[GTMAsset]:
        """Create launch plan asset"""
        try:
            asset_id = f"asset_{int(time.time())}"
            now = datetime.now()
            
            content = f"""# Launch Plan

## Phase 1: Pre-Launch (Months 1-2)
### Market Preparation
- Finalize messaging and positioning
- Create marketing materials
- Set up CRM and tracking systems
- Train sales team
- Build partner relationships

### Content Creation
- Website copy and landing pages
- Product demos and videos
- Case studies and testimonials
- Blog posts and thought leadership
- Social media content calendar

## Phase 2: Soft Launch (Month 3)
### Beta Program
- Invite 50 beta customers
- Collect feedback and testimonials
- Refine product and messaging
- Create case studies
- Build momentum

### Early Access
- Limited public availability
- Early adopter pricing
- Referral program
- PR outreach

## Phase 3: Full Launch (Month 4)
### Go-to-Market Execution
- Full public availability
- Marketing campaign launch
- Sales outreach begins
- Partnership announcements
- Industry event participation

### Success Metrics
- 100 new customers in first 3 months
- $50K MRR by month 6
- 4.5+ customer satisfaction rating
- 20% month-over-month growth

## Budget Allocation
- **Marketing**: $25K (50%)
- **Sales**: $15K (30%)
- **Partnerships**: $5K (10%)
- **Events**: $3K (6%)
- **Miscellaneous**: $2K (4%)
"""
            
            return GTMAsset(
                id=asset_id,
                plan_id=plan_id,
                kind=AssetKind.LAUNCH_PLAN,
                content_md=content,
                meta_json={'launch_timeline': 'Q2 2024'},
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create launch plan asset: {e}")
            return None
    
    def _create_growth_playbook_asset(self, plan_id: str, strategy: Dict[str, Any]) -> Optional[GTMAsset]:
        """Create growth playbook asset"""
        try:
            asset_id = f"asset_{int(time.time())}"
            now = datetime.now()
            
            content = f"""# Growth Playbook

## Customer Acquisition Strategies

### Content Marketing
- **Blog posts**: 2-3 per week on industry topics
- **Webinars**: Monthly educational sessions
- **E-books**: Lead magnets for email capture
- **Case studies**: Customer success stories
- **Thought leadership**: Industry publications

### Sales Outreach
- **LinkedIn**: Personalized connection requests
- **Email sequences**: 5-7 touch point campaigns
- **Cold calling**: Targeted prospect lists
- **Referral program**: Customer incentives
- **Partnerships**: Channel sales opportunities

### Digital Marketing
- **SEO**: Keyword optimization and content
- **PPC**: Google Ads and LinkedIn Ads
- **Social media**: LinkedIn and Twitter engagement
- **Email marketing**: Nurture campaigns
- **Retargeting**: Website visitor campaigns

## Customer Success Strategies
- **Onboarding**: 30-day success program
- **Training**: Video tutorials and documentation
- **Support**: 24/7 chat and email support
- **Success metrics**: Regular check-ins and reviews
- **Expansion**: Upsell and cross-sell opportunities

## Retention Strategies
- **Product adoption**: Feature usage tracking
- **Customer feedback**: Regular surveys and interviews
- **Community**: User groups and forums
- **Loyalty programs**: Rewards for long-term customers
- **Product updates**: Regular feature releases
"""
            
            return GTMAsset(
                id=asset_id,
                plan_id=plan_id,
                kind=AssetKind.GROWTH_PLAYBOOK,
                content_md=content,
                meta_json={'growth_channels': 3},
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"Failed to create growth playbook asset: {e}")
            return None
    
    def _save_gtm_asset(self, asset: GTMAsset):
        """Save GTM asset to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gtm_assets 
                    (id, plan_id, kind, content_md, meta_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    asset.id,
                    asset.plan_id,
                    asset.kind.value,
                    asset.content_md,
                    json.dumps(asset.meta_json),
                    asset.created_at.isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save GTM asset: {e}")
    
    def _initialize_kpis(self, plan_id: str):
        """Initialize KPIs for the plan"""
        try:
            kpis = [
                ('mrr', 0.0),
                ('customer_count', 0),
                ('churn_rate', 0.0),
                ('cac', 0.0),
                ('ltv', 0.0),
                ('conversion_rate', 0.0)
            ]
            
            for kpi, initial_value in kpis:
                self._save_kpi(plan_id, kpi, initial_value)
                
        except Exception as e:
            logger.error(f"Failed to initialize KPIs: {e}")
    
    def _save_kpi(self, plan_id: str, kpi: str, value: float):
        """Save KPI to database"""
        try:
            metric_id = f"metric_{int(time.time())}"
            now = datetime.now()
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gtm_metrics 
                    (id, plan_id, kpi, value, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (metric_id, plan_id, kpi, value, now.isoformat()))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save KPI: {e}")
    
    def get_gtm_plan(self, plan_id: str, tenant_id: str) -> Optional[GTMPlan]:
        """Get GTM plan by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, system_id, version, summary_json, created_at, metadata
                    FROM gtm_plans 
                    WHERE id = ? AND tenant_id = ?
                ''', (plan_id, tenant_id))
                row = cursor.fetchone()
                
                if row:
                    return GTMPlan(
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
            logger.error(f"Failed to get GTM plan: {e}")
            return None
    
    def get_gtm_assets(self, plan_id: str, tenant_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get GTM assets with pagination"""
        try:
            offset = (page - 1) * page_size
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Verify plan belongs to tenant
                cursor.execute('''
                    SELECT id FROM gtm_plans WHERE id = ? AND tenant_id = ?
                ''', (plan_id, tenant_id))
                if not cursor.fetchone():
                    return {'assets': [], 'pagination': {'page': page, 'page_size': page_size, 'total_count': 0, 'total_pages': 0}}
                
                # Get total count
                cursor.execute('''
                    SELECT COUNT(*) FROM gtm_assets WHERE plan_id = ?
                ''', (plan_id,))
                total_count = cursor.fetchone()[0]
                
                # Get assets
                cursor.execute('''
                    SELECT id, plan_id, kind, content_md, meta_json, created_at
                    FROM gtm_assets 
                    WHERE plan_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (plan_id, page_size, offset))
                
                assets = []
                for row in cursor.fetchall():
                    assets.append(GTMAsset(
                        id=row[0],
                        plan_id=row[1],
                        kind=AssetKind(row[2]),
                        content_md=row[3],
                        meta_json=json.loads(row[4]) if row[4] else {},
                        created_at=datetime.fromisoformat(row[5])
                    ))
                
                return {
                    'assets': [asdict(a) for a in assets],
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get GTM assets: {e}")
            return {'assets': [], 'pagination': {'page': page, 'page_size': page_size, 'total_count': 0, 'total_pages': 0}}
    
    def get_gtm_kpis(self, plan_id: str, tenant_id: str) -> List[GTMMetric]:
        """Get KPIs for GTM plan"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Verify plan belongs to tenant
                cursor.execute('''
                    SELECT id FROM gtm_plans WHERE id = ? AND tenant_id = ?
                ''', (plan_id, tenant_id))
                if not cursor.fetchone():
                    return []
                
                cursor.execute('''
                    SELECT id, plan_id, kpi, value, timestamp
                    FROM gtm_metrics 
                    WHERE plan_id = ?
                    ORDER BY timestamp DESC
                ''', (plan_id,))
                
                metrics = []
                for row in cursor.fetchall():
                    metrics.append(GTMMetric(
                        id=row[0],
                        plan_id=row[1],
                        kpi=row[2],
                        value=row[3],
                        timestamp=datetime.fromisoformat(row[4])
                    ))
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get GTM KPIs: {e}")
            return []
    
    def refresh_gtm_plan(self, plan_id: str, tenant_id: str) -> bool:
        """Refresh GTM plan with updated strategy"""
        try:
            # Get existing plan
            plan = self.get_gtm_plan(plan_id, tenant_id)
            if not plan:
                return False
            
            # Generate updated strategy
            updated_strategy = self._analyze_system_and_generate_strategy(plan.system_id, None)
            
            # Update plan
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE gtm_plans 
                    SET version = version + 1, summary_json = ?, metadata = ?
                    WHERE id = ? AND tenant_id = ?
                ''', (
                    json.dumps(updated_strategy),
                    json.dumps({'last_refreshed': datetime.now().isoformat()}),
                    plan_id,
                    tenant_id
                ))
                conn.commit()
            
            # Regenerate assets
            self._generate_gtm_assets(plan_id, updated_strategy)
            
            logger.info(f"Refreshed GTM plan: {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh GTM plan: {e}")
            return False

# Initialize service
gtm_engine_service = GTMEngineService()

# API Routes
@gtm_engine_bp.route('/generate', methods=['POST'])
@cross_origin()
@flag_required('gtm_engine')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def generate_gtm_plan():
    """Generate GTM plan for system"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        goals = data.get('goals')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        plan = gtm_engine_service.generate_gtm_plan(system_id, tenant_id, goals)
        
        if not plan:
            return jsonify({'error': 'Failed to generate GTM plan'}), 500
        
        return jsonify({
            'success': True,
            'plan_id': plan.id,
            'plan': asdict(plan)
        })
        
    except Exception as e:
        logger.error(f"Generate GTM plan error: {e}")
        return jsonify({'error': str(e)}), 500

@gtm_engine_bp.route('/plan/<plan_id>', methods=['GET'])
@cross_origin()
@flag_required('gtm_engine')
@require_tenant_context
def get_gtm_plan(plan_id):
    """Get GTM plan by ID"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        plan = gtm_engine_service.get_gtm_plan(plan_id, tenant_id)
        
        if not plan:
            return jsonify({'error': 'GTM plan not found'}), 404
        
        return jsonify({
            'success': True,
            'plan': asdict(plan)
        })
        
    except Exception as e:
        logger.error(f"Get GTM plan error: {e}")
        return jsonify({'error': str(e)}), 500

@gtm_engine_bp.route('/assets', methods=['GET'])
@cross_origin()
@flag_required('gtm_engine')
@require_tenant_context
def get_gtm_assets():
    """Get GTM assets with pagination"""
    try:
        plan_id = request.args.get('plan_id')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        if not plan_id:
            return jsonify({'error': 'plan_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        result = gtm_engine_service.get_gtm_assets(plan_id, tenant_id, page, page_size)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Get GTM assets error: {e}")
        return jsonify({'error': str(e)}), 500

@gtm_engine_bp.route('/refresh/<plan_id>', methods=['POST'])
@cross_origin()
@flag_required('gtm_engine')
@require_tenant_context
@cost_accounted("api", "operation")
def refresh_gtm_plan(plan_id):
    """Refresh GTM plan with updated strategy"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        success = gtm_engine_service.refresh_gtm_plan(plan_id, tenant_id)
        
        if not success:
            return jsonify({'error': 'Failed to refresh GTM plan'}), 500
        
        return jsonify({
            'success': True,
            'message': 'GTM plan refreshed successfully'
        })
        
    except Exception as e:
        logger.error(f"Refresh GTM plan error: {e}")
        return jsonify({'error': str(e)}), 500

@gtm_engine_bp.route('/kpis', methods=['GET'])
@cross_origin()
@flag_required('gtm_engine')
@require_tenant_context
def get_gtm_kpis():
    """Get KPIs for GTM plan"""
    try:
        plan_id = request.args.get('plan_id')
        
        if not plan_id:
            return jsonify({'error': 'plan_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        kpis = gtm_engine_service.get_gtm_kpis(plan_id, tenant_id)
        
        return jsonify({
            'success': True,
            'kpis': [asdict(k) for k in kpis]
        })
        
    except Exception as e:
        logger.error(f"Get GTM KPIs error: {e}")
        return jsonify({'error': str(e)}), 500
