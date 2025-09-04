"""
💼 System Build Hub OS - Sales Pipeline Builder

This module enables sales pipeline automation with pre-call intake forms,
auto-generated PoC/MVP creation, live refinement during sales calls,
and demo generation capabilities.
"""

import json
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from agent_framework import AgentOrchestrator, MemorySystem
from system_lifecycle import SystemLifecycleManager
from prompt_build_engine import PromptBuildEngine
from fastpath_agent import FastPathAgent

class SalesStage(Enum):
    INTAKE = "intake"
    ANALYSIS = "analysis"
    POC_GENERATION = "poc_generation"
    PRE_CALL = "pre_call"
    LIVE_CALL = "live_call"
    POST_CALL = "post_call"
    PROPOSAL = "proposal"
    CLOSED = "closed"

class ClientType(Enum):
    STARTUP = "startup"
    SME = "sme"
    ENTERPRISE = "enterprise"
    AGENCY = "agency"
    INDIVIDUAL = "individual"

class ProjectScope(Enum):
    MVP = "mvp"
    FULL_FEATURED = "full_featured"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

@dataclass
class ClientIntake:
    """Client intake form data"""
    client_id: str
    company_name: str
    client_type: ClientType
    contact_name: str
    contact_email: str
    contact_phone: str
    project_description: str
    project_scope: ProjectScope
    budget_range: str
    timeline: str
    key_features: List[str]
    technical_requirements: List[str]
    target_users: str
    competitors: List[str]
    success_metrics: List[str]
    additional_notes: str
    call_scheduled: Optional[datetime] = None
    created_at: datetime = None

@dataclass
class SalesOpportunity:
    """Sales opportunity tracking"""
    opportunity_id: str
    client_intake: ClientIntake
    stage: SalesStage
    poc_system_id: Optional[str] = None
    demo_system_id: Optional[str] = None
    proposal_system_id: Optional[str] = None
    estimated_value: float = 0.0
    probability: float = 0.0
    next_steps: List[str] = None
    notes: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class LiveCallSession:
    """Live call session data"""
    session_id: str
    opportunity_id: str
    start_time: datetime
    participants: List[str]
    agenda: List[str]
    live_features: List[str] = None
    feedback: List[str] = None
    decisions: List[str] = None
    next_actions: List[str] = None
    end_time: Optional[datetime] = None
    recording_url: Optional[str] = None

@dataclass
class DemoConfig:
    """Configuration for demo generation"""
    demo_type: str  # "deck", "site", "video", "interactive"
    target_audience: str
    duration: int  # minutes
    key_points: List[str]
    custom_branding: bool = True
    include_pricing: bool = False
    interactive_elements: bool = True

