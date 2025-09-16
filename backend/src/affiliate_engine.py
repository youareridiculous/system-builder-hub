import sqlite3
import json
import threading
import uuid
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
import os

class ReferralStatus(Enum):
    PENDING = "pending"
    CONVERTED = "converted"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class PayoutStatus(Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CommissionType(Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"

@dataclass
class ReferralCode:
    code: str
    referrer_id: str
    referrer_organization_id: str
    referrer_name: str
    commission_rate: float
    commission_type: CommissionType
    max_uses: Optional[int]
    current_uses: int
    expires_at: Optional[str]
    created_at: str
    is_active: bool
    metadata: Dict[str, Any]

@dataclass
class Referral:
    referral_id: str
    code: str
    referrer_id: str
    referrer_organization_id: str
    referred_user_id: str
    referred_organization_id: str
    listing_id: Optional[str]
    purchase_id: Optional[str]
    commission_amount: float
    commission_rate: float
    status: ReferralStatus
    converted_at: Optional[str]
    expires_at: str
    created_at: str
    metadata: Dict[str, Any]

@dataclass
class Payout:
    payout_id: str
    referrer_id: str
    referrer_organization_id: str
    amount: float
    currency: str
    status: PayoutStatus
    payment_method: str
    payment_details: Dict[str, Any]
    processed_at: Optional[str]
    created_at: str
    metadata: Dict[str, Any]

@dataclass
class AffiliateStats:
    referrer_id: str
    total_referrals: int
    total_conversions: int
    total_commission: float
    conversion_rate: float
    average_commission: float
    last_referral_date: Optional[str]
    last_payout_date: Optional[str]

class AffiliateEngine:
    """Affiliate referral and commission tracking system"""
    
    def __init__(self, base_dir: str, agent_marketplace, licensing_module, llm_factory):
        self.base_dir = base_dir
        self.agent_marketplace = agent_marketplace
        self.licensing_module = licensing_module
        self.llm_factory = llm_factory
        
        self.db_path = f"{base_dir}/affiliate_engine.db"
        
        # Initialize database
        self._init_database()
        
        # Background tasks
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def _init_database(self):
        """Initialize affiliate database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create referral codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_codes (
                code TEXT PRIMARY KEY,
                referrer_id TEXT NOT NULL,
                referrer_organization_id TEXT NOT NULL,
                referrer_name TEXT NOT NULL,
                commission_rate REAL NOT NULL,
                commission_type TEXT NOT NULL,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                expires_at TEXT,
                created_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                metadata TEXT
            )
        ''')
        
        # Create referrals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                referral_id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                referrer_id TEXT NOT NULL,
                referrer_organization_id TEXT NOT NULL,
                referred_user_id TEXT NOT NULL,
                referred_organization_id TEXT NOT NULL,
                listing_id TEXT,
                purchase_id TEXT,
                commission_amount REAL DEFAULT 0.0,
                commission_rate REAL NOT NULL,
                status TEXT NOT NULL,
                converted_at TEXT,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (code) REFERENCES referral_codes (code)
            )
        ''')
        
        # Create payouts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payouts (
                payout_id TEXT PRIMARY KEY,
                referrer_id TEXT NOT NULL,
                referrer_organization_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                payment_details TEXT,
                processed_at TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_referral_codes_referrer ON referral_codes (referrer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_referral_codes_active ON referral_codes (is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals (code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals (referrer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_referrer ON payouts (referrer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_status ON payouts (status)')
        
        conn.commit()
        conn.close()
    
    def create_referral_code(self, referrer_id: str, referrer_organization_id: str,
                           referrer_name: str, commission_rate: float = 0.10,
                           commission_type: CommissionType = CommissionType.PERCENTAGE,
                           max_uses: Optional[int] = None,
                           expires_in_days: Optional[int] = 30,
                           custom_code: str = None) -> str:
        """Create a new referral code"""
        # Generate unique code
        if custom_code:
            code = custom_code.upper()
            # Check if code already exists
            if self._code_exists(code):
                raise ValueError("Referral code already exists")
        else:
            code = self._generate_unique_code(referrer_id)
        
        # Set expiration
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
        
        referral_code = ReferralCode(
            code=code,
            referrer_id=referrer_id,
            referrer_organization_id=referrer_organization_id,
            referrer_name=referrer_name,
            commission_rate=commission_rate,
            commission_type=commission_type,
            max_uses=max_uses,
            current_uses=0,
            expires_at=expires_at,
            created_at=datetime.now().isoformat(),
            is_active=True,
            metadata={}
        )
        
        self._save_referral_code(referral_code)
        return code
    
    def _generate_unique_code(self, referrer_id: str) -> str:
        """Generate a unique referral code"""
        base = f"{referrer_id[:4]}{uuid.uuid4().hex[:4]}".upper()
        code = hashlib.md5(base.encode()).hexdigest()[:8].upper()
        
        # Ensure uniqueness
        attempts = 0
        while self._code_exists(code) and attempts < 10:
            code = hashlib.md5(f"{code}{attempts}".encode()).hexdigest()[:8].upper()
            attempts += 1
        
        if attempts >= 10:
            raise ValueError("Unable to generate unique referral code")
        
        return code
    
    def _code_exists(self, code: str) -> bool:
        """Check if referral code exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM referral_codes WHERE code = ?', (code,))
        exists = cursor.fetchone() is not None
        
        conn.close()
        return exists
    
    def _save_referral_code(self, referral_code: ReferralCode):
        """Save referral code to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO referral_codes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            referral_code.code, referral_code.referrer_id,
            referral_code.referrer_organization_id, referral_code.referrer_name,
            referral_code.commission_rate, referral_code.commission_type.value,
            referral_code.max_uses, referral_code.current_uses,
            referral_code.expires_at, referral_code.created_at,
            referral_code.is_active, json.dumps(referral_code.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def get_referral_code(self, code: str) -> Optional[ReferralCode]:
        """Get referral code details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM referral_codes WHERE code = ? AND is_active = TRUE', (code,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_referral_code(row)
    
    def _row_to_referral_code(self, row) -> ReferralCode:
        """Convert database row to ReferralCode"""
        return ReferralCode(
            code=row[0],
            referrer_id=row[1],
            referrer_organization_id=row[2],
            referrer_name=row[3],
            commission_rate=row[4],
            commission_type=CommissionType(row[5]),
            max_uses=row[6],
            current_uses=row[7],
            expires_at=row[8],
            created_at=row[9],
            is_active=bool(row[10]),
            metadata=json.loads(row[11]) if row[11] else {}
        )
    
    def track_referral(self, code: str, referred_user_id: str, referred_organization_id: str,
                      listing_id: str = None) -> str:
        """Track a new referral"""
        referral_code = self.get_referral_code(code)
        if not referral_code:
            raise ValueError("Invalid or inactive referral code")
        
        # Check if code has expired
        if referral_code.expires_at and datetime.fromisoformat(referral_code.expires_at) < datetime.now():
            raise ValueError("Referral code has expired")
        
        # Check if max uses reached
        if referral_code.max_uses and referral_code.current_uses >= referral_code.max_uses:
            raise ValueError("Referral code usage limit reached")
        
        # Create referral record
        referral_id = f"ref_{uuid.uuid4().hex[:8]}"
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()  # 30-day conversion window
        
        referral = Referral(
            referral_id=referral_id,
            code=code,
            referrer_id=referral_code.referrer_id,
            referrer_organization_id=referral_code.referrer_organization_id,
            referred_user_id=referred_user_id,
            referred_organization_id=referred_organization_id,
            listing_id=listing_id,
            purchase_id=None,
            commission_amount=0.0,
            commission_rate=referral_code.commission_rate,
            status=ReferralStatus.PENDING,
            converted_at=None,
            expires_at=expires_at,
            created_at=datetime.now().isoformat(),
            metadata={}
        )
        
        self._save_referral(referral)
        
        # Increment usage count
        self._increment_code_usage(code)
        
        return referral_id
    
    def _save_referral(self, referral: Referral):
        """Save referral to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO referrals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            referral.referral_id, referral.code, referral.referrer_id,
            referral.referrer_organization_id, referral.referred_user_id,
            referral.referred_organization_id, referral.listing_id,
            referral.purchase_id, referral.commission_amount,
            referral.commission_rate, referral.status.value,
            referral.converted_at, referral.expires_at,
            referral.created_at, json.dumps(referral.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _increment_code_usage(self, code: str):
        """Increment usage count for referral code"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE referral_codes SET current_uses = current_uses + 1 WHERE code = ?
        ''', (code,))
        
        conn.commit()
        conn.close()
    
    def track_purchase(self, purchase_id: str, referral_code: str, purchase_amount: float):
        """Track a purchase conversion for a referral"""
        # Find pending referral for this code
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM referrals 
            WHERE code = ? AND status = ? AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (referral_code, ReferralStatus.PENDING.value, datetime.now().isoformat()))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return  # No valid referral found
        
        referral = self._row_to_referral(row)
        
        # Calculate commission
        commission_amount = self._calculate_commission(
            referral.commission_rate, referral.commission_type, purchase_amount
        )
        
        # Update referral
        referral.purchase_id = purchase_id
        referral.commission_amount = commission_amount
        referral.status = ReferralStatus.CONVERTED
        referral.converted_at = datetime.now().isoformat()
        
        self._update_referral(referral)
    
    def _calculate_commission(self, rate: float, commission_type: CommissionType, amount: float) -> float:
        """Calculate commission amount"""
        if commission_type == CommissionType.PERCENTAGE:
            return amount * rate
        elif commission_type == CommissionType.FIXED:
            return rate
        elif commission_type == CommissionType.TIERED:
            # Implement tiered commission logic
            if amount < 100:
                return amount * 0.05
            elif amount < 500:
                return amount * 0.10
            else:
                return amount * 0.15
        return 0.0
    
    def _row_to_referral(self, row) -> Referral:
        """Convert database row to Referral"""
        return Referral(
            referral_id=row[0],
            code=row[1],
            referrer_id=row[2],
            referrer_organization_id=row[3],
            referred_user_id=row[4],
            referred_organization_id=row[5],
            listing_id=row[6],
            purchase_id=row[7],
            commission_amount=row[8],
            commission_rate=row[9],
            status=ReferralStatus(row[10]),
            converted_at=row[11],
            expires_at=row[12],
            created_at=row[13],
            metadata=json.loads(row[14]) if row[14] else {}
        )
    
    def _update_referral(self, referral: Referral):
        """Update referral in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE referrals SET 
                purchase_id = ?, commission_amount = ?, status = ?, converted_at = ?
            WHERE referral_id = ?
        ''', (
            referral.purchase_id, referral.commission_amount,
            referral.status.value, referral.converted_at,
            referral.referral_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_referrer_stats(self, referrer_id: str, organization_id: str = None) -> AffiliateStats:
        """Get affiliate statistics for a referrer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if organization_id:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_referrals,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as conversions,
                    SUM(CASE WHEN status = ? THEN commission_amount ELSE 0 END) as total_commission,
                    MAX(created_at) as last_referral,
                    MAX(converted_at) as last_conversion
                FROM referrals 
                WHERE referrer_id = ? AND referrer_organization_id = ?
            ''', (ReferralStatus.CONVERTED.value, ReferralStatus.CONVERTED.value, referrer_id, organization_id))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_referrals,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as conversions,
                    SUM(CASE WHEN status = ? THEN commission_amount ELSE 0 END) as total_commission,
                    MAX(created_at) as last_referral,
                    MAX(converted_at) as last_conversion
                FROM referrals 
                WHERE referrer_id = ?
            ''', (ReferralStatus.CONVERTED.value, ReferralStatus.CONVERTED.value, referrer_id))
        
        row = cursor.fetchone()
        
        # Get last payout date
        if organization_id:
            cursor.execute('''
                SELECT MAX(processed_at) FROM payouts 
                WHERE referrer_id = ? AND referrer_organization_id = ? AND status = ?
            ''', (referrer_id, organization_id, PayoutStatus.PROCESSED.value))
        else:
            cursor.execute('''
                SELECT MAX(processed_at) FROM payouts 
                WHERE referrer_id = ? AND status = ?
            ''', (referrer_id, PayoutStatus.PROCESSED.value))
        
        last_payout = cursor.fetchone()[0]
        conn.close()
        
        total_referrals = row[0] or 0
        conversions = row[1] or 0
        total_commission = row[2] or 0.0
        conversion_rate = (conversions / total_referrals * 100) if total_referrals > 0 else 0.0
        avg_commission = (total_commission / conversions) if conversions > 0 else 0.0
        
        return AffiliateStats(
            referrer_id=referrer_id,
            total_referrals=total_referrals,
            total_conversions=conversions,
            total_commission=total_commission,
            conversion_rate=conversion_rate,
            average_commission=avg_commission,
            last_referral_date=row[3],
            last_payout_date=last_payout
        )
    
    def get_pending_payouts(self, referrer_id: str, organization_id: str = None) -> List[Referral]:
        """Get pending payouts for a referrer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if organization_id:
            cursor.execute('''
                SELECT * FROM referrals 
                WHERE referrer_id = ? AND referrer_organization_id = ? AND status = ?
                ORDER BY converted_at DESC
            ''', (referrer_id, organization_id, ReferralStatus.CONVERTED.value))
        else:
            cursor.execute('''
                SELECT * FROM referrals 
                WHERE referrer_id = ? AND status = ?
                ORDER BY converted_at DESC
            ''', (referrer_id, ReferralStatus.CONVERTED.value))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_referral(row) for row in rows]
    
    def create_payout(self, referrer_id: str, referrer_organization_id: str,
                     amount: float, payment_method: str = "stripe",
                     payment_details: Dict[str, Any] = None) -> str:
        """Create a payout for a referrer"""
        payout_id = f"payout_{uuid.uuid4().hex[:8]}"
        
        payout = Payout(
            payout_id=payout_id,
            referrer_id=referrer_id,
            referrer_organization_id=referrer_organization_id,
            amount=amount,
            currency="USD",
            status=PayoutStatus.PENDING,
            payment_method=payment_method,
            payment_details=payment_details or {},
            processed_at=None,
            created_at=datetime.now().isoformat(),
            metadata={}
        )
        
        self._save_payout(payout)
        
        # Mark referrals as paid
        self._mark_referrals_paid(referrer_id, referrer_organization_id, payout_id)
        
        return payout_id
    
    def _save_payout(self, payout: Payout):
        """Save payout to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payouts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payout.payout_id, payout.referrer_id, payout.referrer_organization_id,
            payout.amount, payout.currency, payout.status.value,
            payout.payment_method, json.dumps(payout.payment_details),
            payout.processed_at, payout.created_at, json.dumps(payout.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _mark_referrals_paid(self, referrer_id: str, organization_id: str, payout_id: str):
        """Mark referrals as paid"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE referrals SET status = ? 
            WHERE referrer_id = ? AND referrer_organization_id = ? AND status = ?
        ''', (ReferralStatus.PAID.value, referrer_id, organization_id, ReferralStatus.CONVERTED.value))
        
        conn.commit()
        conn.close()
    
    def get_referral_codes_for_user(self, referrer_id: str, organization_id: str = None) -> List[ReferralCode]:
        """Get all referral codes for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if organization_id:
            cursor.execute('''
                SELECT * FROM referral_codes 
                WHERE referrer_id = ? AND referrer_organization_id = ?
                ORDER BY created_at DESC
            ''', (referrer_id, organization_id))
        else:
            cursor.execute('''
                SELECT * FROM referral_codes 
                WHERE referrer_id = ?
                ORDER BY created_at DESC
            ''', (referrer_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_referral_code(row) for row in rows]
    
    def get_affiliate_earnings(self, referrer_id: str, organization_id: str = None,
                             start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get detailed earnings breakdown for affiliate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        conditions = ["referrer_id = ?"]
        params = [referrer_id]
        
        if organization_id:
            conditions.append("referrer_organization_id = ?")
            params.append(organization_id)
        
        if start_date:
            conditions.append("converted_at >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("converted_at <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        
        cursor.execute(f'''
            SELECT 
                listing_id,
                COUNT(*) as conversions,
                SUM(commission_amount) as total_commission,
                AVG(commission_amount) as avg_commission
            FROM referrals 
            WHERE {where_clause} AND status = ?
            GROUP BY listing_id
            ORDER BY total_commission DESC
        ''', params + [ReferralStatus.CONVERTED.value])
        
        earnings_by_listing = []
        for row in cursor.fetchall():
            earnings_by_listing.append({
                "listing_id": row[0],
                "conversions": row[1],
                "total_commission": row[2],
                "avg_commission": row[3]
            })
        
        # Get total earnings
        cursor.execute(f'''
            SELECT SUM(commission_amount) FROM referrals 
            WHERE {where_clause} AND status = ?
        ''', params + [ReferralStatus.CONVERTED.value])
        
        total_earnings = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "total_earnings": total_earnings,
            "earnings_by_listing": earnings_by_listing,
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    def _cleanup_loop(self):
        """Background cleanup of expired referrals"""
        while True:
            try:
                # Clean up expired referrals every hour
                import time
                time.sleep(3600)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Mark expired referrals
                cursor.execute('''
                    UPDATE referrals SET status = ? 
                    WHERE status = ? AND expires_at < ?
                ''', (ReferralStatus.EXPIRED.value, ReferralStatus.PENDING.value, datetime.now().isoformat()))
                
                # Deactivate expired referral codes
                cursor.execute('''
                    UPDATE referral_codes SET is_active = FALSE 
                    WHERE expires_at < ? AND is_active = TRUE
                ''', (datetime.now().isoformat(),))
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                print(f"Affiliate cleanup error: {e}")
                import time
                time.sleep(60)
