import os
import json
import sqlite3
import threading
import queue
import hashlib
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml
import requests
from jinja2 import Template

class GTMStage(Enum):
    """Go-to-market stages"""
    PLANNING = "planning"
    ASSETS_CREATED = "assets_created"
    MICROSITE_DEPLOYED = "microsite_deployed"
    LAUNCHED = "launched"
    OPTIMIZING = "optimizing"

class AssetType(Enum):
    """GTM asset types"""
    LANDING_PAGE = "landing_page"
    LEGAL_DOCS = "legal_docs"
    SALES_FUNNEL = "sales_funnel"
    MARKETING_PLAN = "marketing_plan"
    MICROSITE = "microsite"
    BRAND_ASSETS = "brand_assets"
    LAUNCH_VIDEO = "launch_video"

class LegalRegion(Enum):
    """Legal document regions"""
    US = "us"
    EU = "eu"
    GLOBAL = "global"
    CALIFORNIA = "california"

class FunnelStage(Enum):
    """Sales funnel stages"""
    AWARENESS = "awareness"
    INTEREST = "interest"
    CONSIDERATION = "consideration"
    CONVERSION = "conversion"
    RETENTION = "retention"

@dataclass
class GTMBundle:
    """Complete GTM bundle for a system"""
    bundle_id: str
    system_id: str
    organization_id: str
    stage: GTMStage
    created_at: datetime
    updated_at: datetime
    
    # Core GTM components
    blueprint: Dict[str, Any]
    legal_docs: Dict[str, Any]
    sales_funnel: Dict[str, Any]
    marketing_strategy: Dict[str, Any]
    assets: Dict[str, Any]
    microsite_config: Dict[str, Any]
    
    # Analytics and tracking
    analytics_config: Dict[str, Any]
    conversion_events: List[Dict[str, Any]]
    feedback_data: List[Dict[str, Any]]

@dataclass
class GTMAsset:
    """Individual GTM asset"""
    asset_id: str
    bundle_id: str
    asset_type: AssetType
    name: str
    content: str
    file_path: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime

@dataclass
class LegalDocument:
    """Legal document template"""
    doc_id: str
    region: LegalRegion
    doc_type: str
    template: str
    variables: List[str]
    created_at: datetime

@dataclass
class SalesFunnel:
    """Sales funnel configuration"""
    funnel_id: str
    bundle_id: str
    stages: List[FunnelStage]
    touchpoints: Dict[str, List[Dict[str, Any]]]
    conversion_goals: List[Dict[str, Any]]
    created_at: datetime

@dataclass
class MarketingStrategy:
    """Marketing strategy plan"""
    strategy_id: str
    bundle_id: str
    channels: List[str]
    content_calendar: List[Dict[str, Any]]
    paid_media_plan: Dict[str, Any]
    affiliate_strategy: Dict[str, Any]
    launch_announcements: List[Dict[str, Any]]
    created_at: datetime

