"""
SBH Meta-Builder v2 Agents
Multi-agent system with specialized roles for scaffold generation.
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.meta_builder_v2.models import AgentRole, MetaSpec, RunContext
from src.llm.orchestration import LLMOrchestrator
from src.obs.audit import audit

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all meta-builder agents."""
    
    def __init__(self):
        self.llm = LLMOrchestrator()
        self.role = self.get_role()
    
    @abstractmethod
    def get_role(self) -> AgentRole:
        """Get the agent's role."""
        pass
    
    @abstractmethod
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        """Execute an agent action."""
        pass
    
    def _log_agent_action(self, action: str, inputs: Dict[str, Any], result: Dict[str, Any]):
        """Log agent action for audit."""
        audit(
            event_type='meta_builder.agent_action',
            user_id='system',
            tenant_id=context.run.tenant_id if context else None,
            metadata={
                'agent_role': self.role.value,
                'action': action,
                'inputs': inputs,
                'result': result
            }
        )


class ProductArchitectAgent(BaseAgent):
    """Product Architect: turns goal → formal Spec + acceptance criteria."""
    
    def get_role(self) -> AgentRole:
        return AgentRole.PRODUCT_ARCHITECT
    
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        if action == "create_spec":
            return await self._create_spec(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _create_spec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create a formal specification from goal text."""
        goal_text = inputs['goal_text']
        import_inputs = inputs.get('inputs', {})
        
        # Build prompt for spec creation
        prompt = f"""
        You are a Product Architect. Create a formal specification for the following goal:
        
        Goal: {goal_text}
        
        Import inputs: {json.dumps(import_inputs, indent=2)}
        
        Create a complete MetaSpec with:
        1. Appropriate domain (crm, lms, helpdesk, custom)
        2. Entities with fields and relationships
        3. Workflows if applicable
        4. Required integrations
        5. AI features if needed
        6. Non-functional requirements
        7. Acceptance criteria
        
        Return the specification as a valid JSON object following the MetaSpec schema.
        """
        
        # Get LLM response
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.1,  # Low temperature for consistency
            max_tokens=2000
        )
        
        # Parse and validate spec
        try:
            spec_data = json.loads(response['content'])
            spec = MetaSpec.from_dict(spec_data)
            
            self._log_agent_action("create_spec", inputs, {'spec': spec.to_dict()})
            
            return {
                'spec': spec.to_dict(),
                'domain': spec.domain.value,
                'entities_count': len(spec.entities),
                'acceptance_count': len(spec.acceptance)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse spec: {e}")
            raise ValueError(f"Invalid specification format: {e}")


class SystemDesignerAgent(BaseAgent):
    """System Designer: maps Spec → ScaffoldPlan (entities, APIs, pages, integrations)."""
    
    def get_role(self) -> AgentRole:
        return AgentRole.SYSTEM_DESIGNER
    
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        if action == "create_plan":
            return await self._create_plan(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _create_plan(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scaffold plan from specification."""
        spec = inputs['spec']
        
        prompt = f"""
        You are a System Designer. Create a detailed scaffold plan for the following specification:
        
        Specification: {json.dumps(spec, indent=2)}
        
        Create a comprehensive plan including:
        1. Database schema (tables, relationships, indexes)
        2. API endpoints (RESTful design)
        3. UI pages and components
        4. Authentication and authorization
        5. Integration points
        6. File structure and organization
        7. Dependencies and requirements
        
        Return the plan as a structured JSON object.
        """
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.2,
            max_tokens=3000
        )
        
        try:
            plan = json.loads(response['content'])
            
            self._log_agent_action("create_plan", inputs, plan)
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to parse plan: {e}")
            raise ValueError(f"Invalid plan format: {e}")


