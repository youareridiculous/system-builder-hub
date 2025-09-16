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

class CoachingTrigger(Enum):
    FIRST_LOGIN = "first_login"
    FEATURE_USAGE = "feature_usage"
    SYSTEM_CREATION = "system_creation"
    DEPLOYMENT = "deployment"
    ERROR_ENCOUNTERED = "error_encountered"
    INACTIVITY = "inactivity"
    COMPLETION_MILESTONE = "completion_milestone"
    MANUAL = "manual"

class CoachingType(Enum):
    TIP = "tip"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    CELEBRATION = "celebration"
    TUTORIAL = "tutorial"
    BEST_PRACTICE = "best_practice"

class CoachingPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class AuditType(Enum):
    ARCHITECTURE = "architecture"
    FEATURE_COVERAGE = "feature_coverage"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BEST_PRACTICES = "best_practices"

@dataclass
class CoachingTip:
    tip_id: str
    user_id: str
    coaching_type: CoachingType
    title: str
    message: str
    action_url: Optional[str]
    priority: CoachingPriority
    trigger: CoachingTrigger
    context: Dict[str, Any]
    is_dismissed: bool
    dismissed_at: Optional[datetime]
    is_actioned: bool
    actioned_at: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]

@dataclass
class SystemAudit:
    audit_id: str
    system_id: str
    audit_type: AuditType
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    score: float  # 0-100
    status: str  # "pending", "completed", "failed"
    created_at: datetime
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]

@dataclass
class UserBehavior:
    behavior_id: str
    user_id: str
    behavior_type: str
    context: Dict[str, Any]
    timestamp: datetime
    session_id: Optional[str]
    feature_used: Optional[str]
    system_id: Optional[str]

@dataclass
class CoachingFeedback:
    feedback_id: str
    tip_id: str
    user_id: str
    feedback_type: str  # "helpful", "not_helpful", "dismissed", "actioned"
    feedback_data: Dict[str, Any]
    timestamp: datetime

@dataclass
class CoachingSession:
    session_id: str
    user_id: str
    started_at: datetime
    last_activity: datetime
    tips_shown: int
    tips_actioned: int
    tips_dismissed: int
    current_focus: Optional[str]
    learning_path: List[str]

