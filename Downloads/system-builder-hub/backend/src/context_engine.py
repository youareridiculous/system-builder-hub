"""
Priority 26: Context Engine + Intelligent Instruction Expansion Layer (CIEL)

This module provides comprehensive prompt analysis, scoring, expansion,
and context clarification for system-building instructions.
"""

import sqlite3
import json
import uuid
import time
import threading
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import re
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptClarityLevel(Enum):
    """Prompt clarity levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"

class PromptType(Enum):
    """Types of prompts"""
    SYSTEM_BUILD = "system_build"
    COMPONENT_CREATE = "component_create"
    INTEGRATION = "integration"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"
    VOICE_MEMO = "voice_memo"
    TEXT_INPUT = "text_input"

class ExpansionMethod(Enum):
    """Methods for expanding prompts"""
    LLM_GENERATION = "llm_generation"
    MEMORY_RETRIEVAL = "memory_retrieval"
    TEMPLATE_BASED = "template_based"
    CONTEXT_AUGMENTATION = "context_augmentation"


class ContextType(str, Enum):
    """Types of context"""
    SYSTEM = "system"
    USER = "user"
    SESSION = "session"
    MEMORY = "memory"
    EXTERNAL = "external"
    TEMPORAL = "temporal"


class ContextScope(str, Enum):
    """Scope of context"""
    GLOBAL = "global"
    SESSION = "session"
    USER = "user"
    PROJECT = "project"
    COMPONENT = "component"
    TEMPORARY = "temporary"


@dataclass
class ContextExpansion:
    """Represents context expansion"""
    expansion_id: str
    context_id: str
    context_type: ContextType
    scope: ContextScope
    expanded_content: Dict[str, Any]
    confidence: float
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class PromptScore:
    """Represents a scored prompt"""
    prompt_id: str
    original_prompt: str
    clarity_score: float  # 0.0 to 1.0
    goal_coverage_score: float  # 0.0 to 1.0
    input_spec_score: float  # 0.0 to 1.0
    output_spec_score: float  # 0.0 to 1.0
    context_richness_score: float  # 0.0 to 1.0
    overall_score: float  # 0.0 to 1.0
    clarity_level: PromptClarityLevel
    prompt_type: PromptType
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class PromptExpansion:
    """Represents an expanded prompt"""
    expansion_id: str
    original_prompt_id: str
    expanded_prompt: str
    expansion_method: ExpansionMethod
    confidence_score: float  # 0.0 to 1.0
    improvements: List[str]
    context_added: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class ClarificationQuestion:
    """Represents a clarification question"""
    question_id: str
    prompt_id: str
    question_text: str
    question_type: str  # missing_context, ambiguous_goal, unclear_requirements
    priority: int  # 1-5, higher is more important
    suggested_answers: List[str]
    timestamp: datetime
    answered: bool = False
    answer: Optional[str] = None

@dataclass
class VoiceTranscript:
    """Represents a voice transcript"""
    transcript_id: str
    audio_file_path: str
    transcript_text: str
    confidence_score: float  # 0.0 to 1.0
    duration_seconds: float
    prompt_id: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]

class InstructionScorer:
    """Scores prompts for clarity, completeness, and context richness"""
    
    def __init__(self, llm_factory, memory_system):
        self.llm_factory = llm_factory
        self.memory_system = memory_system
        
    def score_prompt(self, prompt: str, prompt_type: PromptType = PromptType.SYSTEM_BUILD,
                    user_id: Optional[str] = None, session_id: Optional[str] = None) -> PromptScore:
        """Score a prompt for quality and completeness"""
        
        # Analyze prompt characteristics
        clarity_score = self._analyze_clarity(prompt)
        goal_coverage_score = self._analyze_goal_coverage(prompt)
        input_spec_score = self._analyze_input_specification(prompt)
        output_spec_score = self._analyze_output_specification(prompt)
        context_richness_score = self._analyze_context_richness(prompt)
        
        # Calculate overall score
        overall_score = (
            clarity_score * 0.25 +
            goal_coverage_score * 0.25 +
            input_spec_score * 0.2 +
            output_spec_score * 0.2 +
            context_richness_score * 0.1
        )
        
        # Determine clarity level
        clarity_level = self._determine_clarity_level(overall_score)
        
        # Create prompt score
        prompt_score = PromptScore(
            prompt_id=str(uuid.uuid4()),
            original_prompt=prompt,
            clarity_score=clarity_score,
            goal_coverage_score=goal_coverage_score,
            input_spec_score=input_spec_score,
            output_spec_score=output_spec_score,
            context_richness_score=context_richness_score,
            overall_score=overall_score,
            clarity_level=clarity_level,
            prompt_type=prompt_type,
            timestamp=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            metadata={
                "word_count": len(prompt.split()),
                "sentence_count": len(re.split(r'[.!?]+', prompt)),
                "has_technical_terms": self._has_technical_terms(prompt),
                "has_requirements": self._has_requirements(prompt),
                "has_constraints": self._has_constraints(prompt)
            }
        )
        
        return prompt_score
    
    def _analyze_clarity(self, prompt: str) -> float:
        """Analyze prompt clarity"""
        # Check for clear sentence structure
        sentences = re.split(r'[.!?]+', prompt)
        clear_sentences = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 0:
                # Check for clear subject-verb structure
                words = sentence.split()
                if len(words) >= 3:  # Minimum for subject-verb-object
                    clear_sentences += 1
        
        clarity_score = clear_sentences / max(len(sentences), 1)
        
        # Bonus for specific technical terms
        technical_terms = [
            'system', 'component', 'integration', 'api', 'database',
            'authentication', 'authorization', 'workflow', 'pipeline',
            'deployment', 'testing', 'monitoring', 'logging'
        ]
        
        found_terms = sum(1 for term in technical_terms if term.lower() in prompt.lower())
        technical_bonus = min(found_terms * 0.1, 0.3)
        
        return min(clarity_score + technical_bonus, 1.0)
    
    def _analyze_goal_coverage(self, prompt: str) -> float:
        """Analyze how well the goal is covered"""
        goal_indicators = [
            'build', 'create', 'develop', 'implement', 'design',
            'integrate', 'deploy', 'test', 'optimize', 'maintain'
        ]
        
        goal_words = sum(1 for indicator in goal_indicators if indicator.lower() in prompt.lower())
        goal_score = min(goal_words * 0.2, 1.0)
        
        # Check for specific outcomes
        outcome_indicators = [
            'should', 'must', 'will', 'needs to', 'requires',
            'expected', 'desired', 'target', 'objective'
        ]
        
        outcome_words = sum(1 for indicator in outcome_indicators if indicator.lower() in prompt.lower())
        outcome_bonus = min(outcome_words * 0.1, 0.3)
        
        return min(goal_score + outcome_bonus, 1.0)
    
    def _analyze_input_specification(self, prompt: str) -> float:
        """Analyze input specification clarity"""
        input_indicators = [
            'input', 'data', 'file', 'api', 'database', 'user',
            'parameters', 'config', 'settings', 'source'
        ]
        
        input_words = sum(1 for indicator in input_indicators if indicator.lower() in prompt.lower())
        input_score = min(input_words * 0.15, 1.0)
        
        # Check for specific data types
        data_types = [
            'json', 'xml', 'csv', 'text', 'binary', 'image',
            'video', 'audio', 'number', 'string', 'boolean'
        ]
        
        type_words = sum(1 for data_type in data_types if data_type.lower() in prompt.lower())
        type_bonus = min(type_words * 0.1, 0.3)
        
        return min(input_score + type_bonus, 1.0)
    
    def _analyze_output_specification(self, prompt: str) -> float:
        """Analyze output specification clarity"""
        output_indicators = [
            'output', 'result', 'response', 'report', 'file',
            'display', 'show', 'generate', 'produce', 'return'
        ]
        
        output_words = sum(1 for indicator in output_indicators if indicator.lower() in prompt.lower())
        output_score = min(output_words * 0.15, 1.0)
        
        # Check for specific output formats
        output_formats = [
            'json', 'xml', 'csv', 'pdf', 'html', 'email',
            'notification', 'dashboard', 'report', 'log'
        ]
        
        format_words = sum(1 for fmt in output_formats if fmt.lower() in prompt.lower())
        format_bonus = min(format_words * 0.1, 0.3)
        
        return min(output_score + format_bonus, 1.0)
    
    def _analyze_context_richness(self, prompt: str) -> float:
        """Analyze context richness"""
        context_indicators = [
            'because', 'since', 'when', 'where', 'how', 'why',
            'background', 'context', 'environment', 'scenario',
            'user', 'business', 'requirement', 'constraint'
        ]
        
        context_words = sum(1 for indicator in context_indicators if indicator.lower() in prompt.lower())
        context_score = min(context_words * 0.1, 1.0)
        
        # Check for specific context elements
        context_elements = [
            'user type', 'business goal', 'technical constraint',
            'performance requirement', 'security need', 'compliance'
        ]
        
        element_bonus = 0
        for element in context_elements:
            if element.lower() in prompt.lower():
                element_bonus += 0.2
        
        return min(context_score + element_bonus, 1.0)
    
    def _determine_clarity_level(self, overall_score: float) -> PromptClarityLevel:
        """Determine clarity level based on overall score"""
        if overall_score >= 0.8:
            return PromptClarityLevel.EXCELLENT
        elif overall_score >= 0.6:
            return PromptClarityLevel.GOOD
        elif overall_score >= 0.4:
            return PromptClarityLevel.FAIR
        elif overall_score >= 0.2:
            return PromptClarityLevel.POOR
        else:
            return PromptClarityLevel.UNUSABLE
    
    def _has_technical_terms(self, prompt: str) -> bool:
        """Check if prompt contains technical terms"""
        technical_terms = [
            'api', 'database', 'system', 'component', 'integration',
            'deployment', 'testing', 'authentication', 'workflow'
        ]
        return any(term in prompt.lower() for term in technical_terms)
    
    def _has_requirements(self, prompt: str) -> bool:
        """Check if prompt contains requirements"""
        requirement_indicators = [
            'must', 'should', 'required', 'need', 'requirement'
        ]
        return any(indicator in prompt.lower() for indicator in requirement_indicators)
    
    def _has_constraints(self, prompt: str) -> bool:
        """Check if prompt contains constraints"""
        constraint_indicators = [
            'constraint', 'limit', 'budget', 'time', 'performance',
            'security', 'compliance', 'cannot', 'must not'
        ]
        return any(indicator in prompt.lower() for indicator in constraint_indicators)

class PromptExpander:
    """Expands and improves vague prompts"""
    
    def __init__(self, llm_factory, memory_system):
        self.llm_factory = llm_factory
        self.memory_system = memory_system
    
    def expand_prompt(self, original_prompt: str, prompt_score: PromptScore,
                     expansion_method: ExpansionMethod = ExpansionMethod.LLM_GENERATION) -> List[PromptExpansion]:
        """Generate expanded versions of a prompt"""
        
        expansions = []
        
        if expansion_method == ExpansionMethod.LLM_GENERATION:
            expansions.extend(self._llm_expansion(original_prompt, prompt_score))
        elif expansion_method == ExpansionMethod.MEMORY_RETRIEVAL:
            expansions.extend(self._memory_based_expansion(original_prompt, prompt_score))
        elif expansion_method == ExpansionMethod.TEMPLATE_BASED:
            expansions.extend(self._template_based_expansion(original_prompt, prompt_score))
        elif expansion_method == ExpansionMethod.CONTEXT_AUGMENTATION:
            expansions.extend(self._context_augmentation(original_prompt, prompt_score))
        
        return expansions
    
    def _llm_expansion(self, original_prompt: str, prompt_score: PromptScore) -> List[PromptExpansion]:
        """Use LLM to generate expanded prompts"""
        expansions = []
        
        # Generate different types of expansions
        expansion_prompts = [
            f"Expand this system-building prompt to be more specific and detailed: {original_prompt}",
            f"Improve this prompt by adding missing technical context: {original_prompt}",
            f"Enhance this prompt with clear input/output specifications: {original_prompt}"
        ]
        
        for i, expansion_prompt in enumerate(expansion_prompts):
            try:
                # Use LLM to generate expansion
                response = self.llm_factory.generate_text(
                    prompt=expansion_prompt,
                    max_tokens=500,
                    temperature=0.7
                )
                
                if response and response.strip():
                    expansion = PromptExpansion(
                        expansion_id=str(uuid.uuid4()),
                        original_prompt_id=prompt_score.prompt_id,
                        expanded_prompt=response.strip(),
                        expansion_method=ExpansionMethod.LLM_GENERATION,
                        confidence_score=0.8 - (i * 0.1),  # Decreasing confidence for each variant
                        improvements=self._identify_improvements(original_prompt, response.strip()),
                        context_added=self._extract_added_context(original_prompt, response.strip()),
                        timestamp=datetime.now(),
                        metadata={"expansion_type": f"llm_variant_{i+1}"}
                    )
                    expansions.append(expansion)
                    
            except Exception as e:
                logger.error(f"LLM expansion failed: {e}")
        
        return expansions
    
    def _memory_based_expansion(self, original_prompt: str, prompt_score: PromptScore) -> List[PromptExpansion]:
        """Use memory system to find similar prompts and expand"""
        expansions = []
        
        try:
            # Search memory for similar prompts
            similar_prompts = self.memory_system.search_similar_prompts(original_prompt, limit=3)
            
            for similar_prompt in similar_prompts:
                # Combine original with similar prompt context
                combined_prompt = f"{original_prompt}\n\nBased on similar successful implementations: {similar_prompt.get('context', '')}"
                
                expansion = PromptExpansion(
                    expansion_id=str(uuid.uuid4()),
                    original_prompt_id=prompt_score.prompt_id,
                    expanded_prompt=combined_prompt,
                    expansion_method=ExpansionMethod.MEMORY_RETRIEVAL,
                    confidence_score=0.7,
                    improvements=["Added context from similar successful prompts"],
                    context_added={"memory_context": similar_prompt.get('context', '')},
                    timestamp=datetime.now(),
                    metadata={"memory_source": similar_prompt.get('id', 'unknown')}
                )
                expansions.append(expansion)
                
        except Exception as e:
            logger.error(f"Memory-based expansion failed: {e}")
        
        return expansions
    
    def _template_based_expansion(self, original_prompt: str, prompt_score: PromptScore) -> List[PromptExpansion]:
        """Use templates to expand prompts"""
        expansions = []
        
        # Define expansion templates
        templates = [
            {
                "name": "technical_spec",
                "template": "Build a system that {goal}. Technical requirements: {requirements}. Input: {input}. Output: {output}.",
                "confidence": 0.6
            },
            {
                "name": "business_context",
                "template": "Create a system for {business_goal}. The system should {functional_requirements}. Technical constraints: {constraints}.",
                "confidence": 0.5
            }
        ]
        
        for template in templates:
            # Simple template filling (in practice, this would be more sophisticated)
            expanded = template["template"].replace("{goal}", original_prompt)
            
            expansion = PromptExpansion(
                expansion_id=str(uuid.uuid4()),
                original_prompt_id=prompt_score.prompt_id,
                expanded_prompt=expanded,
                expansion_method=ExpansionMethod.TEMPLATE_BASED,
                confidence_score=template["confidence"],
                improvements=[f"Applied {template['name']} template"],
                context_added={"template_used": template["name"]},
                timestamp=datetime.now(),
                metadata={"template": template["name"]}
            )
            expansions.append(expansion)
        
        return expansions
    
    def _context_augmentation(self, original_prompt: str, prompt_score: PromptScore) -> List[PromptExpansion]:
        """Augment prompt with additional context"""
        expansions = []
        
        # Add common context elements
        context_elements = [
            "Consider security requirements and authentication needs.",
            "Include error handling and logging capabilities.",
            "Ensure the system is scalable and maintainable.",
            "Add monitoring and performance considerations."
        ]
        
        for element in context_elements:
            augmented_prompt = f"{original_prompt}\n\nAdditional context: {element}"
            
            expansion = PromptExpansion(
                expansion_id=str(uuid.uuid4()),
                original_prompt_id=prompt_score.prompt_id,
                expanded_prompt=augmented_prompt,
                expansion_method=ExpansionMethod.CONTEXT_AUGMENTATION,
                confidence_score=0.6,
                improvements=[f"Added {element.split(':')[0].lower()} context"],
                context_added={"augmented_context": element},
                timestamp=datetime.now(),
                metadata={"context_element": element}
            )
            expansions.append(expansion)
        
        return expansions
    
    def _identify_improvements(self, original: str, expanded: str) -> List[str]:
        """Identify improvements made in the expansion"""
        improvements = []
        
        # Simple improvement detection
        if len(expanded) > len(original) * 1.5:
            improvements.append("Significantly more detailed")
        
        if "input" in expanded.lower() and "input" not in original.lower():
            improvements.append("Added input specifications")
        
        if "output" in expanded.lower() and "output" not in original.lower():
            improvements.append("Added output specifications")
        
        if "security" in expanded.lower() and "security" not in original.lower():
            improvements.append("Added security considerations")
        
        return improvements
    
    def _extract_added_context(self, original: str, expanded: str) -> Dict[str, Any]:
        """Extract context that was added in the expansion"""
        added_context = {}
        
        # Simple context extraction
        original_words = set(original.lower().split())
        expanded_words = set(expanded.lower().split())
        new_words = expanded_words - original_words
        
        # Categorize new words
        technical_terms = [word for word in new_words if word in [
            'api', 'database', 'authentication', 'security', 'logging',
            'monitoring', 'scalable', 'maintainable', 'error', 'performance'
        ]]
        
        if technical_terms:
            added_context["technical_terms"] = technical_terms
        
        return added_context

class ContextClarifier:
    """Identifies missing information and generates clarification questions"""
    
    def __init__(self, llm_factory):
        self.llm_factory = llm_factory
    
    def generate_clarification_questions(self, prompt: str, prompt_score: PromptScore) -> List[ClarificationQuestion]:
        """Generate questions to clarify missing information"""
        
        questions = []
        
        # Analyze prompt for missing information
        missing_context = self._identify_missing_context(prompt, prompt_score)
        ambiguous_goals = self._identify_ambiguous_goals(prompt, prompt_score)
        unclear_requirements = self._identify_unclear_requirements(prompt, prompt_score)
        
        # Generate questions for missing context
        for context_type, details in missing_context.items():
            question = ClarificationQuestion(
                question_id=str(uuid.uuid4()),
                prompt_id=prompt_score.prompt_id,
                question_text=f"Can you provide more details about {context_type}?",
                question_type="missing_context",
                priority=3,
                suggested_answers=details.get("suggestions", []),
                timestamp=datetime.now()
            )
            questions.append(question)
        
        # Generate questions for ambiguous goals
        for goal_issue in ambiguous_goals:
            question = ClarificationQuestion(
                question_id=str(uuid.uuid4()),
                prompt_id=prompt_score.prompt_id,
                question_text=f"What specifically do you mean by '{goal_issue}'?",
                question_type="ambiguous_goal",
                priority=4,
                suggested_answers=[],
                timestamp=datetime.now()
            )
            questions.append(question)
        
        # Generate questions for unclear requirements
        for requirement in unclear_requirements:
            question = ClarificationQuestion(
                question_id=str(uuid.uuid4()),
                prompt_id=prompt_score.prompt_id,
                question_text=f"Can you clarify the requirement: {requirement}?",
                question_type="unclear_requirements",
                priority=5,
                suggested_answers=[],
                timestamp=datetime.now()
            )
            questions.append(question)
        
        return questions
    
    def _identify_missing_context(self, prompt: str, prompt_score: PromptScore) -> Dict[str, Any]:
        """Identify missing context in the prompt"""
        missing_context = {}
        
        # Check for missing technical context
        if prompt_score.input_spec_score < 0.5:
            missing_context["input specifications"] = {
                "suggestions": ["What data will the system receive?", "What format should the input be in?"]
            }
        
        if prompt_score.output_spec_score < 0.5:
            missing_context["output specifications"] = {
                "suggestions": ["What should the system produce?", "What format should the output be in?"]
            }
        
        if prompt_score.context_richness_score < 0.5:
            missing_context["business context"] = {
                "suggestions": ["What is the business goal?", "Who are the users?"]
            }
        
        return missing_context
    
    def _identify_ambiguous_goals(self, prompt: str, prompt_score: PromptScore) -> List[str]:
        """Identify ambiguous goals in the prompt"""
        ambiguous_goals = []
        
        # Check for vague terms
        vague_terms = [
            'better', 'improve', 'optimize', 'enhance', 'good',
            'fast', 'secure', 'reliable', 'user-friendly'
        ]
        
        for term in vague_terms:
            if term.lower() in prompt.lower():
                ambiguous_goals.append(term)
        
        return ambiguous_goals
    
    def _identify_unclear_requirements(self, prompt: str, prompt_score: PromptScore) -> List[str]:
        """Identify unclear requirements in the prompt"""
        unclear_requirements = []
        
        # Check for incomplete sentences or unclear statements
        sentences = re.split(r'[.!?]+', prompt)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 0:
                # Check for sentences that end with unclear phrases
                unclear_endings = [
                    'and stuff', 'etc', 'and so on', 'and more',
                    'something like', 'similar to', 'you know'
                ]
                
                for ending in unclear_endings:
                    if ending.lower() in sentence.lower():
                        unclear_requirements.append(sentence)
                        break
        
        return unclear_requirements

class ContextAugmentor:
    """Auto-fills missing information from memory and past instructions"""
    
    def __init__(self, memory_system, llm_factory):
        self.memory_system = memory_system
        self.llm_factory = llm_factory
    
    def augment_prompt(self, prompt: str, prompt_score: PromptScore) -> str:
        """Augment prompt with missing information from memory"""
        
        augmented_prompt = prompt
        
        # Find similar past prompts
        similar_prompts = self.memory_system.search_similar_prompts(prompt, limit=5)
        
        if similar_prompts:
            # Extract common patterns and context
            common_context = self._extract_common_context(similar_prompts)
            
            if common_context:
                augmented_prompt += f"\n\nContext from similar implementations: {common_context}"
        
        # Add technical context if missing
        if prompt_score.input_spec_score < 0.5:
            technical_context = self._get_technical_context(prompt)
            if technical_context:
                augmented_prompt += f"\n\nTechnical context: {technical_context}"
        
        return augmented_prompt
    
    def _extract_common_context(self, similar_prompts: List[Dict]) -> str:
        """Extract common context from similar prompts"""
        if not similar_prompts:
            return ""
        
        # Extract common technical terms and patterns
        all_contexts = [prompt.get('context', '') for prompt in similar_prompts]
        
        # Simple context extraction (in practice, this would use NLP)
        common_terms = set()
        for context in all_contexts:
            if context:
                terms = context.lower().split()
                common_terms.update(terms)
        
        # Filter for relevant technical terms
        relevant_terms = [term for term in common_terms if term in [
            'api', 'database', 'authentication', 'security', 'logging',
            'monitoring', 'scalable', 'maintainable', 'error', 'performance'
        ]]
        
        if relevant_terms:
            return f"Common technical elements: {', '.join(relevant_terms)}"
        
        return ""
    
    def _get_technical_context(self, prompt: str) -> str:
        """Get technical context based on prompt content"""
        technical_context = []
        
        # Add context based on prompt keywords
        if 'system' in prompt.lower():
            technical_context.append("Consider system architecture and scalability")
        
        if 'user' in prompt.lower():
            technical_context.append("Include user authentication and authorization")
        
        if 'data' in prompt.lower():
            technical_context.append("Consider data storage and retrieval mechanisms")
        
        if 'api' in prompt.lower():
            technical_context.append("Include API design and documentation")
        
        return "; ".join(technical_context) if technical_context else ""

class ContextEngine:
    """
    Main Context Engine that orchestrates prompt analysis, expansion, and clarification
    """
    
    def __init__(self, base_dir: Path, llm_factory, memory_system, black_box_inspector=None):
        self.base_dir = base_dir
        self.llm_factory = llm_factory
        self.memory_system = memory_system
        self.black_box_inspector = black_box_inspector
        
        # Initialize components
        self.instruction_scorer = InstructionScorer(llm_factory, memory_system)
        self.prompt_expander = PromptExpander(llm_factory, memory_system)
        self.context_clarifier = ContextClarifier(llm_factory)
        self.context_augmentor = ContextAugmentor(memory_system, llm_factory)
        
        # Database setup
        self.db_path = base_dir / "data" / "context_engine.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        logger.info("Context Engine initialized")
    
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_prompts (
                    prompt_id TEXT PRIMARY KEY,
                    original_prompt TEXT NOT NULL,
                    clarity_score REAL NOT NULL,
                    goal_coverage_score REAL NOT NULL,
                    input_spec_score REAL NOT NULL,
                    output_spec_score REAL NOT NULL,
                    context_richness_score REAL NOT NULL,
                    overall_score REAL NOT NULL,
                    clarity_level TEXT NOT NULL,
                    prompt_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    metadata TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_expansions (
                    expansion_id TEXT PRIMARY KEY,
                    original_prompt_id TEXT NOT NULL,
                    expanded_prompt TEXT NOT NULL,
                    expansion_method TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    improvements TEXT NOT NULL,
                    context_added TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    FOREIGN KEY (original_prompt_id) REFERENCES context_prompts (prompt_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clarification_questions (
                    question_id TEXT PRIMARY KEY,
                    prompt_id TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    suggested_answers TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    answered BOOLEAN NOT NULL DEFAULT FALSE,
                    answer TEXT,
                    FOREIGN KEY (prompt_id) REFERENCES context_prompts (prompt_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_transcripts (
                    transcript_id TEXT PRIMARY KEY,
                    audio_file_path TEXT NOT NULL,
                    transcript_text TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    duration_seconds REAL NOT NULL,
                    prompt_id TEXT,
                    timestamp TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    FOREIGN KEY (prompt_id) REFERENCES context_prompts (prompt_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clarification_logs (
                    question_id TEXT PRIMARY KEY,
                    question_text TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    context TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prompts_timestamp ON context_prompts(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prompts_user ON context_prompts(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prompts_session ON context_prompts(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expansions_prompt ON prompt_expansions(original_prompt_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_prompt ON clarification_questions(prompt_id)")
            
            conn.commit()
    
    def process_prompt(self, prompt: str, prompt_type: PromptType = PromptType.SYSTEM_BUILD,
                      user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a prompt through the complete context engine pipeline"""
        
        try:
            # Step 1: Score the prompt
            prompt_score = self.instruction_scorer.score_prompt(
                prompt, prompt_type, user_id, session_id
            )
            
            # Store the prompt score
            self._store_prompt_score(prompt_score)
            
            # Step 2: Generate expansions if score is low
            expansions = []
            if prompt_score.overall_score < 0.6:
                expansions = self.prompt_expander.expand_prompt(prompt, prompt_score)
                for expansion in expansions:
                    self._store_prompt_expansion(expansion)
            
            # Step 3: Generate clarification questions
            questions = self.context_clarifier.generate_clarification_questions(prompt, prompt_score)
            for question in questions:
                self._store_clarification_question(question)
            
            # Step 4: Augment with context
            augmented_prompt = self.context_augmentor.augment_prompt(prompt, prompt_score)
            
            # Log to black box inspector
            if self.black_box_inspector:
                self.black_box_inspector.log_trace_event(
                    trace_type="context_engine_processing",
                    component_id=f"prompt-{prompt_score.prompt_id}",
                    payload={
                        "prompt_id": prompt_score.prompt_id,
                        "original_score": prompt_score.overall_score,
                        "clarity_level": prompt_score.clarity_level.value,
                        "expansions_generated": len(expansions),
                        "questions_generated": len(questions)
                    },
                    metadata={
                        "prompt_type": prompt_type.value,
                        "user_id": user_id,
                        "session_id": session_id
                    }
                )
            
            return {
                "prompt_score": asdict(prompt_score),
                "expansions": [asdict(exp) for exp in expansions],
                "clarification_questions": [asdict(q) for q in questions],
                "augmented_prompt": augmented_prompt,
                "recommendations": self._generate_recommendations(prompt_score, expansions, questions)
            }
            
        except Exception as e:
            logger.error(f"Error processing prompt: {e}")
            raise
    
    def _store_prompt_score(self, prompt_score: PromptScore):
        """Store prompt score in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO context_prompts 
                (prompt_id, original_prompt, clarity_score, goal_coverage_score,
                 input_spec_score, output_spec_score, context_richness_score,
                 overall_score, clarity_level, prompt_type, timestamp,
                 user_id, session_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prompt_score.prompt_id,
                prompt_score.original_prompt,
                prompt_score.clarity_score,
                prompt_score.goal_coverage_score,
                prompt_score.input_spec_score,
                prompt_score.output_spec_score,
                prompt_score.context_richness_score,
                prompt_score.overall_score,
                prompt_score.clarity_level.value,
                prompt_score.prompt_type.value,
                prompt_score.timestamp.isoformat(),
                prompt_score.user_id,
                prompt_score.session_id,
                json.dumps(prompt_score.metadata)
            ))
            conn.commit()
    
    def _store_prompt_expansion(self, expansion: PromptExpansion):
        """Store prompt expansion in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO prompt_expansions 
                (expansion_id, original_prompt_id, expanded_prompt, expansion_method,
                 confidence_score, improvements, context_added, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                expansion.expansion_id,
                expansion.original_prompt_id,
                expansion.expanded_prompt,
                expansion.expansion_method.value,
                expansion.confidence_score,
                json.dumps(expansion.improvements),
                json.dumps(expansion.context_added),
                expansion.timestamp.isoformat(),
                json.dumps(expansion.metadata)
            ))
            conn.commit()
    
    def _store_clarification_question(self, question: ClarificationQuestion):
        """Store clarification question in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO clarification_questions 
                (question_id, prompt_id, question_text, question_type,
                 priority, suggested_answers, timestamp, answered, answer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                question.question_id,
                question.prompt_id,
                question.question_text,
                question.question_type,
                question.priority,
                json.dumps(question.suggested_answers),
                question.timestamp.isoformat(),
                question.answered,
                question.answer
            ))
            conn.commit()
    
    def _generate_recommendations(self, prompt_score: PromptScore, 
                                expansions: List[PromptExpansion],
                                questions: List[ClarificationQuestion]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if prompt_score.overall_score < 0.4:
            recommendations.append("Consider using one of the expanded prompts for better clarity")
        
        if prompt_score.input_spec_score < 0.5:
            recommendations.append("Add specific input requirements and data formats")
        
        if prompt_score.output_spec_score < 0.5:
            recommendations.append("Define clear output expectations and formats")
        
        if prompt_score.context_richness_score < 0.5:
            recommendations.append("Provide more business context and user requirements")
        
        if questions:
            recommendations.append(f"Answer the {len(questions)} clarification questions for better results")
        
        return recommendations
    
    def get_prompt_history(self, user_id: Optional[str] = None, 
                          session_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get prompt processing history"""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM context_prompts"
            params = []
            
            if user_id or session_id:
                conditions = []
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                if session_id:
                    conditions.append("session_id = ?")
                    params.append(session_id)
                
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                {
                    "prompt_id": row[0],
                    "original_prompt": row[1],
                    "clarity_score": row[2],
                    "goal_coverage_score": row[3],
                    "input_spec_score": row[4],
                    "output_spec_score": row[5],
                    "context_richness_score": row[6],
                    "overall_score": row[7],
                    "clarity_level": row[8],
                    "prompt_type": row[9],
                    "timestamp": row[10],
                    "user_id": row[11],
                    "session_id": row[12],
                    "metadata": json.loads(row[13])
                }
                for row in rows
            ]
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Prompt statistics
            cursor = conn.execute("SELECT COUNT(*) FROM context_prompts")
            total_prompts = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT AVG(overall_score) FROM context_prompts")
            avg_score = cursor.fetchone()[0] or 0
            
            cursor = conn.execute("SELECT COUNT(*) FROM prompt_expansions")
            total_expansions = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM clarification_questions")
            total_questions = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM voice_transcripts")
            total_transcripts = cursor.fetchone()[0]
            
            # Score distribution
            cursor = conn.execute("""
                SELECT clarity_level, COUNT(*) 
                FROM context_prompts 
                GROUP BY clarity_level
            """)
            clarity_distribution = {row[0]: row[1] for row in cursor.fetchall()}
            
        return {
            "total_prompts": total_prompts,
            "average_score": avg_score,
            "total_expansions": total_expansions,
            "total_questions": total_questions,
            "total_transcripts": total_transcripts,
            "clarity_distribution": clarity_distribution
        }
