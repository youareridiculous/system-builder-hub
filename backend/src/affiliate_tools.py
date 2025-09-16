"""
Affiliate Tools & Creator Bundles
Priority 11: Autonomous Growth Engine

Features:
- Create & publish bundles (e.g. agent + template + asset packs)
- Branded landing pages for each bundle
- Creator revenue share config
- Stripe Connect or equivalent for payouts
- Metrics dashboard for bundle performance
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
import os


class BundleStatus(Enum):
    """Bundle status enumeration"""
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    ARCHIVED = "archived"


class BundleType(Enum):
    """Bundle type enumeration"""
    AGENT_PACK = "agent_pack"
    TEMPLATE_PACK = "template_pack"
    ASSET_PACK = "asset_pack"
    COMPLETE_SOLUTION = "complete_solution"
    COURSE = "course"
    WORKSHOP = "workshop"


class RevenueShareType(Enum):
    """Revenue share type enumeration"""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    TIERED = "tiered"


class PayoutStatus(Enum):
    """Payout status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AffiliateBundle:
    """Affiliate bundle data structure"""
    bundle_id: str
    creator_id: str
    organization_id: str
    name: str
    description: str
    bundle_type: BundleType
    status: BundleStatus
    price: float
    revenue_share_type: RevenueShareType
    revenue_share_value: float
    revenue_share_tiers: Optional[Dict]
    included_items: List[str]  # List of system/agent/template IDs
    landing_page_url: str
    preview_image_url: Optional[str]
    tags: List[str]
    target_audience: str
    features: List[str]
    requirements: List[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]


@dataclass
class BundleSale:
    """Bundle sale data structure"""
    sale_id: str
    bundle_id: str
    buyer_id: str
    buyer_email: str
    sale_amount: float
    creator_revenue: float
    platform_revenue: float
    commission_paid: float
    sale_date: datetime
    payment_method: str
    status: str  # "completed", "refunded", "pending"


@dataclass
class CreatorPayout:
    """Creator payout data structure"""
    payout_id: str
    creator_id: str
    amount: float
    currency: str
    payment_method: str
    payment_details: Dict
    status: PayoutStatus
    stripe_transfer_id: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    failure_reason: Optional[str]


@dataclass
class BundleAnalytics:
    """Bundle analytics data structure"""
    bundle_id: str
    total_sales: int
    total_revenue: float
    creator_revenue: float
    platform_revenue: float
    conversion_rate: float
    average_order_value: float
    refund_rate: float
    views_count: int
    unique_visitors: int
    time_on_page: float
    last_updated: datetime


@dataclass
class LandingPage:
    """Landing page data structure"""
    page_id: str
    bundle_id: str
    url_slug: str
    title: str
    hero_text: str
    description: str
    features: List[str]
    testimonials: List[Dict]
    pricing_info: Dict
    cta_text: str
    cta_url: str
    custom_css: Optional[str]
    custom_js: Optional[str]
    seo_meta: Dict
    created_at: datetime
    updated_at: datetime


