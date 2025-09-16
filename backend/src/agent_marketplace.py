import sqlite3
import json
import threading
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
import os
import shutil
import zipfile
from pathlib import Path

class ListingType(Enum):
    AGENT = "agent"
    SYSTEM = "system"
    TEMPLATE = "template"
    WORKFLOW = "workflow"
    DOMAIN_TEMPLATE = "domain_template"

class ListingStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    FEATURED = "featured"

class PricingModel(Enum):
    FREE = "free"
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    USAGE_BASED = "usage_based"
    REVENUE_SHARE = "revenue_share"

class LicenseType(Enum):
    MIT = "mit"
    AGPL = "agpl"
    COMMERCIAL = "commercial"
    CUSTOM = "custom"
    PROPRIETARY = "proprietary"

@dataclass
class MarketplaceListing:
    listing_id: str
    title: str
    description: str
    listing_type: ListingType
    status: ListingStatus
    pricing_model: PricingModel
    price: float
    license_type: LicenseType
    author_id: str
    organization_id: str
    tags: List[str]
    categories: List[str]
    use_cases: List[str]
    features: List[str]
    requirements: List[str]
    demo_url: Optional[str]
    documentation_url: Optional[str]
    support_url: Optional[str]
    version: str
    downloads: int
    rating: float
    review_count: int
    featured: bool
    created_at: str
    updated_at: str
    published_at: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class Purchase:
    purchase_id: str
    listing_id: str
    buyer_id: str
    buyer_organization_id: str
    price: float
    currency: str
    license_key: str
    download_url: str
    purchased_at: str
    expires_at: Optional[str]
    status: str
    metadata: Dict[str, Any]

@dataclass
class Review:
    review_id: str
    listing_id: str
    reviewer_id: str
    reviewer_name: str
    rating: int
    title: str
    content: str
    helpful_count: int
    created_at: str
    updated_at: str

