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

class ClientStage(Enum):
    NOT_LAUNCHED = "not_launched"
    LIVE_UNDERUSED = "live_underused"
    POWER_USER = "power_user"
    AT_RISK = "at_risk"
    CHURNED = "churned"
    EXPANDING = "expanding"

class NudgeType(Enum):
    ONBOARDING = "onboarding"
    FEATURE_DISCOVERY = "feature_discovery"
    BEST_PRACTICES = "best_practices"
    UPGRADE = "upgrade"
    ENGAGEMENT = "engagement"
    SUPPORT = "support"

class EmailTrigger(Enum):
    WELCOME = "welcome"
    ONBOARDING_REMINDER = "onboarding_reminder"
    FEATURE_SPOTLIGHT = "feature_spotlight"
    USAGE_REPORT = "usage_report"
    CHURN_WARNING = "churn_warning"
    SUCCESS_STORY = "success_story"
    UPGRADE_OFFER = "upgrade_offer"

@dataclass
class ClientProfile:
    client_id: str
    user_id: str
    organization_id: Optional[str]
    system_id: Optional[str]
    stage: ClientStage
    onboarding_completed: bool
    first_login: datetime
    last_login: datetime
    total_logins: int
    total_usage_time: float  # minutes
    features_used: List[str]
    systems_created: int
    systems_deployed: int
    revenue_generated: float
    support_tickets: int
    satisfaction_score: Optional[float]
    churn_risk_score: float
    created_at: datetime
    updated_at: datetime

@dataclass
class ClientActivity:
    activity_id: str
    client_id: str
    activity_type: str
    activity_data: Dict[str, Any]
    timestamp: datetime
    session_duration: Optional[float]
    feature_used: Optional[str]
    system_id: Optional[str]

@dataclass
class ClientNudge:
    nudge_id: str
    client_id: str
    nudge_type: NudgeType
    title: str
    message: str
    action_url: Optional[str]
    priority: int
    is_sent: bool
    sent_at: Optional[datetime]
    is_clicked: bool
    clicked_at: Optional[datetime]
    is_dismissed: bool
    dismissed_at: Optional[datetime]
    created_at: datetime

@dataclass
class EmailCampaign:
    campaign_id: str
    trigger_type: EmailTrigger
    client_id: str
    subject: str
    content: str
    is_sent: bool
    sent_at: Optional[datetime]
    is_opened: bool
    opened_at: Optional[datetime]
    is_clicked: bool
    clicked_at: Optional[datetime]
    created_at: datetime

@dataclass
class ChurnPrediction:
    prediction_id: str
    client_id: str
    churn_probability: float
    risk_factors: List[str]
    recommended_actions: List[str]
    prediction_date: datetime
    actual_churn_date: Optional[datetime]
    is_accurate: Optional[bool]

