"""
Partner Portal - White-labeled SaaS for agencies and resellers
"""

import json
import secrets as py_secrets
import stripe
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import sqlite3


class PartnerStatus(Enum):
    """Partner status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"


class BillingPlan(Enum):
    """Billing plans"""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class ClientStatus(Enum):
    """Client status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIAL = "trial"
    CANCELLED = "cancelled"


class DeploymentType(Enum):
    """Deployment types"""
    SELF_HOSTED = "self_hosted"
    PARTNER_CLOUD = "partner_cloud"
    CLIENT_INFRASTRUCTURE = "client_infrastructure"


@dataclass
class Partner:
    """Partner entity"""
    partner_id: str
    name: str
    domain: str
    logo_url: str
    primary_color: str
    secondary_color: str
    contact_email: str
    contact_phone: str
    billing_plan: BillingPlan
    status: PartnerStatus
    max_clients: int
    max_systems: int
    revenue_share: float  # Percentage
    stripe_account_id: str
    created_at: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PartnerClient:
    """Partner client entity"""
    client_id: str
    partner_id: str
    name: str
    email: str
    company: str
    status: ClientStatus
    billing_plan: BillingPlan
    monthly_revenue: float
    systems_count: int
    created_at: str = None
    last_login: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PartnerSystem:
    """Partner system entity"""
    system_id: str
    partner_id: str
    client_id: str
    name: str
    description: str
    deployment_type: DeploymentType
    deployment_url: str
    monthly_cost: float
    status: str
    created_at: str = None
    last_updated: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RevenueTransaction:
    """Revenue transaction entity"""
    transaction_id: str
    partner_id: str
    client_id: str
    system_id: str
    amount: float
    partner_share: float
    platform_share: float
    transaction_type: str  # subscription, one_time, refund
    stripe_payment_intent_id: str
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class PartnerAnalytics:
    """Partner analytics data"""
    partner_id: str
    period: str  # daily, weekly, monthly
    total_revenue: float
    partner_share: float
    active_clients: int
    active_systems: int
    new_clients: int
    churned_clients: int
    average_revenue_per_client: float
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class PartnerPortal:
    """Partner portal management system"""

    def __init__(self, base_dir: Path, stripe_secret_key: str = None):
        self.base_dir = base_dir
        self.db_path = base_dir / "partner_portal.db"
        self.partners_dir = base_dir / "partners"
        self.portals_dir = base_dir / "partner_portals"
        
        # Create directories
        self.partners_dir.mkdir(exist_ok=True)
        self.portals_dir.mkdir(exist_ok=True)
        
        # Initialize Stripe
        if stripe_secret_key:
            stripe.api_key = stripe_secret_key
        self.stripe = stripe
        
        # Initialize data storage
        self.partners: Dict[str, Partner] = {}
        self.clients: Dict[str, PartnerClient] = {}
        self.systems: Dict[str, PartnerSystem] = {}
        self.transactions: Dict[str, RevenueTransaction] = {}
        self.analytics: Dict[str, List[PartnerAnalytics]] = {}
        
        self._init_database()
        self._load_data()

    def _init_database(self):
        """Initialize the database with tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Partners table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                partner_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                domain TEXT UNIQUE NOT NULL,
                logo_url TEXT,
                primary_color TEXT,
                secondary_color TEXT,
                contact_email TEXT NOT NULL,
                contact_phone TEXT,
                billing_plan TEXT NOT NULL,
                status TEXT NOT NULL,
                max_clients INTEGER NOT NULL,
                max_systems INTEGER NOT NULL,
                revenue_share REAL NOT NULL,
                stripe_account_id TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # Partner clients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partner_clients (
                client_id TEXT PRIMARY KEY,
                partner_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT,
                status TEXT NOT NULL,
                billing_plan TEXT NOT NULL,
                monthly_revenue REAL DEFAULT 0,
                systems_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login TEXT,
                metadata TEXT,
                FOREIGN KEY (partner_id) REFERENCES partners (partner_id)
            )
        """)

        # Partner systems table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partner_systems (
                system_id TEXT PRIMARY KEY,
                partner_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                deployment_type TEXT NOT NULL,
                deployment_url TEXT,
                monthly_cost REAL DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (partner_id) REFERENCES partners (partner_id),
                FOREIGN KEY (client_id) REFERENCES partner_clients (client_id)
            )
        """)

        # Revenue transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revenue_transactions (
                transaction_id TEXT PRIMARY KEY,
                partner_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                amount REAL NOT NULL,
                partner_share REAL NOT NULL,
                platform_share REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                stripe_payment_intent_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (partner_id) REFERENCES partners (partner_id),
                FOREIGN KEY (client_id) REFERENCES partner_clients (client_id),
                FOREIGN KEY (system_id) REFERENCES partner_systems (system_id)
            )
        """)

        # Partner analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partner_analytics (
                analytics_id TEXT PRIMARY KEY,
                partner_id TEXT NOT NULL,
                period TEXT NOT NULL,
                total_revenue REAL NOT NULL,
                partner_share REAL NOT NULL,
                active_clients INTEGER NOT NULL,
                active_systems INTEGER NOT NULL,
                new_clients INTEGER NOT NULL,
                churned_clients INTEGER NOT NULL,
                average_revenue_per_client REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (partner_id) REFERENCES partners (partner_id)
            )
        """)

        conn.commit()
        conn.close()

    def _load_data(self):
        """Load existing data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load partners
        cursor.execute("SELECT * FROM partners")
        for row in cursor.fetchall():
            partner = Partner(
                partner_id=row[0],
                name=row[1],
                domain=row[2],
                logo_url=row[3],
                primary_color=row[4],
                secondary_color=row[5],
                contact_email=row[6],
                contact_phone=row[7],
                billing_plan=BillingPlan(row[8]),
                status=PartnerStatus(row[9]),
                max_clients=row[10],
                max_systems=row[11],
                revenue_share=row[12],
                stripe_account_id=row[13],
                created_at=row[14],
                metadata=json.loads(row[15]) if row[15] else {}
            )
            self.partners[partner.partner_id] = partner

        # Load clients
        cursor.execute("SELECT * FROM partner_clients")
        for row in cursor.fetchall():
            client = PartnerClient(
                client_id=row[0],
                partner_id=row[1],
                name=row[2],
                email=row[3],
                company=row[4],
                status=ClientStatus(row[5]),
                billing_plan=BillingPlan(row[6]),
                monthly_revenue=row[7],
                systems_count=row[8],
                created_at=row[9],
                last_login=row[10],
                metadata=json.loads(row[11]) if row[11] else {}
            )
            self.clients[client.client_id] = client

        # Load systems
        cursor.execute("SELECT * FROM partner_systems")
        for row in cursor.fetchall():
            system = PartnerSystem(
                system_id=row[0],
                partner_id=row[1],
                client_id=row[2],
                name=row[3],
                description=row[4],
                deployment_type=DeploymentType(row[5]),
                deployment_url=row[6],
                monthly_cost=row[7],
                status=row[8],
                created_at=row[9],
                last_updated=row[10],
                metadata=json.loads(row[11]) if row[11] else {}
            )
            self.systems[system.system_id] = system

        conn.close()

    def create_partner(self, name: str, domain: str, contact_email: str,
                      billing_plan: BillingPlan, revenue_share: float,
                      logo_url: str = None, primary_color: str = "#667eea",
                      secondary_color: str = "#764ba2") -> Partner:
        """Create a new partner"""
        partner_id = f"partner_{py_secrets.token_hex(8)}"
        
        # Set limits based on billing plan
        plan_limits = {
            BillingPlan.STARTER: {"max_clients": 10, "max_systems": 20},
            BillingPlan.PROFESSIONAL: {"max_clients": 50, "max_systems": 100},
            BillingPlan.ENTERPRISE: {"max_clients": 500, "max_systems": 1000}
        }
        
        limits = plan_limits.get(billing_plan, plan_limits[BillingPlan.STARTER])
        
        # Create Stripe Connect account
        stripe_account = None
        if self.stripe:
            try:
                stripe_account = self.stripe.Account.create(
                    type="express",
                    country="US",
                    email=contact_email,
                    capabilities={
                        "card_payments": {"requested": True},
                        "transfers": {"requested": True}
                    }
                )
            except Exception as e:
                print(f"Failed to create Stripe account: {e}")
        
        partner = Partner(
            partner_id=partner_id,
            name=name,
            domain=domain,
            logo_url=logo_url,
            primary_color=primary_color,
            secondary_color=secondary_color,
            contact_email=contact_email,
            contact_phone="",
            billing_plan=billing_plan,
            status=PartnerStatus.PENDING,
            max_clients=limits["max_clients"],
            max_systems=limits["max_systems"],
            revenue_share=revenue_share,
            stripe_account_id=stripe_account.id if stripe_account else None
        )
        
        self._save_partner(partner)
        self.partners[partner_id] = partner
        
        # Generate partner portal
        self._generate_partner_portal(partner)
        
        return partner

    def create_partner_client(self, partner_id: str, name: str, email: str,
                            company: str, billing_plan: BillingPlan) -> PartnerClient:
        """Create a new partner client"""
        if partner_id not in self.partners:
            raise ValueError("Partner not found")
        
        partner = self.partners[partner_id]
        
        # Check client limit
        client_count = self._get_client_count(partner_id)
        if client_count >= partner.max_clients:
            raise ValueError("Partner client limit reached")
        
        client_id = f"client_{py_secrets.token_hex(8)}"
        
        client = PartnerClient(
            client_id=client_id,
            partner_id=partner_id,
            name=name,
            email=email,
            company=company,
            status=ClientStatus.TRIAL,
            billing_plan=billing_plan,
            monthly_revenue=0.0,
            systems_count=0
        )
        
        self._save_client(client)
        self.clients[client_id] = client
        
        return client

    def create_partner_system(self, partner_id: str, client_id: str, name: str,
                            description: str, deployment_type: DeploymentType,
                            deployment_url: str = None) -> PartnerSystem:
        """Create a new partner system"""
        if partner_id not in self.partners:
            raise ValueError("Partner not found")
        
        if client_id not in self.clients:
            raise ValueError("Client not found")
        
        partner = self.partners[partner_id]
        
        # Check system limit
        system_count = self._get_system_count(partner_id)
        if system_count >= partner.max_systems:
            raise ValueError("Partner system limit reached")
        
        system_id = f"system_{py_secrets.token_hex(8)}"
        
        # Calculate monthly cost based on deployment type
        monthly_cost = self._calculate_monthly_cost(deployment_type)
        
        system = PartnerSystem(
            system_id=system_id,
            partner_id=partner_id,
            client_id=client_id,
            name=name,
            description=description,
            deployment_type=deployment_type,
            deployment_url=deployment_url,
            monthly_cost=monthly_cost,
            status="active"
        )
        
        self._save_system(system)
        self.systems[system_id] = system
        
        # Update client system count
        client = self.clients[client_id]
        client.systems_count += 1
        self._save_client(client)
        
        return system

    def record_revenue_transaction(self, partner_id: str, client_id: str, system_id: str,
                                 amount: float, transaction_type: str,
                                 stripe_payment_intent_id: str = None) -> RevenueTransaction:
        """Record a revenue transaction"""
        if partner_id not in self.partners:
            raise ValueError("Partner not found")
        
        partner = self.partners[partner_id]
        
        # Calculate revenue split
        partner_share = amount * (partner.revenue_share / 100)
        platform_share = amount - partner_share
        
        transaction_id = f"txn_{py_secrets.token_hex(8)}"
        
        transaction = RevenueTransaction(
            transaction_id=transaction_id,
            partner_id=partner_id,
            client_id=client_id,
            system_id=system_id,
            amount=amount,
            partner_share=partner_share,
            platform_share=platform_share,
            transaction_type=transaction_type,
            stripe_payment_intent_id=stripe_payment_intent_id
        )
        
        self._save_transaction(transaction)
        self.transactions[transaction_id] = transaction
        
        # Update client monthly revenue
        if client_id in self.clients:
            client = self.clients[client_id]
            client.monthly_revenue += amount
            self._save_client(client)
        
        return transaction

    def generate_partner_analytics(self, partner_id: str, period: str = "monthly") -> PartnerAnalytics:
        """Generate analytics for a partner"""
        if partner_id not in self.partners:
            raise ValueError("Partner not found")
        
        # Calculate analytics
        partner_transactions = [t for t in self.transactions.values() if t.partner_id == partner_id]
        partner_clients = [c for c in self.clients.values() if c.partner_id == partner_id]
        partner_systems = [s for s in self.systems.values() if s.partner_id == partner_id]
        
        total_revenue = sum(t.amount for t in partner_transactions)
        partner_share = sum(t.partner_share for t in partner_transactions)
        active_clients = len([c for c in partner_clients if c.status == ClientStatus.ACTIVE])
        active_systems = len([s for s in partner_systems if s.status == "active"])
        
        # Calculate new and churned clients (simplified)
        new_clients = len([c for c in partner_clients if c.status == ClientStatus.TRIAL])
        churned_clients = len([c for c in partner_clients if c.status == ClientStatus.CANCELLED])
        
        average_revenue_per_client = total_revenue / len(partner_clients) if partner_clients else 0
        
        analytics = PartnerAnalytics(
            partner_id=partner_id,
            period=period,
            total_revenue=total_revenue,
            partner_share=partner_share,
            active_clients=active_clients,
            active_systems=active_systems,
            new_clients=new_clients,
            churned_clients=churned_clients,
            average_revenue_per_client=average_revenue_per_client
        )
        
        self._save_analytics(analytics)
        
        if partner_id not in self.analytics:
            self.analytics[partner_id] = []
        self.analytics[partner_id].append(analytics)
        
        return analytics

    def _generate_partner_portal(self, partner: Partner):
        """Generate white-labeled partner portal"""
        portal_dir = self.portals_dir / partner.domain
        portal_dir.mkdir(exist_ok=True)
        
        # Create portal HTML
        portal_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{partner.name} - System Builder Portal</title>
    <style>
        :root {{
            --primary-color: {partner.primary_color};
            --secondary-color: {partner.secondary_color};
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            min-height: 100vh;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .logo {{
            max-width: 200px;
            margin-bottom: 20px;
        }}
        
        .partner-name {{
            font-size: 2.5rem;
            color: var(--primary-color);
            margin-bottom: 10px;
        }}
        
        .partner-tagline {{
            font-size: 1.2rem;
            color: #666;
        }}
        
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .dashboard-card {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .card-icon {{
            font-size: 3rem;
            margin-bottom: 15px;
        }}
        
        .card-title {{
            font-size: 1.5rem;
            color: var(--primary-color);
            margin-bottom: 10px;
        }}
        
        .card-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .card-label {{
            color: #666;
            font-size: 1rem;
        }}
        
        .btn {{
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            margin: 5px;
            transition: transform 0.2s ease;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
        }}
        
        .systems-section {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .section-title {{
            font-size: 1.8rem;
            color: var(--primary-color);
            margin-bottom: 20px;
        }}
        
        .system-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        
        .system-item {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            transition: border-color 0.3s ease;
        }}
        
        .system-item:hover {{
            border-color: var(--primary-color);
        }}
        
        .system-name {{
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .system-status {{
            color: #28a745;
            font-size: 0.9rem;
        }}
        
        .system-cost {{
            color: var(--primary-color);
            font-weight: 600;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            {f'<img src="{partner.logo_url}" alt="{partner.name}" class="logo">' if partner.logo_url else ''}
            <h1 class="partner-name">{partner.name}</h1>
            <p class="partner-tagline">Professional System Building Solutions</p>
        </div>
        
        <div class="dashboard-grid">
            <div class="dashboard-card">
                <div class="card-icon">👥</div>
                <div class="card-title">Active Clients</div>
                <div class="card-value" id="activeClients">0</div>
                <div class="card-label">Total clients</div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-icon">🚀</div>
                <div class="card-title">Active Systems</div>
                <div class="card-value" id="activeSystems">0</div>
                <div class="card-label">Deployed systems</div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-icon">💰</div>
                <div class="card-title">Monthly Revenue</div>
                <div class="card-value" id="monthlyRevenue">$0</div>
                <div class="card-label">This month</div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-icon">📈</div>
                <div class="card-title">Growth</div>
                <div class="card-value" id="growth">0%</div>
                <div class="card-label">vs last month</div>
            </div>
        </div>
        
        <div class="systems-section">
            <h2 class="section-title">Recent Systems</h2>
            <div class="system-list" id="systemList">
                <p>No systems deployed yet.</p>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/api/partner/{partner.partner_id}/dashboard" class="btn">View Full Dashboard</a>
            <a href="/api/partner/{partner.partner_id}/clients" class="btn">Manage Clients</a>
            <a href="/api/partner/{partner.partner_id}/analytics" class="btn">View Analytics</a>
        </div>
    </div>
    
    <script>
        // Load dashboard data
        async function loadDashboardData() {{
            try {{
                const response = await fetch('/api/partner/{partner.partner_id}/analytics');
                const data = await response.json();
                
                document.getElementById('activeClients').textContent = data.active_clients || 0;
                document.getElementById('activeSystems').textContent = data.active_systems || 0;
                document.getElementById('monthlyRevenue').textContent = '$' + (data.total_revenue || 0).toFixed(2);
                document.getElementById('growth').textContent = '12%'; // Placeholder
            }} catch (error) {{
                console.error('Failed to load dashboard data:', error);
            }}
        }}
        
        // Load systems
        async function loadSystems() {{
            try {{
                const response = await fetch('/api/partner/{partner.partner_id}/systems');
                const systems = await response.json();
                
                const systemList = document.getElementById('systemList');
                if (systems.length === 0) {{
                    systemList.innerHTML = '<p>No systems deployed yet.</p>';
                    return;
                }}
                
                systemList.innerHTML = systems.map(system => `
                    <div class="system-item">
                        <div class="system-name">${{system.name}}</div>
                        <div class="system-status">${{system.status}}</div>
                        <div class="system-cost">$${{system.monthly_cost}}/month</div>
                    </div>
                `).join('');
            }} catch (error) {{
                console.error('Failed to load systems:', error);
            }}
        }}
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {{
            loadDashboardData();
            loadSystems();
        }});
    </script>
</body>
</html>
"""
        
        with open(portal_dir / "index.html", 'w') as f:
            f.write(portal_html)
        
        # Create portal configuration
        portal_config = {
            "partner_id": partner.partner_id,
            "domain": partner.domain,
            "name": partner.name,
            "colors": {
                "primary": partner.primary_color,
                "secondary": partner.secondary_color
            },
            "logo_url": partner.logo_url,
            "contact": {
                "email": partner.contact_email,
                "phone": partner.contact_phone
            },
            "billing": {
                "plan": partner.billing_plan.value,
                "revenue_share": partner.revenue_share
            }
        }
        
        with open(portal_dir / "config.json", 'w') as f:
            json.dump(portal_config, f, indent=2)

    def _calculate_monthly_cost(self, deployment_type: DeploymentType) -> float:
        """Calculate monthly cost based on deployment type"""
        costs = {
            DeploymentType.SELF_HOSTED: 0.0,
            DeploymentType.PARTNER_CLOUD: 99.0,
            DeploymentType.CLIENT_INFRASTRUCTURE: 49.0
        }
        return costs.get(deployment_type, 0.0)

    def _get_client_count(self, partner_id: str) -> int:
        """Get client count for partner"""
        return len([c for c in self.clients.values() if c.partner_id == partner_id])

    def _get_system_count(self, partner_id: str) -> int:
        """Get system count for partner"""
        return len([s for s in self.systems.values() if s.partner_id == partner_id])

    def _save_partner(self, partner: Partner):
        """Save partner to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO partners 
            (partner_id, name, domain, logo_url, primary_color, secondary_color,
             contact_email, contact_phone, billing_plan, status, max_clients,
             max_systems, revenue_share, stripe_account_id, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            partner.partner_id, partner.name, partner.domain, partner.logo_url,
            partner.primary_color, partner.secondary_color, partner.contact_email,
            partner.contact_phone, partner.billing_plan.value, partner.status.value,
            partner.max_clients, partner.max_systems, partner.revenue_share,
            partner.stripe_account_id, partner.created_at, json.dumps(partner.metadata)
        ))
        
        conn.commit()
        conn.close()

    def _save_client(self, client: PartnerClient):
        """Save client to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO partner_clients 
            (client_id, partner_id, name, email, company, status, billing_plan,
             monthly_revenue, systems_count, created_at, last_login, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            client.client_id, client.partner_id, client.name, client.email,
            client.company, client.status.value, client.billing_plan.value,
            client.monthly_revenue, client.systems_count, client.created_at,
            client.last_login, json.dumps(client.metadata)
        ))
        
        conn.commit()
        conn.close()

    def _save_system(self, system: PartnerSystem):
        """Save system to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO partner_systems 
            (system_id, partner_id, client_id, name, description, deployment_type,
             deployment_url, monthly_cost, status, created_at, last_updated, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            system.system_id, system.partner_id, system.client_id, system.name,
            system.description, system.deployment_type.value, system.deployment_url,
            system.monthly_cost, system.status, system.created_at, system.last_updated,
            json.dumps(system.metadata)
        ))
        
        conn.commit()
        conn.close()

    def _save_transaction(self, transaction: RevenueTransaction):
        """Save transaction to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO revenue_transactions 
            (transaction_id, partner_id, client_id, system_id, amount, partner_share,
             platform_share, transaction_type, stripe_payment_intent_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction.transaction_id, transaction.partner_id, transaction.client_id,
            transaction.system_id, transaction.amount, transaction.partner_share,
            transaction.platform_share, transaction.transaction_type,
            transaction.stripe_payment_intent_id, transaction.created_at
        ))
        
        conn.commit()
        conn.close()

    def _save_analytics(self, analytics: PartnerAnalytics):
        """Save analytics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        analytics_id = f"analytics_{py_secrets.token_hex(8)}"
        
        cursor.execute("""
            INSERT OR REPLACE INTO partner_analytics 
            (analytics_id, partner_id, period, total_revenue, partner_share,
             active_clients, active_systems, new_clients, churned_clients,
             average_revenue_per_client, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analytics_id, analytics.partner_id, analytics.period, analytics.total_revenue,
            analytics.partner_share, analytics.active_clients, analytics.active_systems,
            analytics.new_clients, analytics.churned_clients, analytics.average_revenue_per_client,
            analytics.created_at
        ))
        
        conn.commit()
        conn.close()

    def get_partner(self, partner_id: str) -> Optional[Partner]:
        """Get partner by ID"""
        return self.partners.get(partner_id)

    def get_partner_clients(self, partner_id: str) -> List[PartnerClient]:
        """Get clients for a partner"""
        return [c for c in self.clients.values() if c.partner_id == partner_id]

    def get_partner_systems(self, partner_id: str) -> List[PartnerSystem]:
        """Get systems for a partner"""
        return [s for s in self.systems.values() if s.partner_id == partner_id]

    def get_partner_transactions(self, partner_id: str) -> List[RevenueTransaction]:
        """Get transactions for a partner"""
        return [t for t in self.transactions.values() if t.partner_id == partner_id]

    def get_partner_analytics(self, partner_id: str) -> List[PartnerAnalytics]:
        """Get analytics for a partner"""
        return self.analytics.get(partner_id, [])

    def update_partner_status(self, partner_id: str, status: PartnerStatus) -> bool:
        """Update partner status"""
        if partner_id not in self.partners:
            return False
        
        partner = self.partners[partner_id]
        partner.status = status
        
        self._save_partner(partner)
        return True

    def update_client_status(self, client_id: str, status: ClientStatus) -> bool:
        """Update client status"""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        client.status = status
        
        self._save_client(client)
        return True
