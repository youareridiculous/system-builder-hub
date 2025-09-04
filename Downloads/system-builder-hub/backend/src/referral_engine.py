"""
Viral Loops & Referral System
Priority 11: Autonomous Growth Engine

Features:
- Unique referral links per user/org
- Incentive rules (discounts, commission, credit)
- Track installs/sales from referrals
- Referral leaderboard + analytics
- Redeem rewards / payouts
"""

import sqlite3
import json
import secrets as py_secrets
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Tuple
import threading
import time


class ReferralStatus(Enum):
    """Referral status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RewardType(Enum):
    """Reward type enumeration"""
    DISCOUNT = "discount"
    COMMISSION = "commission"
    CREDIT = "credit"
    FEATURE_ACCESS = "feature_access"
    BADGE = "badge"


class ReferralTier(Enum):
    """Referral tier enumeration"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


@dataclass
class ReferralCode:
    """Referral code data structure"""
    code_id: str
    user_id: str
    organization_id: str
    code: str
    tier: ReferralTier
    max_uses: int
    current_uses: int
    reward_type: RewardType
    reward_value: float
    reward_description: str
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class Referral:
    """Referral data structure"""
    referral_id: str
    referrer_id: str
    referrer_code: str
    referred_email: str
    referred_user_id: Optional[str]
    status: ReferralStatus
    reward_earned: float
    reward_paid: float
    conversion_value: float
    conversion_type: str  # "signup", "purchase", "upgrade"
    created_at: datetime
    converted_at: Optional[datetime]
    expires_at: datetime


@dataclass
class ReferralAnalytics:
    """Referral analytics data structure"""
    user_id: str
    total_referrals: int
    active_referrals: int
    completed_referrals: int
    total_reward_earned: float
    total_reward_paid: float
    conversion_rate: float
    average_conversion_value: float
    tier_level: ReferralTier
    rank_position: int


@dataclass
class RewardPayout:
    """Reward payout data structure"""
    payout_id: str
    user_id: str
    amount: float
    reward_type: RewardType
    status: str  # "pending", "processed", "failed"
    payment_method: str
    payment_details: Dict
    created_at: datetime
    processed_at: Optional[datetime]


