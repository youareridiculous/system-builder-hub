"""
🏢 System Build Hub OS - AI Company Builder Presets

This module provides pre-built company templates and architectures
for popular SaaS companies, enabling rapid system generation with
full feature flows, UI/UX suggestions, and infrastructure scaffolding.
"""

import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from .agent_framework import AgentOrchestrator, MemorySystem
from system_lifecycle import SystemLifecycleManager
from .prompt_build_engine import PromptBuildEngine

class CompanyType(Enum):
    ELEVENLABS = "elevenlabs"
    GOHIGHLEVEL = "gohighlevel"
    JASPER = "jasper"
    HYROS = "hyros"
    NOTION = "notion"
    CUSTOM = "custom"

class IntegrationType(Enum):
    STRIPE = "stripe"
    TWILIO = "twilio"
    ZAPIER = "zapier"
    OPENAI = "openai"
    AWS = "aws"
    GOOGLE_CLOUD = "google_cloud"
    SENDGRID = "sendgrid"
    INTERCOM = "intercom"

@dataclass
class FeatureFlow:
    """Feature flow definition"""
    feature_id: str
    name: str
    description: str
    user_journey: List[str]
    technical_requirements: List[str]
    ui_components: List[str]
    api_endpoints: List[str]
    database_schema: Dict[str, Any]
    priority: int

@dataclass
class ArchitecturePlan:
    """System architecture plan"""
    plan_id: str
    company_type: CompanyType
    frontend_stack: List[str]
    backend_stack: List[str]
    database_stack: List[str]
    infrastructure: Dict[str, Any]
    security_measures: List[str]
    scalability_plan: Dict[str, Any]
    estimated_cost: Dict[str, float]

@dataclass
class CompanyPreset:
    """Complete company preset"""
    preset_id: str
    company_type: CompanyType
    name: str
    description: str
    target_audience: str
    core_features: List[FeatureFlow]
    architecture: ArchitecturePlan
    integrations: List[IntegrationType]
    pricing_model: Dict[str, Any]
    go_to_market: Dict[str, Any]
    estimated_timeline: str
    estimated_cost: float

