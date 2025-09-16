"""
Features Catalog - Single source of truth for all SBH features
"""
from typing import TypedDict, Literal, List, Optional
from dataclasses import dataclass


@dataclass
class Feature:
    """Feature definition for the catalog"""
    slug: str
    title: str
    category: Literal["core", "intelligence", "data", "business", "security"]
    route: str
    roles: List[str]
    flag: Optional[str] = None
    status: Optional[Literal["core", "beta", "security"]] = None
    description: str = ""
    icon: Optional[str] = None


# Canonical features registry
FEATURES: List[Feature] = [
    # Hero Features
    Feature(
        slug="start-build",
        title="Start a Build",
        category="core",
        route="/ui/build",
        roles=["viewer", "developer", "owner", "admin"],
        status="core",
        description="Create complete systems with natural language commands using AI-powered orchestration.",
        icon="🚀"
    ),
    Feature(
        slug="open-preview",
        title="Open Preview",
        category="core",
        route="/ui/preview",
        roles=["viewer", "developer", "owner", "admin"],
        status="core",
        description="Test and validate your systems in a secure preview environment with real-time feedback.",
        icon="👁️"
    ),
    Feature(
        slug="create-brain",
        title="Create Brain",
        category="intelligence",
        route="/ui/brain",
        roles=["viewer", "developer", "owner", "admin"],
        status="beta",
        description="Build intelligent agents that optimize your development workflow and automate complex tasks.",
        icon="🧠"
    ),
    
    # Recommended Features
    Feature(
        slug="project-loader",
        title="Project Loader",
        category="core",
        route="/ui/project-loader",
        roles=["viewer", "developer", "owner", "admin"],
        status="core",
        description="Load existing projects, analyze structure, and generate completion plans.",
        icon="📂"
    ),
    Feature(
        slug="visual-builder",
        title="Visual Builder",
        category="core",
        route="/ui/visual-builder",
        roles=["viewer", "developer", "owner", "admin"],
        status="core",
        description="Drag-and-drop interface for creating systems with visual components.",
        icon="🎨"
    ),
    Feature(
        slug="data-refinery",
        title="Data Refinery",
        category="data",
        route="/ui/data-refinery",
        roles=["viewer", "developer", "owner", "admin"],
        status="core",
        description="Process and transform data with automated pipelines.",
        icon="⚙️"
    ),
    Feature(
        slug="gtm-engine",
        title="GTM Engine",
        category="business",
        route="/ui/gtm",
        roles=["viewer", "developer", "owner", "admin"],
        flag="gtm-engine",
        status="beta",
        description="Go-to-market automation with customer journey mapping.",
        icon="🚀"
    ),
    Feature(
        slug="investor-pack",
        title="Investor Pack",
        category="business",
        route="/ui/investor",
        roles=["viewer", "developer", "owner", "admin"],
        flag="investor-pack",
        status="beta",
        description="Investment-ready documentation with financial modeling.",
        icon="📊"
    ),
    Feature(
        slug="access-hub",
        title="Access Hub",
        category="business",
        route="/ui/access-hub",
        roles=["viewer", "developer", "owner", "admin"],
        flag="access-hub",
        status="core",
        description="User access management with SSO integration.",
        icon="🔑"
    ),
    Feature(
        slug="growth-agent",
        title="Growth Agent",
        category="intelligence",
        route="/ui/growth-agent",
        roles=["developer", "owner", "admin"],
        flag="growth-agent",
        status="beta",
        description="AI-powered growth experiments and optimization.",
        icon="📈"
    ),
    
    # Additional User-Facing Features
    Feature(
        slug="autonomous-builder",
        title="Autonomous Builder",
        category="core",
        route="/ui/autonomous-builder",
        roles=["developer", "owner", "admin"],
        status="core",
        description="Continuous build loops with goal-driven development.",
        icon="🔄"
    ),
    Feature(
        slug="template-launcher",
        title="Template Launcher",
        category="core",
        route="/ui/template-launcher",
        roles=["developer", "owner", "admin"],
        status="core",
        description="Launch and customize system templates.",
        icon="📋"
    ),
    Feature(
        slug="fastpath-agent",
        title="FastPath Agent",
        category="intelligence",
        route="/ui/fastpath-agent",
        roles=["developer", "owner", "admin"],
        status="beta",
        description="Intelligent build optimization with bottleneck analysis.",
        icon="🚀"
    ),
    Feature(
        slug="agent-ecosystem",
        title="Agent Ecosystem",
        category="intelligence",
        route="/ui/agent-ecosystem",
        roles=["developer", "owner", "admin"],
        status="beta",
        description="Multi-agent collaboration platform for complex orchestration.",
        icon="🤖"
    ),
    Feature(
        slug="agent-training",
        title="Agent Training",
        category="intelligence",
        route="/ui/agent-training",
        roles=["developer", "owner", "admin"],
        status="beta",
        description="Train and optimize AI agents with custom datasets.",
        icon="🎓"
    ),
    Feature(
        slug="predictive-dashboard",
        title="Predictive Intelligence",
        category="intelligence",
        route="/ui/predictive-dashboard",
        roles=["developer", "owner", "admin"],
        status="beta",
        description="AI-powered insights and forecasting for system performance.",
        icon="🔮"
    ),
    Feature(
        slug="memory-upload",
        title="Memory Upload",
        category="data",
        route="/ui/memory-upload",
        roles=["developer", "owner", "admin"],
        status="core",
        description="Upload and process system memory files.",
        icon="📤"
    ),
    Feature(
        slug="quality-gates",
        title="Quality Gates",
        category="data",
        route="/ui/quality-gates",
        roles=["developer", "owner", "admin"],
        flag="quality-gates",
        status="security",
        description="Automated quality assurance with customizable checks.",
        icon="✅"
    ),
    Feature(
        slug="system-delivery",
        title="System Delivery",
        category="core",
        route="/ui/system-delivery",
        roles=["developer", "owner", "admin"],
        status="core",
        description="Automated deployment pipeline with rollback capabilities.",
        icon="📦"
    ),
]


def get_features_for_role(role: str, category: Optional[str] = None, search_query: Optional[str] = None) -> List[Feature]:
    """Get features filtered by role, category, and search query"""
    filtered_features = []
    
    for feature in FEATURES:
        # Check role access
        if role not in feature.roles:
            continue
            
        # Check feature flag if required (simplified for now)
        if feature.flag:
            # For now, assume all feature flags are enabled
            # In production, this would check the actual feature flag
            pass
            
        # Check category filter
        if category and feature.category != category:
            continue
            
        # Check search query
        if search_query:
            query = search_query.lower()
            if (query not in feature.title.lower() and 
                query not in feature.description.lower() and
                query not in feature.slug.lower()):
                continue
                
        filtered_features.append(feature)
    
    return filtered_features


def get_feature_by_slug(slug: str) -> Optional[Feature]:
    """Get a feature by its slug"""
    for feature in FEATURES:
        if feature.slug == slug:
            return feature
    return None
