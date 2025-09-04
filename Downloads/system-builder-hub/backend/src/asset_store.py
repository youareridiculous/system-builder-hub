"""
Visual Asset Store Module - AI-generated UI kits, brand kits, images, and visual assets
Handles asset management, licensing, preview generation, and integration with the storefront
"""

import os
import json
import uuid
import hashlib
import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import shutil
import zipfile
from pathlib import Path
import mimetypes
from PIL import Image, ImageDraw, ImageFont
import io
import base64


class AssetCategory(Enum):
    """Categories of visual assets"""
    UI_KIT = "ui_kit"
    BRAND_KIT = "brand_kit"
    PLACEHOLDER_IMAGE = "placeholder_image"
    ICON_SET = "icon_set"
    ILLUSTRATION = "illustration"
    PHOTOGRAPHY = "photography"
    ANIMATION = "animation"
    VIDEO = "video"
    FONT = "font"
    TEXTURE = "texture"


class AssetLicense(Enum):
    """License types for visual assets"""
    COMMERCIAL = "commercial"
    PERSONAL = "personal"
    EDUCATIONAL = "educational"
    CREATIVE_COMMONS = "creative_commons"
    CUSTOM = "custom"


class AssetStatus(Enum):
    """Status of visual assets"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    REMOVED = "removed"


@dataclass
class VisualAsset:
    """A visual asset in the store"""
    id: str
    title: str
    description: str
    category: AssetCategory
    author_id: str
    organization_id: str
    file_path: str
    file_size: int
    mime_type: str
    dimensions: Optional[Dict[str, int]] = None
    color_palette: Optional[List[str]] = None
    tags: List[str] = None
    license_type: AssetLicense = AssetLicense.COMMERCIAL
    commercial_use: bool = True
    attribution_required: bool = False
    price: float = 0.0
    currency: str = "USD"
    download_count: int = 0
    view_count: int = 0
    rating: float = 0.0
    review_count: int = 0
    status: AssetStatus = AssetStatus.DRAFT
    created_at: datetime = None
    updated_at: datetime = None
    published_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class AssetPreview:
    """Preview information for a visual asset"""
    asset_id: str
    thumbnail_path: str
    preview_path: str
    color_scheme: List[str] = None
    usage_examples: List[str] = None
    technical_specs: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.color_scheme is None:
            self.color_scheme = []
        if self.usage_examples is None:
            self.usage_examples = []
        if self.technical_specs is None:
            self.technical_specs = {}
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class AssetCollection:
    """A collection of related visual assets"""
    id: str
    title: str
    description: str
    author_id: str
    organization_id: str
    assets: List[str]  # List of asset IDs
    theme: str = ""
    color_scheme: List[str] = None
    tags: List[str] = None
    price: float = 0.0
    currency: str = "USD"
    status: AssetStatus = AssetStatus.DRAFT
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.color_scheme is None:
            self.color_scheme = []
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class AssetStore:
    """Main visual asset store management class"""
    
    def __init__(self, base_dir: str, storefront=None):
        self.base_dir = Path(base_dir)
        self.asset_store_dir = self.base_dir / "asset_store"
        self.assets_dir = self.asset_store_dir / "assets"
        self.previews_dir = self.asset_store_dir / "previews"
        self.collections_dir = self.asset_store_dir / "collections"
        self.temp_dir = self.asset_store_dir / "temp"
        
        # Create directories
        self.asset_store_dir.mkdir(exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)
        self.previews_dir.mkdir(exist_ok=True)
        self.collections_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self.db_path = self.asset_store_dir / "asset_store.db"
        self._init_database()
        
        # Dependencies
        self.storefront = storefront
        
        # Load existing data
        self._load_data()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visual_assets (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                author_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                dimensions TEXT,
                color_palette TEXT,
                tags TEXT,
                license_type TEXT NOT NULL,
                commercial_use BOOLEAN DEFAULT 1,
                attribution_required BOOLEAN DEFAULT 0,
                price REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'USD',
                download_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                review_count INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asset_previews (
                asset_id TEXT PRIMARY KEY,
                thumbnail_path TEXT NOT NULL,
                preview_path TEXT NOT NULL,
                color_scheme TEXT,
                usage_examples TEXT,
                technical_specs TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (asset_id) REFERENCES visual_assets (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asset_collections (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                author_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                assets TEXT NOT NULL,
                theme TEXT,
                color_scheme TEXT,
                tags TEXT,
                price REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'USD',
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_data(self):
        """Load existing data from database"""
        self.assets = {}
        self.previews = {}
        self.collections = {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load visual assets
        cursor.execute('SELECT * FROM visual_assets')
        for row in cursor.fetchall():
            asset = VisualAsset(
                id=row[0], title=row[1], description=row[2], category=AssetCategory(row[3]),
                author_id=row[4], organization_id=row[5], file_path=row[6], file_size=row[7],
                mime_type=row[8], dimensions=json.loads(row[9]) if row[9] else None,
                color_palette=json.loads(row[10]) if row[10] else None,
                tags=json.loads(row[11] or '[]'), license_type=AssetLicense(row[12]),
                commercial_use=bool(row[13]), attribution_required=bool(row[14]),
                price=row[15], currency=row[16], download_count=row[17], view_count=row[18],
                rating=row[19], review_count=row[20], status=AssetStatus(row[21]),
                created_at=datetime.fromisoformat(row[22]), updated_at=datetime.fromisoformat(row[23]),
                published_at=datetime.fromisoformat(row[24]) if row[24] else None
            )
            self.assets[asset.id] = asset
        
        # Load asset previews
        cursor.execute('SELECT * FROM asset_previews')
        for row in cursor.fetchall():
            preview = AssetPreview(
                asset_id=row[0], thumbnail_path=row[1], preview_path=row[2],
                color_scheme=json.loads(row[3]) if row[3] else None,
                usage_examples=json.loads(row[4]) if row[4] else None,
                technical_specs=json.loads(row[5]) if row[5] else None,
                created_at=datetime.fromisoformat(row[6])
            )
            self.previews[preview.asset_id] = preview
        
        # Load asset collections
        cursor.execute('SELECT * FROM asset_collections')
        for row in cursor.fetchall():
            collection = AssetCollection(
                id=row[0], title=row[1], description=row[2], author_id=row[3],
                organization_id=row[4], assets=json.loads(row[5]), theme=row[6],
                color_scheme=json.loads(row[7]) if row[7] else None,
                tags=json.loads(row[8] or '[]'), price=row[9], currency=row[10],
                status=AssetStatus(row[11]), created_at=datetime.fromisoformat(row[12]),
                updated_at=datetime.fromisoformat(row[13])
            )
            self.collections[collection.id] = collection
        
        conn.close()
    
    def _save_data(self):
        """Save data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM visual_assets')
        cursor.execute('DELETE FROM asset_previews')
        cursor.execute('DELETE FROM asset_collections')
        
        # Save visual assets
        for asset in self.assets.values():
            cursor.execute('''
                INSERT INTO visual_assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                asset.id, asset.title, asset.description, asset.category.value,
                asset.author_id, asset.organization_id, asset.file_path, asset.file_size,
                asset.mime_type, json.dumps(asset.dimensions) if asset.dimensions else None,
                json.dumps(asset.color_palette) if asset.color_palette else None,
                json.dumps(asset.tags), asset.license_type.value, asset.commercial_use,
                asset.attribution_required, asset.price, asset.currency, asset.download_count,
                asset.view_count, asset.rating, asset.review_count, asset.status.value,
                asset.created_at.isoformat(), asset.updated_at.isoformat(),
                asset.published_at.isoformat() if asset.published_at else None
            ))
        
        # Save asset previews
        for preview in self.previews.values():
            cursor.execute('''
                INSERT INTO asset_previews VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                preview.asset_id, preview.thumbnail_path, preview.preview_path,
                json.dumps(preview.color_scheme), json.dumps(preview.usage_examples),
                json.dumps(preview.technical_specs), preview.created_at.isoformat()
            ))
        
        # Save asset collections
        for collection in self.collections.values():
            cursor.execute('''
                INSERT INTO asset_collections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                collection.id, collection.title, collection.description, collection.author_id,
                collection.organization_id, json.dumps(collection.assets), collection.theme,
                json.dumps(collection.color_scheme), json.dumps(collection.tags),
                collection.price, collection.currency, collection.status.value,
                collection.created_at.isoformat(), collection.updated_at.isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def upload_asset(self, title: str, description: str, category: AssetCategory,
                    author_id: str, organization_id: str, file_path: str,
                    tags: List[str] = None, license_type: AssetLicense = AssetLicense.COMMERCIAL,
                    price: float = 0.0) -> VisualAsset:
        """Upload a new visual asset"""
        asset_id = str(uuid.uuid4())
        
        # Copy file to assets directory
        file_name = Path(file_path).name
        new_file_path = self.assets_dir / f"{asset_id}_{file_name}"
        shutil.copy2(file_path, new_file_path)
        
        # Get file information
        file_size = new_file_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(new_file_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        
        # Extract dimensions and color palette for images
        dimensions = None
        color_palette = None
        if mime_type.startswith('image/'):
            try:
                with Image.open(new_file_path) as img:
                    dimensions = {"width": img.width, "height": img.height}
                    color_palette = self._extract_color_palette(img)
            except Exception as e:
                print(f"Error processing image: {e}")
        
        asset = VisualAsset(
            id=asset_id,
            title=title,
            description=description,
            category=category,
            author_id=author_id,
            organization_id=organization_id,
            file_path=str(new_file_path),
            file_size=file_size,
            mime_type=mime_type,
            dimensions=dimensions,
            color_palette=color_palette,
            tags=tags or [],
            license_type=license_type,
            price=price
        )
        
        self.assets[asset_id] = asset
        
        # Generate preview
        self._generate_preview(asset)
        
        self._save_data()
        return asset
    
    def _extract_color_palette(self, image: Image.Image, num_colors: int = 8) -> List[str]:
        """Extract color palette from image"""
        try:
            # Resize image for faster processing
            img_small = image.resize((150, 150))
            
            # Convert to RGB if necessary
            if img_small.mode != 'RGB':
                img_small = img_small.convert('RGB')
            
            # Get colors
            colors = img_small.getcolors(maxcolors=1000)
            if not colors:
                return []
            
            # Sort by frequency and get top colors
            colors.sort(key=lambda x: x[0], reverse=True)
            top_colors = colors[:num_colors]
            
            # Convert to hex
            palette = []
            for count, (r, g, b) in top_colors:
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                palette.append(hex_color)
            
            return palette
        except Exception as e:
            print(f"Error extracting color palette: {e}")
            return []
    
    def _generate_preview(self, asset: VisualAsset):
        """Generate preview for an asset"""
        try:
            if asset.mime_type.startswith('image/'):
                self._generate_image_preview(asset)
            else:
                self._generate_generic_preview(asset)
        except Exception as e:
            print(f"Error generating preview for {asset.id}: {e}")
    
    def _generate_image_preview(self, asset: VisualAsset):
        """Generate preview for image assets"""
        try:
            with Image.open(asset.file_path) as img:
                # Generate thumbnail
                thumbnail_size = (200, 200)
                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                thumbnail_path = self.previews_dir / f"{asset.id}_thumb.png"
                img.save(thumbnail_path, "PNG")
                
                # Generate preview (larger)
                preview_size = (800, 600)
                img_copy = img.copy()
                img_copy.thumbnail(preview_size, Image.Resampling.LANCZOS)
                preview_path = self.previews_dir / f"{asset.id}_preview.png"
                img_copy.save(preview_path, "PNG")
                
                # Create usage examples
                usage_examples = self._create_usage_examples(img)
                
                # Technical specs
                technical_specs = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "file_size": asset.file_size,
                    "mime_type": asset.mime_type
                }
                
                preview = AssetPreview(
                    asset_id=asset.id,
                    thumbnail_path=str(thumbnail_path),
                    preview_path=str(preview_path),
                    color_scheme=asset.color_palette,
                    usage_examples=usage_examples,
                    technical_specs=technical_specs
                )
                
                self.previews[asset.id] = preview
                
        except Exception as e:
            print(f"Error generating image preview: {e}")
    
    def _generate_generic_preview(self, asset: VisualAsset):
        """Generate generic preview for non-image assets"""
        # Create a generic preview image
        preview_size = (400, 300)
        img = Image.new('RGB', preview_size, color='#f0f0f0')
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        text = f"{asset.category.value.upper()}\n{asset.title}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (preview_size[0] - text_width) // 2
        y = (preview_size[1] - text_height) // 2
        
        draw.text((x, y), text, fill='#333333', font=font)
        
        # Save preview
        preview_path = self.previews_dir / f"{asset.id}_preview.png"
        img.save(preview_path, "PNG")
        
        # Create thumbnail
        thumbnail_size = (200, 150)
        img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        thumbnail_path = self.previews_dir / f"{asset.id}_thumb.png"
        img.save(thumbnail_path, "PNG")
        
        preview = AssetPreview(
            asset_id=asset.id,
            thumbnail_path=str(thumbnail_path),
            preview_path=str(preview_path),
            technical_specs={
                "file_size": asset.file_size,
                "mime_type": asset.mime_type,
                "category": asset.category.value
            }
        )
        
        self.previews[asset.id] = preview
    
    def _create_usage_examples(self, image: Image.Image) -> List[str]:
        """Create usage examples for an image"""
        examples = []
        
        try:
            # Create different variations
            variations = [
                ("Original", image),
                ("Grayscale", image.convert('L').convert('RGB')),
                ("Sepia", self._apply_sepia_filter(image)),
                ("Blur", self._apply_blur_filter(image))
            ]
            
            for name, variant in variations:
                # Resize for example
                example_size = (150, 100)
                variant_copy = variant.copy()
                variant_copy.thumbnail(example_size, Image.Resampling.LANCZOS)
                
                # Save example
                example_path = self.previews_dir / f"{image.filename}_{name.lower()}.png"
                variant_copy.save(example_path, "PNG")
                examples.append(str(example_path))
                
        except Exception as e:
            print(f"Error creating usage examples: {e}")
        
        return examples
    
    def _apply_sepia_filter(self, image: Image.Image) -> Image.Image:
        """Apply sepia filter to image"""
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply sepia transformation
            width, height = image.size
            pixels = image.load()
            
            for x in range(width):
                for y in range(height):
                    r, g, b = pixels[x, y]
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    pixels[x, y] = (min(tr, 255), min(tg, 255), min(tb, 255))
            
            return image
        except Exception as e:
            print(f"Error applying sepia filter: {e}")
            return image
    
    def _apply_blur_filter(self, image: Image.Image) -> Image.Image:
        """Apply blur filter to image"""
        try:
            from PIL import ImageFilter
            return image.filter(ImageFilter.BLUR)
        except Exception as e:
            print(f"Error applying blur filter: {e}")
            return image
    
    def publish_asset(self, asset_id: str) -> VisualAsset:
        """Publish an asset"""
        if asset_id not in self.assets:
            raise ValueError(f"Asset {asset_id} not found")
        
        asset = self.assets[asset_id]
        asset.status = AssetStatus.PUBLISHED
        asset.published_at = datetime.now()
        asset.updated_at = datetime.now()
        
        self._save_data()
        return asset
    
    def search_assets(self, query: str = None, category: AssetCategory = None,
                     tags: List[str] = None, license_type: AssetLicense = None,
                     price_range: Tuple[float, float] = None,
                     status: AssetStatus = AssetStatus.PUBLISHED) -> List[VisualAsset]:
        """Search for assets"""
        results = []
        
        for asset in self.assets.values():
            if status and asset.status != status:
                continue
            
            if category and asset.category != category:
                continue
            
            if license_type and asset.license_type != license_type:
                continue
            
            if price_range and not (price_range[0] <= asset.price <= price_range[1]):
                continue
            
            if tags and not any(tag in asset.tags for tag in tags):
                continue
            
            if query:
                query_lower = query.lower()
                if (query_lower not in asset.title.lower() and
                    query_lower not in asset.description.lower() and
                    not any(query_lower in tag.lower() for tag in asset.tags)):
                    continue
            
            results.append(asset)
        
        # Sort by rating, then by download count
        results.sort(key=lambda x: (x.rating, x.download_count), reverse=True)
        return results
    
    def get_asset(self, asset_id: str) -> Optional[VisualAsset]:
        """Get a specific asset"""
        return self.assets.get(asset_id)
    
    def get_asset_preview(self, asset_id: str) -> Optional[AssetPreview]:
        """Get preview for an asset"""
        return self.previews.get(asset_id)
    
    def download_asset(self, asset_id: str, user_id: str) -> Optional[str]:
        """Download an asset"""
        if asset_id not in self.assets:
            return None
        
        asset = self.assets[asset_id]
        
        # Update download count
        asset.download_count += 1
        asset.updated_at = datetime.now()
        
        self._save_data()
        
        return asset.file_path
    
    def create_collection(self, title: str, description: str, author_id: str,
                         organization_id: str, assets: List[str], theme: str = "",
                         tags: List[str] = None, price: float = 0.0) -> AssetCollection:
        """Create an asset collection"""
        collection_id = str(uuid.uuid4())
        
        collection = AssetCollection(
            id=collection_id,
            title=title,
            description=description,
            author_id=author_id,
            organization_id=organization_id,
            assets=assets,
            theme=theme,
            tags=tags or [],
            price=price
        )
        
        self.collections[collection_id] = collection
        self._save_data()
        return collection
    
    def get_collection(self, collection_id: str) -> Optional[AssetCollection]:
        """Get a specific collection"""
        return self.collections.get(collection_id)
    
    def search_collections(self, query: str = None, theme: str = None,
                          tags: List[str] = None) -> List[AssetCollection]:
        """Search for collections"""
        results = []
        
        for collection in self.collections.values():
            if theme and theme.lower() not in collection.theme.lower():
                continue
            
            if tags and not any(tag in collection.tags for tag in tags):
                continue
            
            if query:
                query_lower = query.lower()
                if (query_lower not in collection.title.lower() and
                    query_lower not in collection.description.lower()):
                    continue
            
            results.append(collection)
        
        return results
    
    def generate_asset_package(self, asset_ids: List[str], package_name: str) -> str:
        """Generate a package of assets"""
        package_path = self.temp_dir / f"{package_name}.zip"
        
        with zipfile.ZipFile(package_path, 'w') as zipf:
            for asset_id in asset_ids:
                if asset_id in self.assets:
                    asset = self.assets[asset_id]
                    zipf.write(asset.file_path, f"{asset.title}.{Path(asset.file_path).suffix}")
        
        return str(package_path)
    
    def get_asset_statistics(self) -> Dict[str, Any]:
        """Get statistics about assets"""
        total_assets = len(self.assets)
        published_assets = len([a for a in self.assets.values() if a.status == AssetStatus.PUBLISHED])
        total_downloads = sum(a.download_count for a in self.assets.values())
        total_views = sum(a.view_count for a in self.assets.values())
        
        category_counts = {}
        for asset in self.assets.values():
            category = asset.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "total_assets": total_assets,
            "published_assets": published_assets,
            "total_downloads": total_downloads,
            "total_views": total_views,
            "category_distribution": category_counts
        }
    
    def increment_view_count(self, asset_id: str):
        """Increment view count for an asset"""
        if asset_id in self.assets:
            self.assets[asset_id].view_count += 1
            self.assets[asset_id].updated_at = datetime.now()
            self._save_data()
    
    def delete_asset(self, asset_id: str, user_id: str) -> bool:
        """Delete an asset (only by author)"""
        if asset_id not in self.assets:
            return False
        
        asset = self.assets[asset_id]
        if asset.author_id != user_id:
            return False
        
        # Mark as removed
        asset.status = AssetStatus.REMOVED
        asset.updated_at = datetime.now()
        
        self._save_data()
        return True