class GoToMarketEngine:
    """Automated Go-To-Market Engine"""
    
    def __init__(self, base_dir: str, system_delivery, predictive_intelligence, 
                 referral_engine, support_agent, coaching_layer, seo_optimizer, llm_factory):
        self.base_dir = base_dir
        self.system_delivery = system_delivery
        self.predictive_intelligence = predictive_intelligence
        self.referral_engine = referral_engine
        self.support_agent = support_agent
        self.coaching_layer = coaching_layer
        self.seo_optimizer = seo_optimizer
        self.llm_factory = llm_factory
        
        self.db_path = f"{base_dir}/go_to_market_engine.db"
        self.assets_dir = f"{base_dir}/gtm_assets"
        self.microsites_dir = f"{base_dir}/microsites"
        
        # Initialize directories and database
        self._init_directories()
        self._init_database()
        self._load_legal_templates()
        
        # Background tasks
        self.asset_generation_queue = queue.Queue()
        self.asset_worker = threading.Thread(target=self._asset_generation_worker, daemon=True)
        self.asset_worker.start()

    def _init_directories(self):
        """Initialize required directories"""
        Path(self.assets_dir).mkdir(exist_ok=True)
        Path(self.microsites_dir).mkdir(exist_ok=True)

    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # GTM Bundles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gtm_bundles (
                bundle_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                blueprint TEXT,
                legal_docs TEXT,
                sales_funnel TEXT,
                marketing_strategy TEXT,
                assets TEXT,
                microsite_config TEXT,
                analytics_config TEXT,
                conversion_events TEXT,
                feedback_data TEXT
            )
        ''')
        
        # GTM Assets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gtm_assets (
                asset_id TEXT PRIMARY KEY,
                bundle_id TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                name TEXT NOT NULL,
                content TEXT,
                file_path TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (bundle_id) REFERENCES gtm_bundles (bundle_id)
            )
        ''')
        
        # Legal Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS legal_documents (
                doc_id TEXT PRIMARY KEY,
                region TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                template TEXT NOT NULL,
                variables TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Sales Funnels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_funnels (
                funnel_id TEXT PRIMARY KEY,
                bundle_id TEXT NOT NULL,
                stages TEXT NOT NULL,
                touchpoints TEXT,
                conversion_goals TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (bundle_id) REFERENCES gtm_bundles (bundle_id)
            )
        ''')
        
        # Marketing Strategies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marketing_strategies (
                strategy_id TEXT PRIMARY KEY,
                bundle_id TEXT NOT NULL,
                channels TEXT,
                content_calendar TEXT,
                paid_media_plan TEXT,
                affiliate_strategy TEXT,
                launch_announcements TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (bundle_id) REFERENCES gtm_bundles (bundle_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def _load_legal_templates(self):
        """Load legal document templates"""
        self.legal_templates = {
            LegalRegion.US: {
                "terms_of_service": self._get_terms_template(),
                "privacy_policy": self._get_privacy_template(),
                "cookie_notice": self._get_cookie_template()
            },
            LegalRegion.EU: {
                "terms_of_service": self._get_eu_terms_template(),
                "privacy_policy": self._get_gdpr_privacy_template(),
                "cookie_notice": self._get_eu_cookie_template()
            }
        }

    def create_gtm_bundle(self, system_id: str, organization_id: str, 
                         system_metadata: Dict[str, Any]) -> GTMBundle:
        """Create a complete GTM bundle for a system"""
        bundle_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Generate GTM blueprint
        blueprint = self._generate_gtm_blueprint(system_metadata)
        
        # Generate legal documents
        legal_docs = self._generate_legal_documents(system_metadata)
        
        # Generate sales funnel
        sales_funnel = self._generate_sales_funnel(system_metadata)
        
        # Generate marketing strategy
        marketing_strategy = self._generate_marketing_strategy(system_metadata)
        
        # Initialize assets and microsite config
        assets = {}
        microsite_config = self._generate_microsite_config(system_metadata)
        analytics_config = self._generate_analytics_config()
        
        bundle = GTMBundle(
            bundle_id=bundle_id,
            system_id=system_id,
            organization_id=organization_id,
            stage=GTMStage.PLANNING,
            created_at=now,
            updated_at=now,
            blueprint=blueprint,
            legal_docs=legal_docs,
            sales_funnel=sales_funnel,
            marketing_strategy=marketing_strategy,
            assets=assets,
            microsite_config=microsite_config,
            analytics_config=analytics_config,
            conversion_events=[],
            feedback_data=[]
        )
        
        # Save to database
        self._save_bundle(bundle)
        
        # Queue asset generation
        self.asset_generation_queue.put(bundle_id)
        
        return bundle

    def _generate_gtm_blueprint(self, system_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate GTM blueprint from system metadata"""
        name = system_metadata.get("name", "Untitled System")
        purpose = system_metadata.get("description", "")
        system_type = system_metadata.get("type", "web_app")
        target_audience = system_metadata.get("target_audience", "general")
        industry = system_metadata.get("industry", "technology")
        
        # Generate customer personas
        personas = self._generate_customer_personas(target_audience, industry)
        
        # Generate value propositions
        value_props = self._generate_value_propositions(name, purpose, system_type)
        
        # Generate pricing model
        pricing_model = self._generate_pricing_model(system_type, industry)
        
        # Generate differentiation statement
        differentiation = self._generate_differentiation_statement(name, purpose, system_type)
        
        # Generate elevator pitch
        elevator_pitch = self._generate_elevator_pitch(name, purpose, value_props)
        
        return {
            "system_name": name,
            "purpose": purpose,
            "system_type": system_type,
            "target_audience": target_audience,
            "industry": industry,
            "customer_personas": personas,
            "value_propositions": value_props,
            "pricing_model": pricing_model,
            "differentiation_statement": differentiation,
            "elevator_pitch": elevator_pitch,
            "launch_checklist": self._generate_launch_checklist(system_type)
        }

    def _generate_customer_personas(self, target_audience: str, industry: str) -> List[Dict[str, Any]]:
        """Generate customer personas"""
        personas = []
        
        if target_audience == "business":
            personas.extend([
                {
                    "name": "Sarah, Small Business Owner",
                    "age": "35-45",
                    "role": "Business Owner",
                    "pain_points": ["Manual processes", "Limited budget", "Time constraints"],
                    "goals": ["Automate workflows", "Reduce costs", "Scale efficiently"],
                    "channels": ["LinkedIn", "Industry forums", "Word of mouth"]
                },
                {
                    "name": "Mike, Operations Manager",
                    "age": "30-40",
                    "role": "Operations Manager",
                    "pain_points": ["Inefficient processes", "Team coordination", "Reporting"],
                    "goals": ["Streamline operations", "Improve team productivity", "Better insights"],
                    "channels": ["Professional networks", "Trade shows", "Online research"]
                }
            ])
        else:
            personas.extend([
                {
                    "name": "Alex, Tech-Savvy Professional",
                    "age": "25-35",
                    "role": "Professional",
                    "pain_points": ["Productivity tools", "Learning curve", "Integration needs"],
                    "goals": ["Increase efficiency", "Learn new skills", "Stay competitive"],
                    "channels": ["Social media", "Tech blogs", "Product reviews"]
                }
            ])
        
        return personas

    def _generate_value_propositions(self, name: str, purpose: str, system_type: str) -> List[str]:
        """Generate value propositions"""
        base_props = [
            f"{name} streamlines your workflow and saves time",
            f"Built for {system_type} with modern technology",
            "Easy to use and integrate with existing tools"
        ]
        
        if "automation" in purpose.lower():
            base_props.append("Automates repetitive tasks and reduces manual work")
        
        if "collaboration" in purpose.lower():
            base_props.append("Enhances team collaboration and communication")
        
        return base_props

    def _generate_pricing_model(self, system_type: str, industry: str) -> Dict[str, Any]:
        """Generate pricing model suggestions"""
        if system_type == "saas":
            return {
                "model": "subscription",
                "tiers": [
                    {"name": "Starter", "price": 29, "period": "monthly"},
                    {"name": "Professional", "price": 99, "period": "monthly"},
                    {"name": "Enterprise", "price": 299, "period": "monthly"}
                ]
            }
        elif system_type == "marketplace":
            return {
                "model": "commission",
                "commission_rate": 0.05,
                "transaction_fee": 2.99
            }
        else:
            return {
                "model": "one_time",
                "price": 199,
                "support_included": True
            }

    def _generate_legal_documents(self, system_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate legal documents"""
        company_info = system_metadata.get("company_info", {})
        region = LegalRegion(company_info.get("region", "us"))
        
        legal_docs = {}
        for doc_type, template in self.legal_templates[region].items():
            doc_content = self._render_legal_template(template, company_info, system_metadata)
            legal_docs[doc_type] = {
                "content": doc_content,
                "region": region.value,
                "generated_at": datetime.now().isoformat()
            }
        
        return legal_docs

    def _generate_sales_funnel(self, system_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate sales funnel configuration"""
        system_type = system_metadata.get("type", "web_app")
        target_audience = system_metadata.get("target_audience", "general")
        
        funnel_stages = [
            {
                "stage": FunnelStage.AWARENESS.value,
                "touchpoints": [
                    {"type": "content_marketing", "description": "Blog posts and SEO"},
                    {"type": "social_media", "description": "LinkedIn and Twitter presence"},
                    {"type": "paid_ads", "description": "Google Ads and social ads"}
                ]
            },
            {
                "stage": FunnelStage.INTEREST.value,
                "touchpoints": [
                    {"type": "lead_magnet", "description": "Free trial or demo"},
                    {"type": "email_sequence", "description": "Educational email series"},
                    {"type": "webinar", "description": "Product demonstration"}
                ]
            },
            {
                "stage": FunnelStage.CONSIDERATION.value,
                "touchpoints": [
                    {"type": "case_studies", "description": "Customer success stories"},
                    {"type": "comparison", "description": "Feature comparison"},
                    {"type": "consultation", "description": "Sales consultation"}
                ]
            },
            {
                "stage": FunnelStage.CONVERSION.value,
                "touchpoints": [
                    {"type": "trial", "description": "Free trial signup"},
                    {"type": "demo", "description": "Product demonstration"},
                    {"type": "pricing", "description": "Pricing page and offers"}
                ]
            }
        ]
        
        return {
            "stages": funnel_stages,
            "conversion_goals": [
                {"goal": "signup", "value": 100},
                {"goal": "trial_start", "value": 500},
                {"goal": "purchase", "value": 1000}
            ],
            "lead_magnets": self._generate_lead_magnets(system_type),
            "email_templates": self._generate_email_templates(system_type)
        }

    def _generate_marketing_strategy(self, system_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate marketing strategy"""
        system_type = system_metadata.get("type", "web_app")
        industry = system_metadata.get("industry", "technology")
        
        # Content calendar
        content_calendar = self._generate_content_calendar(system_type, industry)
        
        # Paid media plan
        paid_media_plan = {
            "google_ads": {
                "budget": 1000,
                "keywords": self._generate_keywords(system_type, industry),
                "ad_copy": self._generate_ad_copy(system_metadata)
            },
            "social_ads": {
                "platforms": ["LinkedIn", "Facebook", "Twitter"],
                "budget": 800,
                "targeting": self._generate_targeting(system_metadata)
            }
        }
        
        # Affiliate strategy
        affiliate_strategy = {
            "commission_rate": 0.20,
            "affiliate_types": ["influencers", "partners", "customers"],
            "promotional_materials": self._generate_promotional_materials(system_metadata)
        }
        
        # Launch announcements
        launch_announcements = [
            {
                "channel": "email",
                "template": self._generate_launch_email_template(system_metadata),
                "timing": "launch_day"
            },
            {
                "channel": "social_media",
                "template": self._generate_social_launch_template(system_metadata),
                "timing": "launch_day"
            }
        ]
        
        return {
            "content_calendar": content_calendar,
            "paid_media_plan": paid_media_plan,
            "affiliate_strategy": affiliate_strategy,
            "launch_announcements": launch_announcements
        }

    def _generate_microsite_config(self, system_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate microsite configuration"""
        name = system_metadata.get("name", "Untitled System")
        
        return {
            "domain": f"{name.lower().replace(' ', '-')}.yourdomain.com",
            "theme": "modern",
            "sections": [
                {"type": "hero", "title": f"Welcome to {name}"},
                {"type": "features", "title": "Key Features"},
                {"type": "pricing", "title": "Pricing Plans"},
                {"type": "testimonials", "title": "What Our Customers Say"},
                {"type": "contact", "title": "Get Started Today"}
            ],
            "analytics": {
                "google_analytics": True,
                "meta_pixel": True,
                "hotjar": True
            }
        }

    def _generate_analytics_config(self) -> Dict[str, Any]:
        """Generate analytics configuration"""
        return {
            "tracking_events": [
                "page_view",
                "signup",
                "trial_start",
                "purchase",
                "feature_usage"
            ],
            "conversion_funnels": [
                "landing_page_to_signup",
                "signup_to_trial",
                "trial_to_purchase"
            ],
            "feedback_collection": {
                "nps_survey": True,
                "feature_requests": True,
                "bug_reports": True
            }
        }

    def _asset_generation_worker(self):
        """Background worker for asset generation"""
        while True:
            try:
                bundle_id = self.asset_generation_queue.get(timeout=1)
                self._generate_bundle_assets(bundle_id)
                self.asset_generation_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in asset generation worker: {e}")

    def _generate_bundle_assets(self, bundle_id: str):
        """Generate all assets for a GTM bundle"""
        bundle = self._get_bundle(bundle_id)
        if not bundle:
            return
        
        # Generate landing page
        landing_page = self._generate_landing_page(bundle)
        self._save_asset(bundle_id, AssetType.LANDING_PAGE, "landing_page.html", landing_page)
        
        # Generate brand assets
        brand_assets = self._generate_brand_assets(bundle)
        for asset_name, content in brand_assets.items():
            self._save_asset(bundle_id, AssetType.BRAND_ASSETS, asset_name, content)
        
        # Generate launch video script
        video_script = self._generate_launch_video_script(bundle)
        self._save_asset(bundle_id, AssetType.LAUNCH_VIDEO, "launch_video_script.md", video_script)
        
        # Update bundle stage
        self._update_bundle_stage(bundle_id, GTMStage.ASSETS_CREATED)

    def _generate_landing_page(self, bundle: GTMBundle) -> str:
        """Generate landing page HTML"""
        blueprint = bundle.blueprint
        system_name = blueprint["system_name"]
        value_props = blueprint["value_propositions"]
        elevator_pitch = blueprint["elevator_pitch"]
        
        template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ system_name }} - Transform Your Workflow</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .hero-section { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 100px 0; }
        .feature-card { border: none; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .cta-button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; border-radius: 25px; padding: 15px 30px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="#">{{ system_name }}</a>
        </div>
    </nav>

    <section class="hero-section text-center">
        <div class="container">
            <h1 class="display-4 mb-4">{{ system_name }}</h1>
            <p class="lead mb-4">{{ elevator_pitch }}</p>
            <button class="btn btn-light btn-lg cta-button">Get Started Free</button>
        </div>
    </section>

    <section class="py-5">
        <div class="container">
            <h2 class="text-center mb-5">Why Choose {{ system_name }}?</h2>
            <div class="row">
                {% for prop in value_props %}
                <div class="col-md-4">
                    <div class="card feature-card">
                        <div class="card-body text-center">
                            <h5 class="card-title">{{ prop }}</h5>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>

    <section class="bg-light py-5">
        <div class="container text-center">
            <h2>Ready to Get Started?</h2>
            <p class="lead">Join thousands of users who have transformed their workflow</p>
            <button class="btn btn-primary btn-lg cta-button">Start Your Free Trial</button>
        </div>
    </section>

    <footer class="bg-dark text-white py-4">
        <div class="container text-center">
            <p>&copy; 2024 {{ system_name }}. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>
        """
        
        return Template(template).render(
            system_name=system_name,
            value_props=value_props,
            elevator_pitch=elevator_pitch
        )

    def _save_bundle(self, bundle: GTMBundle):
        """Save GTM bundle to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO gtm_bundles 
            (bundle_id, system_id, organization_id, stage, created_at, updated_at,
             blueprint, legal_docs, sales_funnel, marketing_strategy, assets,
             microsite_config, analytics_config, conversion_events, feedback_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bundle.bundle_id, bundle.system_id, bundle.organization_id,
            bundle.stage.value, bundle.created_at.isoformat(), bundle.updated_at.isoformat(),
            json.dumps(bundle.blueprint), json.dumps(bundle.legal_docs),
            json.dumps(bundle.sales_funnel), json.dumps(bundle.marketing_strategy),
            json.dumps(bundle.assets), json.dumps(bundle.microsite_config),
            json.dumps(bundle.analytics_config), json.dumps(bundle.conversion_events),
            json.dumps(bundle.feedback_data)
        ))
        
        conn.commit()
        conn.close()

    def _get_bundle(self, bundle_id: str) -> Optional[GTMBundle]:
        """Get GTM bundle from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM gtm_bundles WHERE bundle_id = ?', (bundle_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return GTMBundle(
            bundle_id=row[0],
            system_id=row[1],
            organization_id=row[2],
            stage=GTMStage(row[3]),
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5]),
            blueprint=json.loads(row[6]) if row[6] else {},
            legal_docs=json.loads(row[7]) if row[7] else {},
            sales_funnel=json.loads(row[8]) if row[8] else {},
            marketing_strategy=json.loads(row[9]) if row[9] else {},
            assets=json.loads(row[10]) if row[10] else {},
            microsite_config=json.loads(row[11]) if row[11] else {},
            analytics_config=json.loads(row[12]) if row[12] else {},
            conversion_events=json.loads(row[13]) if row[13] else [],
            feedback_data=json.loads(row[14]) if row[14] else []
        )

    def _save_asset(self, bundle_id: str, asset_type: AssetType, name: str, content: str):
        """Save GTM asset"""
        asset_id = str(uuid.uuid4())
        file_path = f"{self.assets_dir}/{bundle_id}/{name}"
        
        # Create directory if needed
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save file
        with open(file_path, 'w') as f:
            f.write(content)
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO gtm_assets (asset_id, bundle_id, asset_type, name, content, file_path, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            asset_id, bundle_id, asset_type.value, name, content, file_path,
            json.dumps({}), datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()

    def _update_bundle_stage(self, bundle_id: str, stage: GTMStage):
        """Update bundle stage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE gtm_bundles SET stage = ?, updated_at = ? WHERE bundle_id = ?
        ''', (stage.value, datetime.now().isoformat(), bundle_id))
        
        conn.commit()
        conn.close()

    def get_bundles(self, organization_id: str) -> List[GTMBundle]:
        """Get all GTM bundles for an organization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM gtm_bundles WHERE organization_id = ?', (organization_id,))
        rows = cursor.fetchall()
        conn.close()
        
        bundles = []
        for row in rows:
            bundles.append(GTMBundle(
                bundle_id=row[0],
                system_id=row[1],
                organization_id=row[2],
                stage=GTMStage(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5]),
                blueprint=json.loads(row[6]) if row[6] else {},
                legal_docs=json.loads(row[7]) if row[7] else {},
                sales_funnel=json.loads(row[8]) if row[8] else {},
                marketing_strategy=json.loads(row[9]) if row[9] else {},
                assets=json.loads(row[10]) if row[10] else {},
                microsite_config=json.loads(row[11]) if row[11] else {},
                analytics_config=json.loads(row[12]) if row[12] else {},
                conversion_events=json.loads(row[13]) if row[13] else [],
                feedback_data=json.loads(row[14]) if row[14] else []
            ))
        
        return bundles

    def export_bundle(self, bundle_id: str, export_format: str = "zip") -> str:
        """Export GTM bundle"""
        bundle = self._get_bundle(bundle_id)
        if not bundle:
            raise ValueError("Bundle not found")
        
        if export_format == "zip":
            return self._create_zip_export(bundle)
        elif export_format == "github":
            return self._create_github_export(bundle)
        else:
            raise ValueError("Unsupported export format")

    def _create_zip_export(self, bundle: GTMBundle) -> str:
        """Create ZIP export of GTM bundle"""
        import zipfile
        
        zip_path = f"{self.assets_dir}/{bundle.bundle_id}_gtm_export.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add blueprint
            zipf.writestr("blueprint.json", json.dumps(bundle.blueprint, indent=2))
            
            # Add legal documents
            zipf.writestr("legal_documents.json", json.dumps(bundle.legal_docs, indent=2))
            
            # Add sales funnel
            zipf.writestr("sales_funnel.json", json.dumps(bundle.sales_funnel, indent=2))
            
            # Add marketing strategy
            zipf.writestr("marketing_strategy.json", json.dumps(bundle.marketing_strategy, indent=2))
            
            # Add assets
            assets_dir = f"{self.assets_dir}/{bundle.bundle_id}"
            if os.path.exists(assets_dir):
                for root, dirs, files in os.walk(assets_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, assets_dir)
                        zipf.write(file_path, f"assets/{arc_name}")
        
        return zip_path

    # Helper methods for template generation
    def _get_terms_template(self) -> str:
        return "Terms of Service template for US region"
    
    def _get_privacy_template(self) -> str:
        return "Privacy Policy template for US region"
    
    def _get_cookie_template(self) -> str:
        return "Cookie Notice template for US region"
    
    def _get_eu_terms_template(self) -> str:
        return "Terms of Service template for EU region"
    
    def _get_gdpr_privacy_template(self) -> str:
        return "GDPR Privacy Policy template"
    
    def _get_eu_cookie_template(self) -> str:
        return "EU Cookie Notice template"
    
    def _render_legal_template(self, template: str, company_info: Dict, system_metadata: Dict) -> str:
        """Render legal template with company and system information"""
        return template  # Simplified for now
    
    def _generate_differentiation_statement(self, name: str, purpose: str, system_type: str) -> str:
        return f"{name} is the only {system_type} that {purpose} with unmatched efficiency and ease of use."
    
    def _generate_elevator_pitch(self, name: str, purpose: str, value_props: List[str]) -> str:
        return f"{name} helps you {purpose}. {value_props[0] if value_props else ''}"
    
    def _generate_launch_checklist(self, system_type: str) -> List[str]:
        return [
            "Set up analytics tracking",
            "Create social media accounts",
            "Prepare launch announcement",
            "Set up customer support",
            "Test all user flows"
        ]
    
    def _generate_lead_magnets(self, system_type: str) -> List[Dict[str, Any]]:
        return [
            {"type": "free_trial", "title": "14-Day Free Trial"},
            {"type": "demo", "title": "Product Demo"},
            {"type": "guide", "title": "Getting Started Guide"}
        ]
    
    def _generate_email_templates(self, system_type: str) -> List[Dict[str, Any]]:
        return [
            {"type": "welcome", "subject": "Welcome to our platform"},
            {"type": "onboarding", "subject": "Getting started guide"},
            {"type": "promotion", "subject": "Special launch offer"}
        ]
    
    def _generate_content_calendar(self, system_type: str, industry: str) -> List[Dict[str, Any]]:
        return [
            {"week": 1, "topic": "Introduction to the platform", "format": "blog_post"},
            {"week": 2, "topic": "Key features overview", "format": "video"},
            {"week": 3, "topic": "Customer success story", "format": "case_study"}
        ]
    
    def _generate_keywords(self, system_type: str, industry: str) -> List[str]:
        return [f"{system_type} software", f"{industry} tools", "business automation"]
    
    def _generate_ad_copy(self, system_metadata: Dict[str, Any]) -> List[str]:
        name = system_metadata.get("name", "Our Platform")
        return [
            f"Transform your workflow with {name}",
            f"Get started with {name} today",
            f"Join thousands using {name}"
        ]
    
    def _generate_targeting(self, system_metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "age": "25-45",
            "interests": ["business", "technology", "productivity"],
            "job_titles": ["Manager", "Director", "Owner"]
        }
    
    def _generate_promotional_materials(self, system_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"type": "banner", "size": "728x90", "content": "Promotional banner"},
            {"type": "social_post", "platform": "LinkedIn", "content": "Social media post"},
            {"type": "email_template", "subject": "Affiliate promotion email"}
        ]
    
    def _generate_launch_email_template(self, system_metadata: Dict[str, Any]) -> str:
        name = system_metadata.get("name", "Our Platform")
        return f"Subject: {name} is Now Live! 🚀\n\nWe're excited to announce the launch of {name}..."
    
    def _generate_social_launch_template(self, system_metadata: Dict[str, Any]) -> str:
        name = system_metadata.get("name", "Our Platform")
        return f"🚀 {name} is now live! Transform your workflow with our powerful new platform..."
    
    def _generate_brand_assets(self, bundle: GTMBundle) -> Dict[str, str]:
        """Generate brand assets"""
        name = bundle.blueprint["system_name"]
        return {
            "logo.svg": f"<svg>Logo for {name}</svg>",
            "favicon.ico": "Favicon content",
            "social_banner.png": "Social media banner content"
        }
    
    def _generate_launch_video_script(self, bundle: GTMBundle) -> str:
        """Generate launch video script"""
        name = bundle.blueprint["system_name"]
        elevator_pitch = bundle.blueprint["elevator_pitch"]
        
        return f"""
# Launch Video Script for {name}

## Opening (0-10 seconds)
"Are you tired of [pain point]? Meet {name}, the solution you've been waiting for."

## Problem (10-30 seconds)
"Every day, businesses struggle with [specific problem]. Manual processes, wasted time, and missed opportunities."

## Solution (30-60 seconds)
"{name} solves this by [key benefit]. {elevator_pitch}"

## Demo (60-90 seconds)
[Show key features and benefits]

## Call to Action (90-120 seconds)
"Ready to transform your workflow? Visit [website] and start your free trial today."
        """