class CompanyPresetBuilder:
    """
    AI Company Builder with pre-built templates and architectures
    """
    
    def __init__(self, base_dir: Path, agent_orchestrator: AgentOrchestrator,
                 memory_system: MemorySystem, system_lifecycle: SystemLifecycleManager,
                 prompt_build_engine: PromptBuildEngine):
        self.base_dir = base_dir
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        self.system_lifecycle = system_lifecycle
        self.prompt_build_engine = prompt_build_engine
        
        self.company_presets = self._load_company_presets()
        self.active_builds: Dict[str, Dict[str, Any]] = {}
        
    def build_company(self, company_type: CompanyType, customizations: Dict[str, Any] = None) -> str:
        """Build a complete company system from preset"""
        build_id = str(uuid.uuid4())
        
        # Get preset
        preset = self.company_presets.get(company_type.value)
        if not preset:
            raise ValueError(f"Company type {company_type.value} not found")
        
        # Apply customizations
        if customizations:
            preset = self._apply_customizations(preset, customizations)
        
        # Create build session
        self.active_builds[build_id] = {
            "preset": preset,
            "status": "building",
            "start_time": datetime.now(),
            "progress": 0,
            "current_step": "initializing",
            "generated_artifacts": {}
        }
        
        # Start build in background
        import threading
        thread = threading.Thread(
            target=self._execute_company_build,
            args=(build_id,),
            daemon=True
        )
        thread.start()
        
        # Log build start
        self.memory_system.log_event("company_build_started", {
            "build_id": build_id,
            "company_type": company_type.value,
            "customizations": customizations or {}
        })
        
        return build_id
    
    def _execute_company_build(self, build_id: str):
        """Execute the company build process"""
        build = self.active_builds[build_id]
        preset = build["preset"]
        
        try:
            # Step 1: Generate architecture plan
            build["current_step"] = "architecture"
            build["progress"] = 10
            architecture = self._generate_architecture_plan(preset)
            build["generated_artifacts"]["architecture"] = architecture
            
            # Step 2: Generate feature flows
            build["current_step"] = "features"
            build["progress"] = 30
            features = self._generate_feature_flows(preset)
            build["generated_artifacts"]["features"] = features
            
            # Step 3: Generate UI/UX suggestions
            build["current_step"] = "ui_ux"
            build["progress"] = 50
            ui_ux = self._generate_ui_ux_suggestions(preset)
            build["generated_artifacts"]["ui_ux"] = ui_ux
            
            # Step 4: Generate backend scaffolding
            build["current_step"] = "backend"
            build["progress"] = 70
            backend = self._generate_backend_scaffolding(preset, architecture)
            build["generated_artifacts"]["backend"] = backend
            
            # Step 5: Generate infrastructure setup
            build["current_step"] = "infrastructure"
            build["progress"] = 90
            infrastructure = self._generate_infrastructure_setup(preset, architecture)
            build["generated_artifacts"]["infrastructure"] = infrastructure
            
            # Step 6: Generate integration setup
            build["current_step"] = "integrations"
            build["progress"] = 100
            integrations = self._generate_integration_setup(preset)
            build["generated_artifacts"]["integrations"] = integrations
            
            build["status"] = "completed"
            build["end_time"] = datetime.now()
            
            # Log build completion
            self.memory_system.log_event("company_build_completed", {
                "build_id": build_id,
                "duration": (build["end_time"] - build["start_time"]).total_seconds(),
                "artifacts_generated": list(build["generated_artifacts"].keys())
            })
            
        except Exception as e:
            build["status"] = "failed"
            build["error"] = str(e)
            
            self.memory_system.log_event("company_build_failed", {
                "build_id": build_id,
                "error": str(e)
            })
    
    def _generate_architecture_plan(self, preset: CompanyPreset) -> ArchitecturePlan:
        """Generate detailed architecture plan"""
        architecture_prompt = f"""
        Generate a comprehensive architecture plan for {preset.name}:
        
        Company Type: {preset.company_type.value}
        Target Audience: {preset.target_audience}
        Core Features: {[f.name for f in preset.core_features]}
        Integrations: {[i.value for i in preset.integrations]}
        
        Requirements:
        1. Modern, scalable architecture
        2. Microservices design
        3. Cloud-native approach
        4. Security-first design
        5. Cost-optimized infrastructure
        
        Generate:
        - Frontend stack recommendations
        - Backend stack recommendations
        - Database architecture
        - Infrastructure setup
        - Security measures
        - Scalability plan
        - Cost estimates
        """
        
        # Use prompt build engine to generate architecture
        build_spec = self.prompt_build_engine.parse_prompt(architecture_prompt)
        
        # For now, return a template architecture
        return ArchitecturePlan(
            plan_id=str(uuid.uuid4()),
            company_type=preset.company_type,
            frontend_stack=["React", "TypeScript", "Tailwind CSS", "Next.js"],
            backend_stack=["Python", "FastAPI", "PostgreSQL", "Redis"],
            database_stack=["PostgreSQL", "Redis", "MongoDB"],
            infrastructure={
                "cloud_provider": "AWS",
                "containerization": "Docker + Kubernetes",
                "ci_cd": "GitHub Actions",
                "monitoring": "DataDog"
            },
            security_measures=[
                "JWT authentication",
                "Rate limiting",
                "Input validation",
                "SQL injection prevention",
                "XSS protection"
            ],
            scalability_plan={
                "horizontal_scaling": "Auto-scaling groups",
                "load_balancing": "Application Load Balancer",
                "caching": "Redis cluster",
                "cdn": "CloudFront"
            },
            estimated_cost={
                "monthly": 5000.0,
                "yearly": 60000.0
            }
        )
    
    def _generate_feature_flows(self, preset: CompanyPreset) -> List[FeatureFlow]:
        """Generate detailed feature flows"""
        feature_flows = []
        
        for feature in preset.core_features:
            flow_prompt = f"""
            Generate detailed feature flow for {feature.name} in {preset.name}:
            
            Feature: {feature.name}
            Description: {feature.description}
            Target Audience: {preset.target_audience}
            
            Generate:
            1. Complete user journey
            2. Technical requirements
            3. UI components needed
            4. API endpoints required
            5. Database schema
            6. Priority level
            """
            
            # Use prompt build engine to generate feature flow
            build_spec = self.prompt_build_engine.parse_prompt(flow_prompt)
            
            # For now, return enhanced feature flow
            enhanced_flow = FeatureFlow(
                feature_id=str(uuid.uuid4()),
                name=feature.name,
                description=feature.description,
                user_journey=[
                    "User registration/login",
                    "Feature discovery",
                    "Feature usage",
                    "Results generation",
                    "Export/download"
                ],
                technical_requirements=[
                    "Authentication system",
                    "Data processing pipeline",
                    "File storage",
                    "API rate limiting",
                    "Error handling"
                ],
                ui_components=[
                    "Dashboard",
                    "Feature interface",
                    "Results viewer",
                    "Settings panel",
                    "Help documentation"
                ],
                api_endpoints=[
                    "POST /api/feature/process",
                    "GET /api/feature/status/{id}",
                    "GET /api/feature/results/{id}",
                    "DELETE /api/feature/{id}"
                ],
                database_schema={
                    "users": {"id": "uuid", "email": "string", "created_at": "timestamp"},
                    "features": {"id": "uuid", "user_id": "uuid", "status": "string"},
                    "results": {"id": "uuid", "feature_id": "uuid", "data": "json"}
                },
                priority=feature.priority
            )
            
            feature_flows.append(enhanced_flow)
        
        return feature_flows
    
    def _generate_ui_ux_suggestions(self, preset: CompanyPreset) -> Dict[str, Any]:
        """Generate UI/UX suggestions"""
        ui_prompt = f"""
        Generate UI/UX suggestions for {preset.name}:
        
        Company Type: {preset.company_type.value}
        Target Audience: {preset.target_audience}
        Core Features: {[f.name for f in preset.core_features]}
        
        Generate:
        1. Design system recommendations
        2. Color palette suggestions
        3. Typography recommendations
        4. Layout patterns
        5. Component library suggestions
        6. User experience flows
        7. Accessibility considerations
        """
        
        # Use prompt build engine to generate UI/UX suggestions
        build_spec = self.prompt_build_engine.parse_prompt(ui_prompt)
        
        return {
            "design_system": {
                "colors": {
                    "primary": "#667eea",
                    "secondary": "#764ba2",
                    "success": "#28a745",
                    "warning": "#ffc107",
                    "danger": "#dc3545"
                },
                "typography": {
                    "font_family": "Inter, system-ui, sans-serif",
                    "font_sizes": ["12px", "14px", "16px", "18px", "24px", "32px"],
                    "font_weights": [400, 500, 600, 700]
                },
                "spacing": {
                    "xs": "4px",
                    "sm": "8px",
                    "md": "16px",
                    "lg": "24px",
                    "xl": "32px"
                }
            },
            "layout_patterns": [
                "Dashboard grid layout",
                "Sidebar navigation",
                "Modal dialogs",
                "Card-based content",
                "Responsive design"
            ],
            "component_library": [
                "Button components",
                "Form inputs",
                "Data tables",
                "Charts and graphs",
                "Navigation menus"
            ],
            "user_experience": [
                "Progressive disclosure",
                "Contextual help",
                "Keyboard shortcuts",
                "Mobile-first design",
                "Loading states"
            ],
            "accessibility": [
                "WCAG 2.1 AA compliance",
                "Keyboard navigation",
                "Screen reader support",
                "Color contrast ratios",
                "Focus indicators"
            ]
        }
    
    def _generate_backend_scaffolding(self, preset: CompanyPreset, architecture: ArchitecturePlan) -> Dict[str, Any]:
        """Generate backend scaffolding"""
        backend_prompt = f"""
        Generate backend scaffolding for {preset.name}:
        
        Architecture: {architecture.backend_stack}
        Features: {[f.name for f in preset.core_features]}
        Integrations: {[i.value for i in preset.integrations]}
        
        Generate:
        1. API structure
        2. Database models
        3. Authentication system
        4. Business logic services
        5. Integration services
        6. Testing framework
        7. Deployment configuration
        """
        
        # Use prompt build engine to generate backend scaffolding
        build_spec = self.prompt_build_engine.parse_prompt(backend_prompt)
        
        return {
            "api_structure": {
                "authentication": "/api/auth/*",
                "users": "/api/users/*",
                "features": "/api/features/*",
                "integrations": "/api/integrations/*",
                "admin": "/api/admin/*"
            },
            "database_models": {
                "User": {
                    "id": "UUID",
                    "email": "String",
                    "password_hash": "String",
                    "created_at": "DateTime",
                    "updated_at": "DateTime"
                },
                "Feature": {
                    "id": "UUID",
                    "user_id": "UUID",
                    "name": "String",
                    "status": "String",
                    "created_at": "DateTime"
                },
                "Integration": {
                    "id": "UUID",
                    "user_id": "UUID",
                    "type": "String",
                    "config": "JSON",
                    "created_at": "DateTime"
                }
            },
            "services": [
                "AuthenticationService",
                "UserService",
                "FeatureService",
                "IntegrationService",
                "NotificationService"
            ],
            "middleware": [
                "AuthenticationMiddleware",
                "RateLimitMiddleware",
                "CorsMiddleware",
                "LoggingMiddleware"
            ],
            "testing": {
                "framework": "pytest",
                "coverage": "pytest-cov",
                "mocking": "pytest-mock"
            }
        }
    
    def _generate_infrastructure_setup(self, preset: CompanyPreset, architecture: ArchitecturePlan) -> Dict[str, Any]:
        """Generate infrastructure setup"""
        infra_prompt = f"""
        Generate infrastructure setup for {preset.name}:
        
        Architecture: {architecture.infrastructure}
        Scalability: {architecture.scalability_plan}
        Security: {architecture.security_measures}
        
        Generate:
        1. Cloud infrastructure setup
        2. Containerization configuration
        3. CI/CD pipeline
        4. Monitoring and logging
        5. Backup and disaster recovery
        6. Security configurations
        """
        
        # Use prompt build engine to generate infrastructure setup
        build_spec = self.prompt_build_engine.parse_prompt(infra_prompt)
        
        return {
            "cloud_infrastructure": {
                "vpc": {
                    "cidr": "10.0.0.0/16",
                    "subnets": ["10.0.1.0/24", "10.0.2.0/24"],
                    "security_groups": ["web", "database", "application"]
                },
                "compute": {
                    "ec2_instances": "Auto-scaling group",
                    "load_balancer": "Application Load Balancer",
                    "container_service": "ECS with Fargate"
                },
                "storage": {
                    "database": "RDS PostgreSQL",
                    "cache": "ElastiCache Redis",
                    "file_storage": "S3",
                    "cdn": "CloudFront"
                }
            },
            "containerization": {
                "dockerfile": "Multi-stage build",
                "docker_compose": "Development environment",
                "kubernetes": "Production deployment"
            },
            "ci_cd": {
                "source_control": "GitHub",
                "build_tool": "GitHub Actions",
                "deployment": "Blue-green deployment",
                "environments": ["development", "staging", "production"]
            },
            "monitoring": {
                "application": "DataDog",
                "infrastructure": "CloudWatch",
                "logging": "ELK Stack",
                "alerting": "PagerDuty"
            },
            "security": {
                "ssl_certificates": "AWS Certificate Manager",
                "waf": "AWS WAF",
                "secrets_management": "AWS Secrets Manager",
                "iam": "Least privilege access"
            }
        }
    
    def _generate_integration_setup(self, preset: CompanyPreset) -> Dict[str, Any]:
        """Generate integration setup"""
        integration_setup = {}
        
        for integration in preset.integrations:
            if integration == IntegrationType.STRIPE:
                integration_setup["stripe"] = {
                    "api_keys": "Environment variables",
                    "webhooks": "Event handling",
                    "payment_methods": ["card", "bank_transfer"],
                    "subscription_management": True
                }
            elif integration == IntegrationType.TWILIO:
                integration_setup["twilio"] = {
                    "account_sid": "Environment variable",
                    "auth_token": "Environment variable",
                    "services": ["sms", "voice", "whatsapp"],
                    "webhooks": "Event handling"
                }
            elif integration == IntegrationType.ZAPIER:
                integration_setup["zapier"] = {
                    "api_key": "Environment variable",
                    "webhooks": "Event triggers",
                    "automations": ["user_signup", "feature_usage", "payment_success"]
                }
            elif integration == IntegrationType.OPENAI:
                integration_setup["openai"] = {
                    "api_key": "Environment variable",
                    "models": ["gpt-4", "gpt-3.5-turbo"],
                    "rate_limiting": "Token-based",
                    "caching": "Response caching"
                }
        
        return integration_setup
    
    def _apply_customizations(self, preset: CompanyPreset, customizations: Dict[str, Any]) -> CompanyPreset:
        """Apply customizations to preset"""
        # Create a copy of the preset
        customized_preset = CompanyPreset(
            preset_id=str(uuid.uuid4()),
            company_type=preset.company_type,
            name=customizations.get("name", preset.name),
            description=customizations.get("description", preset.description),
            target_audience=customizations.get("target_audience", preset.target_audience),
            core_features=preset.core_features,
            architecture=preset.architecture,
            integrations=preset.integrations,
            pricing_model=customizations.get("pricing_model", preset.pricing_model),
            go_to_market=customizations.get("go_to_market", preset.go_to_market),
            estimated_timeline=customizations.get("estimated_timeline", preset.estimated_timeline),
            estimated_cost=customizations.get("estimated_cost", preset.estimated_cost)
        )
        
        # Apply feature customizations
        if "features" in customizations:
            customized_preset.core_features = self._customize_features(
                preset.core_features, customizations["features"]
            )
        
        # Apply integration customizations
        if "integrations" in customizations:
            customized_preset.integrations = [
                IntegrationType(integration) for integration in customizations["integrations"]
            ]
        
        return customized_preset
    
    def _customize_features(self, features: List[FeatureFlow], customizations: Dict[str, Any]) -> List[FeatureFlow]:
        """Customize feature flows"""
        customized_features = []
        
        for feature in features:
            if feature.name in customizations:
                customization = customizations[feature.name]
                
                customized_feature = FeatureFlow(
                    feature_id=str(uuid.uuid4()),
                    name=customization.get("name", feature.name),
                    description=customization.get("description", feature.description),
                    user_journey=customization.get("user_journey", feature.user_journey),
                    technical_requirements=customization.get("technical_requirements", feature.technical_requirements),
                    ui_components=customization.get("ui_components", feature.ui_components),
                    api_endpoints=customization.get("api_endpoints", feature.api_endpoints),
                    database_schema=customization.get("database_schema", feature.database_schema),
                    priority=customization.get("priority", feature.priority)
                )
                
                customized_features.append(customized_feature)
            else:
                customized_features.append(feature)
        
        return customized_features
    
    def get_build_status(self, build_id: str) -> Dict[str, Any]:
        """Get build status and results"""
        if build_id not in self.active_builds:
            return {"error": "Build not found"}
        
        build = self.active_builds[build_id]
        
        return {
            "build_id": build_id,
            "status": build["status"],
            "progress": build["progress"],
            "current_step": build["current_step"],
            "start_time": build["start_time"].isoformat(),
            "end_time": build.get("end_time", "").isoformat() if build.get("end_time") else None,
            "generated_artifacts": build.get("generated_artifacts", {}),
            "error": build.get("error")
        }
    
    def get_available_presets(self) -> List[Dict[str, Any]]:
        """Get list of available company presets"""
        presets = []
        
        for company_type in CompanyType:
            if company_type.value in self.company_presets:
                preset = self.company_presets[company_type.value]
                presets.append({
                    "type": company_type.value,
                    "name": preset.name,
                    "description": preset.description,
                    "target_audience": preset.target_audience,
                    "core_features": [f.name for f in preset.core_features],
                    "integrations": [i.value for i in preset.integrations],
                    "estimated_timeline": preset.estimated_timeline,
                    "estimated_cost": preset.estimated_cost
                })
        
        return presets
    
    def _load_company_presets(self) -> Dict[str, CompanyPreset]:
        """Load company presets"""
        return {
            "elevenlabs": CompanyPreset(
                preset_id=str(uuid.uuid4()),
                company_type=CompanyType.ELEVENLABS,
                name="AI Voice Clone SaaS",
                description="Personalized AI voice cloning and text-to-speech platform",
                target_audience="Content creators, marketers, developers",
                core_features=[
                    FeatureFlow(
                        feature_id=str(uuid.uuid4()),
                        name="Voice Cloning",
                        description="Create personalized AI voice clones",
                        user_journey=["Upload voice sample", "Train model", "Generate speech"],
                        technical_requirements=["Audio processing", "AI model training", "Voice synthesis"],
                        ui_components=["Voice uploader", "Training dashboard", "Speech generator"],
                        api_endpoints=["POST /api/voice/clone", "GET /api/voice/{id}", "POST /api/speech/generate"],
                        database_schema={"voices": {"id": "uuid", "user_id": "uuid", "audio_url": "string"}},
                        priority=1
                    ),
                    FeatureFlow(
                        feature_id=str(uuid.uuid4()),
                        name="Text-to-Speech",
                        description="Convert text to natural-sounding speech",
                        user_journey=["Enter text", "Select voice", "Generate audio"],
                        technical_requirements=["Text processing", "Voice synthesis", "Audio generation"],
                        ui_components=["Text editor", "Voice selector", "Audio player"],
                        api_endpoints=["POST /api/tts/generate", "GET /api/tts/{id}"],
                        database_schema={"tts_jobs": {"id": "uuid", "text": "text", "voice_id": "uuid"}},
                        priority=2
                    )
                ],
                architecture=ArchitecturePlan(
                    plan_id=str(uuid.uuid4()),
                    company_type=CompanyType.ELEVENLABS,
                    frontend_stack=["React", "TypeScript", "Web Audio API"],
                    backend_stack=["Python", "FastAPI", "PyTorch", "FFmpeg"],
                    database_stack=["PostgreSQL", "Redis", "S3"],
                    infrastructure={"cloud": "AWS", "gpu": "EC2 P3 instances"},
                    security_measures=["Audio encryption", "Rate limiting"],
                    scalability_plan={"auto_scaling": True, "cdn": True},
                    estimated_cost={"monthly": 8000.0, "yearly": 96000.0}
                ),
                integrations=[IntegrationType.STRIPE, IntegrationType.AWS, IntegrationType.OPENAI],
                pricing_model={"tiered": True, "usage_based": True},
                go_to_market={"strategy": "Product-led growth", "channels": ["Content marketing", "API partnerships"]},
                estimated_timeline="6-8 months",
                estimated_cost=96000.0
            ),
            "gohighlevel": CompanyPreset(
                preset_id=str(uuid.uuid4()),
                company_type=CompanyType.GOHIGHLEVEL,
                name="Marketing Automation Platform",
                description="All-in-one marketing automation and CRM platform",
                target_audience="Agencies, small businesses, marketers",
                core_features=[
                    FeatureFlow(
                        feature_id=str(uuid.uuid4()),
                        name="CRM System",
                        description="Customer relationship management",
                        user_journey=["Add contacts", "Track interactions", "Manage pipelines"],
                        technical_requirements=["Contact management", "Pipeline tracking", "Reporting"],
                        ui_components=["Contact list", "Pipeline view", "Dashboard"],
                        api_endpoints=["POST /api/contacts", "GET /api/pipeline", "PUT /api/contacts/{id}"],
                        database_schema={"contacts": {"id": "uuid", "email": "string", "pipeline_stage": "string"}},
                        priority=1
                    ),
                    FeatureFlow(
                        feature_id=str(uuid.uuid4()),
                        name="Email Marketing",
                        description="Email campaign automation",
                        user_journey=["Create campaign", "Design email", "Send to list"],
                        technical_requirements=["Email templating", "List management", "Analytics"],
                        ui_components=["Campaign builder", "Email editor", "Analytics dashboard"],
                        api_endpoints=["POST /api/campaigns", "POST /api/emails/send"],
                        database_schema={"campaigns": {"id": "uuid", "name": "string", "status": "string"}},
                        priority=2
                    )
                ],
                architecture=ArchitecturePlan(
                    plan_id=str(uuid.uuid4()),
                    company_type=CompanyType.GOHIGHLEVEL,
                    frontend_stack=["React", "TypeScript", "Material-UI"],
                    backend_stack=["Node.js", "Express", "MongoDB"],
                    database_stack=["MongoDB", "Redis", "Elasticsearch"],
                    infrastructure={"cloud": "AWS", "email": "SendGrid"},
                    security_measures=["OAuth", "Data encryption"],
                    scalability_plan={"microservices": True, "load_balancing": True},
                    estimated_cost={"monthly": 6000.0, "yearly": 72000.0}
                ),
                integrations=[IntegrationType.STRIPE, IntegrationType.TWILIO, IntegrationType.SENDGRID],
                pricing_model={"subscription": True, "per_user": True},
                go_to_market={"strategy": "Agency partnerships", "channels": ["Direct sales", "Referrals"]},
                estimated_timeline="8-10 months",
                estimated_cost=72000.0
            ),
            "jasper": CompanyPreset(
                preset_id=str(uuid.uuid4()),
                company_type=CompanyType.JASPER,
                name="AI Content Generation Platform",
                description="AI-powered content creation and copywriting platform",
                target_audience="Marketers, content creators, businesses",
                core_features=[
                    FeatureFlow(
                        feature_id=str(uuid.uuid4()),
                        name="Content Generation",
                        description="Generate various types of content",
                        user_journey=["Select template", "Input prompts", "Generate content"],
                        technical_requirements=["AI integration", "Template system", "Content storage"],
                        ui_components=["Template gallery", "Prompt editor", "Content viewer"],
                        api_endpoints=["POST /api/content/generate", "GET /api/templates"],
                        database_schema={"content": {"id": "uuid", "type": "string", "content": "text"}},
                        priority=1
                    )
                ],
                architecture=ArchitecturePlan(
                    plan_id=str(uuid.uuid4()),
                    company_type=CompanyType.JASPER,
                    frontend_stack=["React", "TypeScript", "Tailwind CSS"],
                    backend_stack=["Python", "FastAPI", "OpenAI API"],
                    database_stack=["PostgreSQL", "Redis"],
                    infrastructure={"cloud": "AWS", "ai": "OpenAI"},
                    security_measures=["API key management", "Content filtering"],
                    scalability_plan={"caching": True, "rate_limiting": True},
                    estimated_cost={"monthly": 4000.0, "yearly": 48000.0}
                ),
                integrations=[IntegrationType.STRIPE, IntegrationType.OPENAI],
                pricing_model={"subscription": True, "usage_based": True},
                go_to_market={"strategy": "Content marketing", "channels": ["SEO", "Social media"]},
                estimated_timeline="4-6 months",
                estimated_cost=48000.0
            )
        }