class AgentMarketplace:
    """Marketplace for agents, systems, and templates"""
    
    def __init__(self, base_dir: str, system_delivery, licensing_module, affiliate_engine, llm_factory):
        self.base_dir = base_dir
        self.system_delivery = system_delivery
        self.licensing_module = licensing_module
        self.affiliate_engine = affiliate_engine
        self.llm_factory = llm_factory
        
        self.db_path = f"{base_dir}/agent_marketplace.db"
        self.listings_dir = f"{base_dir}/marketplace_listings"
        self.downloads_dir = f"{base_dir}/marketplace_downloads"
        
        # Initialize directories and database
        self._init_directories()
        self._init_database()
        
        # Background tasks
        self.analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        self.analytics_thread.start()
    
    def _init_directories(self):
        """Initialize marketplace directories"""
        os.makedirs(self.listings_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize marketplace database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                listing_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                listing_type TEXT NOT NULL,
                status TEXT NOT NULL,
                pricing_model TEXT NOT NULL,
                price REAL NOT NULL,
                license_type TEXT NOT NULL,
                author_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                tags TEXT,
                categories TEXT,
                use_cases TEXT,
                features TEXT,
                requirements TEXT,
                demo_url TEXT,
                documentation_url TEXT,
                support_url TEXT,
                version TEXT NOT NULL,
                downloads INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                review_count INTEGER DEFAULT 0,
                featured BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT,
                metadata TEXT
            )
        ''')
        
        # Create purchases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                buyer_organization_id TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                license_key TEXT NOT NULL,
                download_url TEXT NOT NULL,
                purchased_at TEXT NOT NULL,
                expires_at TEXT,
                status TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (listing_id) REFERENCES listings (listing_id)
            )
        ''')
        
        # Create reviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                reviewer_name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                helpful_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (listing_id) REFERENCES listings (listing_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_listings_status ON listings (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_listings_type ON listings (listing_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_listings_author ON listings (author_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_listings_featured ON listings (featured)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_buyer ON purchases (buyer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_listing ON reviews (listing_id)')
        
        conn.commit()
        conn.close()
    
    def create_listing(self, title: str, description: str, listing_type: ListingType,
                      pricing_model: PricingModel, price: float, license_type: LicenseType,
                      author_id: str, organization_id: str, tags: List[str] = None,
                      categories: List[str] = None, use_cases: List[str] = None,
                      features: List[str] = None, requirements: List[str] = None,
                      demo_url: str = None, documentation_url: str = None,
                      support_url: str = None, version: str = "1.0.0",
                      metadata: Dict[str, Any] = None) -> str:
        """Create a new marketplace listing"""
        listing_id = f"listing_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        listing = MarketplaceListing(
            listing_id=listing_id,
            title=title,
            description=description,
            listing_type=listing_type,
            status=ListingStatus.DRAFT,
            pricing_model=pricing_model,
            price=price,
            license_type=license_type,
            author_id=author_id,
            organization_id=organization_id,
            tags=tags or [],
            categories=categories or [],
            use_cases=use_cases or [],
            features=features or [],
            requirements=requirements or [],
            demo_url=demo_url,
            documentation_url=documentation_url,
            support_url=support_url,
            version=version,
            downloads=0,
            rating=0.0,
            review_count=0,
            featured=False,
            created_at=now,
            updated_at=now,
            published_at=None,
            metadata=metadata or {}
        )
        
        self._save_listing(listing)
        return listing_id
    
    def _save_listing(self, listing: MarketplaceListing):
        """Save listing to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO listings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing.listing_id, listing.title, listing.description,
            listing.listing_type.value, listing.status.value,
            listing.pricing_model.value, listing.price,
            listing.license_type.value, listing.author_id,
            listing.organization_id, json.dumps(listing.tags),
            json.dumps(listing.categories), json.dumps(listing.use_cases),
            json.dumps(listing.features), json.dumps(listing.requirements),
            listing.demo_url, listing.documentation_url, listing.support_url,
            listing.version, listing.downloads, listing.rating,
            listing.review_count, listing.featured, listing.created_at,
            listing.updated_at, listing.published_at, json.dumps(listing.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        """Get a specific listing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM listings WHERE listing_id = ?', (listing_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_listing(row)
    
    def _row_to_listing(self, row) -> MarketplaceListing:
        """Convert database row to MarketplaceListing"""
        return MarketplaceListing(
            listing_id=row[0],
            title=row[1],
            description=row[2],
            listing_type=ListingType(row[3]),
            status=ListingStatus(row[4]),
            pricing_model=PricingModel(row[5]),
            price=row[6],
            license_type=LicenseType(row[7]),
            author_id=row[8],
            organization_id=row[9],
            tags=json.loads(row[10]) if row[10] else [],
            categories=json.loads(row[11]) if row[11] else [],
            use_cases=json.loads(row[12]) if row[12] else [],
            features=json.loads(row[13]) if row[13] else [],
            requirements=json.loads(row[14]) if row[14] else [],
            demo_url=row[15],
            documentation_url=row[16],
            support_url=row[17],
            version=row[18],
            downloads=row[19],
            rating=row[20],
            review_count=row[21],
            featured=bool(row[22]),
            created_at=row[23],
            updated_at=row[24],
            published_at=row[25],
            metadata=json.loads(row[26]) if row[26] else {}
        )
    
    def search_listings(self, query: str = None, listing_type: ListingType = None,
                       status: ListingStatus = ListingStatus.APPROVED,
                       categories: List[str] = None, tags: List[str] = None,
                       min_price: float = None, max_price: float = None,
                       featured_only: bool = False, limit: int = 50,
                       offset: int = 0) -> List[MarketplaceListing]:
        """Search marketplace listings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if query:
            conditions.append("(title LIKE ? OR description LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if listing_type:
            conditions.append("listing_type = ?")
            params.append(listing_type.value)
        
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        
        if categories:
            for category in categories:
                conditions.append("categories LIKE ?")
                params.append(f"%{category}%")
        
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
        
        if min_price is not None:
            conditions.append("price >= ?")
            params.append(min_price)
        
        if max_price is not None:
            conditions.append("price <= ?")
            params.append(max_price)
        
        if featured_only:
            conditions.append("featured = TRUE")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f'''
            SELECT * FROM listings 
            WHERE {where_clause}
            ORDER BY featured DESC, rating DESC, downloads DESC
            LIMIT ? OFFSET ?
        '''
        
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_listing(row) for row in rows]
    
    def purchase_listing(self, listing_id: str, buyer_id: str, buyer_organization_id: str,
                        referral_code: str = None) -> str:
        """Purchase a marketplace listing"""
        listing = self.get_listing(listing_id)
        if not listing or listing.status != ListingStatus.APPROVED:
            raise ValueError("Listing not available for purchase")
        
        # Generate license key
        license_key = self.licensing_module.generate_license_key(
            listing_id, listing.license_type, buyer_organization_id
        )
        
        # Create download package
        download_url = self._create_download_package(listing, buyer_organization_id)
        
        # Create purchase record
        purchase_id = f"purchase_{uuid.uuid4().hex[:8]}"
        purchase = Purchase(
            purchase_id=purchase_id,
            listing_id=listing_id,
            buyer_id=buyer_id,
            buyer_organization_id=buyer_organization_id,
            price=listing.price,
            currency="USD",
            license_key=license_key,
            download_url=download_url,
            purchased_at=datetime.now().isoformat(),
            expires_at=None,  # Could be set for subscription models
            status="completed",
            metadata={"referral_code": referral_code} if referral_code else {}
        )
        
        self._save_purchase(purchase)
        
        # Update listing stats
        self._increment_downloads(listing_id)
        
        # Track affiliate referral if provided
        if referral_code:
            self.affiliate_engine.track_purchase(purchase_id, referral_code, listing.price)
        
        return purchase_id
    
    def _create_download_package(self, listing: MarketplaceListing, buyer_org_id: str) -> str:
        """Create downloadable package for purchased listing"""
        package_dir = f"{self.downloads_dir}/{listing.listing_id}_{buyer_org_id}"
        os.makedirs(package_dir, exist_ok=True)
        
        # Copy listing files and add license
        source_path = f"{self.listings_dir}/{listing.listing_id}"
        if os.path.exists(source_path):
            shutil.copytree(source_path, f"{package_dir}/content", dirs_exist_ok=True)
        
        # Add license file
        license_content = self.licensing_module.generate_license_file(
            listing.license_type, listing.title, listing.author_id
        )
        with open(f"{package_dir}/LICENSE", 'w') as f:
            f.write(license_content)
        
        # Create ZIP file
        zip_path = f"{package_dir}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    def _save_purchase(self, purchase: Purchase):
        """Save purchase to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO purchases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            purchase.purchase_id, purchase.listing_id, purchase.buyer_id,
            purchase.buyer_organization_id, purchase.price, purchase.currency,
            purchase.license_key, purchase.download_url, purchase.purchased_at,
            purchase.expires_at, purchase.status, json.dumps(purchase.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _increment_downloads(self, listing_id: str):
        """Increment download count for listing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE listings SET downloads = downloads + 1 WHERE listing_id = ?
        ''', (listing_id,))
        
        conn.commit()
        conn.close()
    
    def add_review(self, listing_id: str, reviewer_id: str, reviewer_name: str,
                   rating: int, title: str, content: str) -> str:
        """Add a review to a listing"""
        review_id = f"review_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        review = Review(
            review_id=review_id,
            listing_id=listing_id,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            rating=rating,
            title=title,
            content=content,
            helpful_count=0,
            created_at=now,
            updated_at=now
        )
        
        self._save_review(review)
        self._update_listing_rating(listing_id)
        
        return review_id
    
    def _save_review(self, review: Review):
        """Save review to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            review.review_id, review.listing_id, review.reviewer_id,
            review.reviewer_name, review.rating, review.title,
            review.content, review.helpful_count, review.created_at,
            review.updated_at
        ))
        
        conn.commit()
        conn.close()
    
    def _update_listing_rating(self, listing_id: str):
        """Update average rating for listing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT AVG(rating), COUNT(*) FROM reviews WHERE listing_id = ?
        ''', (listing_id,))
        
        avg_rating, count = cursor.fetchone()
        
        cursor.execute('''
            UPDATE listings SET rating = ?, review_count = ? WHERE listing_id = ?
        ''', (avg_rating or 0.0, count or 0, listing_id))
        
        conn.commit()
        conn.close()
    
    def get_listing_reviews(self, listing_id: str, limit: int = 20, offset: int = 0) -> List[Review]:
        """Get reviews for a listing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM reviews WHERE listing_id = ? 
            ORDER BY helpful_count DESC, created_at DESC
            LIMIT ? OFFSET ?
        ''', (listing_id, limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_review(row) for row in rows]
    
    def _row_to_review(self, row) -> Review:
        """Convert database row to Review"""
        return Review(
            review_id=row[0],
            listing_id=row[1],
            reviewer_id=row[2],
            reviewer_name=row[3],
            rating=row[4],
            title=row[5],
            content=row[6],
            helpful_count=row[7],
            created_at=row[8],
            updated_at=row[9]
        )
    
    def get_user_purchases(self, user_id: str, organization_id: str = None) -> List[Purchase]:
        """Get purchases for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if organization_id:
            cursor.execute('''
                SELECT * FROM purchases 
                WHERE buyer_id = ? AND buyer_organization_id = ?
                ORDER BY purchased_at DESC
            ''', (user_id, organization_id))
        else:
            cursor.execute('''
                SELECT * FROM purchases 
                WHERE buyer_id = ?
                ORDER BY purchased_at DESC
            ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_purchase(row) for row in rows]
    
    def _row_to_purchase(self, row) -> Purchase:
        """Convert database row to Purchase"""
        return Purchase(
            purchase_id=row[0],
            listing_id=row[1],
            buyer_id=row[2],
            buyer_organization_id=row[3],
            price=row[4],
            currency=row[5],
            license_key=row[6],
            download_url=row[7],
            purchased_at=row[8],
            expires_at=row[9],
            status=row[10],
            metadata=json.loads(row[11]) if row[11] else {}
        )
    
    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total listings
        cursor.execute('SELECT COUNT(*) FROM listings WHERE status = ?', (ListingStatus.APPROVED.value,))
        total_listings = cursor.fetchone()[0]
        
        # Total downloads
        cursor.execute('SELECT SUM(downloads) FROM listings')
        total_downloads = cursor.fetchone()[0] or 0
        
        # Total revenue
        cursor.execute('SELECT SUM(price) FROM purchases WHERE status = ?', ("completed",))
        total_revenue = cursor.fetchone()[0] or 0
        
        # Top categories
        cursor.execute('''
            SELECT categories, COUNT(*) as count 
            FROM listings 
            WHERE status = ? 
            GROUP BY categories 
            ORDER BY count DESC 
            LIMIT 5
        ''', (ListingStatus.APPROVED.value,))
        
        top_categories = []
        for row in cursor.fetchall():
            categories = json.loads(row[0]) if row[0] else []
            top_categories.extend(categories[:2])  # Take first 2 categories from each listing
        
        conn.close()
        
        return {
            "total_listings": total_listings,
            "total_downloads": total_downloads,
            "total_revenue": total_revenue,
            "top_categories": list(set(top_categories))[:10]
        }
    
    def _analytics_loop(self):
        """Background analytics processing"""
        while True:
            try:
                # Process analytics every hour
                import time
                time.sleep(3600)
                
                # Could add analytics processing here
                # - Update trending listings
                # - Calculate revenue metrics
                # - Generate marketplace insights
                
            except Exception as e:
                print(f"Marketplace analytics error: {e}")
                import time
                time.sleep(60)
