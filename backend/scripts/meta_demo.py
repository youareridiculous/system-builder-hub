#!/usr/bin/env python3
"""
Meta-Builder v2 Demo Script
Creates a sample specification and runs the build process.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from meta_builder_v2.models import create_spec, create_plan, create_run
from meta_builder_v2.orchestrator import MetaBuilderOrchestrator
from meta_builder_v2.agents import AgentContext
from src.llm.llm_core import LLMClient
from src.redis_core import get_redis_client


async def create_demo_spec():
    """Create a demo CRM specification."""
    spec_data = {
        "name": "Demo CRM System",
        "domain": "crm",
        "entities": [
            {
                "name": "Contact",
                "fields": [
                    {"name": "email", "type": "email", "unique": True, "required": True},
                    {"name": "first_name", "type": "string", "required": True},
                    {"name": "last_name", "type": "string", "required": True},
                    {"name": "phone", "type": "string"},
                    {"name": "company", "type": "string"},
                    {"name": "title", "type": "string"}
                ]
            },
            {
                "name": "Deal",
                "fields": [
                    {"name": "title", "type": "string", "required": True},
                    {"name": "amount", "type": "decimal", "precision": 10, "scale": 2},
                    {"name": "stage", "type": "enum", "values": ["lead", "qualified", "proposal", "negotiation", "won", "lost"]},
                    {"name": "contact_id", "type": "uuid", "foreign_key": "Contact.id"},
                    {"name": "expected_close_date", "type": "datetime"}
                ]
            },
            {
                "name": "Task",
                "fields": [
                    {"name": "title", "type": "string", "required": True},
                    {"name": "description", "type": "text"},
                    {"name": "due_date", "type": "datetime"},
                    {"name": "status", "type": "enum", "values": ["pending", "in_progress", "completed"]},
                    {"name": "contact_id", "type": "uuid", "foreign_key": "Contact.id"},
                    {"name": "deal_id", "type": "uuid", "foreign_key": "Deal.id"}
                ]
            }
        ],
        "workflows": [
            {
                "name": "lead_to_customer",
                "states": ["lead", "qualified", "proposal", "negotiation", "won"],
                "transitions": [
                    {"from": "lead", "to": "qualified", "trigger": "qualify"},
                    {"from": "qualified", "to": "proposal", "trigger": "create_proposal"},
                    {"from": "proposal", "to": "negotiation", "trigger": "start_negotiation"},
                    {"from": "negotiation", "to": "won", "trigger": "close_deal"}
                ]
            }
        ],
        "integrations": ["email", "calendar", "analytics"],
        "ai": {
            "copilots": ["sales", "support"],
            "rag": True,
            "automation": ["lead_scoring", "follow_up_reminders"]
        },
        "non_functional": {
            "multi_tenant": True,
            "rbac": True,
            "observability": True,
            "security": ["encryption", "audit_logging", "rate_limiting"]
        },
        "acceptance": [
            {
                "id": "AC1",
                "text": "User can create and manage contacts",
                "category": "functional"
            },
            {
                "id": "AC2", 
                "text": "User can create deals and associate with contacts",
                "category": "functional"
            },
            {
                "id": "AC3",
                "text": "User can track deal pipeline stages",
                "category": "functional"
            },
            {
                "id": "AC4",
                "text": "User can create and assign tasks",
                "category": "functional"
            },
            {
                "id": "AC5",
                "text": "System enforces user authentication and authorization",
                "category": "security"
            }
        ]
    }
    
    return spec_data


async def run_demo():
    """Run the Meta-Builder v2 demo."""
    print("🚀 Starting Meta-Builder v2 Demo")
    print("=" * 50)
    
    # Create demo specification
    print("📝 Creating demo CRM specification...")
    spec_data = await create_demo_spec()
    
    print(f"✅ Specification created:")
    print(f"   Name: {spec_data['name']}")
    print(f"   Domain: {spec_data['domain']}")
    print(f"   Entities: {len(spec_data['entities'])}")
    print(f"   Workflows: {len(spec_data['workflows'])}")
    print(f"   Integrations: {len(spec_data['integrations'])}")
    print(f"   Acceptance Criteria: {len(spec_data['acceptance'])}")
    
    # Create agent context
    print("\n🔧 Setting up agent context...")
    agent_context = AgentContext(
        tenant_id=uuid4(),
        user_id=uuid4(),
        llm=LLMClient(),
        redis=get_redis_client()
    )
    
    # Initialize orchestrator
    print("⚙️ Initializing Meta-Builder orchestrator...")
    orchestrator = MetaBuilderOrchestrator()
    
    # Simulate the build process
    print("\n🔄 Simulating build process...")
    
    # Step 1: Product Architect
    print("   📋 Product Architect: Analyzing requirements...")
    architect_agent = orchestrator.agents["product_architect"](agent_context)
    spec_result = await architect_agent.execute("create_spec", {
        "goal_text": "Build a CRM system for managing contacts, deals, and tasks",
        "guided_input": spec_data
    })
    print(f"   ✅ Specification analysis complete (confidence: {spec_result['confidence']:.1%})")
    
    # Step 2: System Designer
    print("   🏗️ System Designer: Creating system plan...")
    designer_agent = orchestrator.agents["system_designer"](agent_context)
    plan_result = await designer_agent.execute("create_plan", {
        "spec": spec_result["spec"]
    })
    print(f"   ✅ System plan created (estimated effort: {plan_result['estimated_effort']['total']} hours)")
    
    # Step 3: Security/Compliance
    print("   🔒 Security/Compliance: Reviewing security...")
    security_agent = orchestrator.agents["security_compliance"](agent_context)
    security_result = await security_agent.execute("review_security", {
        "spec": spec_result["spec"],
        "plan": plan_result["plan"]
    })
    print(f"   ✅ Security review complete (risk score: {security_result['risk_score']:.1f})")
    
    # Step 4: Codegen Engineer
    print("   💻 Codegen Engineer: Generating code...")
    codegen_agent = orchestrator.agents["codegen_engineer"](agent_context)
    codegen_result = await codegen_agent.execute("generate_code", {
        "spec": spec_result["spec"],
        "plan": plan_result["plan"]
    })
    print(f"   ✅ Code generation complete ({codegen_result['summary']['files_generated']} files)")
    
    # Step 5: QA/Evaluator
    print("   🧪 QA/Evaluator: Running tests...")
    evaluator_agent = orchestrator.agents["qa_evaluator"](agent_context)
    eval_result = await evaluator_agent.execute("evaluate", {
        "spec": spec_result["spec"],
        "artifacts": codegen_result["artifacts"]
    })
    print(f"   ✅ Evaluation complete (score: {eval_result['score']:.1f}/100)")
    
    # Step 6: DevOps
    print("   🚀 DevOps: Preparing deployment...")
    devops_agent = orchestrator.agents["devops"](agent_context)
    devops_result = await devops_agent.execute("generate_artifacts", {
        "spec": spec_result["spec"],
        "artifacts": codegen_result["artifacts"]
    })
    print(f"   ✅ Deployment artifacts created ({len(devops_result['artifacts'])} artifacts)")
    
    # Step 7: Reviewer
    print("   👀 Reviewer: Generating summary...")
    reviewer_agent = orchestrator.agents["reviewer"](agent_context)
    review_result = await reviewer_agent.execute("review_run", {
        "run_data": {
            "id": str(uuid4()),
            "status": "succeeded",
            "iteration": 1,
            "started_at": datetime.utcnow(),
            "finished_at": datetime.utcnow()
        },
        "spec": spec_result["spec"],
        "plan": plan_result["plan"],
        "evaluation_report": eval_result,
        "artifacts": codegen_result["artifacts"]
    })
    print(f"   ✅ Review complete (approval required: {review_result['approval_required']})")
    
    # Demo summary
    print("\n" + "=" * 50)
    print("🎉 Meta-Builder v2 Demo Complete!")
    print("\n📊 Summary:")
    print(f"   • Specification: {spec_data['name']}")
    print(f"   • Entities: {len(spec_data['entities'])}")
    print(f"   • API Endpoints: {len(plan_result['plan']['api_endpoints'])}")
    print(f"   • Files Generated: {codegen_result['summary']['files_generated']}")
    print(f"   • Test Score: {eval_result['score']:.1f}/100")
    print(f"   • Security Risk: {security_result['risk_score']:.1f}/100")
    print(f"   • Overall Status: {'✅ PASSED' if eval_result['passed'] else '❌ FAILED'}")
    
    if review_result['approval_required']:
        print("\n⚠️  Human approval required before deployment")
        print("   This is normal for systems with security requirements")
    
    print("\n🔗 Next Steps:")
    print("   1. Review generated code in the artifacts")
    print("   2. Run tests locally: make test")
    print("   3. Deploy to staging: make deploy-staging")
    print("   4. Approve and deploy to production")
    
    print("\n✨ Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_demo())