class SalesPipelineBuilder:
    """
    Sales pipeline automation with pre-call PoC generation and live refinement
    """
    
    def __init__(self, base_dir: Path, agent_orchestrator: AgentOrchestrator,
                 memory_system: MemorySystem, system_lifecycle: SystemLifecycleManager,
                 prompt_build_engine: PromptBuildEngine, fastpath_agent: FastPathAgent):
        self.base_dir = base_dir
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        self.system_lifecycle = system_lifecycle
        self.prompt_build_engine = prompt_build_engine
        self.fastpath_agent = fastpath_agent
        
        self.opportunities: Dict[str, SalesOpportunity] = {}
        self.live_sessions: Dict[str, LiveCallSession] = {}
        self.intake_templates = self._load_intake_templates()
        self.demo_templates = self._load_demo_templates()
        
        self._load_opportunities()
    
    def create_client_intake(self, intake_data: Dict[str, Any]) -> str:
        """Create a new client intake and opportunity"""
        client_id = str(uuid.uuid4())
        
        # Create client intake
        intake = ClientIntake(
            client_id=client_id,
            company_name=intake_data["company_name"],
            client_type=ClientType(intake_data["client_type"]),
            contact_name=intake_data["contact_name"],
            contact_email=intake_data["contact_email"],
            contact_phone=intake_data.get("contact_phone", ""),
            project_description=intake_data["project_description"],
            project_scope=ProjectScope(intake_data["project_scope"]),
            budget_range=intake_data["budget_range"],
            timeline=intake_data["timeline"],
            key_features=intake_data.get("key_features", []),
            technical_requirements=intake_data.get("technical_requirements", []),
            target_users=intake_data["target_users"],
            competitors=intake_data.get("competitors", []),
            success_metrics=intake_data.get("success_metrics", []),
            additional_notes=intake_data.get("additional_notes", ""),
            call_scheduled=datetime.fromisoformat(intake_data["call_scheduled"]) if intake_data.get("call_scheduled") else None,
            created_at=datetime.now()
        )
        
        # Create sales opportunity
        opportunity_id = str(uuid.uuid4())
        opportunity = SalesOpportunity(
            opportunity_id=opportunity_id,
            client_intake=intake,
            stage=SalesStage.INTAKE,
            estimated_value=self._estimate_opportunity_value(intake),
            probability=0.3,  # Initial probability
            next_steps=["Analyze requirements", "Generate PoC", "Schedule call"],
            notes=["New opportunity created from intake form"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.opportunities[opportunity_id] = opportunity
        self._save_opportunities()
        
        # Log the opportunity creation
        self.memory_system.log_event("sales_opportunity_created", {
            "opportunity_id": opportunity_id,
            "client_id": client_id,
            "company_name": intake.company_name,
            "project_scope": intake.project_scope.value,
            "estimated_value": opportunity.estimated_value
        })
        
        return opportunity_id
    
    def analyze_requirements(self, opportunity_id: str) -> Dict[str, Any]:
        """Analyze client requirements and generate initial assessment"""
        if opportunity_id not in self.opportunities:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opportunity = self.opportunities[opportunity_id]
        intake = opportunity.client_intake
        
        # Update stage
        opportunity.stage = SalesStage.ANALYSIS
        opportunity.updated_at = datetime.now()
        
        # Analyze requirements using AI
        analysis_prompt = f"""
        Analyze the following client requirements for a software system:
        
        Company: {intake.company_name}
        Project Description: {intake.project_description}
        Key Features: {', '.join(intake.key_features)}
        Technical Requirements: {', '.join(intake.technical_requirements)}
        Target Users: {intake.target_users}
        Budget Range: {intake.budget_range}
        Timeline: {intake.timeline}
        
        Provide:
        1. System architecture recommendations
        2. Technology stack suggestions
        3. Development timeline estimate
        4. Resource requirements
        5. Risk assessment
        6. Success probability factors
        """
        
        # Use prompt build engine to generate analysis
        build_spec = self.prompt_build_engine.parse_prompt(analysis_prompt)
        
        analysis_result = {
            "opportunity_id": opportunity_id,
            "system_architecture": self._extract_architecture_recommendations(build_spec),
            "technology_stack": self._extract_tech_stack(build_spec),
            "timeline_estimate": self._extract_timeline(build_spec),
            "resource_requirements": self._extract_resources(build_spec),
            "risk_assessment": self._extract_risks(build_spec),
            "success_factors": self._extract_success_factors(build_spec),
            "complexity_score": self._calculate_complexity_score(intake),
            "estimated_effort": self._estimate_effort_hours(intake),
            "recommended_approach": self._generate_recommended_approach(intake, build_spec)
        }
        
        # Update opportunity with analysis
        opportunity.notes.append(f"Requirements analysis completed: {analysis_result['complexity_score']} complexity")
        opportunity.probability = min(0.7, opportunity.probability + 0.2)  # Increase probability after analysis
        
        self._save_opportunities()
        
        # Log analysis completion
        self.memory_system.log_event("sales_requirements_analyzed", {
            "opportunity_id": opportunity_id,
            "complexity_score": analysis_result["complexity_score"],
            "estimated_effort": analysis_result["estimated_effort"],
            "new_probability": opportunity.probability
        })
        
        return analysis_result
    
    def generate_poc(self, opportunity_id: str) -> str:
        """Generate a proof-of-concept system for the opportunity"""
        if opportunity_id not in self.opportunities:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opportunity = self.opportunities[opportunity_id]
        intake = opportunity.client_intake
        
        # Update stage
        opportunity.stage = SalesStage.POC_GENERATION
        opportunity.updated_at = datetime.now()
        
        # Generate PoC prompt
        poc_prompt = f"""
        Create a proof-of-concept system for:
        
        Company: {intake.company_name}
        Project: {intake.project_description}
        Key Features: {', '.join(intake.key_features[:3])}  # Top 3 features for PoC
        Target Users: {intake.target_users}
        
        Requirements:
        - Focus on core functionality only
        - Create a working prototype
        - Include basic UI/UX
        - Demonstrate key value propositions
        - Keep it simple but impressive
        - Include basic documentation
        
        Generate a complete system specification that can be built quickly.
        """
        
        # Use prompt build engine to create PoC
        build_spec = self.prompt_build_engine.parse_prompt(poc_prompt)
        
        # Execute the build to create the PoC system
        poc_system_id = self.prompt_build_engine.execute_build(build_spec)
        
        # Update opportunity with PoC system ID
        opportunity.poc_system_id = poc_system_id
        opportunity.notes.append(f"PoC system created: {poc_system_id}")
        opportunity.probability = min(0.8, opportunity.probability + 0.1)
        
        self._save_opportunities()
        
        # Log PoC generation
        self.memory_system.log_event("sales_poc_generated", {
            "opportunity_id": opportunity_id,
            "poc_system_id": poc_system_id,
            "features_included": intake.key_features[:3]
        })
        
        return poc_system_id
    
    def start_live_call_session(self, opportunity_id: str, participants: List[str], agenda: List[str]) -> str:
        """Start a live call session for real-time system refinement"""
        if opportunity_id not in self.opportunities:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opportunity = self.opportunities[opportunity_id]
        
        # Update stage
        opportunity.stage = SalesStage.LIVE_CALL
        opportunity.updated_at = datetime.now()
        
        # Create live call session
        session_id = str(uuid.uuid4())
        session = LiveCallSession(
            session_id=session_id,
            opportunity_id=opportunity_id,
            start_time=datetime.now(),
            participants=participants,
            agenda=agenda,
            live_features=[],
            feedback=[],
            decisions=[],
            next_actions=[]
        )
        
        self.live_sessions[session_id] = session
        
        # Log session start
        self.memory_system.log_event("sales_live_call_started", {
            "session_id": session_id,
            "opportunity_id": opportunity_id,
            "participants": participants,
            "agenda_items": len(agenda)
        })
        
        return session_id
    
    def add_live_feature(self, session_id: str, feature_description: str) -> str:
        """Add a new feature during live call"""
        if session_id not in self.live_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.live_sessions[session_id]
        opportunity = self.opportunities[session.opportunity_id]
        
        # Add feature to session
        session.live_features.append(feature_description)
        
        # Generate feature implementation
        feature_prompt = f"""
        Add the following feature to the existing system:
        
        Feature: {feature_description}
        Context: This is being added during a live sales call
        Requirements:
        - Implement quickly
        - Keep it simple but functional
        - Show immediate value
        - Integrate with existing system
        
        Generate the implementation specification.
        """
        
        # Use prompt build engine to add feature
        build_spec = self.prompt_build_engine.parse_prompt(feature_prompt)
        
        # Execute the feature addition
        feature_system_id = self.prompt_build_engine.execute_build(build_spec)
        
        # Log feature addition
        self.memory_system.log_event("sales_live_feature_added", {
            "session_id": session_id,
            "opportunity_id": session.opportunity_id,
            "feature_description": feature_description,
            "feature_system_id": feature_system_id
        })
        
        return feature_system_id
    
    def end_live_call_session(self, session_id: str, feedback: List[str], decisions: List[str], next_actions: List[str]) -> Dict[str, Any]:
        """End a live call session and generate summary"""
        if session_id not in self.live_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.live_sessions[session_id]
        opportunity = self.opportunities[session.opportunity_id]
        
        # Update session
        session.end_time = datetime.now()
        session.feedback = feedback
        session.decisions = decisions
        session.next_actions = next_actions
        
        # Update opportunity
        opportunity.stage = SalesStage.POST_CALL
        opportunity.updated_at = datetime.now()
        opportunity.notes.extend(feedback)
        opportunity.next_steps = next_actions
        
        # Calculate session metrics
        session_duration = (session.end_time - session.start_time).total_seconds() / 60  # minutes
        features_added = len(session.live_features)
        
        # Update probability based on call outcome
        if any("positive" in f.lower() or "interested" in f.lower() for f in feedback):
            opportunity.probability = min(0.9, opportunity.probability + 0.15)
        elif any("concern" in f.lower() or "issue" in f.lower() for f in feedback):
            opportunity.probability = max(0.2, opportunity.probability - 0.1)
        
        self._save_opportunities()
        
        # Generate call summary
        summary = {
            "session_id": session_id,
            "opportunity_id": session.opportunity_id,
            "duration_minutes": session_duration,
            "features_added": features_added,
            "feedback": feedback,
            "decisions": decisions,
            "next_actions": next_actions,
            "new_probability": opportunity.probability
        }
        
        # Log session end
        self.memory_system.log_event("sales_live_call_ended", summary)
        
        return summary
    
    def generate_demo(self, opportunity_id: str, demo_config: DemoConfig) -> str:
        """Generate a demo (deck, site, video, or interactive) for the opportunity"""
        if opportunity_id not in self.opportunities:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opportunity = self.opportunities[opportunity_id]
        intake = opportunity.client_intake
        
        # Generate demo prompt based on type
        if demo_config.demo_type == "deck":
            demo_prompt = self._generate_deck_prompt(intake, demo_config)
        elif demo_config.demo_type == "site":
            demo_prompt = self._generate_site_prompt(intake, demo_config)
        elif demo_config.demo_type == "video":
            demo_prompt = self._generate_video_prompt(intake, demo_config)
        else:
            demo_prompt = self._generate_interactive_prompt(intake, demo_config)
        
        # Use prompt build engine to create demo
        build_spec = self.prompt_build_engine.parse_prompt(demo_prompt)
        
        # Execute the demo build
        demo_system_id = self.prompt_build_engine.execute_build(build_spec)
        
        # Update opportunity
        opportunity.demo_system_id = demo_system_id
        opportunity.notes.append(f"Demo {demo_config.demo_type} created: {demo_system_id}")
        
        self._save_opportunities()
        
        # Log demo generation
        self.memory_system.log_event("sales_demo_generated", {
            "opportunity_id": opportunity_id,
            "demo_system_id": demo_system_id,
            "demo_type": demo_config.demo_type,
            "target_audience": demo_config.target_audience
        })
        
        return demo_system_id
    
    def generate_proposal(self, opportunity_id: str) -> str:
        """Generate a formal proposal for the opportunity"""
        if opportunity_id not in self.opportunities:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opportunity = self.opportunities[opportunity_id]
        intake = opportunity.client_intake
        
        # Update stage
        opportunity.stage = SalesStage.PROPOSAL
        opportunity.updated_at = datetime.now()
        
        # Generate proposal prompt
        proposal_prompt = f"""
        Create a comprehensive proposal for:
        
        Client: {intake.company_name}
        Project: {intake.project_description}
        Scope: {intake.project_scope.value}
        Budget Range: {intake.budget_range}
        Timeline: {intake.timeline}
        
        Include:
        1. Executive Summary
        2. Project Overview
        3. Technical Approach
        4. Deliverables
        5. Timeline & Milestones
        6. Investment & Pricing
        7. Team & Resources
        8. Risk Mitigation
        9. Success Metrics
        10. Next Steps
        
        Make it professional, comprehensive, and compelling.
        """
        
        # Use prompt build engine to create proposal
        build_spec = self.prompt_build_engine.parse_prompt(proposal_prompt)
        
        # Execute the proposal build
        proposal_system_id = self.prompt_build_engine.execute_build(build_spec)
        
        # Update opportunity
        opportunity.proposal_system_id = proposal_system_id
        opportunity.notes.append(f"Proposal created: {proposal_system_id}")
        
        self._save_opportunities()
        
        # Log proposal generation
        self.memory_system.log_event("sales_proposal_generated", {
            "opportunity_id": opportunity_id,
            "proposal_system_id": proposal_system_id,
            "estimated_value": opportunity.estimated_value
        })
        
        return proposal_system_id
    
    def close_opportunity(self, opportunity_id: str, outcome: str, final_value: float = None) -> Dict[str, Any]:
        """Close an opportunity with final outcome"""
        if opportunity_id not in self.opportunities:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opportunity = self.opportunities[opportunity_id]
        
        # Update stage
        opportunity.stage = SalesStage.CLOSED
        opportunity.updated_at = datetime.now()
        
        if final_value:
            opportunity.estimated_value = final_value
        
        # Update probability based on outcome
        if outcome.lower() == "won":
            opportunity.probability = 1.0
        elif outcome.lower() == "lost":
            opportunity.probability = 0.0
        else:
            opportunity.probability = 0.5  # Deferred or other
        
        opportunity.notes.append(f"Opportunity closed: {outcome}")
        
        self._save_opportunities()
        
        # Log opportunity closure
        self.memory_system.log_event("sales_opportunity_closed", {
            "opportunity_id": opportunity_id,
            "outcome": outcome,
            "final_value": final_value,
            "final_probability": opportunity.probability,
            "total_duration_days": (opportunity.updated_at - opportunity.created_at).days
        })
        
        return {
            "opportunity_id": opportunity_id,
            "outcome": outcome,
            "final_value": final_value,
            "final_probability": opportunity.probability,
            "total_duration_days": (opportunity.updated_at - opportunity.created_at).days
        }
    
    def get_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        """Get opportunity details"""
        if opportunity_id not in self.opportunities:
            return {"error": "Opportunity not found"}
        
        opportunity = self.opportunities[opportunity_id]
        
        return {
            "opportunity_id": opportunity.opportunity_id,
            "client_intake": asdict(opportunity.client_intake),
            "stage": opportunity.stage.value,
            "poc_system_id": opportunity.poc_system_id,
            "demo_system_id": opportunity.demo_system_id,
            "proposal_system_id": opportunity.proposal_system_id,
            "estimated_value": opportunity.estimated_value,
            "probability": opportunity.probability,
            "next_steps": opportunity.next_steps,
            "notes": opportunity.notes,
            "created_at": opportunity.created_at.isoformat(),
            "updated_at": opportunity.updated_at.isoformat()
        }
    
    def get_all_opportunities(self) -> List[Dict[str, Any]]:
        """Get all opportunities"""
        return [self.get_opportunity(opp_id) for opp_id in self.opportunities.keys()]
    
    def get_sales_analytics(self) -> Dict[str, Any]:
        """Get sales pipeline analytics"""
        total_opportunities = len(self.opportunities)
        total_value = sum(opp.estimated_value for opp in self.opportunities.values())
        
        # Stage breakdown
        stage_counts = {}
        for stage in SalesStage:
            stage_counts[stage.value] = len([opp for opp in self.opportunities.values() if opp.stage == stage])
        
        # Probability distribution
        high_prob = len([opp for opp in self.opportunities.values() if opp.probability >= 0.7])
        medium_prob = len([opp for opp in self.opportunities.values() if 0.3 <= opp.probability < 0.7])
        low_prob = len([opp for opp in self.opportunities.values() if opp.probability < 0.3])
        
        # Client type breakdown
        client_types = {}
        for client_type in ClientType:
            client_types[client_type.value] = len([
                opp for opp in self.opportunities.values() 
                if opp.client_intake.client_type == client_type
            ])
        
        return {
            "total_opportunities": total_opportunities,
            "total_pipeline_value": total_value,
            "stage_breakdown": stage_counts,
            "probability_distribution": {
                "high": high_prob,
                "medium": medium_prob,
                "low": low_prob
            },
            "client_type_breakdown": client_types,
            "average_opportunity_value": total_value / total_opportunities if total_opportunities > 0 else 0,
            "conversion_rate": stage_counts.get("closed", 0) / total_opportunities if total_opportunities > 0 else 0
        }
    
    def _estimate_opportunity_value(self, intake: ClientIntake) -> float:
        """Estimate opportunity value based on intake data"""
        base_values = {
            ClientType.STARTUP: 15000,
            ClientType.SME: 25000,
            ClientType.ENTERPRISE: 75000,
            ClientType.AGENCY: 35000,
            ClientType.INDIVIDUAL: 8000
        }
        
        base_value = base_values.get(intake.client_type, 20000)
        
        # Adjust for scope
        scope_multipliers = {
            ProjectScope.MVP: 0.6,
            ProjectScope.FULL_FEATURED: 1.0,
            ProjectScope.ENTERPRISE: 2.5,
            ProjectScope.CUSTOM: 1.5
        }
        
        scope_multiplier = scope_multipliers.get(intake.project_scope, 1.0)
        
        # Adjust for complexity
        complexity_score = self._calculate_complexity_score(intake)
        complexity_multiplier = 1.0 + (complexity_score * 0.3)
        
        return base_value * scope_multiplier * complexity_multiplier
    
    def _calculate_complexity_score(self, intake: ClientIntake) -> float:
        """Calculate complexity score based on intake data"""
        score = 0.0
        
        # Feature complexity
        score += len(intake.key_features) * 0.1
        
        # Technical requirements complexity
        score += len(intake.technical_requirements) * 0.15
        
        # Integration complexity
        if any("api" in req.lower() or "integration" in req.lower() for req in intake.technical_requirements):
            score += 0.3
        
        # AI/ML complexity
        if any("ai" in req.lower() or "machine learning" in req.lower() for req in intake.technical_requirements):
            score += 0.5
        
        return min(2.0, score)  # Cap at 2.0
    
    def _estimate_effort_hours(self, intake: ClientIntake) -> int:
        """Estimate effort in hours"""
        complexity_score = self._calculate_complexity_score(intake)
        base_hours = 80  # Base hours for a typical project
        
        return int(base_hours * (1 + complexity_score * 0.5))
    
    def _generate_recommended_approach(self, intake: ClientIntake, build_spec) -> str:
        """Generate recommended approach based on analysis"""
        complexity_score = self._calculate_complexity_score(intake)
        
        if complexity_score > 1.5:
            return "Phased development with FastPath optimization"
        elif complexity_score > 1.0:
            return "Parallel development with specialized agents"
        else:
            return "Standard development approach"
    
    def _extract_architecture_recommendations(self, build_spec) -> List[str]:
        """Extract architecture recommendations from build spec"""
        # In production, parse build_spec for architecture info
        return ["Microservices architecture", "API-first design", "Scalable database"]
    
    def _extract_tech_stack(self, build_spec) -> List[str]:
        """Extract technology stack from build spec"""
        # In production, parse build_spec for tech stack
        return ["React frontend", "Python backend", "PostgreSQL database"]
    
    def _extract_timeline(self, build_spec) -> str:
        """Extract timeline estimate from build spec"""
        # In production, parse build_spec for timeline
        return "8-12 weeks"
    
    def _extract_resources(self, build_spec) -> List[str]:
        """Extract resource requirements from build spec"""
        # In production, parse build_spec for resources
        return ["2 developers", "1 designer", "1 project manager"]
    
    def _extract_risks(self, build_spec) -> List[str]:
        """Extract risk assessment from build spec"""
        # In production, parse build_spec for risks
        return ["Third-party API dependencies", "Data security requirements", "Performance optimization"]
    
    def _extract_success_factors(self, build_spec) -> List[str]:
        """Extract success factors from build spec"""
        # In production, parse build_spec for success factors
        return ["Clear requirements", "Regular client feedback", "Agile development process"]
    
    def _generate_deck_prompt(self, intake: ClientIntake, config: DemoConfig) -> str:
        """Generate prompt for demo deck creation"""
        return f"""
        Create a professional sales presentation deck for:
        
        Company: {intake.company_name}
        Project: {intake.project_description}
        Target Audience: {config.target_audience}
        Duration: {config.duration} minutes
        
        Key Points to Cover:
        {chr(10).join(f"- {point}" for point in config.key_points)}
        
        Include:
        1. Problem statement
        2. Solution overview
        3. Key features demonstration
        4. Technical architecture
        5. Implementation timeline
        6. Investment and ROI
        7. Next steps
        
        Make it visually appealing and compelling.
        """
    
    def _generate_site_prompt(self, intake: ClientIntake, config: DemoConfig) -> str:
        """Generate prompt for demo site creation"""
        return f"""
        Create a demo website for:
        
        Company: {intake.company_name}
        Project: {intake.project_description}
        Target Audience: {config.target_audience}
        
        Requirements:
        - Interactive demo of key features
        - Professional design
        - Mobile responsive
        - Fast loading
        - Clear call-to-action
        - Contact information
        
        Include demo functionality for the main features.
        """
    
    def _generate_video_prompt(self, intake: ClientIntake, config: DemoConfig) -> str:
        """Generate prompt for demo video creation"""
        return f"""
        Create a demo video script for:
        
        Company: {intake.company_name}
        Project: {intake.project_description}
        Duration: {config.duration} minutes
        Target Audience: {config.target_audience}
        
        Script should include:
        1. Introduction and problem statement
        2. Solution overview
        3. Feature demonstrations
        4. Technical highlights
        5. Benefits and ROI
        6. Call to action
        
        Make it engaging and professional.
        """
    
    def _generate_interactive_prompt(self, intake: ClientIntake, config: DemoConfig) -> str:
        """Generate prompt for interactive demo creation"""
        return f"""
        Create an interactive demo application for:
        
        Company: {intake.company_name}
        Project: {intake.project_description}
        Target Audience: {config.target_audience}
        
        Requirements:
        - Hands-on experience with key features
        - Guided tour functionality
        - Interactive elements
        - Real-time feedback
        - Professional UI/UX
        - Easy navigation
        
        Make it engaging and demonstrate real value.
        """
    
    def _load_intake_templates(self) -> Dict[str, Any]:
        """Load intake form templates"""
        return {
            "startup": {
                "budget_ranges": ["$5K-$15K", "$15K-$30K", "$30K-$50K"],
                "timelines": ["2-4 weeks", "1-2 months", "2-3 months"],
                "common_features": ["User authentication", "Basic CRUD", "API integration"]
            },
            "enterprise": {
                "budget_ranges": ["$50K-$100K", "$100K-$250K", "$250K+"],
                "timelines": ["3-6 months", "6-12 months", "12+ months"],
                "common_features": ["SSO integration", "Advanced analytics", "Custom workflows"]
            }
        }
    
    def _load_demo_templates(self) -> Dict[str, Any]:
        """Load demo templates"""
        return {
            "deck": {
                "sections": ["Problem", "Solution", "Features", "Architecture", "Timeline", "Investment"],
                "duration": 15
            },
            "site": {
                "pages": ["Home", "Features", "Demo", "Pricing", "Contact"],
                "interactive": True
            }
        }
    
    def _save_opportunities(self):
        """Save opportunities to file"""
        opportunities_file = self.base_dir / "sales_opportunities.json"
        
        # Convert to serializable format
        data = {}
        for opp_id, opportunity in self.opportunities.items():
            data[opp_id] = {
                "opportunity_id": opportunity.opportunity_id,
                "client_intake": asdict(opportunity.client_intake),
                "stage": opportunity.stage.value,
                "poc_system_id": opportunity.poc_system_id,
                "demo_system_id": opportunity.demo_system_id,
                "proposal_system_id": opportunity.proposal_system_id,
                "estimated_value": opportunity.estimated_value,
                "probability": opportunity.probability,
                "next_steps": opportunity.next_steps,
                "notes": opportunity.notes,
                "created_at": opportunity.created_at.isoformat(),
                "updated_at": opportunity.updated_at.isoformat()
            }
        
        with open(opportunities_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_opportunities(self):
        """Load opportunities from file"""
        opportunities_file = self.base_dir / "sales_opportunities.json"
        
        if not opportunities_file.exists():
            return
        
        with open(opportunities_file, 'r') as f:
            data = json.load(f)
        
        for opp_id, opp_data in data.items():
            # Reconstruct ClientIntake
            intake_data = opp_data["client_intake"]
            client_intake = ClientIntake(
                client_id=intake_data["client_id"],
                company_name=intake_data["company_name"],
                client_type=ClientType(intake_data["client_type"]),
                contact_name=intake_data["contact_name"],
                contact_email=intake_data["contact_email"],
                contact_phone=intake_data["contact_phone"],
                project_description=intake_data["project_description"],
                project_scope=ProjectScope(intake_data["project_scope"]),
                budget_range=intake_data["budget_range"],
                timeline=intake_data["timeline"],
                key_features=intake_data["key_features"],
                technical_requirements=intake_data["technical_requirements"],
                target_users=intake_data["target_users"],
                competitors=intake_data["competitors"],
                success_metrics=intake_data["success_metrics"],
                additional_notes=intake_data["additional_notes"],
                call_scheduled=datetime.fromisoformat(intake_data["call_scheduled"]) if intake_data["call_scheduled"] else None,
                created_at=datetime.fromisoformat(intake_data["created_at"])
            )
            
            # Reconstruct SalesOpportunity
            opportunity = SalesOpportunity(
                opportunity_id=opp_data["opportunity_id"],
                client_intake=client_intake,
                stage=SalesStage(opp_data["stage"]),
                poc_system_id=opp_data["poc_system_id"],
                demo_system_id=opp_data["demo_system_id"],
                proposal_system_id=opp_data["proposal_system_id"],
                estimated_value=opp_data["estimated_value"],
                probability=opp_data["probability"],
                next_steps=opp_data["next_steps"],
                notes=opp_data["notes"],
                created_at=datetime.fromisoformat(opp_data["created_at"]),
                updated_at=datetime.fromisoformat(opp_data["updated_at"])
            )
            
            self.opportunities[opp_id] = opportunity
