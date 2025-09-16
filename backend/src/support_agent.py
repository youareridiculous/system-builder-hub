import os
import json
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import logging
from pathlib import Path
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupportChannel(Enum):
    CHAT = "chat"
    EMAIL = "email"
    TICKET = "ticket"
    PHONE = "phone"
    INTERCOM = "intercom"
    CRISP = "crisp"

class SupportPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class SupportStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_USER = "waiting_for_user"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"

class SupportCategory(Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    ONBOARDING = "onboarding"
    INTEGRATION = "integration"
    GENERAL = "general"

@dataclass
class SupportTicket:
    ticket_id: str
    user_id: str
    system_id: Optional[str]
    channel: SupportChannel
    priority: SupportPriority
    status: SupportStatus
    category: SupportCategory
    subject: str
    description: str
    context: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    assigned_to: Optional[str]
    tags: List[str]
    satisfaction_score: Optional[int]

@dataclass
class SupportMessage:
    message_id: str
    ticket_id: str
    sender_id: str
    sender_type: str  # "user", "agent", "system"
    content: str
    message_type: str  # "text", "image", "file", "system"
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class SupportContext:
    context_id: str
    system_id: str
    context_type: str  # "architecture", "deployment", "error_logs", "changelogs", "licensing"
    content: str
    last_updated: datetime
    relevance_score: float
    tags: List[str]

@dataclass
class SupportKnowledge:
    knowledge_id: str
    title: str
    content: str
    category: SupportCategory
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    view_count: int
    helpful_count: int
    not_helpful_count: int
    is_public: bool

@dataclass
class SupportSession:
    session_id: str
    user_id: str
    system_id: Optional[str]
    channel: SupportChannel
    started_at: datetime
    last_activity: datetime
    message_count: int
    is_active: bool
    context_summary: str
    satisfaction_score: Optional[int]

class SupportAgent:
    def __init__(self, base_dir: str, llm_factory=None, system_delivery=None, access_control=None):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data" / "support_agent"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Dependencies
        self.llm_factory = llm_factory
        self.system_delivery = system_delivery
        self.access_control = access_control
        
        # Database
        self.db_path = self.data_dir / "support_agent.db"
        self._init_database()
        
        # Support state
        self.active_sessions = {}
        self.knowledge_base = {}
        self.context_cache = {}
        
        # Load knowledge base
        self._load_knowledge_base()
        
        # Start context indexing
        self._index_system_contexts()
    
    def _init_database(self):
        """Initialize SQLite database for support agent data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Support tickets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id TEXT PRIMARY KEY,
                user_id TEXT,
                system_id TEXT,
                channel TEXT,
                priority TEXT,
                status TEXT,
                category TEXT,
                subject TEXT,
                description TEXT,
                context TEXT,
                created_at TEXT,
                updated_at TEXT,
                resolved_at TEXT,
                assigned_to TEXT,
                tags TEXT,
                satisfaction_score INTEGER
            )
        ''')
        
        # Support messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_messages (
                message_id TEXT PRIMARY KEY,
                ticket_id TEXT,
                sender_id TEXT,
                sender_type TEXT,
                content TEXT,
                message_type TEXT,
                timestamp TEXT,
                metadata TEXT,
                FOREIGN KEY (ticket_id) REFERENCES support_tickets (ticket_id)
            )
        ''')
        
        # Support context table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_context (
                context_id TEXT PRIMARY KEY,
                system_id TEXT,
                context_type TEXT,
                content TEXT,
                last_updated TEXT,
                relevance_score REAL,
                tags TEXT
            )
        ''')
        
        # Support knowledge table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_knowledge (
                knowledge_id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                category TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                view_count INTEGER,
                helpful_count INTEGER,
                not_helpful_count INTEGER,
                is_public INTEGER
            )
        ''')
        
        # Support sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                system_id TEXT,
                channel TEXT,
                started_at TEXT,
                last_activity TEXT,
                message_count INTEGER,
                is_active INTEGER,
                context_summary TEXT,
                satisfaction_score INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_knowledge_base(self):
        """Load knowledge base from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM support_knowledge')
        results = cursor.fetchall()
        conn.close()
        
        for result in results:
            knowledge_id, title, content, category, tags, created_at, updated_at, view_count, helpful_count, not_helpful_count, is_public = result
            
            knowledge = SupportKnowledge(
                knowledge_id=knowledge_id,
                title=title,
                content=content,
                category=SupportCategory(category),
                tags=json.loads(tags),
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at),
                view_count=view_count,
                helpful_count=helpful_count,
                not_helpful_count=not_helpful_count,
                is_public=bool(is_public)
            )
            
            self.knowledge_base[knowledge_id] = knowledge
    
    def _index_system_contexts(self):
        """Index system contexts for support queries"""
        if not self.system_delivery:
            return
        
        try:
            # Get all systems
            systems = self.system_delivery.get_all_systems()
            
            for system in systems:
                # Index architecture docs
                if hasattr(system, 'architecture_docs'):
                    self._add_support_context(
                        system_id=system.system_id,
                        context_type="architecture",
                        content=system.architecture_docs,
                        tags=["architecture", "documentation"]
                    )
                
                # Index deployment logs
                if hasattr(system, 'deployment_logs'):
                    self._add_support_context(
                        system_id=system.system_id,
                        context_type="deployment",
                        content=system.deployment_logs,
                        tags=["deployment", "logs"]
                    )
                
                # Index changelogs
                if hasattr(system, 'changelog'):
                    self._add_support_context(
                        system_id=system.system_id,
                        context_type="changelogs",
                        content=system.changelog,
                        tags=["changelog", "updates"]
                    )
                    
        except Exception as e:
            logger.error(f"Error indexing system contexts: {e}")
    
    def _add_support_context(self, system_id: str, context_type: str, content: str, tags: List[str]):
        """Add support context for a system"""
        context_id = f"context_{int(time.time())}_{system_id}_{context_type}"
        
        context = SupportContext(
            context_id=context_id,
            system_id=system_id,
            context_type=context_type,
            content=content,
            last_updated=datetime.now(),
            relevance_score=1.0,
            tags=tags
        )
        
        self._save_support_context(context)
        self.context_cache[context_id] = context
    
    def _save_support_context(self, context: SupportContext):
        """Save support context to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO support_context 
            (context_id, system_id, context_type, content, last_updated, relevance_score, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            context.context_id,
            context.system_id,
            context.context_type,
            context.content,
            context.last_updated.isoformat(),
            context.relevance_score,
            json.dumps(context.tags)
        ))
        
        conn.commit()
        conn.close()
    
    def create_support_session(self, user_id: str, system_id: Optional[str] = None, 
                             channel: SupportChannel = SupportChannel.CHAT) -> str:
        """Create a new support session"""
        session_id = f"session_{int(time.time())}_{user_id}"
        
        session = SupportSession(
            session_id=session_id,
            user_id=user_id,
            system_id=system_id,
            channel=channel,
            started_at=datetime.now(),
            last_activity=datetime.now(),
            message_count=0,
            is_active=True,
            context_summary="",
            satisfaction_score=None
        )
        
        self._save_support_session(session)
        self.active_sessions[session_id] = session
        
        return session_id
    
    def _save_support_session(self, session: SupportSession):
        """Save support session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO support_sessions 
            (session_id, user_id, system_id, channel, started_at, last_activity,
            message_count, is_active, context_summary, satisfaction_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id,
            session.user_id,
            session.system_id,
            session.channel.value,
            session.started_at.isoformat(),
            session.last_activity.isoformat(),
            session.message_count,
            1 if session.is_active else 0,
            session.context_summary,
            session.satisfaction_score
        ))
        
        conn.commit()
        conn.close()
    
    def process_support_query(self, session_id: str, user_id: str, query: str, 
                            system_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a support query and generate response"""
        try:
            # Update session activity
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.last_activity = datetime.now()
                session.message_count += 1
                self._save_support_session(session)
            
            # Get relevant context
            context = self._get_relevant_context(query, system_id)
            
            # Search knowledge base
            knowledge_results = self._search_knowledge_base(query)
            
            # Generate response using LLM if available
            if self.llm_factory:
                response = self._generate_llm_response(query, context, knowledge_results, system_id)
            else:
                response = self._generate_fallback_response(query, knowledge_results)
            
            # Create or update ticket if needed
            ticket_id = self._create_or_update_ticket(session_id, user_id, query, response, system_id)
            
            # Save message
            message_id = self._save_support_message(session_id, user_id, query, "user", "text")
            
            return {
                "response": response,
                "ticket_id": ticket_id,
                "message_id": message_id,
                "context_used": context,
                "knowledge_used": knowledge_results[:3] if knowledge_results else [],
                "confidence_score": 0.8  # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Error processing support query: {e}")
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again or contact support directly.",
                "error": str(e),
                "confidence_score": 0.0
            }
    
    def _get_relevant_context(self, query: str, system_id: Optional[str] = None) -> List[SupportContext]:
        """Get relevant context for a support query"""
        relevant_contexts = []
        
        # Search in context cache
        for context_id, context in self.context_cache.items():
            relevance_score = self._calculate_relevance(query, context.content, context.tags)
            
            if relevance_score > 0.3:  # Threshold for relevance
                context.relevance_score = relevance_score
                relevant_contexts.append(context)
        
        # Filter by system if specified
        if system_id:
            relevant_contexts = [c for c in relevant_contexts if c.system_id == system_id]
        
        # Sort by relevance score
        relevant_contexts.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return relevant_contexts[:5]  # Return top 5 most relevant
    
    def _calculate_relevance(self, query: str, content: str, tags: List[str]) -> float:
        """Calculate relevance score between query and content"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Simple relevance calculation
        score = 0.0
        
        # Check for exact word matches
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        word_matches = len(query_words.intersection(content_words))
        if len(query_words) > 0:
            score += (word_matches / len(query_words)) * 0.6
        
        # Check for tag matches
        for tag in tags:
            if tag.lower() in query_lower:
                score += 0.2
        
        # Check for phrase matches
        if any(word in content_lower for word in query_words):
            score += 0.2
        
        return min(score, 1.0)
    
    def _search_knowledge_base(self, query: str) -> List[SupportKnowledge]:
        """Search knowledge base for relevant articles"""
        results = []
        
        for knowledge_id, knowledge in self.knowledge_base.items():
            relevance_score = self._calculate_relevance(query, knowledge.content, knowledge.tags)
            
            if relevance_score > 0.3:
                results.append((knowledge, relevance_score))
        
        # Sort by relevance and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return [knowledge for knowledge, score in results[:5]]
    
    def _generate_llm_response(self, query: str, context: List[SupportContext], 
                             knowledge_results: List[SupportKnowledge], 
                             system_id: Optional[str] = None) -> str:
        """Generate response using LLM factory"""
        try:
            # Prepare context for LLM
            context_text = ""
            if context:
                context_text = "\n\n".join([f"{c.context_type}: {c.content[:500]}..." for c in context])
            
            knowledge_text = ""
            if knowledge_results:
                knowledge_text = "\n\n".join([f"{k.title}: {k.content[:300]}..." for k in knowledge_results[:2]])
            
            # Create prompt
            prompt = f"""
You are a helpful support agent for a system builder platform. A user has asked: "{query}"

Relevant system context:
{context_text}

Relevant knowledge base articles:
{knowledge_text}

Please provide a helpful, accurate, and friendly response. If you don't know something, say so and offer to escalate the issue.

Response:"""
            
            # Generate response using LLM factory
            if hasattr(self.llm_factory, 'generate_response'):
                response = self.llm_factory.generate_response(prompt)
            else:
                response = self._generate_fallback_response(query, knowledge_results)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._generate_fallback_response(query, knowledge_results)
    
    def _generate_fallback_response(self, query: str, knowledge_results: List[SupportKnowledge]) -> str:
        """Generate fallback response when LLM is not available"""
        if knowledge_results:
            best_match = knowledge_results[0]
            return f"I found a relevant article that might help: '{best_match.title}'. {best_match.content[:200]}...\n\nIf this doesn't answer your question, please let me know and I'll help you further."
        else:
            return f"Thank you for your question about '{query}'. I'm here to help! Could you provide more details about what you're trying to accomplish? This will help me give you a more specific and helpful response."
    
    def _create_or_update_ticket(self, session_id: str, user_id: str, query: str, 
                               response: str, system_id: Optional[str] = None) -> str:
        """Create or update support ticket"""
        # Check if there's an existing open ticket for this session
        existing_ticket = self._get_open_ticket_for_session(session_id)
        
        if existing_ticket:
            # Update existing ticket
            ticket_id = existing_ticket.ticket_id
            self._update_ticket(ticket_id, query, response)
        else:
            # Create new ticket
            ticket_id = self._create_ticket(session_id, user_id, query, response, system_id)
        
        return ticket_id
    
    def _get_open_ticket_for_session(self, session_id: str) -> Optional[SupportTicket]:
        """Get open ticket for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM support_tickets 
            WHERE session_id = ? AND status IN ('open', 'in_progress')
            ORDER BY created_at DESC LIMIT 1
        ''', (session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return self._result_to_ticket(result)
        
        return None
    
    def _create_ticket(self, session_id: str, user_id: str, query: str, 
                      response: str, system_id: Optional[str] = None) -> str:
        """Create a new support ticket"""
        ticket_id = f"ticket_{int(time.time())}_{user_id}"
        
        # Determine category and priority
        category = self._categorize_query(query)
        priority = self._determine_priority(query, category)
        
        ticket = SupportTicket(
            ticket_id=ticket_id,
            user_id=user_id,
            system_id=system_id,
            channel=SupportChannel.CHAT,
            priority=priority,
            status=SupportStatus.OPEN,
            category=category,
            subject=query[:100] + "..." if len(query) > 100 else query,
            description=query,
            context={"session_id": session_id, "initial_response": response},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            resolved_at=None,
            assigned_to=None,
            tags=self._extract_tags(query),
            satisfaction_score=None
        )
        
        self._save_ticket(ticket)
        return ticket_id
    
    def _categorize_query(self, query: str) -> SupportCategory:
        """Categorize a support query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["error", "bug", "crash", "broken", "not working"]):
            return SupportCategory.BUG_REPORT
        elif any(word in query_lower for word in ["bill", "payment", "subscription", "charge"]):
            return SupportCategory.BILLING
        elif any(word in query_lower for word in ["feature", "add", "new", "enhancement"]):
            return SupportCategory.FEATURE_REQUEST
        elif any(word in query_lower for word in ["integrate", "api", "webhook", "connection"]):
            return SupportCategory.INTEGRATION
        elif any(word in query_lower for word in ["setup", "install", "configure", "onboard"]):
            return SupportCategory.ONBOARDING
        elif any(word in query_lower for word in ["how", "what", "where", "when", "why"]):
            return SupportCategory.TECHNICAL
        else:
            return SupportCategory.GENERAL
    
    def _determine_priority(self, query: str, category: SupportCategory) -> SupportPriority:
        """Determine priority for a support query"""
        query_lower = query.lower()
        
        # High priority keywords
        high_priority_words = ["urgent", "critical", "emergency", "down", "broken", "crash"]
        if any(word in query_lower for word in high_priority_words):
            return SupportPriority.URGENT
        
        # Medium priority for certain categories
        if category in [SupportCategory.BUG_REPORT, SupportCategory.BILLING]:
            return SupportPriority.HIGH
        
        # Default to medium
        return SupportPriority.MEDIUM
    
    def _extract_tags(self, query: str) -> List[str]:
        """Extract tags from a query"""
        tags = []
        query_lower = query.lower()
        
        # Common tags
        tag_keywords = {
            "deployment": ["deploy", "deployment", "hosting"],
            "api": ["api", "endpoint", "rest"],
            "database": ["database", "db", "sql"],
            "authentication": ["auth", "login", "password"],
            "performance": ["slow", "performance", "speed"],
            "mobile": ["mobile", "app", "ios", "android"],
            "web": ["web", "website", "frontend"]
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                tags.append(tag)
        
        return tags
    
    def _save_ticket(self, ticket: SupportTicket):
        """Save ticket to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO support_tickets 
            (ticket_id, user_id, system_id, channel, priority, status, category,
            subject, description, context, created_at, updated_at, resolved_at,
            assigned_to, tags, satisfaction_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticket.ticket_id,
            ticket.user_id,
            ticket.system_id,
            ticket.channel.value,
            ticket.priority.value,
            ticket.status.value,
            ticket.category.value,
            ticket.subject,
            ticket.description,
            json.dumps(ticket.context),
            ticket.created_at.isoformat(),
            ticket.updated_at.isoformat(),
            ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            ticket.assigned_to,
            json.dumps(ticket.tags),
            ticket.satisfaction_score
        ))
        
        conn.commit()
        conn.close()
    
    def _update_ticket(self, ticket_id: str, query: str, response: str):
        """Update existing ticket"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE support_tickets 
            SET description = description || '\n\n' || ?, 
                updated_at = ?, 
                context = json_set(context, '$.latest_query', ?)
            WHERE ticket_id = ?
        ''', (query, datetime.now().isoformat(), query, ticket_id))
        
        conn.commit()
        conn.close()
    
    def _save_support_message(self, session_id: str, sender_id: str, content: str, 
                            sender_type: str, message_type: str) -> str:
        """Save support message"""
        message_id = f"msg_{int(time.time())}_{sender_id}"
        
        message = SupportMessage(
            message_id=message_id,
            ticket_id=session_id,  # Using session_id as ticket_id for now
            sender_id=sender_id,
            sender_type=sender_type,
            content=content,
            message_type=message_type,
            timestamp=datetime.now(),
            metadata={}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO support_messages 
            (message_id, ticket_id, sender_id, sender_type, content, message_type, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.message_id,
            message.ticket_id,
            message.sender_id,
            message.sender_type,
            message.content,
            message.message_type,
            message.timestamp.isoformat(),
            json.dumps(message.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        return message_id
    
    def _result_to_ticket(self, result) -> SupportTicket:
        """Convert database result to SupportTicket"""
        ticket_id, user_id, system_id, channel, priority, status, category, subject, description, context, created_at, updated_at, resolved_at, assigned_to, tags, satisfaction_score = result
        
        return SupportTicket(
            ticket_id=ticket_id,
            user_id=user_id,
            system_id=system_id,
            channel=SupportChannel(channel),
            priority=SupportPriority(priority),
            status=SupportStatus(status),
            category=SupportCategory(category),
            subject=subject,
            description=description,
            context=json.loads(context),
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at),
            resolved_at=datetime.fromisoformat(resolved_at) if resolved_at else None,
            assigned_to=assigned_to,
            tags=json.loads(tags),
            satisfaction_score=satisfaction_score
        )
    
    def get_support_context(self, system_id: str) -> List[SupportContext]:
        """Get support context for a system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM support_context WHERE system_id = ?', (system_id,))
        results = cursor.fetchall()
        conn.close()
        
        contexts = []
        for result in results:
            context_id, system_id, context_type, content, last_updated, relevance_score, tags = result
            
            contexts.append(SupportContext(
                context_id=context_id,
                system_id=system_id,
                context_type=context_type,
                content=content,
                last_updated=datetime.fromisoformat(last_updated),
                relevance_score=relevance_score,
                tags=json.loads(tags)
            ))
        
        return contexts
    
    def record_feedback(self, message_id: str, user_feedback: str, satisfaction_score: Optional[int] = None):
        """Record user feedback on support interaction"""
        try:
            # Update message metadata with feedback
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE support_messages 
                SET metadata = json_set(metadata, '$.feedback', ?)
                WHERE message_id = ?
            ''', (user_feedback, message_id))
            
            # If satisfaction score provided, update related ticket
            if satisfaction_score is not None:
                cursor.execute('''
                    UPDATE support_tickets 
                    SET satisfaction_score = ?
                    WHERE ticket_id = (
                        SELECT ticket_id FROM support_messages WHERE message_id = ?
                    )
                ''', (satisfaction_score, message_id))
            
            conn.commit()
            conn.close()
            
            # Feed to LLM factory for learning if available
            if self.llm_factory:
                self._feed_feedback_to_llm(message_id, user_feedback, satisfaction_score)
                
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
    
    def _feed_feedback_to_llm(self, message_id: str, user_feedback: str, satisfaction_score: Optional[int]):
        """Feed feedback to LLM factory for learning"""
        try:
            # Get the original message
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM support_messages WHERE message_id = ?', (message_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                message_id, ticket_id, sender_id, sender_type, content, message_type, timestamp, metadata = result
                
                # Create training data
                training_data = {
                    "type": "support_feedback",
                    "original_query": content,
                    "user_feedback": user_feedback,
                    "satisfaction_score": satisfaction_score,
                    "timestamp": timestamp
                }
                
                # Add to LLM factory training dataset
                if hasattr(self.llm_factory, 'add_training_data'):
                    self.llm_factory.add_training_data(training_data)
                    
        except Exception as e:
            logger.error(f"Error feeding feedback to LLM: {e}")
    
    def escalate_issue(self, ticket_id: str, reason: str, escalation_level: str = "tier2") -> bool:
        """Escalate a support issue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE support_tickets 
                SET status = ?, context = json_set(context, '$.escalation', ?)
                WHERE ticket_id = ?
            ''', (SupportStatus.ESCALATED.value, json.dumps({
                "reason": reason,
                "level": escalation_level,
                "escalated_at": datetime.now().isoformat()
            }), ticket_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error escalating issue: {e}")
            return False
    
    def get_support_statistics(self) -> Dict[str, Any]:
        """Get support statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total tickets
        cursor.execute('SELECT COUNT(*) FROM support_tickets')
        total_tickets = cursor.fetchone()[0]
        
        # Open tickets
        cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE status = "open"')
        open_tickets = cursor.fetchone()[0]
        
        # Resolved tickets
        cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE status = "resolved"')
        resolved_tickets = cursor.fetchone()[0]
        
        # Average satisfaction score
        cursor.execute('SELECT AVG(satisfaction_score) FROM support_tickets WHERE satisfaction_score IS NOT NULL')
        avg_satisfaction = cursor.fetchone()[0] or 0
        
        # Active sessions
        cursor.execute('SELECT COUNT(*) FROM support_sessions WHERE is_active = 1')
        active_sessions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolved_tickets": resolved_tickets,
            "resolution_rate": (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0,
            "average_satisfaction": round(avg_satisfaction, 2),
            "active_sessions": active_sessions
        }