class ProactiveCoachingLayer:
    def __init__(self, base_dir: str, system_delivery=None, client_success=None, llm_factory=None):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data" / "coaching_layer"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Dependencies
        self.system_delivery = system_delivery
        self.client_success = client_success
        self.llm_factory = llm_factory
        
        # Database
        self.db_path = self.data_dir / "coaching_layer.db"
        self._init_database()
        
        # Coaching state
        self.active_sessions = {}
        self.tip_templates = {}
        self.behavior_patterns = {}
        
        # Load tip templates
        self._load_tip_templates()
        
        # Start coaching thread
        self.coaching_active = False
        self.coaching_thread = None
        self.start_coaching()
    
    def _init_database(self):
        """Initialize SQLite database for coaching layer data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Coaching tips table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coaching_tips (
                tip_id TEXT PRIMARY KEY,
                user_id TEXT,
                coaching_type TEXT,
                title TEXT,
                message TEXT,
                action_url TEXT,
                priority TEXT,
                trigger TEXT,
                context TEXT,
                is_dismissed INTEGER,
                dismissed_at TEXT,
                is_actioned INTEGER,
                actioned_at TEXT,
                created_at TEXT,
                expires_at TEXT
            )
        ''')
        
        # System audits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_audits (
                audit_id TEXT PRIMARY KEY,
                system_id TEXT,
                audit_type TEXT,
                findings TEXT,
                recommendations TEXT,
                score REAL,
                status TEXT,
                created_at TEXT,
                completed_at TEXT,
                metadata TEXT
            )
        ''')
        
        # User behavior table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_behavior (
                behavior_id TEXT PRIMARY KEY,
                user_id TEXT,
                behavior_type TEXT,
                context TEXT,
                timestamp TEXT,
                session_id TEXT,
                feature_used TEXT,
                system_id TEXT
            )
        ''')
        
        # Coaching feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coaching_feedback (
                feedback_id TEXT PRIMARY KEY,
                tip_id TEXT,
                user_id TEXT,
                feedback_type TEXT,
                feedback_data TEXT,
                timestamp TEXT,
                FOREIGN KEY (tip_id) REFERENCES coaching_tips (tip_id)
            )
        ''')
        
        # Coaching sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coaching_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                started_at TEXT,
                last_activity TEXT,
                tips_shown INTEGER,
                tips_actioned INTEGER,
                tips_dismissed INTEGER,
                current_focus TEXT,
                learning_path TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_tip_templates(self):
        """Load coaching tip templates"""
        self.tip_templates = {
            "first_login": {
                "title": "Welcome to System Builder! 🚀",
                "message": "Let's get you started with your first system build. Click here to begin your journey!",
                "coaching_type": CoachingType.TUTORIAL,
                "priority": CoachingPriority.HIGH,
                "action_url": "/onboarding"
            },
            "system_creation": {
                "title": "Great Start! 💡",
                "message": "You've created your first system! Consider adding more features to make it even better.",
                "coaching_type": CoachingType.SUGGESTION,
                "priority": CoachingPriority.MEDIUM,
                "action_url": "/features"
            },
            "deployment": {
                "title": "Deployment Success! 🎉",
                "message": "Your system is live! Learn about monitoring and scaling options.",
                "coaching_type": CoachingType.CELEBRATION,
                "priority": CoachingPriority.MEDIUM,
                "action_url": "/monitoring"
            },
            "error_encountered": {
                "title": "Need Help? 🤝",
                "message": "We noticed you encountered an issue. Here are some helpful resources to get you back on track.",
                "coaching_type": CoachingType.TIP,
                "priority": CoachingPriority.HIGH,
                "action_url": "/support"
            },
            "inactivity": {
                "title": "Missing You! 💭",
                "message": "Ready to build something amazing? Here's a quick tip to get you inspired.",
                "coaching_type": CoachingType.SUGGESTION,
                "priority": CoachingPriority.LOW,
                "action_url": "/templates"
            },
            "best_practice": {
                "title": "Pro Tip! ⚡",
                "message": "Here's a best practice that can help you build better systems faster.",
                "coaching_type": CoachingType.BEST_PRACTICE,
                "priority": CoachingPriority.MEDIUM,
                "action_url": None
            }
        }
    
    def start_coaching(self):
        """Start the coaching thread"""
        if not self.coaching_active:
            self.coaching_active = True
            self.coaching_thread = threading.Thread(target=self._coaching_loop, daemon=True)
            self.coaching_thread.start()
            logger.info("Proactive coaching started")
    
    def stop_coaching(self):
        """Stop the coaching thread"""
        self.coaching_active = False
        if self.coaching_thread:
            self.coaching_thread.join()
            logger.info("Proactive coaching stopped")
    
    def _coaching_loop(self):
        """Main coaching loop"""
        while self.coaching_active:
            try:
                # Analyze user behavior
                self._analyze_user_behavior()
                
                # Generate coaching tips
                self._generate_coaching_tips()
                
                # Trigger system audits
                self._trigger_system_audits()
                
                # Update learning paths
                self._update_learning_paths()
                
                # Sleep for coaching interval
                time.sleep(180)  # Check every 3 minutes
                
            except Exception as e:
                logger.error(f"Error in coaching loop: {e}")
                time.sleep(60)
    
    def record_user_behavior(self, user_id: str, behavior_type: str, context: Dict[str, Any],
                           session_id: Optional[str] = None, feature_used: Optional[str] = None,
                           system_id: Optional[str] = None):
        """Record user behavior for coaching analysis"""
        behavior_id = f"behavior_{int(time.time())}_{user_id}"
        
        behavior = UserBehavior(
            behavior_id=behavior_id,
            user_id=user_id,
            behavior_type=behavior_type,
            context=context,
            timestamp=datetime.now(),
            session_id=session_id,
            feature_used=feature_used,
            system_id=system_id
        )
        
        self._save_user_behavior(behavior)
        
        # Update coaching session
        self._update_coaching_session(user_id, behavior)
        
        # Check for coaching triggers
        self._check_coaching_triggers(user_id, behavior)
    
    def _save_user_behavior(self, behavior: UserBehavior):
        """Save user behavior to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_behavior 
            (behavior_id, user_id, behavior_type, context, timestamp, session_id, feature_used, system_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            behavior.behavior_id,
            behavior.user_id,
            behavior.behavior_type,
            json.dumps(behavior.context),
            behavior.timestamp.isoformat(),
            behavior.session_id,
            behavior.feature_used,
            behavior.system_id
        ))
        
        conn.commit()
        conn.close()
    
    def _update_coaching_session(self, user_id: str, behavior: UserBehavior):
        """Update coaching session for user"""
        if user_id not in self.active_sessions:
            # Create new session
            session = CoachingSession(
                session_id=f"session_{int(time.time())}_{user_id}",
                user_id=user_id,
                started_at=datetime.now(),
                last_activity=datetime.now(),
                tips_shown=0,
                tips_actioned=0,
                tips_dismissed=0,
                current_focus=None,
                learning_path=[]
            )
            self.active_sessions[user_id] = session
            self._save_coaching_session(session)
        else:
            # Update existing session
            session = self.active_sessions[user_id]
            session.last_activity = datetime.now()
            self._save_coaching_session(session)
    
    def _save_coaching_session(self, session: CoachingSession):
        """Save coaching session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO coaching_sessions 
            (session_id, user_id, started_at, last_activity, tips_shown, tips_actioned,
            tips_dismissed, current_focus, learning_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id,
            session.user_id,
            session.started_at.isoformat(),
            session.last_activity.isoformat(),
            session.tips_shown,
            session.tips_actioned,
            session.tips_dismissed,
            session.current_focus,
            json.dumps(session.learning_path)
        ))
        
        conn.commit()
        conn.close()
    
    def _check_coaching_triggers(self, user_id: str, behavior: UserBehavior):
        """Check for coaching triggers based on user behavior"""
        triggers = []
        
        # First login trigger
        if behavior.behavior_type == "login" and self._is_first_login(user_id):
            triggers.append(CoachingTrigger.FIRST_LOGIN)
        
        # System creation trigger
        if behavior.behavior_type == "system_created":
            triggers.append(CoachingTrigger.SYSTEM_CREATION)
        
        # Deployment trigger
        if behavior.behavior_type == "system_deployed":
            triggers.append(CoachingTrigger.DEPLOYMENT)
        
        # Error trigger
        if behavior.behavior_type == "error_encountered":
            triggers.append(CoachingTrigger.ERROR_ENCOUNTERED)
        
        # Feature usage trigger
        if behavior.feature_used:
            triggers.append(CoachingTrigger.FEATURE_USAGE)
        
        # Generate tips for triggers
        for trigger in triggers:
            self._generate_tip_for_trigger(user_id, trigger, behavior)
    
    def _is_first_login(self, user_id: str) -> bool:
        """Check if this is the user's first login"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM user_behavior 
            WHERE user_id = ? AND behavior_type = 'login'
        ''', (user_id,))
        
        login_count = cursor.fetchone()[0]
        conn.close()
        
        return login_count <= 1
    
    def _generate_tip_for_trigger(self, user_id: str, trigger: CoachingTrigger, behavior: UserBehavior):
        """Generate coaching tip for a specific trigger"""
        if trigger.value in self.tip_templates:
            template = self.tip_templates[trigger.value]
            
            tip = CoachingTip(
                tip_id=f"tip_{int(time.time())}_{user_id}",
                user_id=user_id,
                coaching_type=template["coaching_type"],
                title=template["title"],
                message=template["message"],
                action_url=template["action_url"],
                priority=template["priority"],
                trigger=trigger,
                context={
                    "behavior_type": behavior.behavior_type,
                    "feature_used": behavior.feature_used,
                    "system_id": behavior.system_id
                },
                is_dismissed=False,
                dismissed_at=None,
                is_actioned=False,
                actioned_at=None,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7)  # Tips expire after 7 days
            )
            
            self._save_coaching_tip(tip)
    
    def _save_coaching_tip(self, tip: CoachingTip):
        """Save coaching tip to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO coaching_tips 
            (tip_id, user_id, coaching_type, title, message, action_url, priority,
            trigger, context, is_dismissed, dismissed_at, is_actioned, actioned_at,
            created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tip.tip_id,
            tip.user_id,
            tip.coaching_type.value,
            tip.title,
            tip.message,
            tip.action_url,
            tip.priority.value,
            tip.trigger.value,
            json.dumps(tip.context),
            1 if tip.is_dismissed else 0,
            tip.dismissed_at.isoformat() if tip.dismissed_at else None,
            1 if tip.is_actioned else 0,
            tip.actioned_at.isoformat() if tip.actioned_at else None,
            tip.created_at.isoformat(),
            tip.expires_at.isoformat() if tip.expires_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_coaching_tips(self, user_id: str, limit: int = 5) -> List[CoachingTip]:
        """Get coaching tips for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM coaching_tips 
            WHERE user_id = ? AND is_dismissed = 0 AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        ''', (user_id, datetime.now().isoformat(), limit))
        
        results = cursor.fetchall()
        conn.close()
        
        tips = []
        for result in results:
            tip_id, user_id, coaching_type, title, message, action_url, priority, trigger, context, is_dismissed, dismissed_at, is_actioned, actioned_at, created_at, expires_at = result
            
            tips.append(CoachingTip(
                tip_id=tip_id,
                user_id=user_id,
                coaching_type=CoachingType(coaching_type),
                title=title,
                message=message,
                action_url=action_url,
                priority=CoachingPriority(priority),
                trigger=CoachingTrigger(trigger),
                context=json.loads(context),
                is_dismissed=bool(is_dismissed),
                dismissed_at=datetime.fromisoformat(dismissed_at) if dismissed_at else None,
                is_actioned=bool(is_actioned),
                actioned_at=datetime.fromisoformat(actioned_at) if actioned_at else None,
                created_at=datetime.fromisoformat(created_at),
                expires_at=datetime.fromisoformat(expires_at) if expires_at else None
            ))
        
        return tips
    
    def dismiss_tip(self, tip_id: str, user_id: str, feedback: Optional[str] = None):
        """Dismiss a coaching tip"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE coaching_tips 
                SET is_dismissed = 1, dismissed_at = ?
                WHERE tip_id = ? AND user_id = ?
            ''', (datetime.now().isoformat(), tip_id, user_id))
            
            conn.commit()
            conn.close()
            
            # Record feedback
            if feedback:
                self._record_coaching_feedback(tip_id, user_id, "dismissed", {"feedback": feedback})
            
            # Update session stats
            if user_id in self.active_sessions:
                self.active_sessions[user_id].tips_dismissed += 1
                self._save_coaching_session(self.active_sessions[user_id])
                
        except Exception as e:
            logger.error(f"Error dismissing tip: {e}")
    
    def action_tip(self, tip_id: str, user_id: str, action_data: Optional[Dict[str, Any]] = None):
        """Mark a coaching tip as actioned"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE coaching_tips 
                SET is_actioned = 1, actioned_at = ?
                WHERE tip_id = ? AND user_id = ?
            ''', (datetime.now().isoformat(), tip_id, user_id))
            
            conn.commit()
            conn.close()
            
            # Record feedback
            self._record_coaching_feedback(tip_id, user_id, "actioned", action_data or {})
            
            # Update session stats
            if user_id in self.active_sessions:
                self.active_sessions[user_id].tips_actioned += 1
                self._save_coaching_session(self.active_sessions[user_id])
                
        except Exception as e:
            logger.error(f"Error actioning tip: {e}")
    
    def _record_coaching_feedback(self, tip_id: str, user_id: str, feedback_type: str, feedback_data: Dict[str, Any]):
        """Record coaching feedback"""
        feedback_id = f"feedback_{int(time.time())}_{tip_id}"
        
        feedback = CoachingFeedback(
            feedback_id=feedback_id,
            tip_id=tip_id,
            user_id=user_id,
            feedback_type=feedback_type,
            feedback_data=feedback_data,
            timestamp=datetime.now()
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO coaching_feedback 
            (feedback_id, tip_id, user_id, feedback_type, feedback_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            feedback.feedback_id,
            feedback.tip_id,
            feedback.user_id,
            feedback.feedback_type,
            json.dumps(feedback.feedback_data),
            feedback.timestamp.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Feed to LLM factory for learning if available
        if self.llm_factory:
            self._feed_coaching_feedback_to_llm(feedback)
    
    def _feed_coaching_feedback_to_llm(self, feedback: CoachingFeedback):
        """Feed coaching feedback to LLM factory for learning"""
        try:
            # Create training data
            training_data = {
                "type": "coaching_feedback",
                "tip_id": feedback.tip_id,
                "user_id": feedback.user_id,
                "feedback_type": feedback.feedback_type,
                "feedback_data": feedback.feedback_data,
                "timestamp": feedback.timestamp.isoformat()
            }
            
            # Add to LLM factory training dataset
            if hasattr(self.llm_factory, 'add_training_data'):
                self.llm_factory.add_training_data(training_data)
                
        except Exception as e:
            logger.error(f"Error feeding coaching feedback to LLM: {e}")
    
    def audit_system(self, system_id: str, audit_type: AuditType) -> str:
        """Trigger a system audit"""
        audit_id = f"audit_{int(time.time())}_{system_id}"
        
        audit = SystemAudit(
            audit_id=audit_id,
            system_id=system_id,
            audit_type=audit_type,
            findings=[],
            recommendations=[],
            score=0.0,
            status="pending",
            created_at=datetime.now(),
            completed_at=None,
            metadata={}
        )
        
        self._save_system_audit(audit)
        
        # Start audit in background
        threading.Thread(target=self._perform_system_audit, args=(audit_id,), daemon=True).start()
        
        return audit_id
    
    def _save_system_audit(self, audit: SystemAudit):
        """Save system audit to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_audits 
            (audit_id, system_id, audit_type, findings, recommendations, score,
            status, created_at, completed_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            audit.audit_id,
            audit.system_id,
            audit.audit_type.value,
            json.dumps(audit.findings),
            json.dumps(audit.recommendations),
            audit.score,
            audit.status,
            audit.created_at.isoformat(),
            audit.completed_at.isoformat() if audit.completed_at else None,
            json.dumps(audit.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _perform_system_audit(self, audit_id: str):
        """Perform system audit in background"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM system_audits WHERE audit_id = ?', (audit_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                audit_id, system_id, audit_type, findings, recommendations, score, status, created_at, completed_at, metadata = result
                
                # Perform audit based on type
                if audit_type == AuditType.ARCHITECTURE.value:
                    findings, recommendations, score = self._audit_architecture(system_id)
                elif audit_type == AuditType.FEATURE_COVERAGE.value:
                    findings, recommendations, score = self._audit_feature_coverage(system_id)
                elif audit_type == AuditType.COMPLIANCE.value:
                    findings, recommendations, score = self._audit_compliance(system_id)
                elif audit_type == AuditType.PERFORMANCE.value:
                    findings, recommendations, score = self._audit_performance(system_id)
                elif audit_type == AuditType.SECURITY.value:
                    findings, recommendations, score = self._audit_security(system_id)
                elif audit_type == AuditType.BEST_PRACTICES.value:
                    findings, recommendations, score = self._audit_best_practices(system_id)
                
                # Update audit results
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE system_audits 
                    SET findings = ?, recommendations = ?, score = ?, status = ?, completed_at = ?
                    WHERE audit_id = ?
                ''', (
                    json.dumps(findings),
                    json.dumps(recommendations),
                    score,
                    "completed",
                    datetime.now().isoformat(),
                    audit_id
                ))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            logger.error(f"Error performing system audit: {e}")
    
    def _audit_architecture(self, system_id: str) -> Tuple[List[Dict[str, Any]], List[str], float]:
        """Audit system architecture"""
        findings = []
        recommendations = []
        score = 80.0  # Base score
        
        # Sample architecture audit
        findings.append({
            "type": "architecture",
            "severity": "medium",
            "description": "System has good modular structure",
            "details": "Components are well-separated"
        })
        
        recommendations.append("Consider implementing microservices pattern for better scalability")
        recommendations.append("Add API documentation for better integration")
        
        return findings, recommendations, score
    
    def _audit_feature_coverage(self, system_id: str) -> Tuple[List[Dict[str, Any]], List[str], float]:
        """Audit feature coverage"""
        findings = []
        recommendations = []
        score = 75.0  # Base score
        
        # Sample feature coverage audit
        findings.append({
            "type": "feature_coverage",
            "severity": "low",
            "description": "Good core feature implementation",
            "details": "Essential features are present"
        })
        
        recommendations.append("Consider adding advanced analytics features")
        recommendations.append("Implement user customization options")
        
        return findings, recommendations, score
    
    def _audit_compliance(self, system_id: str) -> Tuple[List[Dict[str, Any]], List[str], float]:
        """Audit compliance"""
        findings = []
        recommendations = []
        score = 90.0  # Base score
        
        # Sample compliance audit
        findings.append({
            "type": "compliance",
            "severity": "low",
            "description": "Good compliance posture",
            "details": "Basic compliance requirements met"
        })
        
        recommendations.append("Implement GDPR compliance features")
        recommendations.append("Add data retention policies")
        
        return findings, recommendations, score
    
    def _audit_performance(self, system_id: str) -> Tuple[List[Dict[str, Any]], List[str], float]:
        """Audit performance"""
        findings = []
        recommendations = []
        score = 85.0  # Base score
        
        # Sample performance audit
        findings.append({
            "type": "performance",
            "severity": "medium",
            "description": "Good performance characteristics",
            "details": "Response times are acceptable"
        })
        
        recommendations.append("Implement caching for frequently accessed data")
        recommendations.append("Optimize database queries")
        
        return findings, recommendations, score
    
    def _audit_security(self, system_id: str) -> Tuple[List[Dict[str, Any]], List[str], float]:
        """Audit security"""
        findings = []
        recommendations = []
        score = 88.0  # Base score
        
        # Sample security audit
        findings.append({
            "type": "security",
            "severity": "low",
            "description": "Good security practices",
            "details": "Basic security measures in place"
        })
        
        recommendations.append("Implement two-factor authentication")
        recommendations.append("Add rate limiting for API endpoints")
        
        return findings, recommendations, score
    
    def _audit_best_practices(self, system_id: str) -> Tuple[List[Dict[str, Any]], List[str], float]:
        """Audit best practices"""
        findings = []
        recommendations = []
        score = 82.0  # Base score
        
        # Sample best practices audit
        findings.append({
            "type": "best_practices",
            "severity": "medium",
            "description": "Good adherence to best practices",
            "details": "Code follows established patterns"
        })
        
        recommendations.append("Add comprehensive error handling")
        recommendations.append("Implement logging and monitoring")
        
        return findings, recommendations, score
    
    def get_system_audit(self, system_id: str, audit_type: Optional[AuditType] = None) -> List[SystemAudit]:
        """Get system audits"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if audit_type:
            cursor.execute('''
                SELECT * FROM system_audits 
                WHERE system_id = ? AND audit_type = ?
                ORDER BY created_at DESC
            ''', (system_id, audit_type.value))
        else:
            cursor.execute('''
                SELECT * FROM system_audits 
                WHERE system_id = ?
                ORDER BY created_at DESC
            ''', (system_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        audits = []
        for result in results:
            audit_id, system_id, audit_type, findings, recommendations, score, status, created_at, completed_at, metadata = result
            
            audits.append(SystemAudit(
                audit_id=audit_id,
                system_id=system_id,
                audit_type=AuditType(audit_type),
                findings=json.loads(findings),
                recommendations=json.loads(recommendations),
                score=score,
                status=status,
                created_at=datetime.fromisoformat(created_at),
                completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
                metadata=json.loads(metadata)
            ))
        
        return audits
    
    def get_coaching_nudges(self, user_id: str) -> List[Dict[str, Any]]:
        """Get coaching nudges for a user"""
        nudges = []
        
        # Get active tips
        tips = self.get_coaching_tips(user_id, limit=3)
        for tip in tips:
            nudges.append({
                "type": "tip",
                "id": tip.tip_id,
                "title": tip.title,
                "message": tip.message,
                "action_url": tip.action_url,
                "priority": tip.priority.value,
                "coaching_type": tip.coaching_type.value
            })
        
        # Get system audit recommendations
        if self.system_delivery:
            try:
                systems = self.system_delivery.get_user_systems(user_id)
                for system in systems:
                    audits = self.get_system_audit(system.system_id)
                    for audit in audits:
                        if audit.status == "completed" and audit.score < 80:
                            nudges.append({
                                "type": "audit",
                                "id": audit.audit_id,
                                "title": f"System Improvement: {audit.audit_type.value.title()}",
                                "message": f"Your system scored {audit.score}/100. Consider these improvements.",
                                "action_url": f"/system/{system.system_id}/audit",
                                "priority": "medium",
                                "coaching_type": "suggestion"
                            })
            except Exception as e:
                logger.error(f"Error getting system audit nudges: {e}")
        
        return nudges
    
    def _analyze_user_behavior(self):
        """Analyze user behavior patterns"""
        # This would analyze behavior patterns and update coaching strategies
        pass
    
    def _generate_coaching_tips(self):
        """Generate coaching tips based on behavior analysis"""
        # This would generate tips based on behavior patterns
        pass
    
    def _trigger_system_audits(self):
        """Trigger system audits based on usage patterns"""
        # This would trigger audits for systems that need attention
        pass
    
    def _update_learning_paths(self):
        """Update learning paths based on user progress"""
        # This would update personalized learning paths
        pass
    
    def get_coaching_statistics(self) -> Dict[str, Any]:
        """Get coaching statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total tips
        cursor.execute('SELECT COUNT(*) FROM coaching_tips')
        total_tips = cursor.fetchone()[0]
        
        # Actioned tips
        cursor.execute('SELECT COUNT(*) FROM coaching_tips WHERE is_actioned = 1')
        actioned_tips = cursor.fetchone()[0]
        
        # Dismissed tips
        cursor.execute('SELECT COUNT(*) FROM coaching_tips WHERE is_dismissed = 1')
        dismissed_tips = cursor.fetchone()[0]
        
        # Active sessions
        cursor.execute('SELECT COUNT(*) FROM coaching_sessions')
        active_sessions = cursor.fetchone()[0]
        
        # Completed audits
        cursor.execute('SELECT COUNT(*) FROM system_audits WHERE status = "completed"')
        completed_audits = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_tips": total_tips,
            "actioned_tips": actioned_tips,
            "dismissed_tips": dismissed_tips,
            "action_rate": (actioned_tips / total_tips * 100) if total_tips > 0 else 0,
            "active_sessions": active_sessions,
            "completed_audits": completed_audits
        }
