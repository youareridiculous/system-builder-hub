import sqlite3
import json
import threading
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
import os

class AdminAction(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    SUSPEND = "suspend"
    FEATURE = "feature"
    UNFEATURE = "unfeature"
    DELETE = "delete"
    WARN = "warn"

class AbuseType(Enum):
    SPAM = "spam"
    COPYRIGHT = "copyright"
    MALWARE = "malware"
    MISLEADING = "misleading"
    INAPPROPRIATE = "inappropriate"
    QUALITY = "quality"
    OTHER = "other"

class TakeRateType(Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"

@dataclass
class AdminAction:
    action_id: str
    admin_id: str
    target_type: str  # listing, user, organization
    target_id: str
    action: AdminAction
    reason: str
    metadata: Dict[str, Any]
    created_at: str

@dataclass
class AbuseReport:
    report_id: str
    reporter_id: str
    listing_id: str
    abuse_type: AbuseType
    description: str
    evidence: List[str]
    status: str  # pending, reviewed, resolved, dismissed
    admin_notes: Optional[str]
    created_at: str
    resolved_at: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class TakeRate:
    take_rate_id: str
    listing_type: str
    price_range_min: float
    price_range_max: float
    take_rate_type: TakeRateType
    take_rate_value: float
    is_active: bool
    created_at: str
    updated_at: str

@dataclass
class FeaturedListing:
    listing_id: str
    featured_at: str
    featured_until: Optional[str]
    position: int
    admin_notes: Optional[str]
    created_at: str

class MarketplaceAdmin:
    """Marketplace administration and moderation system"""
    
    def __init__(self, base_dir: str, agent_marketplace, affiliate_engine, licensing_module, llm_factory):
        self.base_dir = base_dir
        self.agent_marketplace = agent_marketplace
        self.affiliate_engine = affiliate_engine
        self.licensing_module = licensing_module
        self.llm_factory = llm_factory
        
        self.db_path = f"{base_dir}/marketplace_admin.db"
        
        # Initialize database
        self._init_database()
        
        # Background tasks
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def _init_database(self):
        """Initialize admin database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create admin actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                action_id TEXT PRIMARY KEY,
                admin_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create abuse reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS abuse_reports (
                report_id TEXT PRIMARY KEY,
                reporter_id TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                abuse_type TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence TEXT,
                status TEXT NOT NULL,
                admin_notes TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                metadata TEXT
            )
        ''')
        
        # Create take rates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS take_rates (
                take_rate_id TEXT PRIMARY KEY,
                listing_type TEXT NOT NULL,
                price_range_min REAL NOT NULL,
                price_range_max REAL NOT NULL,
                take_rate_type TEXT NOT NULL,
                take_rate_value REAL NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create featured listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS featured_listings (
                listing_id TEXT PRIMARY KEY,
                featured_at TEXT NOT NULL,
                featured_until TEXT,
                position INTEGER NOT NULL,
                admin_notes TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_admin_actions_target ON admin_actions (target_type, target_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_admin_actions_admin ON admin_actions (admin_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_abuse_reports_listing ON abuse_reports (listing_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_abuse_reports_status ON abuse_reports (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_take_rates_active ON take_rates (is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_featured_listings_position ON featured_listings (position)')
        
        conn.commit()
        conn.close()
        
        # Initialize default take rates
        self._init_default_take_rates()
    
    def _init_default_take_rates(self):
        """Initialize default take rates"""
        default_rates = [
            {"listing_type": "agent", "min": 0, "max": 50, "type": TakeRateType.PERCENTAGE, "value": 0.15},
            {"listing_type": "agent", "min": 50, "max": 200, "type": TakeRateType.PERCENTAGE, "value": 0.12},
            {"listing_type": "agent", "min": 200, "max": 1000, "type": TakeRateType.PERCENTAGE, "value": 0.10},
            {"listing_type": "system", "min": 0, "max": 100, "type": TakeRateType.PERCENTAGE, "value": 0.20},
            {"listing_type": "system", "min": 100, "max": 500, "type": TakeRateType.PERCENTAGE, "value": 0.15},
            {"listing_type": "system", "min": 500, "max": 10000, "type": TakeRateType.PERCENTAGE, "value": 0.12},
            {"listing_type": "template", "min": 0, "max": 1000, "type": TakeRateType.PERCENTAGE, "value": 0.10},
        ]
        
        for rate in default_rates:
            self.create_take_rate(
                listing_type=rate["listing_type"],
                price_range_min=rate["min"],
                price_range_max=rate["max"],
                take_rate_type=rate["type"],
                take_rate_value=rate["value"]
            )
    
    def approve_listing(self, listing_id: str, admin_id: str, reason: str = "Approved by admin") -> str:
        """Approve a pending listing"""
        action_id = self._log_admin_action(
            admin_id=admin_id,
            target_type="listing",
            target_id=listing_id,
            action=AdminAction.APPROVE,
            reason=reason
        )
        
        # Update listing status in marketplace
        self._update_listing_status(listing_id, "approved")
        
        return action_id
    
    def reject_listing(self, listing_id: str, admin_id: str, reason: str) -> str:
        """Reject a pending listing"""
        action_id = self._log_admin_action(
            admin_id=admin_id,
            target_type="listing",
            target_id=listing_id,
            action=AdminAction.REJECT,
            reason=reason
        )
        
        # Update listing status in marketplace
        self._update_listing_status(listing_id, "rejected")
        
        return action_id
    
    def suspend_listing(self, listing_id: str, admin_id: str, reason: str, duration_days: int = None) -> str:
        """Suspend a listing"""
        action_id = self._log_admin_action(
            admin_id=admin_id,
            target_type="listing",
            target_id=listing_id,
            action=AdminAction.SUSPEND,
            reason=reason,
            metadata={"duration_days": duration_days}
        )
        
        # Update listing status in marketplace
        self._update_listing_status(listing_id, "suspended")
        
        return action_id
    
    def feature_listing(self, listing_id: str, admin_id: str, position: int = None, 
                       featured_until: str = None, notes: str = None) -> str:
        """Feature a listing"""
        action_id = self._log_admin_action(
            admin_id=admin_id,
            target_type="listing",
            target_id=listing_id,
            action=AdminAction.FEATURE,
            reason="Featured by admin",
            metadata={"position": position, "featured_until": featured_until}
        )
        
        # Add to featured listings
        self._add_featured_listing(listing_id, position, featured_until, notes)
        
        return action_id
    
    def unfeature_listing(self, listing_id: str, admin_id: str, reason: str = "Unfeatured by admin") -> str:
        """Remove listing from featured"""
        action_id = self._log_admin_action(
            admin_id=admin_id,
            target_type="listing",
            target_id=listing_id,
            action=AdminAction.UNFEATURE,
            reason=reason
        )
        
        # Remove from featured listings
        self._remove_featured_listing(listing_id)
        
        return action_id
    
    def _log_admin_action(self, admin_id: str, target_type: str, target_id: str,
                         action: AdminAction, reason: str, metadata: Dict[str, Any] = None) -> str:
        """Log an admin action"""
        action_id = f"action_{uuid.uuid4().hex[:8]}"
        
        admin_action = AdminAction(
            action_id=action_id,
            admin_id=admin_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            reason=reason,
            metadata=metadata or {},
            created_at=datetime.now().isoformat()
        )
        
        self._save_admin_action(admin_action)
        return action_id
    
    def _save_admin_action(self, admin_action: AdminAction):
        """Save admin action to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO admin_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            admin_action.action_id, admin_action.admin_id, admin_action.target_type,
            admin_action.target_id, admin_action.action.value, admin_action.reason,
            json.dumps(admin_action.metadata), admin_action.created_at
        ))
        
        conn.commit()
        conn.close()
    
    def _update_listing_status(self, listing_id: str, status: str):
        """Update listing status in marketplace"""
        # This would update the listing status in the agent_marketplace database
        # For now, we'll assume the marketplace has a method to update status
        pass
    
    def _add_featured_listing(self, listing_id: str, position: int = None, 
                             featured_until: str = None, notes: str = None):
        """Add listing to featured listings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get next position if not specified
        if position is None:
            cursor.execute('SELECT MAX(position) FROM featured_listings')
            max_pos = cursor.fetchone()[0]
            position = (max_pos or 0) + 1
        
        cursor.execute('''
            INSERT OR REPLACE INTO featured_listings VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            listing_id, datetime.now().isoformat(), featured_until,
            position, notes, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _remove_featured_listing(self, listing_id: str):
        """Remove listing from featured listings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM featured_listings WHERE listing_id = ?', (listing_id,))
        
        conn.commit()
        conn.close()
    
    def report_abuse(self, reporter_id: str, listing_id: str, abuse_type: AbuseType,
                    description: str, evidence: List[str] = None) -> str:
        """Report abuse for a listing"""
        report_id = f"report_{uuid.uuid4().hex[:8]}"
        
        abuse_report = AbuseReport(
            report_id=report_id,
            reporter_id=reporter_id,
            listing_id=listing_id,
            abuse_type=abuse_type,
            description=description,
            evidence=evidence or [],
            status="pending",
            admin_notes=None,
            created_at=datetime.now().isoformat(),
            resolved_at=None,
            metadata={}
        )
        
        self._save_abuse_report(abuse_report)
        return report_id
    
    def _save_abuse_report(self, abuse_report: AbuseReport):
        """Save abuse report to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO abuse_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            abuse_report.report_id, abuse_report.reporter_id, abuse_report.listing_id,
            abuse_report.abuse_type.value, abuse_report.description,
            json.dumps(abuse_report.evidence), abuse_report.status,
            abuse_report.admin_notes, abuse_report.created_at,
            abuse_report.resolved_at, json.dumps(abuse_report.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def review_abuse_report(self, report_id: str, admin_id: str, status: str,
                          admin_notes: str = None) -> str:
        """Review an abuse report"""
        action_id = self._log_admin_action(
            admin_id=admin_id,
            target_type="abuse_report",
            target_id=report_id,
            action=AdminAction.WARN,
            reason=f"Abuse report reviewed: {status}",
            metadata={"status": status, "admin_notes": admin_notes}
        )
        
        # Update abuse report status
        self._update_abuse_report_status(report_id, status, admin_notes)
        
        return action_id
    
    def _update_abuse_report_status(self, report_id: str, status: str, admin_notes: str = None):
        """Update abuse report status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE abuse_reports SET status = ?, admin_notes = ?, resolved_at = ?
            WHERE report_id = ?
        ''', (status, admin_notes, datetime.now().isoformat(), report_id))
        
        conn.commit()
        conn.close()
    
    def create_take_rate(self, listing_type: str, price_range_min: float, price_range_max: float,
                        take_rate_type: TakeRateType, take_rate_value: float) -> str:
        """Create a new take rate"""
        take_rate_id = f"take_rate_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        take_rate = TakeRate(
            take_rate_id=take_rate_id,
            listing_type=listing_type,
            price_range_min=price_range_min,
            price_range_max=price_range_max,
            take_rate_type=take_rate_type,
            take_rate_value=take_rate_value,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        self._save_take_rate(take_rate)
        return take_rate_id
    
    def _save_take_rate(self, take_rate: TakeRate):
        """Save take rate to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO take_rates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            take_rate.take_rate_id, take_rate.listing_type, take_rate.price_range_min,
            take_rate.price_range_max, take_rate.take_rate_type.value,
            take_rate.take_rate_value, take_rate.is_active, take_rate.created_at,
            take_rate.updated_at
        ))
        
        conn.commit()
        conn.close()
    
    def get_take_rate(self, listing_type: str, price: float) -> Optional[TakeRate]:
        """Get applicable take rate for a listing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM take_rates 
            WHERE listing_type = ? AND price_range_min <= ? AND price_range_max >= ? AND is_active = TRUE
            ORDER BY take_rate_value ASC
            LIMIT 1
        ''', (listing_type, price, price))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_take_rate(row)
    
    def _row_to_take_rate(self, row) -> TakeRate:
        """Convert database row to TakeRate"""
        return TakeRate(
            take_rate_id=row[0],
            listing_type=row[1],
            price_range_min=row[2],
            price_range_max=row[3],
            take_rate_type=TakeRateType(row[4]),
            take_rate_value=row[5],
            is_active=bool(row[6]),
            created_at=row[7],
            updated_at=row[8]
        )
    
    def calculate_platform_fee(self, listing_type: str, price: float) -> float:
        """Calculate platform fee for a listing"""
        take_rate = self.get_take_rate(listing_type, price)
        if not take_rate:
            return 0.0
        
        if take_rate.take_rate_type == TakeRateType.PERCENTAGE:
            return price * take_rate.take_rate_value
        elif take_rate.take_rate_type == TakeRateType.FIXED:
            return take_rate.take_rate_value
        elif take_rate.take_rate_type == TakeRateType.TIERED:
            # Implement tiered calculation
            if price < 100:
                return price * 0.15
            elif price < 500:
                return price * 0.12
            else:
                return price * 0.10
        
        return 0.0
    
    def get_pending_listings(self) -> List[Dict[str, Any]]:
        """Get listings pending review"""
        # This would query the marketplace for pending listings
        # For now, return placeholder data
        return [
            {
                "listing_id": "listing_123",
                "title": "AI Chat Agent",
                "author_id": "user_456",
                "status": "pending_review",
                "created_at": datetime.now().isoformat(),
                "listing_type": "agent",
                "price": 29.99
            }
        ]
    
    def get_pending_abuse_reports(self) -> List[AbuseReport]:
        """Get pending abuse reports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM abuse_reports 
            WHERE status = 'pending'
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_abuse_report(row) for row in rows]
    
    def _row_to_abuse_report(self, row) -> AbuseReport:
        """Convert database row to AbuseReport"""
        return AbuseReport(
            report_id=row[0],
            reporter_id=row[1],
            listing_id=row[2],
            abuse_type=AbuseType(row[3]),
            description=row[4],
            evidence=json.loads(row[5]) if row[5] else [],
            status=row[6],
            admin_notes=row[7],
            created_at=row[8],
            resolved_at=row[9],
            metadata=json.loads(row[10]) if row[10] else {}
        )
    
    def get_featured_listings(self) -> List[FeaturedListing]:
        """Get featured listings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM featured_listings 
            ORDER BY position ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_featured_listing(row) for row in rows]
    
    def _row_to_featured_listing(self, row) -> FeaturedListing:
        """Convert database row to FeaturedListing"""
        return FeaturedListing(
            listing_id=row[0],
            featured_at=row[1],
            featured_until=row[2],
            position=row[3],
            admin_notes=row[4],
            created_at=row[5]
        )
    
    def get_admin_actions(self, target_type: str = None, target_id: str = None,
                         admin_id: str = None, limit: int = 50) -> List[AdminAction]:
        """Get admin actions with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if target_type:
            conditions.append("target_type = ?")
            params.append(target_type)
        
        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)
        
        if admin_id:
            conditions.append("admin_id = ?")
            params.append(admin_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f'''
            SELECT * FROM admin_actions 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        '''
        
        params.append(limit)
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_admin_action(row) for row in rows]
    
    def _row_to_admin_action(self, row) -> AdminAction:
        """Convert database row to AdminAction"""
        return AdminAction(
            action_id=row[0],
            admin_id=row[1],
            target_type=row[2],
            target_id=row[3],
            action=AdminAction(row[4]),
            reason=row[5],
            metadata=json.loads(row[6]) if row[6] else {},
            created_at=row[7]
        )
    
    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace administration statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Pending listings
        cursor.execute('SELECT COUNT(*) FROM admin_actions WHERE action = ?', (AdminAction.APPROVE.value,))
        approved_count = cursor.fetchone()[0]
        
        # Abuse reports
        cursor.execute('SELECT COUNT(*) FROM abuse_reports WHERE status = ?', ("pending",))
        pending_reports = cursor.fetchone()[0]
        
        # Featured listings
        cursor.execute('SELECT COUNT(*) FROM featured_listings')
        featured_count = cursor.fetchone()[0]
        
        # Recent actions
        cursor.execute('''
            SELECT COUNT(*) FROM admin_actions 
            WHERE created_at >= ?
        ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        recent_actions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "approved_listings": approved_count,
            "pending_abuse_reports": pending_reports,
            "featured_listings": featured_count,
            "recent_admin_actions": recent_actions
        }
    
    def _monitoring_loop(self):
        """Background monitoring and enforcement"""
        while True:
            try:
                # Monitor marketplace every hour
                import time
                time.sleep(3600)
                
                # Check for expired featured listings
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT listing_id FROM featured_listings 
                    WHERE featured_until < ? AND featured_until IS NOT NULL
                ''', (datetime.now().isoformat(),))
                
                expired_featured = cursor.fetchall()
                
                for (listing_id,) in expired_featured:
                    self._remove_featured_listing(listing_id)
                
                conn.close()
                
            except Exception as e:
                print(f"Marketplace admin monitoring error: {e}")
                import time
                time.sleep(60)
