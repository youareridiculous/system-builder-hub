"""
Demo Generator & Auto Microsite Builder
Priority 11: Autonomous Growth Engine

Features:
- Auto-generate embeddable demo widgets from system builds
- "Launch demo" button on public storefront
- Microsite generator: landing page + video walkthrough + CTA
- Demo analytics (views, conversions, time-on-page)
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


class DemoStatus(Enum):
    """Demo status enumeration"""
    GENERATING = "generating"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class DemoType(Enum):
    """Demo type enumeration"""
    EMBEDDED_WIDGET = "embedded_widget"
    MICROSITE = "microsite"
    VIDEO_WALKTHROUGH = "video_walkthrough"
    INTERACTIVE_DEMO = "interactive_demo"


@dataclass
class Demo:
    """Demo data structure"""
    demo_id: str
    system_id: str
    creator_id: str
    demo_type: DemoType
    status: DemoStatus
    title: str
    description: str
    embed_code: str
    demo_url: str
    microsite_url: Optional[str]
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    features_highlighted: List[str]
    target_audience: str
    conversion_goal: str
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]


@dataclass
class DemoAnalytics:
    """Demo analytics data structure"""
    demo_id: str
    total_views: int
    unique_visitors: int
    time_on_page: float
    conversion_count: int
    conversion_rate: float
    bounce_rate: float
    avg_session_duration: float
    last_updated: datetime


@dataclass
class Microsite:
    """Microsite data structure"""
    site_id: str
    demo_id: str
    url_slug: str
    title: str
    hero_text: str
    description: str
    features: List[str]
    video_embed: Optional[str]
    cta_text: str
    cta_url: str
    custom_css: Optional[str]
    custom_js: Optional[str]
    seo_meta: Dict
    created_at: datetime
    updated_at: datetime


class DemoGenerator:
    """Demo Generator & Auto Microsite Builder"""
    
    def __init__(self, base_dir: str, system_delivery, storefront, llm_factory):
        self.base_dir = base_dir
        self.system_delivery = system_delivery
        self.storefront = storefront
        self.llm_factory = llm_factory
        self.db_path = f"{base_dir}/demo_generator.db"
        self.microsites_dir = f"{base_dir}/microsites"
        self._init_database()
        self._init_directories()
        
        # Start analytics loop
        self.analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        self.analytics_thread.start()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Demos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS demos (
                demo_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                demo_type TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                embed_code TEXT,
                demo_url TEXT,
                microsite_url TEXT,
                video_url TEXT,
                thumbnail_url TEXT,
                features_highlighted TEXT,
                target_audience TEXT,
                conversion_goal TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
        ''')
        
        # Demo analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS demo_analytics (
                demo_id TEXT PRIMARY KEY,
                total_views INTEGER DEFAULT 0,
                unique_visitors INTEGER DEFAULT 0,
                time_on_page REAL DEFAULT 0,
                conversion_count INTEGER DEFAULT 0,
                conversion_rate REAL DEFAULT 0,
                bounce_rate REAL DEFAULT 0,
                avg_session_duration REAL DEFAULT 0,
                last_updated TEXT NOT NULL
            )
        ''')
        
        # Microsites table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS microsites (
                site_id TEXT PRIMARY KEY,
                demo_id TEXT NOT NULL,
                url_slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                hero_text TEXT,
                description TEXT,
                features TEXT,
                video_embed TEXT,
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
        os.makedirs(self.microsites_dir, exist_ok=True)
    
    def generate_demo(self, system_id: str, creator_id: str, demo_type: DemoType,
                     title: str, description: str, features_highlighted: List[str] = None,
                     target_audience: str = "", conversion_goal: str = "signup") -> Demo:
        """Generate a demo for a system"""
        demo_id = py_secrets.token_urlsafe(16)
        
        # Generate embed code
        embed_code = self._generate_embed_code(demo_id, system_id)
        
        # Generate demo URL
        demo_url = f"/demo/{demo_id}"
        
        # Create demo
        demo = Demo(
            demo_id=demo_id,
            system_id=system_id,
            creator_id=creator_id,
            demo_type=demo_type,
            status=DemoStatus.GENERATING,
            title=title,
            description=description,
            embed_code=embed_code,
            demo_url=demo_url,
            microsite_url=None,
            video_url=None,
            thumbnail_url=None,
            features_highlighted=features_highlighted or [],
            target_audience=target_audience,
            conversion_goal=conversion_goal,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=None
        )
        
        # Save demo
        self._save_demo(demo)
        
        # Generate demo content based on type
        if demo_type == DemoType.EMBEDDED_WIDGET:
            self._generate_embedded_widget(demo)
        elif demo_type == DemoType.MICROSITE:
            self._generate_microsite(demo)
        elif demo_type == DemoType.VIDEO_WALKTHROUGH:
            self._generate_video_walkthrough(demo)
        elif demo_type == DemoType.INTERACTIVE_DEMO:
            self._generate_interactive_demo(demo)
        
        # Update status to active
        demo.status = DemoStatus.ACTIVE
        demo.published_at = datetime.now()
        self._update_demo(demo)
        
        return demo
    
    def _generate_embed_code(self, demo_id: str, system_id: str) -> str:
        """Generate embed code for demo"""
        return f"""
