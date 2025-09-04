"""
Storefront Module - Native marketplace for agents, templates, and visual assets
Handles publishing, discovery, installation, monetization, and LLM feedback integration
"""

import os
import json
import uuid
import hashlib
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
import shutil
import zipfile
from pathlib import Path


class ListingType(Enum):
    """Types of items that can be published to the storefront"""
    AGENT = "agent"
    TEMPLATE = "template"
    VISUAL_ASSET = "visual_asset"
    SYSTEM = "system"


class ListingStatus(Enum):
    """Status of storefront listings"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class PricingModel(Enum):
    """Pricing models for storefront items"""
    FREE = "free"
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    USAGE_BASED = "usage_based"


class AssetType(Enum):
    """Types of visual assets"""
    UI_KIT = "ui_kit"
    BRAND_KIT = "brand_kit"
    PLACEHOLDER_IMAGE = "placeholder_image"
    ICON_SET = "icon_set"
    ILLUSTRATION = "illustration"


class InstallStatus(Enum):
    """Status of installations"""
    PENDING = "pending"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StorefrontListing:
    """A listing in the storefront"""
    id: str
    title: str
    description: str
    listing_type: ListingType
    status: ListingStatus
    author_id: str
    organization_id: str
    tags: List[str]
    categories: List[str]
    pricing_model: PricingModel
    price: float
    currency: str = "USD"
    license_id: Optional[str] = None
    preview_image: Optional[str] = None
    demo_url: Optional[str] = None
    documentation_url: Optional[str] = None
    source_id: Optional[str] = None  # ID of the original agent/template/system
    install_count: int = 0
    rating: float = 0.0
    review_count: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    published_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class VisualAsset:
    """A visual asset in the storefront"""
    id: str
    listing_id: str
    asset_type: AssetType
    file_path: str
    file_size: int
    mime_type: str
    dimensions: Optional[Dict[str, int]] = None
    color_palette: Optional[List[str]] = None
    tags: List[str] = None
    license_type: str = "commercial"
    commercial_use: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Installation:
    """An installation of a storefront item"""
    id: str
    listing_id: str
    user_id: str
    organization_id: str
    install_path: str
    status: InstallStatus
    license_accepted: bool = False
    customizations: Dict[str, Any] = None
    install_logs: List[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.customizations is None:
            self.customizations = {}
        if self.install_logs is None:
            self.install_logs = []
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Review:
    """A review for a storefront item"""
    id: str
    listing_id: str
    user_id: str
    rating: int  # 1-5 stars
    title: str
    content: str
    helpful_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class UsageMetrics:
    """Usage metrics for storefront items"""
    listing_id: str
    install_count: int = 0
    download_count: int = 0
    view_count: int = 0
    revenue: float = 0.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class Storefront:
    """Main storefront management class"""
    
    def __init__(self, base_dir: str, access_control=None, agent_ecosystem=None, 
                 system_licensing=None, llm_factory=None):
        self.base_dir = Path(base_dir)
        self.storefront_dir = self.base_dir / "storefront"
        self.listings_dir = self.storefront_dir / "listings"
        self.assets_dir = self.storefront_dir / "assets"
        self.installations_dir = self.storefront_dir / "installations"
        
        # Create directories
        self.storefront_dir.mkdir(exist_ok=True)
        self.listings_dir.mkdir(exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)
        self.installations_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self.db_path = self.storefront_dir / "storefront.db"
        self._init_database()
        
        # Dependencies
        self.access_control = access_control
        self.agent_ecosystem = agent_ecosystem
        self.system_licensing = system_licensing
        self.llm_factory = llm_factory
        
        # Load existing data
        self._load_data()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                listing_type TEXT NOT NULL,
                status TEXT NOT NULL,
                author_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                tags TEXT,
                categories TEXT,
                pricing_model TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                license_id TEXT,
                preview_image TEXT,
                demo_url TEXT,
                documentation_url TEXT,
                source_id TEXT,
                install_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                review_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visual_assets (
                id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                dimensions TEXT,
                color_palette TEXT,
                tags TEXT,
                license_type TEXT DEFAULT 'commercial',
                commercial_use BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (listing_id) REFERENCES listings (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS installations (
                id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                install_path TEXT NOT NULL,
                status TEXT NOT NULL,
                license_accepted BOOLEAN DEFAULT 0,
                customizations TEXT,
                install_logs TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (listing_id) REFERENCES listings (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                helpful_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (listing_id) REFERENCES listings (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_metrics (
                listing_id TEXT PRIMARY KEY,
                install_count INTEGER DEFAULT 0,
                download_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0.0,
                last_updated TEXT NOT NULL,
                FOREIGN KEY (listing_id) REFERENCES listings (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_data(self):
        """Load existing data from database"""
        self.listings = {}
        self.visual_assets = {}
        self.installations = {}
        self.reviews = {}
        self.usage_metrics = {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load listings
        cursor.execute('SELECT * FROM listings')
        for row in cursor.fetchall():
            listing = StorefrontListing(
                id=row[0], title=row[1], description=row[2],
                listing_type=ListingType(row[3]), status=ListingStatus(row[4]),
                author_id=row[5], organization_id=row[6], tags=json.loads(row[7] or '[]'),
                categories=json.loads(row[8] or '[]'), pricing_model=PricingModel(row[9]),
                price=row[10], currency=row[11], license_id=row[12],
                preview_image=row[13], demo_url=row[14], documentation_url=row[15],
                source_id=row[16], install_count=row[17], rating=row[18],
                review_count=row[19], created_at=datetime.fromisoformat(row[20]),
                updated_at=datetime.fromisoformat(row[21]),
                published_at=datetime.fromisoformat(row[22]) if row[22] else None
            )
            self.listings[listing.id] = listing
        
        # Load visual assets
        cursor.execute('SELECT * FROM visual_assets')
        for row in cursor.fetchall():
            asset = VisualAsset(
                id=row[0], listing_id=row[1], asset_type=AssetType(row[2]),
                file_path=row[3], file_size=row[4], mime_type=row[5],
                dimensions=json.loads(row[6]) if row[6] else None,
                color_palette=json.loads(row[7]) if row[7] else None,
                tags=json.loads(row[8] or '[]'), license_type=row[9],
                commercial_use=bool(row[10]), created_at=datetime.fromisoformat(row[11])
            )
            self.visual_assets[asset.id] = asset
        
        # Load installations
        cursor.execute('SELECT * FROM installations')
        for row in cursor.fetchall():
            installation = Installation(
                id=row[0], listing_id=row[1], user_id=row[2], organization_id=row[3],
                install_path=row[4], status=InstallStatus(row[5]), license_accepted=bool(row[6]),
                customizations=json.loads(row[7] or '{}'), install_logs=json.loads(row[8] or '[]'),
                created_at=datetime.fromisoformat(row[9]),
                completed_at=datetime.fromisoformat(row[10]) if row[10] else None
            )
            self.installations[installation.id] = installation
        
        # Load reviews
        cursor.execute('SELECT * FROM reviews')
        for row in cursor.fetchall():
            review = Review(
                id=row[0], listing_id=row[1], user_id=row[2], rating=row[3],
                title=row[4], content=row[5], helpful_count=row[6],
                created_at=datetime.fromisoformat(row[7])
            )
            self.reviews[review.id] = review
        
        # Load usage metrics
        cursor.execute('SELECT * FROM usage_metrics')
        for row in cursor.fetchall():
            metrics = UsageMetrics(
                listing_id=row[0], install_count=row[1], download_count=row[2],
                view_count=row[3], revenue=row[4], last_updated=datetime.fromisoformat(row[5])
            )
            self.usage_metrics[metrics.listing_id] = metrics
        
        conn.close()
    
    def _save_data(self):
        """Save data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM listings')
        cursor.execute('DELETE FROM visual_assets')
        cursor.execute('DELETE FROM installations')
        cursor.execute('DELETE FROM reviews')
        cursor.execute('DELETE FROM usage_metrics')
        
        # Save listings
        for listing in self.listings.values():
            cursor.execute('''
                INSERT INTO listings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                listing.id, listing.title, listing.description, listing.listing_type.value,
                listing.status.value, listing.author_id, listing.organization_id,
                json.dumps(listing.tags), json.dumps(listing.categories),
                listing.pricing_model.value, listing.price, listing.currency,
                listing.license_id, listing.preview_image, listing.demo_url,
                listing.documentation_url, listing.source_id, listing.install_count,
                listing.rating, listing.review_count, listing.created_at.isoformat(),
                listing.updated_at.isoformat(),
                listing.published_at.isoformat() if listing.published_at else None
            ))
        
        # Save visual assets
        for asset in self.visual_assets.values():
            cursor.execute('''
                INSERT INTO visual_assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                asset.id, asset.listing_id, asset.asset_type.value, asset.file_path,
                asset.file_size, asset.mime_type, json.dumps(asset.dimensions) if asset.dimensions else None,
                json.dumps(asset.color_palette) if asset.color_palette else None,
                json.dumps(asset.tags), asset.license_type, asset.commercial_use,
                asset.created_at.isoformat()
            ))
        
        # Save installations
        for installation in self.installations.values():
            cursor.execute('''
                INSERT INTO installations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                installation.id, installation.listing_id, installation.user_id,
                installation.organization_id, installation.install_path,
                installation.status.value, installation.license_accepted,
                json.dumps(installation.customizations), json.dumps(installation.install_logs),
                installation.created_at.isoformat(),
                installation.completed_at.isoformat() if installation.completed_at else None
            ))
        
        # Save reviews
        for review in self.reviews.values():
            cursor.execute('''
                INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                review.id, review.listing_id, review.user_id, review.rating,
                review.title, review.content, review.helpful_count, review.created_at.isoformat()
            ))
        
        # Save usage metrics
        for metrics in self.usage_metrics.values():
            cursor.execute('''
                INSERT INTO usage_metrics VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metrics.listing_id, metrics.install_count, metrics.download_count,
                metrics.view_count, metrics.revenue, metrics.last_updated.isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def create_listing(self, title: str, description: str, listing_type: ListingType,
                      author_id: str, organization_id: str, tags: List[str] = None,
                      categories: List[str] = None, pricing_model: PricingModel = PricingModel.FREE,
                      price: float = 0.0, source_id: str = None) -> StorefrontListing:
        """Create a new storefront listing"""
        listing_id = str(uuid.uuid4())
        
        listing = StorefrontListing(
            id=listing_id,
            title=title,
            description=description,
            listing_type=listing_type,
            status=ListingStatus.DRAFT,
            author_id=author_id,
            organization_id=organization_id,
            tags=tags or [],
            categories=categories or [],
            pricing_model=pricing_model,
            price=price,
            source_id=source_id
        )
        
        self.listings[listing_id] = listing
        self._save_data()
        
        # Initialize usage metrics
        self.usage_metrics[listing_id] = UsageMetrics(listing_id=listing_id)
        self._save_data()
        
        return listing
    
    def publish_listing(self, listing_id: str) -> StorefrontListing:
        """Publish a listing to the storefront"""
        if listing_id not in self.listings:
            raise ValueError(f"Listing {listing_id} not found")
        
        listing = self.listings[listing_id]
        listing.status = ListingStatus.PUBLISHED
        listing.published_at = datetime.now()
        listing.updated_at = datetime.now()
        
        self._save_data()
        return listing
    
    def update_listing(self, listing_id: str, **kwargs) -> StorefrontListing:
        """Update a listing"""
        if listing_id not in self.listings:
            raise ValueError(f"Listing {listing_id} not found")
        
        listing = self.listings[listing_id]
        for key, value in kwargs.items():
            if hasattr(listing, key):
                setattr(listing, key, value)
        
        listing.updated_at = datetime.now()
        self._save_data()
        return listing
    
    def search_listings(self, query: str = None, listing_type: ListingType = None,
                       category: str = None, tags: List[str] = None,
                       pricing_model: PricingModel = None, author_id: str = None,
                       status: ListingStatus = ListingStatus.PUBLISHED) -> List[StorefrontListing]:
        """Search for listings"""
        results = []
        
        for listing in self.listings.values():
            if status and listing.status != status:
                continue
            
            if listing_type and listing.listing_type != listing_type:
                continue
            
            if author_id and listing.author_id != author_id:
                continue
            
            if pricing_model and listing.pricing_model != pricing_model:
                continue
            
            if category and category not in listing.categories:
                continue
            
            if tags and not any(tag in listing.tags for tag in tags):
                continue
            
            if query:
                query_lower = query.lower()
                if (query_lower not in listing.title.lower() and
                    query_lower not in listing.description.lower() and
                    not any(query_lower in tag.lower() for tag in listing.tags)):
                    continue
            
            results.append(listing)
        
        # Sort by rating, then by install count
        results.sort(key=lambda x: (x.rating, x.install_count), reverse=True)
        return results
    
    def get_listing(self, listing_id: str) -> Optional[StorefrontListing]:
        """Get a specific listing"""
        return self.listings.get(listing_id)
    
    def add_visual_asset(self, listing_id: str, asset_type: AssetType, file_path: str,
                        mime_type: str, tags: List[str] = None) -> VisualAsset:
        """Add a visual asset to a listing"""
        if listing_id not in self.listings:
            raise ValueError(f"Listing {listing_id} not found")
        
        asset_id = str(uuid.uuid4())
        
        # Copy file to assets directory
        file_name = Path(file_path).name
        new_file_path = self.assets_dir / f"{asset_id}_{file_name}"
        shutil.copy2(file_path, new_file_path)
        
        asset = VisualAsset(
            id=asset_id,
            listing_id=listing_id,
            asset_type=asset_type,
            file_path=str(new_file_path),
            file_size=new_file_path.stat().st_size,
            mime_type=mime_type,
            tags=tags or []
        )
        
        self.visual_assets[asset_id] = asset
        self._save_data()
        return asset
    
    def install_listing(self, listing_id: str, user_id: str, organization_id: str,
                       install_path: str, license_accepted: bool = False) -> Installation:
        """Install a listing"""
        if listing_id not in self.listings:
            raise ValueError(f"Listing {listing_id} not found")
        
        listing = self.listings[listing_id]
        
        # Check license if required
        if listing.license_id and not license_accepted:
            raise ValueError("License must be accepted for installation")
        
        installation_id = str(uuid.uuid4())
        
        installation = Installation(
            id=installation_id,
            listing_id=listing_id,
            user_id=user_id,
            organization_id=organization_id,
            install_path=install_path,
            status=InstallStatus.PENDING,
            license_accepted=license_accepted
        )
        
        self.installations[installation_id] = installation
        
        # Update usage metrics
        if listing_id in self.usage_metrics:
            self.usage_metrics[listing_id].install_count += 1
            self.usage_metrics[listing_id].last_updated = datetime.now()
        
        # Update listing stats
        listing.install_count += 1
        listing.updated_at = datetime.now()
        
        self._save_data()
        
        # Perform actual installation
        self._perform_installation(installation)
        
        return installation
    
    def _perform_installation(self, installation: Installation):
        """Perform the actual installation"""
        try:
            installation.status = InstallStatus.INSTALLING
            self._save_data()
            
            listing = self.listings[installation.listing_id]
            
            # Create installation directory
            install_dir = Path(installation.install_path)
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy source files based on listing type
            if listing.listing_type == ListingType.AGENT and self.agent_ecosystem:
                # Export agent from ecosystem
                agent_export = self.agent_ecosystem.export_agent(
                    listing.source_id, "python_package"
                )
                # Extract to installation directory
                with zipfile.ZipFile(agent_export['file_path'], 'r') as zip_ref:
                    zip_ref.extractall(install_dir)
            
            elif listing.listing_type == ListingType.TEMPLATE:
                # Copy template files
                template_dir = self.base_dir / "templates" / listing.source_id
                if template_dir.exists():
                    shutil.copytree(template_dir, install_dir, dirs_exist_ok=True)
            
            elif listing.listing_type == ListingType.VISUAL_ASSET:
                # Copy visual assets
                assets = [asset for asset in self.visual_assets.values() 
                         if asset.listing_id == listing.id]
                for asset in assets:
                    asset_path = Path(asset.file_path)
                    if asset_path.exists():
                        shutil.copy2(asset_path, install_dir / asset_path.name)
            
            # Create installation metadata
            metadata = {
                "installation_id": installation.id,
                "listing_id": installation.listing_id,
                "installed_at": installation.created_at.isoformat(),
                "license_accepted": installation.license_accepted,
                "customizations": installation.customizations
            }
            
            with open(install_dir / "installation.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            installation.status = InstallStatus.COMPLETED
            installation.completed_at = datetime.now()
            installation.install_logs.append("Installation completed successfully")
            
        except Exception as e:
            installation.status = InstallStatus.FAILED
            installation.install_logs.append(f"Installation failed: {str(e)}")
        
        self._save_data()
    
    def add_review(self, listing_id: str, user_id: str, rating: int, title: str, content: str) -> Review:
        """Add a review to a listing"""
        if listing_id not in self.listings:
            raise ValueError(f"Listing {listing_id} not found")
        
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        review_id = str(uuid.uuid4())
        
        review = Review(
            id=review_id,
            listing_id=listing_id,
            user_id=user_id,
            rating=rating,
            title=title,
            content=content
        )
        
        self.reviews[review_id] = review
        
        # Update listing rating
        listing = self.listings[listing_id]
        listing_reviews = [r for r in self.reviews.values() if r.listing_id == listing_id]
        if listing_reviews:
            listing.rating = sum(r.rating for r in listing_reviews) / len(listing_reviews)
            listing.review_count = len(listing_reviews)
            listing.updated_at = datetime.now()
        
        self._save_data()
        return review
    
    def get_listing_reviews(self, listing_id: str) -> List[Review]:
        """Get all reviews for a listing"""
        return [review for review in self.reviews.values() if review.listing_id == listing_id]
    
    def auto_publish_from_build(self, source_id: str, source_type: ListingType, 
                               build_score: float, test_coverage: float,
                               llm_confidence: float, threshold: float = 0.8) -> Optional[StorefrontListing]:
        """Auto-publish a build output to the storefront based on quality metrics"""
        total_score = (build_score + test_coverage + llm_confidence) / 3
        
        if total_score < threshold:
            return None
        
        # Get source information based on type
        if source_type == ListingType.AGENT and self.agent_ecosystem:
            agent = self.agent_ecosystem.get_agent(source_id)
            if not agent:
                return None
            
            title = f"High-Quality {agent.name} Agent"
            description = f"Auto-published {agent.name} agent with {total_score:.1%} quality score"
            tags = [agent.category, "auto-published", "high-quality"]
            categories = [agent.category]
        
        elif source_type == ListingType.TEMPLATE:
            # Get template information
            title = f"High-Quality Template {source_id}"
            description = f"Auto-published template with {total_score:.1%} quality score"
            tags = ["auto-published", "high-quality", "template"]
            categories = ["templates"]
        
        else:
            return None
        
        # Create listing
        listing = self.create_listing(
            title=title,
            description=description,
            listing_type=source_type,
            author_id="system",  # Auto-published by system
            organization_id="system",
            tags=tags,
            categories=categories,
            pricing_model=PricingModel.FREE,  # Auto-published items are free
            source_id=source_id
        )
        
        # Auto-publish
        self.publish_listing(listing.id)
        
        # Log to LLM factory for feedback
        if self.llm_factory:
            self.llm_factory.log_auto_publish_event({
                "listing_id": listing.id,
                "source_id": source_id,
                "source_type": source_type.value,
                "build_score": build_score,
                "test_coverage": test_coverage,
                "llm_confidence": llm_confidence,
                "total_score": total_score,
                "auto_published": True
            })
        
        return listing
    
    def get_trending_listings(self, limit: int = 10) -> List[StorefrontListing]:
        """Get trending listings based on recent activity"""
        # Get listings with recent installations and high ratings
        recent_installations = [
            inst for inst in self.installations.values()
            if inst.created_at > datetime.now() - timedelta(days=7)
        ]
        
        # Count recent installations per listing
        installation_counts = {}
        for inst in recent_installations:
            installation_counts[inst.listing_id] = installation_counts.get(inst.listing_id, 0) + 1
        
        # Sort by recent installations and rating
        trending = []
        for listing in self.listings.values():
            if listing.status == ListingStatus.PUBLISHED:
                recent_installs = installation_counts.get(listing.id, 0)
                trending.append((listing, recent_installs, listing.rating))
        
        trending.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return [listing for listing, _, _ in trending[:limit]]
    
    def get_user_listings(self, user_id: str) -> List[StorefrontListing]:
        """Get all listings by a user"""
        return [listing for listing in self.listings.values() 
                if listing.author_id == user_id]
    
    def delete_listing(self, listing_id: str, user_id: str) -> bool:
        """Delete a listing (only by author)"""
        if listing_id not in self.listings:
            return False
        
        listing = self.listings[listing_id]
        if listing.author_id != user_id:
            return False
        
        # Mark as removed instead of actually deleting
        listing.status = ListingStatus.REMOVED
        listing.updated_at = datetime.now()
        
        self._save_data()
        return True
    
    def get_installation_status(self, installation_id: str) -> Optional[Installation]:
        """Get installation status"""
        return self.installations.get(installation_id)
    
    def get_usage_metrics(self, listing_id: str) -> Optional[UsageMetrics]:
        """Get usage metrics for a listing"""
        return self.usage_metrics.get(listing_id)
    
    def increment_view_count(self, listing_id: str):
        """Increment view count for a listing"""
        if listing_id in self.usage_metrics:
            self.usage_metrics[listing_id].view_count += 1
            self.usage_metrics[listing_id].last_updated = datetime.now()
            self._save_data()
    
    def export_listing_data(self, listing_id: str) -> Dict[str, Any]:
        """Export listing data for LLM training"""
        if listing_id not in self.listings:
            return {}
        
        listing = self.listings[listing_id]
        reviews = self.get_listing_reviews(listing_id)
        metrics = self.get_usage_metrics(listing_id)
        
        return {
            "listing": asdict(listing),
            "reviews": [asdict(review) for review in reviews],
            "metrics": asdict(metrics) if metrics else {},
            "installations": [
                asdict(inst) for inst in self.installations.values()
                if inst.listing_id == listing_id
            ]
        }
