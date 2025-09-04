"""
SEO + Public Build Directory
Priority 11: Autonomous Growth Engine

Features:
- Auto-generate SEO metadata for systems, agents, bundles
- Sitemap.xml and open graph tagging
- Public directory of builds with filters, tags, and popularity metrics
- Search indexing toggle per org or system
- Activity-based ranking signals
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
import xml.etree.ElementTree as ET


class IndexingStatus(Enum):
    """Indexing status enumeration"""
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"


class ContentType(Enum):
    """Content type enumeration"""
    SYSTEM = "system"
    AGENT = "agent"
    BUNDLE = "bundle"
    TEMPLATE = "template"
    DEMO = "demo"


@dataclass
class SEOMetadata:
    """SEO metadata data structure"""
    content_id: str
    content_type: ContentType
    title: str
    description: str
    keywords: List[str]
    og_title: str
    og_description: str
    og_image: Optional[str]
    og_type: str
    canonical_url: str
    meta_robots: str
    structured_data: Dict
    last_updated: datetime


@dataclass
class PublicListing:
    """Public directory listing data structure"""
    listing_id: str
    content_id: str
    content_type: ContentType
    creator_id: str
    organization_id: str
    title: str
    description: str
    tags: List[str]
    category: str
    popularity_score: float
    view_count: int
    download_count: int
    rating: float
    review_count: int
    indexing_status: IndexingStatus
    featured: bool
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]


@dataclass
class SitemapEntry:
    """Sitemap entry data structure"""
    url: str
    last_modified: datetime
    change_frequency: str
    priority: float


class SEOOptimizer:
    """SEO + Public Build Directory System"""
    
    def __init__(self, base_dir: str, system_delivery, storefront, llm_factory):
        self.base_dir = base_dir
        self.system_delivery = system_delivery
        self.storefront = storefront
        self.llm_factory = llm_factory
        self.db_path = f"{base_dir}/seo_optimizer.db"
        self.sitemap_path = f"{base_dir}/sitemap.xml"
        self._init_database()
        
        # Start sitemap generation loop
        self.sitemap_thread = threading.Thread(target=self._sitemap_loop, daemon=True)
        self.sitemap_thread.start()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # SEO metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seo_metadata (
                content_id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                keywords TEXT,
                og_title TEXT,
                og_description TEXT,
                og_image TEXT,
                og_type TEXT,
                canonical_url TEXT,
                meta_robots TEXT,
                structured_data TEXT,
                last_updated TEXT NOT NULL
            )
        ''')
        
        # Public listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS public_listings (
                listing_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                content_type TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                category TEXT,
                popularity_score REAL DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                download_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                indexing_status TEXT NOT NULL,
                featured BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
        ''')
        
        # Sitemap entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sitemap_entries (
                url TEXT PRIMARY KEY,
                last_modified TEXT NOT NULL,
                change_frequency TEXT NOT NULL,
                priority REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_seo_metadata(self, content_id: str, content_type: ContentType,
                            title: str, description: str, tags: List[str] = None,
                            image_url: Optional[str] = None) -> SEOMetadata:
        """Generate SEO metadata for content"""
        # Generate optimized title
        optimized_title = self._optimize_title(title)
        
        # Generate optimized description
        optimized_description = self._optimize_description(description)
        
        # Generate keywords
        keywords = self._generate_keywords(title, description, tags or [])
        
        # Generate Open Graph data
        og_title = optimized_title
        og_description = optimized_description[:160]  # OG description limit
        og_type = self._get_og_type(content_type)
        
        # Generate canonical URL
        canonical_url = f"/{content_type.value}/{content_id}"
        
        # Generate structured data
        structured_data = self._generate_structured_data(content_id, content_type, title, description)
        
        # Create SEO metadata
        seo_metadata = SEOMetadata(
            content_id=content_id,
            content_type=content_type,
            title=optimized_title,
            description=optimized_description,
            keywords=keywords,
            og_title=og_title,
            og_description=og_description,
            og_image=image_url,
            og_type=og_type,
            canonical_url=canonical_url,
            meta_robots="index, follow",
            structured_data=structured_data,
            last_updated=datetime.now()
        )
        
        # Save metadata
        self._save_seo_metadata(seo_metadata)
        
        return seo_metadata
    
    def _optimize_title(self, title: str) -> str:
        """Optimize title for SEO"""
        # Remove extra spaces and limit length
        optimized = " ".join(title.split())
        if len(optimized) > 60:
            optimized = optimized[:57] + "..."
        return optimized
    
    def _optimize_description(self, description: str) -> str:
        """Optimize description for SEO"""
        # Remove extra spaces and limit length
        optimized = " ".join(description.split())
        if len(optimized) > 160:
            optimized = optimized[:157] + "..."
        return optimized
    
    def _generate_keywords(self, title: str, description: str, tags: List[str]) -> List[str]:
        """Generate keywords from content"""
        keywords = set()
        
        # Add tags
        keywords.update(tags)
        
        # Extract keywords from title and description
        text = f"{title} {description}".lower()
        
        # Common tech keywords
        tech_keywords = [
            "ai", "artificial intelligence", "machine learning", "automation",
            "system", "platform", "tool", "software", "application",
            "api", "integration", "workflow", "productivity", "efficiency"
        ]
        
        for keyword in tech_keywords:
            if keyword in text:
                keywords.add(keyword)
        
        return list(keywords)[:10]  # Limit to 10 keywords
    
    def _get_og_type(self, content_type: ContentType) -> str:
        """Get Open Graph type for content type"""
        og_types = {
            ContentType.SYSTEM: "website",
            ContentType.AGENT: "website",
            ContentType.BUNDLE: "product",
            ContentType.TEMPLATE: "website",
            ContentType.DEMO: "video.other"
        }
        return og_types.get(content_type, "website")
    
    def _generate_structured_data(self, content_id: str, content_type: ContentType,
                                title: str, description: str) -> Dict:
        """Generate structured data for content"""
        base_data = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": title,
            "description": description,
            "url": f"https://systembuilderhub.com/{content_type.value}/{content_id}",
            "applicationCategory": "DeveloperApplication",
            "operatingSystem": "Web Browser",
            "offers": {
                "@type": "Offer",
                "availability": "https://schema.org/InStock"
            }
        }
        
        return base_data
    
    def _save_seo_metadata(self, metadata: SEOMetadata):
        """Save SEO metadata to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO seo_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.content_id,
            metadata.content_type.value,
            metadata.title,
            metadata.description,
            json.dumps(metadata.keywords),
            metadata.og_title,
            metadata.og_description,
            metadata.og_image,
            metadata.og_type,
            metadata.canonical_url,
            metadata.meta_robots,
            json.dumps(metadata.structured_data),
            metadata.last_updated.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def create_public_listing(self, content_id: str, content_type: ContentType,
                            creator_id: str, organization_id: str, title: str,
                            description: str, tags: List[str] = None,
                            category: str = "general", indexing_status: IndexingStatus = IndexingStatus.PUBLIC) -> PublicListing:
        """Create a public listing for content"""
        listing_id = py_secrets.token_urlsafe(16)
        
        # Calculate initial popularity score
        popularity_score = self._calculate_popularity_score(0, 0, 0, 0)
        
        # Create listing
        listing = PublicListing(
            listing_id=listing_id,
            content_id=content_id,
            content_type=content_type,
            creator_id=creator_id,
            organization_id=organization_id,
            title=title,
            description=description,
            tags=tags or [],
            category=category,
            popularity_score=popularity_score,
            view_count=0,
            download_count=0,
            rating=0,
            review_count=0,
            indexing_status=indexing_status,
            featured=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now() if indexing_status == IndexingStatus.PUBLIC else None
        )
        
        # Save listing
        self._save_public_listing(listing)
        
        # Add to sitemap if public
        if indexing_status == IndexingStatus.PUBLIC:
            self._add_to_sitemap(listing)
        
        return listing
    
    def _calculate_popularity_score(self, views: int, downloads: int, rating: float, reviews: int) -> float:
        """Calculate popularity score based on metrics"""
        # Simple scoring algorithm
        view_score = views * 0.1
        download_score = downloads * 0.5
        rating_score = rating * 10
        review_score = reviews * 0.2
        
        return view_score + download_score + rating_score + review_score
    
    def _save_public_listing(self, listing: PublicListing):
        """Save public listing to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO public_listings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing.listing_id,
            listing.content_id,
            listing.content_type.value,
            listing.creator_id,
            listing.organization_id,
            listing.title,
            listing.description,
            json.dumps(listing.tags),
            listing.category,
            listing.popularity_score,
            listing.view_count,
            listing.download_count,
            listing.rating,
            listing.review_count,
            listing.indexing_status.value,
            listing.featured,
            listing.created_at.isoformat(),
            listing.updated_at.isoformat(),
            listing.published_at.isoformat() if listing.published_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def _add_to_sitemap(self, listing: PublicListing):
        """Add listing to sitemap"""
        sitemap_entry = SitemapEntry(
            url=f"https://systembuilderhub.com/{listing.content_type.value}/{listing.content_id}",
            last_modified=listing.updated_at,
            change_frequency="weekly",
            priority=0.7
        )
        
        # Save sitemap entry
        self._save_sitemap_entry(sitemap_entry)
    
    def _save_sitemap_entry(self, entry: SitemapEntry):
        """Save sitemap entry to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sitemap_entries VALUES (?, ?, ?, ?)
        ''', (
            entry.url,
            entry.last_modified.isoformat(),
            entry.change_frequency,
            entry.priority
        ))
        
        conn.commit()
        conn.close()
    
    def update_listing_metrics(self, listing_id: str, views: int = None, downloads: int = None,
                             rating: float = None, reviews: int = None):
        """Update listing metrics and recalculate popularity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current metrics
        cursor.execute('''
            SELECT view_count, download_count, rating, review_count 
            FROM public_listings WHERE listing_id = ?
        ''', (listing_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
        
        current_views, current_downloads, current_rating, current_reviews = row
        
        # Update metrics
        new_views = views if views is not None else current_views
        new_downloads = downloads if downloads is not None else current_downloads
        new_rating = rating if rating is not None else current_rating
        new_reviews = reviews if reviews is not None else current_reviews
        
        # Calculate new popularity score
        popularity_score = self._calculate_popularity_score(new_views, new_downloads, new_rating, new_reviews)
        
        # Update listing
        cursor.execute('''
            UPDATE public_listings 
            SET view_count = ?, download_count = ?, rating = ?, review_count = ?,
                popularity_score = ?, updated_at = ?
            WHERE listing_id = ?
        ''', (
            new_views, new_downloads, new_rating, new_reviews,
            popularity_score, datetime.now().isoformat(), listing_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_public_listings(self, category: str = None, tags: List[str] = None,
                          content_type: ContentType = None, limit: int = 50,
                          sort_by: str = "popularity") -> List[PublicListing]:
        """Get public listings with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM public_listings WHERE indexing_status = 'public'"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if content_type:
            query += " AND content_type = ?"
            params.append(content_type.value)
        
        # Add sorting
        if sort_by == "popularity":
            query += " ORDER BY popularity_score DESC"
        elif sort_by == "recent":
            query += " ORDER BY created_at DESC"
        elif sort_by == "rating":
            query += " ORDER BY rating DESC"
        
        query += " LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        listings = [self._row_to_public_listing(row) for row in rows]
        
        # Filter by tags if specified
        if tags:
            listings = [listing for listing in listings if any(tag in listing.tags for tag in tags)]
        
        return listings
    
    def _row_to_public_listing(self, row) -> PublicListing:
        """Convert database row to PublicListing object"""
        return PublicListing(
            listing_id=row[0],
            content_id=row[1],
            content_type=ContentType(row[2]),
            creator_id=row[3],
            organization_id=row[4],
            title=row[5],
            description=row[6],
            tags=json.loads(row[7]) if row[7] else [],
            category=row[8],
            popularity_score=row[9],
            view_count=row[10],
            download_count=row[11],
            rating=row[12],
            review_count=row[13],
            indexing_status=IndexingStatus(row[14]),
            featured=bool(row[15]),
            created_at=datetime.fromisoformat(row[16]),
            updated_at=datetime.fromisoformat(row[17]),
            published_at=datetime.fromisoformat(row[18]) if row[18] else None
        )
    
    def get_seo_metadata(self, content_id: str) -> Optional[SEOMetadata]:
        """Get SEO metadata for content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM seo_metadata WHERE content_id = ?
        ''', (content_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_seo_metadata(row)
        return None
    
    def _row_to_seo_metadata(self, row) -> SEOMetadata:
        """Convert database row to SEOMetadata object"""
        return SEOMetadata(
            content_id=row[0],
            content_type=ContentType(row[1]),
            title=row[2],
            description=row[3],
            keywords=json.loads(row[4]) if row[4] else [],
            og_title=row[5],
            og_description=row[6],
            og_image=row[7],
            og_type=row[8],
            canonical_url=row[9],
            meta_robots=row[10],
            structured_data=json.loads(row[11]) if row[11] else {},
            last_updated=datetime.fromisoformat(row[12])
        )
    
    def generate_sitemap(self):
        """Generate sitemap.xml file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sitemap_entries ORDER BY priority DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Create XML sitemap
        root = ET.Element("urlset")
        root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        
        for row in rows:
            url_elem = ET.SubElement(root, "url")
            
            loc_elem = ET.SubElement(url_elem, "loc")
            loc_elem.text = row[0]
            
            lastmod_elem = ET.SubElement(url_elem, "lastmod")
            lastmod_elem.text = row[1]
            
            changefreq_elem = ET.SubElement(url_elem, "changefreq")
            changefreq_elem.text = row[2]
            
            priority_elem = ET.SubElement(url_elem, "priority")
            priority_elem.text = str(row[3])
        
        # Write sitemap to file
        tree = ET.ElementTree(root)
        tree.write(self.sitemap_path, encoding="utf-8", xml_declaration=True)
    
    def _sitemap_loop(self):
        """Background sitemap generation loop"""
        while True:
            try:
                self.generate_sitemap()
                time.sleep(86400)  # Generate sitemap daily
                
            except Exception as e:
                print(f"Error in sitemap generation loop: {e}")
                time.sleep(3600)  # Wait 1 hour on error
    
    def get_seo_statistics(self) -> Dict:
        """Get overall SEO statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # SEO metadata statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_metadata,
                COUNT(DISTINCT content_type) as content_types
            FROM seo_metadata
        ''')
        
        seo_stats = cursor.fetchone()
        
        # Public listings statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_listings,
                SUM(CASE WHEN indexing_status = 'public' THEN 1 ELSE 0 END) as public_listings,
                SUM(view_count) as total_views,
                SUM(download_count) as total_downloads,
                AVG(rating) as avg_rating
            FROM public_listings
        ''')
        
        listing_stats = cursor.fetchone()
        
        # Sitemap statistics
        cursor.execute('''
            SELECT COUNT(*) as sitemap_entries
            FROM sitemap_entries
        ''')
        
        sitemap_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_metadata": seo_stats[0] or 0,
            "content_types": seo_stats[1] or 0,
            "total_listings": listing_stats[0] or 0,
            "public_listings": listing_stats[1] or 0,
            "total_views": listing_stats[2] or 0,
            "total_downloads": listing_stats[3] or 0,
            "average_rating": listing_stats[4] or 0,
            "sitemap_entries": sitemap_stats[0] or 0
        }