class ReferralEngine:
    """Viral Loops & Referral System"""
    
    def __init__(self, base_dir: str, access_control, system_delivery, llm_factory):
        self.base_dir = base_dir
        self.access_control = access_control
        self.system_delivery = system_delivery
        self.llm_factory = llm_factory
        self.db_path = f"{base_dir}/referral_engine.db"
        self._init_database()
        
        # Start analytics loop
        self.analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        self.analytics_thread.start()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Referral codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_codes (
                code_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                tier TEXT NOT NULL,
                max_uses INTEGER DEFAULT -1,
                current_uses INTEGER DEFAULT 0,
                reward_type TEXT NOT NULL,
                reward_value REAL NOT NULL,
                reward_description TEXT,
                expires_at TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Referrals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                referral_id TEXT PRIMARY KEY,
                referrer_id TEXT NOT NULL,
                referrer_code TEXT NOT NULL,
                referred_email TEXT NOT NULL,
                referred_user_id TEXT,
                status TEXT NOT NULL,
                reward_earned REAL DEFAULT 0,
                reward_paid REAL DEFAULT 0,
                conversion_value REAL DEFAULT 0,
                conversion_type TEXT,
                created_at TEXT NOT NULL,
                converted_at TEXT,
                expires_at TEXT NOT NULL
            )
        ''')
        
        # Reward payouts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reward_payouts (
                payout_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                reward_type TEXT NOT NULL,
                status TEXT NOT NULL,
                payment_method TEXT,
                payment_details TEXT,
                created_at TEXT NOT NULL,
                processed_at TEXT
            )
        ''')
        
        # Analytics cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_analytics (
                user_id TEXT PRIMARY KEY,
                total_referrals INTEGER DEFAULT 0,
                active_referrals INTEGER DEFAULT 0,
                completed_referrals INTEGER DEFAULT 0,
                total_reward_earned REAL DEFAULT 0,
                total_reward_paid REAL DEFAULT 0,
                conversion_rate REAL DEFAULT 0,
                average_conversion_value REAL DEFAULT 0,
                tier_level TEXT,
                rank_position INTEGER DEFAULT 0,
                last_updated TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_referral_code(self, user_id: str, organization_id: str, 
                             reward_type: RewardType, reward_value: float,
                             max_uses: int = -1, expires_days: int = 365) -> ReferralCode:
        """Generate a unique referral code for a user"""
        # Generate unique code
        code = self._generate_unique_code()
        
        # Determine tier based on user's referral history
        tier = self._determine_user_tier(user_id)
        
        # Calculate reward based on tier
        adjusted_reward = self._calculate_tier_reward(reward_value, tier)
        
        # Set expiration
        expires_at = datetime.now() + timedelta(days=expires_days) if expires_days > 0 else None
        
        # Create referral code
        referral_code = ReferralCode(
            code_id=py_secrets.token_urlsafe(16),
            user_id=user_id,
            organization_id=organization_id,
            code=code,
            tier=tier,
            max_uses=max_uses,
            current_uses=0,
            reward_type=reward_type,
            reward_value=adjusted_reward,
            reward_description=self._generate_reward_description(reward_type, adjusted_reward),
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save to database
        self._save_referral_code(referral_code)
        
        return referral_code
    
    def _generate_unique_code(self) -> str:
        """Generate a unique referral code"""
        while True:
            # Generate 8-character alphanumeric code
            code = ''.join(py_secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
            
            # Check if code exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM referral_codes WHERE code = ?", (code,))
            if cursor.fetchone()[0] == 0:
                conn.close()
                return code
            conn.close()
    
    def _determine_user_tier(self, user_id: str) -> ReferralTier:
        """Determine user's referral tier based on history"""
        analytics = self.get_user_analytics(user_id)
        
        if analytics.total_referrals >= 50:
            return ReferralTier.PLATINUM
        elif analytics.total_referrals >= 25:
            return ReferralTier.GOLD
        elif analytics.total_referrals >= 10:
            return ReferralTier.SILVER
        else:
            return ReferralTier.BRONZE
    
    def _calculate_tier_reward(self, base_reward: float, tier: ReferralTier) -> float:
        """Calculate reward based on tier multiplier"""
        multipliers = {
            ReferralTier.BRONZE: 1.0,
            ReferralTier.SILVER: 1.2,
            ReferralTier.GOLD: 1.5,
            ReferralTier.PLATINUM: 2.0
        }
        return base_reward * multipliers.get(tier, 1.0)
    
    def _generate_reward_description(self, reward_type: RewardType, value: float) -> str:
        """Generate human-readable reward description"""
        if reward_type == RewardType.DISCOUNT:
            return f"{value}% discount on next purchase"
        elif reward_type == RewardType.COMMISSION:
            return f"${value} commission per successful referral"
        elif reward_type == RewardType.CREDIT:
            return f"${value} platform credit"
        elif reward_type == RewardType.FEATURE_ACCESS:
            return f"Access to premium features for {value} days"
        else:
            return f"Special reward: {value}"
    
    def _save_referral_code(self, referral_code: ReferralCode):
        """Save referral code to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO referral_codes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            referral_code.code_id,
            referral_code.user_id,
            referral_code.organization_id,
            referral_code.code,
            referral_code.tier.value,
            referral_code.max_uses,
            referral_code.current_uses,
            referral_code.reward_type.value,
            referral_code.reward_value,
            referral_code.reward_description,
            referral_code.expires_at.isoformat() if referral_code.expires_at else None,
            referral_code.is_active,
            referral_code.created_at.isoformat(),
            referral_code.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def process_referral(self, code: str, referred_email: str, 
                        referred_user_id: Optional[str] = None) -> Referral:
        """Process a referral using a referral code"""
        # Get referral code
        referral_code = self.get_referral_code(code)
        if not referral_code:
            raise ValueError("Invalid referral code")
        
        if not referral_code.is_active:
            raise ValueError("Referral code is inactive")
        
        if referral_code.expires_at and referral_code.expires_at < datetime.now():
            raise ValueError("Referral code has expired")
        
        if referral_code.max_uses > 0 and referral_code.current_uses >= referral_code.max_uses:
            raise ValueError("Referral code usage limit reached")
        
        # Check if email already referred
        if self._is_email_already_referred(referred_email):
            raise ValueError("Email already referred")
        
        # Create referral
        referral = Referral(
            referral_id=py_secrets.token_urlsafe(16),
            referrer_id=referral_code.user_id,
            referrer_code=code,
            referred_email=referred_email,
            referred_user_id=referred_user_id,
            status=ReferralStatus.PENDING,
            reward_earned=0,
            reward_paid=0,
            conversion_value=0,
            conversion_type=None,
            created_at=datetime.now(),
            converted_at=None,
            expires_at=datetime.now() + timedelta(days=30)  # 30 days to convert
        )
        
        # Save referral
        self._save_referral(referral)
        
        # Update code usage
        self._increment_code_usage(code)
        
        return referral
    
    def get_referral_code(self, code: str) -> Optional[ReferralCode]:
        """Get referral code by code string"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM referral_codes WHERE code = ?
        ''', (code,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_referral_code(row)
        return None
    
    def _row_to_referral_code(self, row) -> ReferralCode:
        """Convert database row to ReferralCode object"""
        return ReferralCode(
            code_id=row[0],
            user_id=row[1],
            organization_id=row[2],
            code=row[3],
            tier=ReferralTier(row[4]),
            max_uses=row[5],
            current_uses=row[6],
            reward_type=RewardType(row[7]),
            reward_value=row[8],
            reward_description=row[9],
            expires_at=datetime.fromisoformat(row[10]) if row[10] else None,
            is_active=bool(row[11]),
            created_at=datetime.fromisoformat(row[12]),
            updated_at=datetime.fromisoformat(row[13])
        )
    
    def _is_email_already_referred(self, email: str) -> bool:
        """Check if email has already been referred"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM referrals WHERE referred_email = ?
        ''', (email,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def _save_referral(self, referral: Referral):
        """Save referral to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO referrals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            referral.referral_id,
            referral.referrer_id,
            referral.referrer_code,
            referral.referred_email,
            referral.referred_user_id,
            referral.status.value,
            referral.reward_earned,
            referral.reward_paid,
            referral.conversion_value,
            referral.conversion_type,
            referral.created_at.isoformat(),
            referral.converted_at.isoformat() if referral.converted_at else None,
            referral.expires_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _increment_code_usage(self, code: str):
        """Increment referral code usage count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE referral_codes 
            SET current_uses = current_uses + 1, updated_at = ?
            WHERE code = ?
        ''', (datetime.now().isoformat(), code))
        
        conn.commit()
        conn.close()
    
    def convert_referral(self, referral_id: str, conversion_type: str, 
                        conversion_value: float = 0) -> Referral:
        """Convert a referral to completed status"""
        # Get referral
        referral = self.get_referral(referral_id)
        if not referral:
            raise ValueError("Referral not found")
        
        if referral.status != ReferralStatus.PENDING:
            raise ValueError("Referral already converted or expired")
        
        # Calculate reward
        referral_code = self.get_referral_code(referral.referrer_code)
        reward_earned = self._calculate_conversion_reward(referral_code, conversion_value)
        
        # Update referral
        referral.status = ReferralStatus.COMPLETED
        referral.reward_earned = reward_earned
        referral.conversion_value = conversion_value
        referral.conversion_type = conversion_type
        referral.converted_at = datetime.now()
        
        # Save updated referral
        self._update_referral(referral)
        
        # Update analytics
        self._update_user_analytics(referral.referrer_id)
        
        return referral
    
    def get_referral(self, referral_id: str) -> Optional[Referral]:
        """Get referral by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM referrals WHERE referral_id = ?
        ''', (referral_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_referral(row)
        return None
    
    def _row_to_referral(self, row) -> Referral:
        """Convert database row to Referral object"""
        return Referral(
            referral_id=row[0],
            referrer_id=row[1],
            referrer_code=row[2],
            referred_email=row[3],
            referred_user_id=row[4],
            status=ReferralStatus(row[5]),
            reward_earned=row[6],
            reward_paid=row[7],
            conversion_value=row[8],
            conversion_type=row[9],
            created_at=datetime.fromisoformat(row[10]),
            converted_at=datetime.fromisoformat(row[11]) if row[11] else None,
            expires_at=datetime.fromisoformat(row[12])
        )
    
    def _calculate_conversion_reward(self, referral_code: ReferralCode, 
                                   conversion_value: float) -> float:
        """Calculate reward for conversion"""
        if referral_code.reward_type == RewardType.COMMISSION:
            return conversion_value * (referral_code.reward_value / 100)
        elif referral_code.reward_type == RewardType.CREDIT:
            return referral_code.reward_value
        else:
            return referral_code.reward_value
    
    def _update_referral(self, referral: Referral):
        """Update referral in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE referrals 
            SET status = ?, reward_earned = ?, conversion_value = ?, 
                conversion_type = ?, converted_at = ?
            WHERE referral_id = ?
        ''', (
            referral.status.value,
            referral.reward_earned,
            referral.conversion_value,
            referral.conversion_type,
            referral.converted_at.isoformat() if referral.converted_at else None,
            referral.referral_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_analytics(self, user_id: str) -> ReferralAnalytics:
        """Get referral analytics for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM referral_analytics WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_analytics(row)
        else:
            # Create default analytics
            return ReferralAnalytics(
                user_id=user_id,
                total_referrals=0,
                active_referrals=0,
                completed_referrals=0,
                total_reward_earned=0,
                total_reward_paid=0,
                conversion_rate=0,
                average_conversion_value=0,
                tier_level=ReferralTier.BRONZE,
                rank_position=0
            )
    
    def _row_to_analytics(self, row) -> ReferralAnalytics:
        """Convert database row to ReferralAnalytics object"""
        return ReferralAnalytics(
            user_id=row[0],
            total_referrals=row[1],
            active_referrals=row[2],
            completed_referrals=row[3],
            total_reward_earned=row[4],
            total_reward_paid=row[5],
            conversion_rate=row[6],
            average_conversion_value=row[7],
            tier_level=ReferralTier(row[8]) if row[8] else ReferralTier.BRONZE,
            rank_position=row[9]
        )
    
    def _update_user_analytics(self, user_id: str):
        """Update user analytics"""
        # Calculate analytics from referrals
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get referral counts
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(reward_earned) as total_earned,
                SUM(reward_paid) as total_paid,
                AVG(conversion_value) as avg_value
            FROM referrals 
            WHERE referrer_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        total_referrals = row[0] or 0
        active_referrals = row[1] or 0
        completed_referrals = row[2] or 0
        total_reward_earned = row[3] or 0
        total_reward_paid = row[4] or 0
        average_conversion_value = row[5] or 0
        
        conversion_rate = (completed_referrals / total_referrals * 100) if total_referrals > 0 else 0
        tier_level = self._determine_user_tier(user_id)
        
        # Save analytics
        self._save_analytics(user_id, total_referrals, active_referrals, completed_referrals,
                           total_reward_earned, total_reward_paid, conversion_rate,
                           average_conversion_value, tier_level)
    
    def _save_analytics(self, user_id: str, total_referrals: int, active_referrals: int,
                       completed_referrals: int, total_reward_earned: float,
                       total_reward_paid: float, conversion_rate: float,
                       average_conversion_value: float, tier_level: ReferralTier):
        """Save analytics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO referral_analytics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            total_referrals,
            active_referrals,
            completed_referrals,
            total_reward_earned,
            total_reward_paid,
            conversion_rate,
            average_conversion_value,
            tier_level.value,
            0,  # rank_position will be updated separately
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_leaderboard(self, limit: int = 50) -> List[ReferralAnalytics]:
        """Get referral leaderboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM referral_analytics 
            ORDER BY total_reward_earned DESC, completed_referrals DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        analytics = [self._row_to_analytics(row) for row in rows]
        
        # Update rank positions
        for i, analytic in enumerate(analytics):
            analytic.rank_position = i + 1
        
        return analytics
    
    def request_payout(self, user_id: str, amount: float, 
                      payment_method: str, payment_details: Dict) -> RewardPayout:
        """Request a reward payout"""
        analytics = self.get_user_analytics(user_id)
        
        if amount > analytics.total_reward_earned - analytics.total_reward_paid:
            raise ValueError("Insufficient reward balance")
        
        payout = RewardPayout(
            payout_id=py_secrets.token_urlsafe(16),
            user_id=user_id,
            amount=amount,
            reward_type=RewardType.COMMISSION,  # Default to commission
            status="pending",
            payment_method=payment_method,
            payment_details=payment_details,
            created_at=datetime.now(),
            processed_at=None
        )
        
        # Save payout
        self._save_payout(payout)
        
        return payout
    
    def _save_payout(self, payout: RewardPayout):
        """Save payout to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reward_payouts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payout.payout_id,
            payout.user_id,
            payout.amount,
            payout.reward_type.value,
            payout.status,
            payout.payment_method,
            json.dumps(payout.payment_details),
            payout.created_at.isoformat(),
            payout.processed_at.isoformat() if payout.processed_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_referrals(self, user_id: str, status: Optional[ReferralStatus] = None) -> List[Referral]:
        """Get referrals for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM referrals 
                WHERE referrer_id = ? AND status = ?
                ORDER BY created_at DESC
            ''', (user_id, status.value))
        else:
            cursor.execute('''
                SELECT * FROM referrals 
                WHERE referrer_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_referral(row) for row in rows]
    
    def get_user_codes(self, user_id: str) -> List[ReferralCode]:
        """Get referral codes for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM referral_codes 
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY created_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_referral_code(row) for row in rows]
    
    def _analytics_loop(self):
        """Background analytics processing loop"""
        while True:
            try:
                # Update all user analytics
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT DISTINCT user_id FROM referral_codes')
                user_ids = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                for user_id in user_ids:
                    self._update_user_analytics(user_id)
                
                # Update leaderboard rankings
                self._update_leaderboard_rankings()
                
                # Clean up expired referrals
                self._cleanup_expired_referrals()
                
                time.sleep(3600)  # Run every hour
                
            except Exception as e:
                print(f"Error in referral analytics loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _update_leaderboard_rankings(self):
        """Update leaderboard rankings"""
        leaderboard = self.get_leaderboard(1000)  # Get all users
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for i, analytic in enumerate(leaderboard):
            cursor.execute('''
                UPDATE referral_analytics 
                SET rank_position = ?
                WHERE user_id = ?
            ''', (i + 1, analytic.user_id))
        
        conn.commit()
        conn.close()
    
    def _cleanup_expired_referrals(self):
        """Clean up expired referrals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE referrals 
            SET status = 'expired'
            WHERE status = 'pending' AND expires_at < ?
        ''', (datetime.now().isoformat(),))
        
        conn.commit()
        conn.close()
    
    def get_referral_statistics(self) -> Dict:
        """Get overall referral statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_codes,
                SUM(current_uses) as total_uses,
                COUNT(DISTINCT user_id) as active_users
            FROM referral_codes 
            WHERE is_active = TRUE
        ''')
        
        code_stats = cursor.fetchone()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_referrals,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(reward_earned) as total_earned,
                AVG(conversion_value) as avg_value
            FROM referrals
        ''')
        
        referral_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_codes": code_stats[0] or 0,
            "total_uses": code_stats[1] or 0,
            "active_users": code_stats[2] or 0,
            "total_referrals": referral_stats[0] or 0,
            "completed_referrals": referral_stats[1] or 0,
            "total_reward_earned": referral_stats[2] or 0,
            "average_conversion_value": referral_stats[3] or 0,
            "conversion_rate": (referral_stats[1] / referral_stats[0] * 100) if referral_stats[0] > 0 else 0
        }