class ClientSuccessEngine:
    def __init__(self, base_dir: str, system_delivery=None, support_agent=None, llm_factory=None):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data" / "client_success"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Dependencies
        self.system_delivery = system_delivery
        self.support_agent = support_agent
        self.llm_factory = llm_factory
        
        # Database
        self.db_path = self.data_dir / "client_success.db"
        self._init_database()
        
        # Success state
        self.client_profiles = {}
        self.activity_tracking = {}
        self.nudge_queue = []
        
        # Load client profiles
        self._load_client_profiles()
        
        # Start monitoring thread
        self.monitoring_active = False
        self.monitor_thread = None
        self.start_monitoring()
    
    def _init_database(self):
        """Initialize SQLite database for client success data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Client profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_profiles (
                client_id TEXT PRIMARY KEY,
                user_id TEXT,
                organization_id TEXT,
                system_id TEXT,
                stage TEXT,
                onboarding_completed INTEGER,
                first_login TEXT,
                last_login TEXT,
                total_logins INTEGER,
                total_usage_time REAL,
                features_used TEXT,
                systems_created INTEGER,
                systems_deployed INTEGER,
                revenue_generated REAL,
                support_tickets INTEGER,
                satisfaction_score REAL,
                churn_risk_score REAL,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Client activity table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_activity (
                activity_id TEXT PRIMARY KEY,
                client_id TEXT,
                activity_type TEXT,
                activity_data TEXT,
                timestamp TEXT,
                session_duration REAL,
                feature_used TEXT,
                system_id TEXT,
                FOREIGN KEY (client_id) REFERENCES client_profiles (client_id)
            )
        ''')
        
        # Client nudges table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_nudges (
                nudge_id TEXT PRIMARY KEY,
                client_id TEXT,
                nudge_type TEXT,
                title TEXT,
                message TEXT,
                action_url TEXT,
                priority INTEGER,
                is_sent INTEGER,
                sent_at TEXT,
                is_clicked INTEGER,
                clicked_at TEXT,
                is_dismissed INTEGER,
                dismissed_at TEXT,
                created_at TEXT,
                FOREIGN KEY (client_id) REFERENCES client_profiles (client_id)
            )
        ''')
        
        # Email campaigns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_campaigns (
                campaign_id TEXT PRIMARY KEY,
                trigger_type TEXT,
                client_id TEXT,
                subject TEXT,
                content TEXT,
                is_sent INTEGER,
                sent_at TEXT,
                is_opened INTEGER,
                opened_at TEXT,
                is_clicked INTEGER,
                clicked_at TEXT,
                created_at TEXT,
                FOREIGN KEY (client_id) REFERENCES client_profiles (client_id)
            )
        ''')
        
        # Churn predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS churn_predictions (
                prediction_id TEXT PRIMARY KEY,
                client_id TEXT,
                churn_probability REAL,
                risk_factors TEXT,
                recommended_actions TEXT,
                prediction_date TEXT,
                actual_churn_date TEXT,
                is_accurate INTEGER,
                FOREIGN KEY (client_id) REFERENCES client_profiles (client_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_client_profiles(self):
        """Load client profiles from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM client_profiles')
        results = cursor.fetchall()
        conn.close()
        
        for result in results:
            client_id, user_id, organization_id, system_id, stage, onboarding_completed, first_login, last_login, total_logins, total_usage_time, features_used, systems_created, systems_deployed, revenue_generated, support_tickets, satisfaction_score, churn_risk_score, created_at, updated_at = result
            
            profile = ClientProfile(
                client_id=client_id,
                user_id=user_id,
                organization_id=organization_id,
                system_id=system_id,
                stage=ClientStage(stage),
                onboarding_completed=bool(onboarding_completed),
                first_login=datetime.fromisoformat(first_login),
                last_login=datetime.fromisoformat(last_login),
                total_logins=total_logins,
                total_usage_time=total_usage_time,
                features_used=json.loads(features_used),
                systems_created=systems_created,
                systems_deployed=systems_deployed,
                revenue_generated=revenue_generated,
                support_tickets=support_tickets,
                satisfaction_score=satisfaction_score,
                churn_risk_score=churn_risk_score,
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at)
            )
            
            self.client_profiles[client_id] = profile
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Client success monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
            logger.info("Client success monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Update client stages
                self._update_client_stages()
                
                # Generate nudges
                self._generate_nudges()
                
                # Predict churn
                self._predict_churn()
                
                # Send email triggers
                self._send_email_triggers()
                
                # Sleep for monitoring interval
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in client success monitoring: {e}")
                time.sleep(60)
    
    def create_client_profile(self, user_id: str, organization_id: Optional[str] = None, 
                            system_id: Optional[str] = None) -> str:
        """Create a new client profile"""
        client_id = f"client_{int(time.time())}_{user_id}"
        
        profile = ClientProfile(
            client_id=client_id,
            user_id=user_id,
            organization_id=organization_id,
            system_id=system_id,
            stage=ClientStage.NOT_LAUNCHED,
            onboarding_completed=False,
            first_login=datetime.now(),
            last_login=datetime.now(),
            total_logins=1,
            total_usage_time=0.0,
            features_used=[],
            systems_created=0,
            systems_deployed=0,
            revenue_generated=0.0,
            support_tickets=0,
            satisfaction_score=None,
            churn_risk_score=0.0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._save_client_profile(profile)
        self.client_profiles[client_id] = profile
        
        return client_id
    
    def _save_client_profile(self, profile: ClientProfile):
        """Save client profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO client_profiles 
            (client_id, user_id, organization_id, system_id, stage, onboarding_completed,
            first_login, last_login, total_logins, total_usage_time, features_used,
            systems_created, systems_deployed, revenue_generated, support_tickets,
            satisfaction_score, churn_risk_score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.client_id,
            profile.user_id,
            profile.organization_id,
            profile.system_id,
            profile.stage.value,
            1 if profile.onboarding_completed else 0,
            profile.first_login.isoformat(),
            profile.last_login.isoformat(),
            profile.total_logins,
            profile.total_usage_time,
            json.dumps(profile.features_used),
            profile.systems_created,
            profile.systems_deployed,
            profile.revenue_generated,
            profile.support_tickets,
            profile.satisfaction_score,
            profile.churn_risk_score,
            profile.created_at.isoformat(),
            profile.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def record_client_activity(self, client_id: str, activity_type: str, 
                             activity_data: Dict[str, Any], session_duration: Optional[float] = None,
                             feature_used: Optional[str] = None, system_id: Optional[str] = None):
        """Record client activity"""
        activity_id = f"activity_{int(time.time())}_{client_id}"
        
        activity = ClientActivity(
            activity_id=activity_id,
            client_id=client_id,
            activity_type=activity_type,
            activity_data=activity_data,
            timestamp=datetime.now(),
            session_duration=session_duration,
            feature_used=feature_used,
            system_id=system_id
        )
        
        self._save_client_activity(activity)
        
        # Update client profile
        if client_id in self.client_profiles:
            profile = self.client_profiles[client_id]
            profile.last_login = datetime.now()
            profile.total_logins += 1
            
            if session_duration:
                profile.total_usage_time += session_duration
            
            if feature_used and feature_used not in profile.features_used:
                profile.features_used.append(feature_used)
            
            if activity_type == "system_created":
                profile.systems_created += 1
            elif activity_type == "system_deployed":
                profile.systems_deployed += 1
            
            profile.updated_at = datetime.now()
            self._save_client_profile(profile)
    
    def _save_client_activity(self, activity: ClientActivity):
        """Save client activity to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO client_activity 
            (activity_id, client_id, activity_type, activity_data, timestamp,
            session_duration, feature_used, system_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            activity.activity_id,
            activity.activity_id,
            activity.activity_type,
            json.dumps(activity.activity_data),
            activity.timestamp.isoformat(),
            activity.session_duration,
            activity.feature_used,
            activity.system_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_client_status(self, client_id: str) -> Optional[ClientProfile]:
        """Get client status and analytics"""
        return self.client_profiles.get(client_id)
    
    def _update_client_stages(self):
        """Update client stages based on activity"""
        for client_id, profile in self.client_profiles.items():
            new_stage = self._determine_client_stage(profile)
            
            if new_stage != profile.stage:
                profile.stage = new_stage
                profile.updated_at = datetime.now()
                self._save_client_profile(profile)
                
                logger.info(f"Client {client_id} stage updated to {new_stage.value}")
    
    def _determine_client_stage(self, profile: ClientProfile) -> ClientStage:
        """Determine client stage based on profile data"""
        days_since_first_login = (datetime.now() - profile.first_login).days
        days_since_last_login = (datetime.now() - profile.last_login).days
        
        # Not launched - no significant activity
        if days_since_first_login < 7 and profile.total_usage_time < 60:
            return ClientStage.NOT_LAUNCHED
        
        # Live but underused - some activity but minimal
        if profile.total_usage_time < 300 and profile.systems_created < 2:
            return ClientStage.LIVE_UNDERUSED
        
        # At risk - declining activity
        if days_since_last_login > 14 or profile.churn_risk_score > 0.7:
            return ClientStage.AT_RISK
        
        # Churned - no activity for extended period
        if days_since_last_login > 30:
            return ClientStage.CHURNED
        
        # Power user - high activity
        if profile.total_usage_time > 1000 and profile.systems_created > 5:
            return ClientStage.POWER_USER
        
        # Expanding - growing activity
        if profile.systems_created > 2 and profile.revenue_generated > 0:
            return ClientStage.EXPANDING
        
        # Default to live but underused
        return ClientStage.LIVE_UNDERUSED
    
    def _generate_nudges(self):
        """Generate nudges for clients"""
        for client_id, profile in self.client_profiles.items():
            if profile.stage in [ClientStage.NOT_LAUNCHED, ClientStage.LIVE_UNDERUSED, ClientStage.AT_RISK]:
                nudges = self._create_nudges_for_client(profile)
                
                for nudge in nudges:
                    self._save_client_nudge(nudge)
                    self.nudge_queue.append(nudge)
    
    def _create_nudges_for_client(self, profile: ClientProfile) -> List[ClientNudge]:
        """Create nudges for a specific client"""
        nudges = []
        
        if profile.stage == ClientStage.NOT_LAUNCHED:
            # Onboarding nudges
            if not profile.onboarding_completed:
                nudges.append(ClientNudge(
                    nudge_id=f"nudge_{int(time.time())}_{profile.client_id}",
                    client_id=profile.client_id,
                    nudge_type=NudgeType.ONBOARDING,
                    title="Complete Your Setup",
                    message="Get started with your first system build in just 5 minutes!",
                    action_url="/onboarding",
                    priority=1,
                    is_sent=False,
                    sent_at=None,
                    is_clicked=False,
                    clicked_at=None,
                    is_dismissed=False,
                    dismissed_at=None,
                    created_at=datetime.now()
                ))
        
        elif profile.stage == ClientStage.LIVE_UNDERUSED:
            # Feature discovery nudges
            if len(profile.features_used) < 3:
                nudges.append(ClientNudge(
                    nudge_id=f"nudge_{int(time.time())}_{profile.client_id}",
                    client_id=profile.client_id,
                    nudge_type=NudgeType.FEATURE_DISCOVERY,
                    title="Discover More Features",
                    message="Explore our advanced features to build even better systems!",
                    action_url="/features",
                    priority=2,
                    is_sent=False,
                    sent_at=None,
                    is_clicked=False,
                    clicked_at=None,
                    is_dismissed=False,
                    dismissed_at=None,
                    created_at=datetime.now()
                ))
        
        elif profile.stage == ClientStage.AT_RISK:
            # Engagement nudges
            nudges.append(ClientNudge(
                nudge_id=f"nudge_{int(time.time())}_{profile.client_id}",
                client_id=profile.client_id,
                nudge_type=NudgeType.ENGAGEMENT,
                title="We Miss You!",
                message="Come back and continue building amazing systems with us.",
                action_url="/dashboard",
                priority=1,
                is_sent=False,
                sent_at=None,
                is_clicked=False,
                clicked_at=None,
                is_dismissed=False,
                dismissed_at=None,
                created_at=datetime.now()
            ))
        
        return nudges
    
    def _save_client_nudge(self, nudge: ClientNudge):
        """Save client nudge to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO client_nudges 
            (nudge_id, client_id, nudge_type, title, message, action_url, priority,
            is_sent, sent_at, is_clicked, clicked_at, is_dismissed, dismissed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nudge.nudge_id,
            nudge.client_id,
            nudge.nudge_type.value,
            nudge.title,
            nudge.message,
            nudge.action_url,
            nudge.priority,
            1 if nudge.is_sent else 0,
            nudge.sent_at.isoformat() if nudge.sent_at else None,
            1 if nudge.is_clicked else 0,
            nudge.clicked_at.isoformat() if nudge.clicked_at else None,
            1 if nudge.is_dismissed else 0,
            nudge.dismissed_at.isoformat() if nudge.dismissed_at else None,
            nudge.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_client_nudges(self, client_id: str) -> List[ClientNudge]:
        """Get nudges for a client"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM client_nudges 
            WHERE client_id = ? AND is_dismissed = 0
            ORDER BY priority DESC, created_at DESC
        ''', (client_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        nudges = []
        for result in results:
            nudge_id, client_id, nudge_type, title, message, action_url, priority, is_sent, sent_at, is_clicked, clicked_at, is_dismissed, dismissed_at, created_at = result
            
            nudges.append(ClientNudge(
                nudge_id=nudge_id,
                client_id=client_id,
                nudge_type=NudgeType(nudge_type),
                title=title,
                message=message,
                action_url=action_url,
                priority=priority,
                is_sent=bool(is_sent),
                sent_at=datetime.fromisoformat(sent_at) if sent_at else None,
                is_clicked=bool(is_clicked),
                clicked_at=datetime.fromisoformat(clicked_at) if clicked_at else None,
                is_dismissed=bool(is_dismissed),
                dismissed_at=datetime.fromisoformat(dismissed_at) if dismissed_at else None,
                created_at=datetime.fromisoformat(created_at)
            ))
        
        return nudges
    
    def _predict_churn(self):
        """Predict churn for all clients"""
        for client_id, profile in self.client_profiles.items():
            if profile.stage != ClientStage.CHURNED:
                churn_probability = self._calculate_churn_probability(profile)
                risk_factors = self._identify_risk_factors(profile)
                recommended_actions = self._generate_recommended_actions(profile, risk_factors)
                
                # Update profile
                profile.churn_risk_score = churn_probability
                profile.updated_at = datetime.now()
                self._save_client_profile(profile)
                
                # Save prediction
                prediction = ChurnPrediction(
                    prediction_id=f"pred_{int(time.time())}_{client_id}",
                    client_id=client_id,
                    churn_probability=churn_probability,
                    risk_factors=risk_factors,
                    recommended_actions=recommended_actions,
                    prediction_date=datetime.now(),
                    actual_churn_date=None,
                    is_accurate=None
                )
                
                self._save_churn_prediction(prediction)
    
    def _calculate_churn_probability(self, profile: ClientProfile) -> float:
        """Calculate churn probability for a client"""
        probability = 0.0
        
        # Days since last login
        days_since_last_login = (datetime.now() - profile.last_login).days
        if days_since_last_login > 30:
            probability += 0.4
        elif days_since_last_login > 14:
            probability += 0.2
        elif days_since_last_login > 7:
            probability += 0.1
        
        # Low usage time
        if profile.total_usage_time < 100:
            probability += 0.2
        
        # No systems created
        if profile.systems_created == 0:
            probability += 0.3
        
        # Support tickets (high number might indicate dissatisfaction)
        if profile.support_tickets > 5:
            probability += 0.1
        
        # Low satisfaction score
        if profile.satisfaction_score and profile.satisfaction_score < 3.0:
            probability += 0.2
        
        return min(probability, 1.0)
    
    def _identify_risk_factors(self, profile: ClientProfile) -> List[str]:
        """Identify risk factors for a client"""
        risk_factors = []
        
        days_since_last_login = (datetime.now() - profile.last_login).days
        
        if days_since_last_login > 14:
            risk_factors.append("inactive_user")
        
        if profile.total_usage_time < 100:
            risk_factors.append("low_engagement")
        
        if profile.systems_created == 0:
            risk_factors.append("no_systems_created")
        
        if profile.support_tickets > 5:
            risk_factors.append("high_support_volume")
        
        if profile.satisfaction_score and profile.satisfaction_score < 3.0:
            risk_factors.append("low_satisfaction")
        
        if not profile.onboarding_completed:
            risk_factors.append("incomplete_onboarding")
        
        return risk_factors
    
    def _generate_recommended_actions(self, profile: ClientProfile, risk_factors: List[str]) -> List[str]:
        """Generate recommended actions to prevent churn"""
        actions = []
        
        if "inactive_user" in risk_factors:
            actions.append("Send re-engagement email campaign")
            actions.append("Offer personalized onboarding session")
        
        if "low_engagement" in risk_factors:
            actions.append("Highlight key features and use cases")
            actions.append("Provide tutorial videos and documentation")
        
        if "no_systems_created" in risk_factors:
            actions.append("Offer guided system creation workshop")
            actions.append("Provide template library access")
        
        if "high_support_volume" in risk_factors:
            actions.append("Proactive support outreach")
            actions.append("Feature training session")
        
        if "low_satisfaction" in risk_factors:
            actions.append("Customer success manager assignment")
            actions.append("Feedback collection and improvement plan")
        
        if "incomplete_onboarding" in risk_factors:
            actions.append("Complete onboarding checklist")
            actions.append("First system build assistance")
        
        return actions
    
    def _save_churn_prediction(self, prediction: ChurnPrediction):
        """Save churn prediction to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO churn_predictions 
            (prediction_id, client_id, churn_probability, risk_factors, recommended_actions,
            prediction_date, actual_churn_date, is_accurate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            prediction.prediction_id,
            prediction.client_id,
            prediction.churn_probability,
            json.dumps(prediction.risk_factors),
            json.dumps(prediction.recommended_actions),
            prediction.prediction_date.isoformat(),
            prediction.actual_churn_date.isoformat() if prediction.actual_churn_date else None,
            prediction.is_accurate
        ))
        
        conn.commit()
        conn.close()
    
    def get_churn_score(self, client_id: str) -> Optional[float]:
        """Get churn risk score for a client"""
        if client_id in self.client_profiles:
            return self.client_profiles[client_id].churn_risk_score
        return None
    
    def _send_email_triggers(self):
        """Send email triggers based on client status"""
        for client_id, profile in self.client_profiles.items():
            if profile.stage == ClientStage.NOT_LAUNCHED and not profile.onboarding_completed:
                self._create_email_campaign(client_id, EmailTrigger.ONBOARDING_REMINDER)
            
            elif profile.stage == ClientStage.AT_RISK and profile.churn_risk_score > 0.7:
                self._create_email_campaign(client_id, EmailTrigger.CHURN_WARNING)
            
            elif profile.stage == ClientStage.POWER_USER:
                self._create_email_campaign(client_id, EmailTrigger.SUCCESS_STORY)
    
    def _create_email_campaign(self, client_id: str, trigger_type: EmailTrigger):
        """Create email campaign for a client"""
        campaign_id = f"email_{int(time.time())}_{client_id}"
        
        # Generate email content based on trigger type
        subject, content = self._generate_email_content(trigger_type, self.client_profiles[client_id])
        
        campaign = EmailCampaign(
            campaign_id=campaign_id,
            trigger_type=trigger_type,
            client_id=client_id,
            subject=subject,
            content=content,
            is_sent=False,
            sent_at=None,
            is_opened=False,
            opened_at=None,
            is_clicked=False,
            clicked_at=None,
            created_at=datetime.now()
        )
        
        self._save_email_campaign(campaign)
    
    def _generate_email_content(self, trigger_type: EmailTrigger, profile: ClientProfile) -> Tuple[str, str]:
        """Generate email content based on trigger type"""
        if trigger_type == EmailTrigger.ONBOARDING_REMINDER:
            subject = "Complete Your System Builder Setup"
            content = f"""
Hi there!

We noticed you haven't completed your setup yet. Let's get you building amazing systems in just a few minutes!

Your personalized onboarding checklist:
- Complete your first system build
- Explore our template library
- Set up your first deployment

Get started here: [Onboarding Link]

Best regards,
The System Builder Team
            """
        
        elif trigger_type == EmailTrigger.CHURN_WARNING:
            subject = "We'd Love to Help You Succeed"
            content = f"""
Hi there!

We want to make sure you're getting the most out of System Builder. We've noticed you haven't been active lately, and we'd love to help you get back on track.

Here are some resources that might help:
- Quick start guide
- Feature tutorials
- Support team contact

Let's chat: [Support Link]

Best regards,
The System Builder Team
            """
        
        elif trigger_type == EmailTrigger.SUCCESS_STORY:
            subject = "You're Crushing It! 🚀"
            content = f"""
Hi there!

Congratulations! You've created {profile.systems_created} systems and deployed {profile.systems_deployed} of them. You're a power user!

Keep up the amazing work and consider exploring our advanced features:
- Custom LLM training
- Advanced integrations
- White-label solutions

Explore more: [Advanced Features]

Best regards,
The System Builder Team
            """
        
        else:
            subject = "System Builder Update"
            content = "Thank you for using System Builder!"
        
        return subject, content
    
    def _save_email_campaign(self, campaign: EmailCampaign):
        """Save email campaign to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO email_campaigns 
            (campaign_id, trigger_type, client_id, subject, content, is_sent, sent_at,
            is_opened, opened_at, is_clicked, clicked_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            campaign.campaign_id,
            campaign.trigger_type.value,
            campaign.client_id,
            campaign.subject,
            campaign.content,
            1 if campaign.is_sent else 0,
            campaign.sent_at.isoformat() if campaign.sent_at else None,
            1 if campaign.is_opened else 0,
            campaign.opened_at.isoformat() if campaign.opened_at else None,
            1 if campaign.is_clicked else 0,
            campaign.clicked_at.isoformat() if campaign.clicked_at else None,
            campaign.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def trigger_email(self, client_id: str, trigger_type: EmailTrigger) -> bool:
        """Manually trigger an email for a client"""
        try:
            if client_id in self.client_profiles:
                self._create_email_campaign(client_id, trigger_type)
                return True
            return False
        except Exception as e:
            logger.error(f"Error triggering email: {e}")
            return False
    
    def collect_feedback(self, client_id: str, feedback_type: str, feedback_data: Dict[str, Any]):
        """Collect feedback from clients"""
        try:
            if client_id in self.client_profiles:
                profile = self.client_profiles[client_id]
                
                # Update satisfaction score if provided
                if "satisfaction_score" in feedback_data:
                    profile.satisfaction_score = feedback_data["satisfaction_score"]
                
                # Update support tickets count
                if feedback_type == "support_request":
                    profile.support_tickets += 1
                
                profile.updated_at = datetime.now()
                self._save_client_profile(profile)
                
                # Feed to LLM factory for learning if available
                if self.llm_factory:
                    self._feed_feedback_to_llm(client_id, feedback_type, feedback_data)
                    
        except Exception as e:
            logger.error(f"Error collecting feedback: {e}")
    
    def _feed_feedback_to_llm(self, client_id: str, feedback_type: str, feedback_data: Dict[str, Any]):
        """Feed feedback to LLM factory for learning"""
        try:
            # Create training data
            training_data = {
                "type": "client_feedback",
                "client_id": client_id,
                "feedback_type": feedback_type,
                "feedback_data": feedback_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to LLM factory training dataset
            if hasattr(self.llm_factory, 'add_training_data'):
                self.llm_factory.add_training_data(training_data)
                
        except Exception as e:
            logger.error(f"Error feeding feedback to LLM: {e}")
    
    def get_client_success_statistics(self) -> Dict[str, Any]:
        """Get client success statistics"""
        total_clients = len(self.client_profiles)
        
        stage_counts = {}
        for stage in ClientStage:
            stage_counts[stage.value] = 0
        
        total_revenue = 0.0
        total_systems_created = 0
        total_systems_deployed = 0
        avg_satisfaction = 0.0
        satisfaction_count = 0
        
        for profile in self.client_profiles.values():
            stage_counts[profile.stage.value] += 1
            total_revenue += profile.revenue_generated
            total_systems_created += profile.systems_created
            total_systems_deployed += profile.systems_deployed
            
            if profile.satisfaction_score:
                avg_satisfaction += profile.satisfaction_score
                satisfaction_count += 1
        
        if satisfaction_count > 0:
            avg_satisfaction /= satisfaction_count
        
        return {
            "total_clients": total_clients,
            "stage_distribution": stage_counts,
            "total_revenue": total_revenue,
            "total_systems_created": total_systems_created,
            "total_systems_deployed": total_systems_deployed,
            "average_satisfaction": round(avg_satisfaction, 2),
            "deployment_rate": (total_systems_deployed / total_systems_created * 100) if total_systems_created > 0 else 0
        }