<div id="system-builder-demo-{demo_id}" style="width: 100%; height: 600px; border: 1px solid #ddd; border-radius: 8px;">
    <iframe src="/demo/{demo_id}/embed" 
            style="width: 100%; height: 100%; border: none; border-radius: 8px;"
            allowfullscreen>
    </iframe>
</div>
<script>
    // Demo analytics tracking
    (function() {{
        var demoFrame = document.getElementById('system-builder-demo-{demo_id}');
        if (demoFrame) {{
            demoFrame.addEventListener('load', function() {{
                fetch('/api/demo/track-view/{demo_id}', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        referrer: document.referrer,
                        user_agent: navigator.userAgent,
                        timestamp: new Date().toISOString()
                    }})
                }});
            }});
        }}
    }})();
</script>
        """
    
    def _generate_embedded_widget(self, demo: Demo):
        """Generate embedded widget demo"""
        # Create widget HTML file
        widget_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{demo.title} - Demo</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .demo-container {{
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .feature-highlight {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="demo-container">
        <h2>{demo.title}</h2>
        <p class="lead">{demo.description}</p>
        
        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5>System Preview</h5>
                    </div>
                    <div class="card-body">
                        <div class="text-center py-5">
                            <i class="fas fa-cog fa-3x text-muted mb-3"></i>
                            <p>Interactive system demo would be embedded here</p>
                            <button class="btn btn-primary" onclick="launchFullDemo()">
                                Launch Full Demo
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <h5>Key Features</h5>
                {self._generate_features_html(demo.features_highlighted)}
                
                <div class="mt-4">
                    <h6>Target Audience</h6>
                    <p class="text-muted">{demo.target_audience}</p>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function launchFullDemo() {{
            window.open('/demo/{demo.demo_id}/full', '_blank');
        }}
    </script>
</body>
</html>
        """
        
        # Save widget HTML
        widget_file_path = os.path.join(self.microsites_dir, f"widget_{demo.demo_id}.html")
        with open(widget_file_path, 'w') as f:
            f.write(widget_html)
    
    def _generate_features_html(self, features: List[str]) -> str:
        """Generate HTML for features section"""
        html = ""
        for feature in features:
            html += f"""
                <div class="feature-highlight">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    {feature}
                </div>
            """
        return html
    
    def _generate_microsite(self, demo: Demo):
        """Generate microsite for demo"""
        # Generate URL slug
        url_slug = self._generate_url_slug(demo.title)
        
        # Create microsite
        microsite = Microsite(
            site_id=py_secrets.token_urlsafe(16),
            demo_id=demo.demo_id,
            url_slug=url_slug,
            title=demo.title,
            hero_text=f"Experience {demo.title}",
            description=demo.description,
            features=demo.features_highlighted,
            video_embed=None,
            cta_text="Try This System",
            cta_url=f"/system/{demo.system_id}",
            custom_css=None,
            custom_js=None,
            seo_meta={
                "title": f"{demo.title} - Demo",
                "description": demo.description[:160],
                "keywords": ", ".join(demo.features_highlighted),
                "og_title": demo.title,
                "og_description": demo.description[:160]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save microsite
        self._save_microsite(microsite)
        
        # Generate microsite HTML
        self._generate_microsite_html(microsite, demo)
        
        # Update demo with microsite URL
        demo.microsite_url = f"/microsite/{url_slug}"
        self._update_demo(demo)
    
    def _generate_url_slug(self, title: str) -> str:
        """Generate URL slug from title"""
        slug = title.lower().replace(' ', '-').replace('_', '-')
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
            SELECT COUNT(*) FROM microsites WHERE url_slug = ?
        ''', (slug,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def _save_microsite(self, microsite: Microsite):
        """Save microsite to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO microsites VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            microsite.site_id,
            microsite.demo_id,
            microsite.url_slug,
            microsite.title,
            microsite.hero_text,
            microsite.description,
            json.dumps(microsite.features),
            microsite.video_embed,
            microsite.cta_text,
            microsite.cta_url,
            microsite.custom_css,
            microsite.custom_js,
            json.dumps(microsite.seo_meta),
            microsite.created_at.isoformat(),
            microsite.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_microsite_html(self, microsite: Microsite, demo: Demo):
        """Generate HTML file for microsite"""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{microsite.seo_meta['title']}</title>
    <meta name="description" content="{microsite.seo_meta['description']}">
    <meta name="keywords" content="{microsite.seo_meta['keywords']}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{microsite.seo_meta['og_title']}">
    <meta property="og:description" content="{microsite.seo_meta['og_description']}">
    <meta property="og:type" content="website">
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .hero-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 100px 0;
        }}
        .demo-preview {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 40px;
            margin: 40px 0;
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
        {microsite.custom_css or ''}
    </style>
</head>
<body>
    <!-- Hero Section -->
    <section class="hero-section">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-lg-8">
                    <h1 class="display-4 fw-bold mb-4">{microsite.hero_text}</h1>
                    <p class="lead mb-4">{microsite.description}</p>
                    <a href="{microsite.cta_url}" class="btn btn-light btn-lg">
                        <i class="fas fa-rocket me-2"></i>{microsite.cta_text}
                    </a>
                </div>
                <div class="col-lg-4">
                    <div class="demo-preview text-center">
                        <i class="fas fa-play-circle fa-4x text-primary mb-3"></i>
                        <h5>Interactive Demo</h5>
                        <p>Experience the system in action</p>
                        <button class="btn btn-primary" onclick="launchDemo()">
                            Launch Demo
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="py-5">
        <div class="container">
            <h2 class="text-center mb-5">Key Features</h2>
            <div class="row">
                {self._generate_microsite_features_html(microsite.features)}
            </div>
        </div>
    </section>

    <!-- Demo Section -->
    <section class="py-5 bg-light">
        <div class="container">
            <div class="row">
                <div class="col-lg-8 mx-auto text-center">
                    <h2>See It In Action</h2>
                    <p class="lead mb-4">Watch how this system can transform your workflow</p>
                    <div class="ratio ratio-16x9">
                        <iframe src="{demo.demo_url}/embed" 
                                title="{demo.title} Demo"
                                allowfullscreen>
                        </iframe>
                    </div>
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
                    <p class="lead mb-4">Join thousands of users who have already benefited from this system.</p>
                    <a href="{microsite.cta_url}" class="btn btn-primary btn-lg">
                        <i class="fas fa-rocket me-2"></i>{microsite.cta_text}
                    </a>
                </div>
            </div>
        </div>
    </section>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function launchDemo() {{
            window.open('{demo.demo_url}', '_blank');
        }}
        
        // Track microsite views
        fetch('/api/demo/track-view/{demo.demo_id}', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
                referrer: document.referrer,
                user_agent: navigator.userAgent,
                timestamp: new Date().toISOString(),
                page_type: 'microsite'
            }})
        }});
    </script>
    {microsite.custom_js or ''}
</body>
</html>
        """
        
        # Save HTML file
        html_file_path = os.path.join(self.microsites_dir, f"{microsite.url_slug}.html")
        with open(html_file_path, 'w') as f:
            f.write(html_content)
    
    def _generate_microsite_features_html(self, features: List[str]) -> str:
        """Generate HTML for microsite features section"""
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
    
    def _generate_video_walkthrough(self, demo: Demo):
        """Generate video walkthrough demo"""
        # This would integrate with video generation services
        # For now, we'll create a placeholder
        demo.video_url = f"/demo/{demo.demo_id}/video"
        self._update_demo(demo)
    
    def _generate_interactive_demo(self, demo: Demo):
        """Generate interactive demo"""
        # This would create an interactive demo interface
        # For now, we'll create a placeholder
        demo.demo_url = f"/demo/{demo.demo_id}/interactive"
        self._update_demo(demo)
    
    def _save_demo(self, demo: Demo):
        """Save demo to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO demos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            demo.demo_id,
            demo.system_id,
            demo.creator_id,
            demo.demo_type.value,
            demo.status.value,
            demo.title,
            demo.description,
            demo.embed_code,
            demo.demo_url,
            demo.microsite_url,
            demo.video_url,
            demo.thumbnail_url,
            json.dumps(demo.features_highlighted),
            demo.target_audience,
            demo.conversion_goal,
            demo.created_at.isoformat(),
            demo.updated_at.isoformat(),
            demo.published_at.isoformat() if demo.published_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def _update_demo(self, demo: Demo):
        """Update demo in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE demos 
            SET status = ?, demo_url = ?, microsite_url = ?, video_url = ?, 
                thumbnail_url = ?, published_at = ?, updated_at = ?
            WHERE demo_id = ?
        ''', (
            demo.status.value,
            demo.demo_url,
            demo.microsite_url,
            demo.video_url,
            demo.thumbnail_url,
            demo.published_at.isoformat() if demo.published_at else None,
            demo.updated_at.isoformat(),
            demo.demo_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_demo(self, demo_id: str) -> Optional[Demo]:
        """Get demo by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM demos WHERE demo_id = ?
        ''', (demo_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_demo(row)
        return None
    
    def _row_to_demo(self, row) -> Demo:
        """Convert database row to Demo object"""
        return Demo(
            demo_id=row[0],
            system_id=row[1],
            creator_id=row[2],
            demo_type=DemoType(row[3]),
            status=DemoStatus(row[4]),
            title=row[5],
            description=row[6],
            embed_code=row[7],
            demo_url=row[8],
            microsite_url=row[9],
            video_url=row[10],
            thumbnail_url=row[11],
            features_highlighted=json.loads(row[12]) if row[12] else [],
            target_audience=row[13],
            conversion_goal=row[14],
            created_at=datetime.fromisoformat(row[15]),
            updated_at=datetime.fromisoformat(row[16]),
            published_at=datetime.fromisoformat(row[17]) if row[17] else None
        )
    
    def track_demo_view(self, demo_id: str, view_data: Dict):
        """Track demo view for analytics"""
        # Save view data to analytics
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update analytics
        cursor.execute('''
            UPDATE demo_analytics 
            SET total_views = total_views + 1, last_updated = ?
            WHERE demo_id = ?
        ''', (datetime.now().isoformat(), demo_id))
        
        # If no analytics record exists, create one
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO demo_analytics VALUES (?, 1, 0, 0, 0, 0, 0, 0, ?)
            ''', (demo_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_demo_analytics(self, demo_id: str) -> Optional[DemoAnalytics]:
        """Get analytics for a demo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM demo_analytics WHERE demo_id = ?
        ''', (demo_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_demo_analytics(row)
        return None
    
    def _row_to_demo_analytics(self, row) -> DemoAnalytics:
        """Convert database row to DemoAnalytics object"""
        return DemoAnalytics(
            demo_id=row[0],
            total_views=row[1],
            unique_visitors=row[2],
            time_on_page=row[3],
            conversion_count=row[4],
            conversion_rate=row[5],
            bounce_rate=row[6],
            avg_session_duration=row[7],
            last_updated=datetime.fromisoformat(row[8])
        )
    
    def get_creator_demos(self, creator_id: str) -> List[Demo]:
        """Get demos created by a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM demos 
            WHERE creator_id = ?
            ORDER BY created_at DESC
        ''', (creator_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_demo(row) for row in rows]
    
    def _analytics_loop(self):
        """Background analytics processing loop"""
        while True:
            try:
                # Update demo analytics
                time.sleep(3600)  # Run every hour
                
            except Exception as e:
                print(f"Error in demo analytics loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def get_demo_statistics(self) -> Dict:
        """Get overall demo statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Demo statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_demos,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_demos,
                COUNT(DISTINCT creator_id) as active_creators
            FROM demos
        ''')
        
        demo_stats = cursor.fetchone()
        
        # Analytics statistics
        cursor.execute('''
            SELECT 
                SUM(total_views) as total_views,
                SUM(conversion_count) as total_conversions,
                AVG(conversion_rate) as avg_conversion_rate
            FROM demo_analytics
        ''')
        
        analytics_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_demos": demo_stats[0] or 0,
            "active_demos": demo_stats[1] or 0,
            "active_creators": demo_stats[2] or 0,
            "total_views": analytics_stats[0] or 0,
            "total_conversions": analytics_stats[1] or 0,
            "average_conversion_rate": analytics_stats[2] or 0
        }