class SecurityComplianceAgent(BaseAgent):
    """Security/Compliance: injects RBAC, RLS, PII redaction, rate limits, audit."""
    
    def get_role(self) -> AgentRole:
        return AgentRole.SECURITY_COMPLIANCE
    
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        if action == "review_security":
            return await self._review_security(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _review_security(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Review and enhance security for the specification and plan."""
        spec = inputs['spec']
        plan = inputs['plan']
        
        prompt = f"""
        You are a Security and Compliance expert. Review the following specification and plan for security issues:
        
        Specification: {json.dumps(spec, indent=2)}
        Plan: {json.dumps(plan, indent=2)}
        
        Provide a comprehensive security review including:
        1. RBAC (Role-Based Access Control) requirements
        2. RLS (Row-Level Security) policies
        3. PII (Personally Identifiable Information) handling
        4. Rate limiting and throttling
        5. Audit logging requirements
        6. Data encryption needs
        7. Security vulnerabilities and recommendations
        8. Compliance considerations (GDPR, SOC2, etc.)
        
        Return a detailed security report with recommendations.
        """
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=2500
        )
        
        try:
            security_report = json.loads(response['content'])
            
            self._log_agent_action("review_security", inputs, security_report)
            
            return security_report
            
        except Exception as e:
            logger.error(f"Failed to parse security report: {e}")
            raise ValueError(f"Invalid security report format: {e}")


class CodegenEngineerAgent(BaseAgent):
    """Codegen Engineer: produces diffs over target repo/export bundle."""
    
    def get_role(self) -> AgentRole:
        return AgentRole.CODEGEN_ENGINEER
    
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        if action == "generate_code":
            return await self._generate_code(inputs, context)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _generate_code(self, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        """Generate code artifacts from specification and plan."""
        spec = inputs['spec']
        plan = inputs['plan']
        security_report = inputs['security_report']
        
        prompt = f"""
        You are a Code Generation Engineer. Generate complete code for the following specification:
        
        Specification: {json.dumps(spec, indent=2)}
        Plan: {json.dumps(plan, indent=2)}
        Security Report: {json.dumps(security_report, indent=2)}
        
        Generate the following artifacts:
        1. Database models (SQLAlchemy)
        2. API routes (Flask blueprints)
        3. UI components (React/TypeScript)
        4. Authentication middleware
        5. Security policies
        6. Configuration files
        7. Test files
        
        Return each file as a separate artifact with:
        - file_path: relative path
        - content: file content
        - type: file type (model, api, ui, config, test)
        """
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=5000
        )
        
        try:
            artifacts_data = json.loads(response['content'])
            
            # Create artifact records
            artifacts = []
            for artifact_data in artifacts_data.get('artifacts', []):
                artifact = {
                    'name': artifact_data['file_path'].split('/')[-1],
                    'type': 'code',
                    'content': artifact_data['content'],
                    'metadata': {
                        'file_path': artifact_data['file_path'],
                        'file_type': artifact_data['type'],
                        'agent_role': self.role.value
                    }
                }
                artifacts.append(artifact)
            
            self._log_agent_action("generate_code", inputs, {'artifacts_count': len(artifacts)})
            
            return {
                'artifacts': artifacts,
                'total_files': len(artifacts),
                'file_types': list(set(a['metadata']['file_type'] for a in artifacts))
            }
            
        except Exception as e:
            logger.error(f"Failed to parse code artifacts: {e}")
            raise ValueError(f"Invalid code artifacts format: {e}")


class QAEvaluatorAgent(BaseAgent):
    """QA/Evaluator: runs tests, smoke, golden tasks; summarizes failures."""
    
    def get_role(self) -> AgentRole:
        return AgentRole.QA_EVALUATOR
    
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        if action == "evaluate":
            return await self._evaluate(inputs, context)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _evaluate(self, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        """Evaluate the generated artifacts against acceptance criteria."""
        spec = inputs['spec']
        artifacts = inputs['artifacts']
        acceptance_criteria = inputs['acceptance_criteria']
        
        prompt = f"""
        You are a QA Evaluator. Evaluate the following artifacts against acceptance criteria:
        
        Specification: {json.dumps(spec, indent=2)}
        Artifacts: {json.dumps(artifacts, indent=2)}
        Acceptance Criteria: {json.dumps(acceptance_criteria, indent=2)}
        
        Perform a comprehensive evaluation including:
        1. Code quality assessment
        2. Security compliance check
        3. Acceptance criteria validation
        4. Performance considerations
        5. Maintainability analysis
        6. Test coverage assessment
        
        For each acceptance criterion, provide:
        - Pass/Fail status
        - Detailed reasoning
        - Specific issues found
        - Recommendations for improvement
        
        Calculate an overall score (0-100) and provide a summary.
        """
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=3000
        )
        
        try:
            evaluation = json.loads(response['content'])
            
            # Calculate overall score
            total_criteria = len(acceptance_criteria)
            passed_criteria = sum(1 for c in evaluation.get('criteria_results', []) if c.get('passed', False))
            score = (passed_criteria / total_criteria * 100) if total_criteria > 0 else 0
            
            evaluation['overall_score'] = score
            evaluation['passed'] = score >= 80  # 80% threshold
            
            self._log_agent_action("evaluate", inputs, evaluation)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Failed to parse evaluation: {e}")
            raise ValueError(f"Invalid evaluation format: {e}")


class AutoFixerAgent(BaseAgent):
    """Auto-Fixer: proposes & applies targeted patches until pass or budget exhausted."""
    
    def get_role(self) -> AgentRole:
        return AgentRole.AUTO_FIXER
    
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        if action == "fix_issues":
            return await self._fix_issues(inputs, context)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _fix_issues(self, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        """Fix issues identified in the evaluation."""
        spec = inputs['spec']
        evaluation_report = inputs['evaluation_report']
        artifacts = inputs['artifacts']
        
        prompt = f"""
        You are an Auto-Fixer. Fix the issues identified in the evaluation:
        
        Specification: {json.dumps(spec, indent=2)}
        Evaluation Report: {json.dumps(evaluation_report, indent=2)}
        Current Artifacts: {json.dumps(artifacts, indent=2)}
        
        Analyze the evaluation report and create targeted fixes for:
        1. Failed acceptance criteria
        2. Security issues
        3. Code quality problems
        4. Missing functionality
        5. Performance issues
        
        For each issue, provide:
        - Root cause analysis
        - Specific fix implementation
        - Updated artifact content
        - Test cases to verify the fix
        
        Return the fixes as updated artifacts.
        """
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.2,
            max_tokens=4000
        )
        
        try:
            fixes_data = json.loads(response['content'])
            
            # Create updated artifacts
            new_artifacts = []
            for fix in fixes_data.get('fixes', []):
                artifact = {
                    'name': fix['file_path'].split('/')[-1],
                    'type': 'fix',
                    'content': fix['updated_content'],
                    'metadata': {
                        'file_path': fix['file_path'],
                        'fix_type': fix['fix_type'],
                        'issue_description': fix['issue_description'],
                        'agent_role': self.role.value
                    }
                }
                new_artifacts.append(artifact)
            
            self._log_agent_action("fix_issues", inputs, {'fixes_count': len(new_artifacts)})
            
            return {
                'fixed': len(new_artifacts) > 0,
                'new_artifacts': new_artifacts,
                'fixes_applied': len(new_artifacts),
                'fix_types': list(set(a['metadata']['fix_type'] for a in new_artifacts))
            }
            
        except Exception as e:
            logger.error(f"Failed to parse fixes: {e}")
            raise ValueError(f"Invalid fixes format: {e}")


class DevOpsAgent(BaseAgent):
    """DevOps: ensures migrations, seed, envs, CI steps, deploy preview."""
    
    def get_role(self) -> AgentRole:
        return AgentRole.DEVOPS
    
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        if action == "setup_devops":
            return await self._setup_devops(inputs, context)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _setup_devops(self, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        """Setup DevOps infrastructure and deployment."""
        spec = inputs['spec']
        code_artifacts = inputs['code_artifacts']
        
        prompt = f"""
        You are a DevOps Engineer. Setup the DevOps infrastructure for the following project:
        
        Specification: {json.dumps(spec, indent=2)}
        Code Artifacts: {json.dumps(code_artifacts, indent=2)}
        
        Create the following DevOps artifacts:
        1. Database migrations (Alembic)
        2. Seed data scripts
        3. Environment configuration
        4. CI/CD pipeline configuration
        5. Docker configuration
        6. Deployment scripts
        7. Monitoring and logging setup
        8. Backup and recovery procedures
        
        Return each artifact with appropriate configuration.
        """
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=3000
        )
        
        try:
            devops_data = json.loads(response['content'])
            
            # Create DevOps artifacts
            artifacts = []
            for artifact_data in devops_data.get('artifacts', []):
                artifact = {
                    'name': artifact_data['file_path'].split('/')[-1],
                    'type': 'devops',
                    'content': artifact_data['content'],
                    'metadata': {
                        'file_path': artifact_data['file_path'],
                        'artifact_type': artifact_data['type'],
                        'agent_role': self.role.value
                    }
                }
                artifacts.append(artifact)
            
            self._log_agent_action("setup_devops", inputs, {'artifacts_count': len(artifacts)})
            
            return {
                'artifacts': artifacts,
                'total_files': len(artifacts),
                'artifact_types': list(set(a['metadata']['artifact_type'] for a in artifacts))
            }
            
        except Exception as e:
            logger.error(f"Failed to parse DevOps artifacts: {e}")
            raise ValueError(f"Invalid DevOps artifacts format: {e}")


class ReviewerAgent(BaseAgent):
    """Reviewer: composes PR body with risks, migrations, test results, and rollout notes."""
    
    def get_role(self) -> AgentRole:
        return AgentRole.REVIEWER
    
    async def execute(self, action: str, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        if action == "generate_rollback_plan":
            return await self._generate_rollback_plan(inputs, context)
        elif action == "finalize_run":
            return await self._finalize_run(inputs, context)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _generate_rollback_plan(self, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        """Generate a rollback plan for the changes."""
        spec = inputs.get('spec')
        artifacts = inputs.get('artifacts', [])
        
        prompt = f"""
        You are a Reviewer. Generate a comprehensive rollback plan for the following changes:
        
        Specification: {json.dumps(spec, indent=2) if spec else 'None'}
        Artifacts: {json.dumps(artifacts, indent=2)}
        
        Create a detailed rollback plan including:
        1. Database rollback steps
        2. Code rollback procedures
        3. Configuration rollback
        4. Data backup verification
        5. Rollback testing procedures
        6. Communication plan
        7. Timeline and dependencies
        
        Return a structured rollback plan.
        """
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=2000
        )
        
        try:
            rollback_plan = json.loads(response['content'])
            
            self._log_agent_action("generate_rollback_plan", inputs, rollback_plan)
            
            return rollback_plan
            
        except Exception as e:
            logger.error(f"Failed to parse rollback plan: {e}")
            raise ValueError(f"Invalid rollback plan format: {e}")
    
    async def _finalize_run(self, inputs: Dict[str, Any], context: RunContext) -> Dict[str, Any]:
        """Finalize the run and prepare for deployment."""
        spec = inputs.get('spec')
        artifacts = inputs.get('artifacts', [])
        approval = inputs.get('approval')
        
        prompt = f"""
        You are a Reviewer. Finalize the meta-builder run and prepare deployment:
        
        Specification: {json.dumps(spec, indent=2) if spec else 'None'}
        Artifacts: {json.dumps(artifacts, indent=2)}
        Approval: {json.dumps(approval, indent=2) if approval else 'None'}
        
        Create final deployment artifacts:
        1. PR description with changes summary
        2. Risk assessment and mitigation
        3. Migration checklist
        4. Test results summary
        5. Rollout and rollback procedures
        6. Monitoring and alerting setup
        7. Documentation updates
        
        Return the final deployment package.
        """
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=2500
        )
        
        try:
            final_package = json.loads(response['content'])
            
            self._log_agent_action("finalize_run", inputs, final_package)
            
            return final_package
            
        except Exception as e:
            logger.error(f"Failed to parse final package: {e}")
            raise ValueError(f"Invalid final package format: {e}")