class AffiliateTools:
    """Affiliate Tools & Creator Bundles System"""
    
    def __init__(self, base_dir: str, access_control, system_delivery, storefront, llm_factory):
        self.base_dir = base_dir
        self.access_control = access_control
        self.system_delivery = system_delivery
        self.storefront = storefront
        self.llm_factory = llm_factory
        self.db_path = f"{base_dir}/affiliate_tools.db"
        self.landing_pages_dir = f"{base_dir}/landing_pages"
        self._init_database()
        self._init_directories()
        
        # Start analytics loop
        self.analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        self.analytics_thread.start()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Affiliate bundles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS affiliate_bundles (
                bundle_id TEXT PRIMARY KEY,
                creator_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                bundle_type TEXT NOT NULL,
                status TEXT NOT NULL,
                price REAL NOT NULL,
                revenue_share_type TEXT NOT NULL,
                revenue_share_value REAL NOT NULL,
                revenue_share_tiers TEXT,
                included_items TEXT NOT NULL,
                landing_page_url TEXT,
                preview_image_url TEXT,
                tags TEXT,
                target_audience TEXT,
                features TEXT,
                requirements TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
        ''')
        
        # Bundle sales table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bundle_sales (
                sale_id TEXT PRIMARY KEY,
                bundle_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                buyer_email TEXT NOT NULL,
                sale_amount REAL NOT NULL,
                creator_revenue REAL NOT NULL,
                platform_revenue REAL NOT NULL,
                commission_paid REAL DEFAULT 0,
                sale_date TEXT NOT NULL,
                payment_method TEXT,
                status TEXT NOT NULL
            )
        ''')
        
        # Creator payouts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS creator_payouts (
                payout_id TEXT PRIMARY KEY,
                creator_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                payment_method TEXT NOT NULL,
                payment_details TEXT NOT NULL,
                status TEXT NOT NULL,
                stripe_transfer_id TEXT,
                created_at TEXT NOT NULL,
                processed_at TEXT,
                failure_reason TEXT
            )
        ''')
        
        # Bundle analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bundle_analytics (
                bundle_id TEXT PRIMARY KEY,
                total_sales INTEGER DEFAULT 0,
                total_revenue REAL DEFAULT 0,
                creator_revenue REAL DEFAULT 0,
                platform_revenue REAL DEFAULT 0,
                conversion_rate REAL DEFAULT 0,
                average_order_value REAL DEFAULT 0,
                refund_rate REAL DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                unique_visitors INTEGER DEFAULT 0,
                time_on_page REAL DEFAULT 0,
                last_updated TEXT NOT NULL
            )
        ''')
        
        # Landing pages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS landing_pages (
                page_id TEXT PRIMARY KEY,
                bundle_id TEXT NOT NULL,
                url_slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                hero_text TEXT,
                description TEXT,
                features TEXT,
                testimonials TEXT,
                pricing_info TEXT,
                cta_text TEXT,
                cta_url TEXT,
                custom_css TEXT,
                custom_js TEXT,
                seo_meta TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_directories(self):
        """Initialize necessary directories"""
        os.makedirs(self.landing_pages_dir, exist_ok=True)
    
    def create_bundle(self, creator_id: str, organization_id: str, name: str,
                     description: str, bundle_type: BundleType, price: float,
                     revenue_share_type: RevenueShareType, revenue_share_value: float,
                     included_items: List[str], tags: List[str] = None,
                     target_audience: str = "", features: List[str] = None,
                     requirements: List[str] = None) -> AffiliateBundle:
        """Create a new affiliate bundle"""
        bundle_id = py_secrets.token_urlsafe(16)
        
        # Generate URL slug
        url_slug = self._generate_url_slug(name)
        
        # Create bundle
        bundle = AffiliateBundle(
            bundle_id=bundle_id,
            creator_id=creator_id,
            organization_id=organization_id,
            name=name,
            description=description,
            bundle_type=bundle_type,
            status=BundleStatus.DRAFT,
            price=price,
            revenue_share_type=revenue_share_type,
            revenue_share_value=revenue_share_value,
            revenue_share_tiers=None,
            included_items=included_items,
            landing_page_url=f"/bundle/{url_slug}",
            preview_image_url=None,
            tags=tags or [],
            target_audience=target_audience,
            features=features or [],
            requirements=requirements or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=None
        )
        
        # Save bundle
        self._save_bundle(bundle)
        
        # Create landing page
        self._create_landing_page(bundle)
        
        return bundle
    
    def _generate_url_slug(self, name: str) -> str:
        """Generate URL slug from bundle name"""
        slug = name.lower().replace(' ', '-').replace('_', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        slug = '-'.join(filter(None, slug.split('-')))
        
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while self._slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def _slug_exists(self, slug: str) -> bool:
        """Check if URL slug already exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM landing_pages WHERE url_slug = ?
        ''', (slug,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def _save_bundle(self, bundle: AffiliateBundle):
        """Save bundle to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO affiliate_bundles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bundle.bundle_id,
            bundle.creator_id,
            bundle.organization_id,
            bundle.name,
            bundle.description,
            bundle.bundle_type.value,
            bundle.status.value,
            bundle.price,
            bundle.revenue_share_type.value,
            bundle.revenue_share_value,
            json.dumps(bundle.revenue_share_tiers) if bundle.revenue_share_tiers else None,
            json.dumps(bundle.included_items),
            bundle.landing_page_url,
            bundle.preview_image_url,
            json.dumps(bundle.tags),
            bundle.target_audience,
            json.dumps(bundle.features),
            json.dumps(bundle.requirements),
            bundle.created_at.isoformat(),
            bundle.updated_at.isoformat(),
            bundle.published_at.isoformat() if bundle.published_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def _create_landing_page(self, bundle: AffiliateBundle):
        """Create landing page for bundle"""
        page_id = py_secrets.token_urlsafe(16)
        url_slug = bundle.landing_page_url.split('/')[-1]
        
        landing_page = LandingPage(
            page_id=page_id,
            bundle_id=bundle.bundle_id,
            url_slug=url_slug,
            title=bundle.name,
            hero_text=f"Discover {bundle.name}",
            description=bundle.description,
            features=bundle.features,
            testimonials=[],
            pricing_info={
                "price": bundle.price,
                "currency": "USD",
                "discount": None,
                "original_price": bundle.price
            },
            cta_text="Get This Bundle",
            cta_url=f"/checkout/bundle/{bundle.bundle_id}",
            custom_css=None,
            custom_js=None,
            seo_meta={
                "title": bundle.name,
                "description": bundle.description[:160],
                "keywords": ", ".join(bundle.tags),
                "og_title": bundle.name,
                "og_description": bundle.description[:160],
                "og_image": bundle.preview_image_url
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save landing page
        self._save_landing_page(landing_page)
        
        # Generate HTML file
        self._generate_landing_page_html(landing_page, bundle)
    
    def _save_landing_page(self, landing_page: LandingPage):
        """Save landing page to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO landing_pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            landing_page.page_id,
            landing_page.bundle_id,
            landing_page.url_slug,
            landing_page.title,
            landing_page.hero_text,
            landing_page.description,
            json.dumps(landing_page.features),
            json.dumps(landing_page.testimonials),
            json.dumps(landing_page.pricing_info),
            landing_page.cta_text,
            landing_page.cta_url,
            landing_page.custom_css,
            landing_page.custom_js,
            json.dumps(landing_page.seo_meta),
            landing_page.created_at.isoformat(),
            landing_page.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_landing_page_html(self, landing_page: LandingPage, bundle: AffiliateBundle):
        """Generate HTML file for landing page"""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{landing_page.seo_meta['title']}</title>
    <meta name="description" content="{landing_page.seo_meta['description']}">
    <meta name="keywords" content="{landing_page.seo_meta['keywords']}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{landing_page.seo_meta['og_title']}">
    <meta property="og:description" content="{landing_page.seo_meta['og_description']}">
    <meta property="og:image" content="{landing_page.seo_meta['og_image'] or ''}">
    <meta property="og:type" content="product">
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .hero-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 100px 0;
        }}
        .feature-card {{
            border: none;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .feature-card:hover {{
            transform: translateY(-5px);
        }}
        .cta-button {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            font-size: 18px;
            font-weight: bold;
        }}
        {landing_page.custom_css or ''}
    </style>
</head>
<body>
    <!-- Hero Section -->
    <section class="hero-section">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-lg-8">
                    <h1 class="display-4 fw-bold mb-4">{landing_page.hero_text}</h1>
                    <p class="lead mb-4">{landing_page.description}</p>
                    <div class="d-flex align-items-center mb-4">
                        <span class="h3 me-3">${landing_page.pricing_info['price']}</span>
                        {f"<span class='text-decoration-line-through me-2'>${landing_page.pricing_info['original_price']}</span>" if landing_page.pricing_info.get('original_price') and landing_page.pricing_info['original_price'] != landing_page.pricing_info['price'] else ''}
                    </div>
                    <a href="{landing_page.cta_url}" class="btn btn-light btn-lg cta-button">
                        <i class="fas fa-shopping-cart me-2"></i>{landing_page.cta_text}
                    </a>
                </div>
                <div class="col-lg-4">
                    {f'<img src="{bundle.preview_image_url}" class="img-fluid rounded" alt="{bundle.name}">' if bundle.preview_image_url else ''}
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="py-5">
        <div class="container">
            <h2 class="text-center mb-5">What's Included</h2>
            <div class="row">
                {self._generate_features_html(landing_page.features)}
            </div>
        </div>
    </section>

    <!-- Bundle Type Info -->
    <section class="py-5 bg-light">
        <div class="container">
            <div class="row">
                <div class="col-lg-8 mx-auto text-center">
                    <h3>Bundle Type: {bundle.bundle_type.value.replace('_', ' ').title()}</h3>
                    <p class="text-muted">Perfect for {bundle.target_audience or 'developers and creators'}</p>
                </div>
            </div>
        </div>
    </section>

    <!-- CTA Section -->
    <section class="py-5">
        <div class="container">
            <div class="row">
                <div class="col-lg-8 mx-auto text-center">
                    <h2>Ready to Get Started?</h2>
                    <p class="lead mb-4">Join thousands of developers who have already benefited from this bundle.</p>
                    <a href="{landing_page.cta_url}" class="btn btn-primary btn-lg cta-button">
                        <i class="fas fa-rocket me-2"></i>{landing_page.cta_text}
                    </a>
                </div>
            </div>
        </div>
    </section>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {landing_page.custom_js or ''}
</body>
</html>
        """
        
        # Save HTML file
        html_file_path = os.path.join(self.landing_pages_dir, f"{landing_page.url_slug}.html")
        with open(html_file_path, 'w') as f:
            f.write(html_content)
    
    def _generate_features_html(self, features: List[str]) -> str:
        """Generate HTML for features section"""
        html = ""
        for feature in features:
            html += f"""
                <div class="col-md-6 col-lg-4 mb-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <i class="fas fa-check-circle text-success fa-2x mb-3"></i>
                            <h5 class="card-title">{feature}</h5>
                        </div>
                    </div>
                </div>
            """
        return html
    
    def publish_bundle(self, bundle_id: str) -> AffiliateBundle:
        """Publish a bundle"""
        bundle = self.get_bundle(bundle_id)
        if not bundle:
            raise ValueError("Bundle not found")
        
        bundle.status = BundleStatus.PUBLISHED
        bundle.published_at = datetime.now()
        bundle.updated_at = datetime.now()
        
        # Update bundle
        self._update_bundle(bundle)
        
        # Add to storefront
        self._add_to_storefront(bundle)
        
        return bundle
    
    def get_bundle(self, bundle_id: str) -> Optional[AffiliateBundle]:
        """Get bundle by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM affiliate_bundles WHERE bundle_id = ?
        ''', (bundle_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_bundle(row)
        return None
    
    def _row_to_bundle(self, row) -> AffiliateBundle:
        """Convert database row to AffiliateBundle object"""
        return AffiliateBundle(
            bundle_id=row[0],
            creator_id=row[1],
            organization_id=row[2],
            name=row[3],
            description=row[4],
            bundle_type=BundleType(row[5]),
            status=BundleStatus(row[6]),
            price=row[7],
            revenue_share_type=RevenueShareType(row[8]),
            revenue_share_value=row[9],
            revenue_share_tiers=json.loads(row[10]) if row[10] else None,
            included_items=json.loads(row[11]),
            landing_page_url=row[12],
            preview_image_url=row[13],
            tags=json.loads(row[14]) if row[14] else [],
            target_audience=row[15],
            features=json.loads(row[16]) if row[16] else [],
            requirements=json.loads(row[17]) if row[17] else [],
            created_at=datetime.fromisoformat(row[18]),
            updated_at=datetime.fromisoformat(row[19]),
            published_at=datetime.fromisoformat(row[20]) if row[20] else None
        )
    
    def _update_bundle(self, bundle: AffiliateBundle):
        """Update bundle in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE affiliate_bundles 
            SET status = ?, published_at = ?, updated_at = ?
            WHERE bundle_id = ?
        ''', (
            bundle.status.value,
            bundle.published_at.isoformat() if bundle.published_at else None,
            bundle.updated_at.isoformat(),
            bundle.bundle_id
        ))
        
        conn.commit()
        conn.close()
    
    def _add_to_storefront(self, bundle: AffiliateBundle):
        """Add bundle to storefront"""
        # This would integrate with the existing storefront system
        # For now, we'll just log the action
        print(f"Bundle {bundle.bundle_id} added to storefront")
    
    def process_bundle_sale(self, bundle_id: str, buyer_id: str, buyer_email: str,
                           sale_amount: float, payment_method: str = "stripe") -> BundleSale:
        """Process a bundle sale"""
        bundle = self.get_bundle(bundle_id)
        if not bundle:
            raise ValueError("Bundle not found")
        
        if bundle.status != BundleStatus.PUBLISHED:
            raise ValueError("Bundle is not published")
        
        # Calculate revenue split
        creator_revenue = self._calculate_creator_revenue(bundle, sale_amount)
        platform_revenue = sale_amount - creator_revenue
        
        # Create sale record
        sale = BundleSale(
            sale_id=py_secrets.token_urlsafe(16),
            bundle_id=bundle_id,
            buyer_id=buyer_id,
            buyer_email=buyer_email,
            sale_amount=sale_amount,
            creator_revenue=creator_revenue,
            platform_revenue=platform_revenue,
            commission_paid=0,
            sale_date=datetime.now(),
            payment_method=payment_method,
            status="completed"
        )
        
        # Save sale
        self._save_bundle_sale(sale)
        
        # Update analytics
        self._update_bundle_analytics(bundle_id)
        
        return sale
    
    def _calculate_creator_revenue(self, bundle: AffiliateBundle, sale_amount: float) -> float:
        """Calculate creator revenue based on revenue share settings"""
        if bundle.revenue_share_type == RevenueShareType.PERCENTAGE:
            return sale_amount * (bundle.revenue_share_value / 100)
        elif bundle.revenue_share_type == RevenueShareType.FIXED_AMOUNT:
            return min(bundle.revenue_share_value, sale_amount)
        else:
            return sale_amount * 0.7  # Default 70% to creator
    
    def _save_bundle_sale(self, sale: BundleSale):
        """Save bundle sale to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bundle_sales VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sale.sale_id,
            sale.bundle_id,
            sale.buyer_id,
            sale.buyer_email,
            sale.sale_amount,
            sale.creator_revenue,
            sale.platform_revenue,
            sale.commission_paid,
            sale.sale_date.isoformat(),
            sale.payment_method,
            sale.status
        ))
        
        conn.commit()
        conn.close()
    
    def _update_bundle_analytics(self, bundle_id: str):
        """Update bundle analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate analytics from sales
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sales,
                SUM(sale_amount) as total_revenue,
                SUM(creator_revenue) as creator_revenue,
                SUM(platform_revenue) as platform_revenue,
                AVG(sale_amount) as avg_order_value
            FROM bundle_sales 
            WHERE bundle_id = ? AND status = 'completed'
        ''', (bundle_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        total_sales = row[0] or 0
        total_revenue = row[1] or 0
        creator_revenue = row[2] or 0
        platform_revenue = row[3] or 0
        avg_order_value = row[4] or 0
        
        # Save analytics
        self._save_bundle_analytics(bundle_id, total_sales, total_revenue, creator_revenue,
                                  platform_revenue, avg_order_value)
    
    def _save_bundle_analytics(self, bundle_id: str, total_sales: int, total_revenue: float,
                             creator_revenue: float, platform_revenue: float, avg_order_value: float):
        """Save bundle analytics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO bundle_analytics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bundle_id,
            total_sales,
            total_revenue,
            creator_revenue,
            platform_revenue,
            0,  # conversion_rate
            avg_order_value,
            0,  # refund_rate
            0,  # views_count
            0,  # unique_visitors
            0,  # time_on_page
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_creator_bundles(self, creator_id: str) -> List[AffiliateBundle]:
        """Get bundles created by a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM affiliate_bundles 
            WHERE creator_id = ?
            ORDER BY created_at DESC
        ''', (creator_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_bundle(row) for row in rows]
    
    def get_bundle_analytics(self, bundle_id: str) -> Optional[BundleAnalytics]:
        """Get analytics for a bundle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM bundle_analytics WHERE bundle_id = ?
        ''', (bundle_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_bundle_analytics(row)
        return None
    
    def _row_to_bundle_analytics(self, row) -> BundleAnalytics:
        """Convert database row to BundleAnalytics object"""
        return BundleAnalytics(
            bundle_id=row[0],
            total_sales=row[1],
            total_revenue=row[2],
            creator_revenue=row[3],
            platform_revenue=row[4],
            conversion_rate=row[5],
            average_order_value=row[6],
            refund_rate=row[7],
            views_count=row[8],
            unique_visitors=row[9],
            time_on_page=row[10],
            last_updated=datetime.fromisoformat(row[11])
        )
    
    def request_payout(self, creator_id: str, amount: float, 
                      payment_method: str, payment_details: Dict) -> CreatorPayout:
        """Request a payout for a creator"""
        # Calculate available balance
        available_balance = self._calculate_creator_balance(creator_id)
        
        if amount > available_balance:
            raise ValueError("Insufficient balance for payout")
        
        payout = CreatorPayout(
            payout_id=py_secrets.token_urlsafe(16),
            creator_id=creator_id,
            amount=amount,
            currency="USD",
            payment_method=payment_method,
            payment_details=payment_details,
            status=PayoutStatus.PENDING,
            stripe_transfer_id=None,
            created_at=datetime.now(),
            processed_at=None,
            failure_reason=None
        )
        
        # Save payout
        self._save_creator_payout(payout)
        
        return payout
    
    def _calculate_creator_balance(self, creator_id: str) -> float:
        """Calculate creator's available balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                SUM(creator_revenue) as total_earned,
                SUM(amount) as total_paid
            FROM bundle_sales bs
            LEFT JOIN creator_payouts cp ON bs.bundle_id IN (
                SELECT bundle_id FROM affiliate_bundles WHERE creator_id = ?
            ) AND cp.creator_id = ? AND cp.status = 'completed'
            WHERE bs.bundle_id IN (
                SELECT bundle_id FROM affiliate_bundles WHERE creator_id = ?
            )
        ''', (creator_id, creator_id, creator_id))
        
        row = cursor.fetchone()
        conn.close()
        
        total_earned = row[0] or 0
        total_paid = row[1] or 0
        
        return total_earned - total_paid
    
    def _save_creator_payout(self, payout: CreatorPayout):
        """Save creator payout to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO creator_payouts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payout.payout_id,
            payout.creator_id,
            payout.amount,
            payout.currency,
            payout.payment_method,
            json.dumps(payout.payment_details),
            payout.status.value,
            payout.stripe_transfer_id,
            payout.created_at.isoformat(),
            payout.processed_at.isoformat() if payout.processed_at else None,
            payout.failure_reason
        ))
        
        conn.commit()
        conn.close()
    
    def get_landing_page(self, url_slug: str) -> Optional[LandingPage]:
        """Get landing page by URL slug"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM landing_pages WHERE url_slug = ?
        ''', (url_slug,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_landing_page(row)
        return None
    
    def _row_to_landing_page(self, row) -> LandingPage:
        """Convert database row to LandingPage object"""
        return LandingPage(
            page_id=row[0],
            bundle_id=row[1],
            url_slug=row[2],
            title=row[3],
            hero_text=row[4],
            description=row[5],
            features=json.loads(row[6]) if row[6] else [],
            testimonials=json.loads(row[7]) if row[7] else [],
            pricing_info=json.loads(row[8]) if row[8] else {},
            cta_text=row[9],
            cta_url=row[10],
            custom_css=row[11],
            custom_js=row[12],
            seo_meta=json.loads(row[13]) if row[13] else {},
            created_at=datetime.fromisoformat(row[14]),
            updated_at=datetime.fromisoformat(row[15])
        )
    
    def _analytics_loop(self):
        """Background analytics processing loop"""
        while True:
            try:
                # Update all bundle analytics
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT DISTINCT bundle_id FROM affiliate_bundles')
                bundle_ids = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                for bundle_id in bundle_ids:
                    self._update_bundle_analytics(bundle_id)
                
                time.sleep(3600)  # Run every hour
                
            except Exception as e:
                print(f"Error in affiliate analytics loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def get_affiliate_statistics(self) -> Dict:
        """Get overall affiliate statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bundle statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_bundles,
                SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) as published_bundles,
                COUNT(DISTINCT creator_id) as active_creators
            FROM affiliate_bundles
        ''')
        
        bundle_stats = cursor.fetchone()
        
        # Sales statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sales,
                SUM(sale_amount) as total_revenue,
                SUM(creator_revenue) as total_creator_revenue,
                AVG(sale_amount) as avg_sale_value
            FROM bundle_sales 
            WHERE status = 'completed'
        ''')
        
        sales_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_bundles": bundle_stats[0] or 0,
            "published_bundles": bundle_stats[1] or 0,
            "active_creators": bundle_stats[2] or 0,
            "total_sales": sales_stats[0] or 0,
            "total_revenue": sales_stats[1] or 0,
            "total_creator_revenue": sales_stats[2] or 0,
            "average_sale_value": sales_stats[3] or 0
        }
