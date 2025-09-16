#!/usr/bin/env python3
"""
Access Hub for System Builder Hub
Handles hub tiles, favorites, branding settings, API tokens, share links, and activity feeds.
"""

import os
import json
import time
import logging
import sqlite3
import hashlib
import hmac
import secrets as py_secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from flask import current_app, g, request
from config import config

logger = logging.getLogger(__name__)

class TileType(Enum):
    """Hub tile types"""
    SYSTEM = "system"
    TOOL = "tool"
    DASHBOARD = "dashboard"
    EXTERNAL = "external"
    CUSTOM = "custom"

class ActivityType(Enum):
    """Activity types"""
    TILE_CREATED = "tile_created"
    TILE_UPDATED = "tile_updated"
    TILE_DELETED = "tile_deleted"
    TILE_LAUNCHED = "tile_launched"
    FAVORITE_ADDED = "favorite_added"
    FAVORITE_REMOVED = "favorite_removed"
    SHARE_LINK_CREATED = "share_link_created"
    TOKEN_CREATED = "token_created"
    TOKEN_REVOKED = "token_revoked"

@dataclass
class HubTile:
    """Hub tile"""
    id: str
    name: str
    description: str
    tile_type: TileType
    icon: str
    color: str
    url: str
    target: str
    position: int
    enabled: bool
    created_by: str
    tenant_id: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class HubFavorite:
    """Hub favorite"""
    id: str
    user_id: str
    tenant_id: str
    tile_id: str
    created_at: datetime

@dataclass
class BrandingSettings:
    """Branding settings"""
    id: str
    tenant_id: str
    logo_url: str
    primary_color: str
    secondary_color: str
    theme: str
    custom_css: str
    domain: str
    domain_verified: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class ApiToken:
    """API token"""
    id: str
    user_id: str
    tenant_id: str
    name: str
    token_hash: str
    permissions: List[str]
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    active: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class ShareLink:
    """Share link"""
    id: str
    user_id: str
    tenant_id: str
    tile_id: str
    share_token: str
    expires_at: datetime
    max_uses: int
    current_uses: int
    active: bool
    created_at: datetime

@dataclass
class ActivityEvent:
    """Activity event"""
    id: str
    user_id: str
    tenant_id: str
    activity_type: ActivityType
    target_id: str
    target_type: str
    description: str
    metadata: Dict[str, Any]
    created_at: datetime

class AccessHub:
    """Manages access hub functionality"""
    
    def __init__(self):
        self._init_database()
    
    def _init_database(self):
        """Initialize access hub database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create hub_tiles table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS hub_tiles (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        tile_type TEXT NOT NULL,
                        icon TEXT,
                        color TEXT,
                        url TEXT NOT NULL,
                        target TEXT DEFAULT '_self',
                        position INTEGER DEFAULT 0,
                        enabled BOOLEAN DEFAULT TRUE,
                        created_by TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create hub_favorites table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS hub_favorites (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        tile_id TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (tile_id) REFERENCES hub_tiles (id)
                    )
                ''')
                
                # Create branding_settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS branding_settings (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        logo_url TEXT,
                        primary_color TEXT,
                        secondary_color TEXT,
                        theme TEXT DEFAULT 'light',
                        custom_css TEXT,
                        domain TEXT,
                        domain_verified BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create api_tokens table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS api_tokens (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        token_hash TEXT NOT NULL UNIQUE,
                        permissions TEXT,
                        last_used TIMESTAMP,
                        expires_at TIMESTAMP,
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create share_links table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS share_links (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        tile_id TEXT NOT NULL,
                        share_token TEXT NOT NULL UNIQUE,
                        expires_at TIMESTAMP NOT NULL,
                        max_uses INTEGER DEFAULT 1,
                        current_uses INTEGER DEFAULT 0,
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (tile_id) REFERENCES hub_tiles (id)
                    )
                ''')
                
                # Create activity_events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activity_events (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        activity_type TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        target_type TEXT NOT NULL,
                        description TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL
                    )
                ''')
                
                conn.commit()
                logger.info("Access hub database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize access hub database: {e}")
    
    def create_tile(self, name: str, description: str, tile_type: TileType, url: str,
                   icon: str = "", color: str = "#007bff", target: str = "_self",
                   position: int = 0, metadata: Dict[str, Any] = None) -> HubTile:
        """Create a new hub tile"""
        tile_id = f"tile_{int(time.time())}"
        now = datetime.now()
        
        tile = HubTile(
            id=tile_id,
            name=name,
            description=description,
            tile_type=tile_type,
            icon=icon,
            color=color,
            url=url,
            target=target,
            position=position,
            enabled=True,
            created_by=getattr(g, 'user_id', 'system'),
            tenant_id=getattr(g, 'tenant_id', 'default'),
            metadata=metadata or {},
            created_at=now,
            updated_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO hub_tiles 
                    (id, name, description, tile_type, icon, color, url, target, position, 
                     enabled, created_by, tenant_id, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tile.id,
                    tile.name,
                    tile.description,
                    tile.tile_type.value,
                    tile.icon,
                    tile.color,
                    tile.url,
                    tile.target,
                    tile.position,
                    tile.enabled,
                    tile.created_by,
                    tile.tenant_id,
                    json.dumps(tile.metadata),
                    tile.created_at.isoformat(),
                    tile.updated_at.isoformat()
                ))
                conn.commit()
                
                # Create activity event
                self.create_activity_event(
                    user_id=tile.created_by,
                    tenant_id=tile.tenant_id,
                    activity_type=ActivityType.TILE_CREATED,
                    target_id=tile.id,
                    target_type="tile",
                    description=f"Created tile: {tile.name}"
                )
                
                logger.info(f"Created hub tile: {tile_id}")
                return tile
                
        except Exception as e:
            logger.error(f"Failed to create hub tile: {e}")
            raise
    
    def get_tiles(self, tenant_id: str = None, enabled_only: bool = True) -> List[HubTile]:
        """Get hub tiles"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM hub_tiles'
                params = []
                
                conditions = []
                if tenant_id:
                    conditions.append('tenant_id = ?')
                    params.append(tenant_id)
                if enabled_only:
                    conditions.append('enabled = TRUE')
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY position ASC, created_at ASC'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [HubTile(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    tile_type=TileType(row[3]),
                    icon=row[4],
                    color=row[5],
                    url=row[6],
                    target=row[7],
                    position=row[8],
                    enabled=bool(row[9]),
                    created_by=row[10],
                    tenant_id=row[11],
                    metadata=json.loads(row[12]) if row[12] else {},
                    created_at=datetime.fromisoformat(row[13]),
                    updated_at=datetime.fromisoformat(row[14])
                ) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get hub tiles: {e}")
            return []
    
    def get_tile(self, tile_id: str) -> Optional[HubTile]:
        """Get hub tile by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM hub_tiles WHERE id = ?', (tile_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return HubTile(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    tile_type=TileType(row[3]),
                    icon=row[4],
                    color=row[5],
                    url=row[6],
                    target=row[7],
                    position=row[8],
                    enabled=bool(row[9]),
                    created_by=row[10],
                    tenant_id=row[11],
                    metadata=json.loads(row[12]) if row[12] else {},
                    created_at=datetime.fromisoformat(row[13]),
                    updated_at=datetime.fromisoformat(row[14])
                )
                
        except Exception as e:
            logger.error(f"Failed to get hub tile: {e}")
            return None
    
    def update_tile(self, tile_id: str, **kwargs) -> bool:
        """Update hub tile"""
        try:
            tile = self.get_tile(tile_id)
            if not tile:
                return False
            
            # Build update query
            updates = []
            params = []
            
            for key, value in kwargs.items():
                if hasattr(tile, key):
                    updates.append(f"{key} = ?")
                    if key == 'tile_type':
                        params.append(value.value)
                    elif key == 'metadata':
                        params.append(json.dumps(value))
                    else:
                        params.append(value)
            
            if not updates:
                return True
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(tile_id)
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE hub_tiles 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                # Create activity event
                self.create_activity_event(
                    user_id=getattr(g, 'user_id', 'system'),
                    tenant_id=tile.tenant_id,
                    activity_type=ActivityType.TILE_UPDATED,
                    target_id=tile_id,
                    target_type="tile",
                    description=f"Updated tile: {tile.name}"
                )
                
                logger.info(f"Updated hub tile: {tile_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update hub tile: {e}")
            return False
    
    def delete_tile(self, tile_id: str) -> bool:
        """Delete hub tile"""
        try:
            tile = self.get_tile(tile_id)
            if not tile:
                return False
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Delete related records first
                cursor.execute('DELETE FROM hub_favorites WHERE tile_id = ?', (tile_id,))
                cursor.execute('DELETE FROM share_links WHERE tile_id = ?', (tile_id,))
                
                # Delete tile
                cursor.execute('DELETE FROM hub_tiles WHERE id = ?', (tile_id,))
                conn.commit()
                
                # Create activity event
                self.create_activity_event(
                    user_id=getattr(g, 'user_id', 'system'),
                    tenant_id=tile.tenant_id,
                    activity_type=ActivityType.TILE_DELETED,
                    target_id=tile_id,
                    target_type="tile",
                    description=f"Deleted tile: {tile.name}"
                )
                
                logger.info(f"Deleted hub tile: {tile_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete hub tile: {e}")
            return False
    
    def add_favorite(self, tile_id: str) -> bool:
        """Add tile to favorites"""
        try:
            user_id = getattr(g, 'user_id', 'system')
            tenant_id = getattr(g, 'tenant_id', 'default')
            
            # Check if already favorited
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM hub_favorites 
                    WHERE user_id = ? AND tenant_id = ? AND tile_id = ?
                ''', (user_id, tenant_id, tile_id))
                
                if cursor.fetchone():
                    return True  # Already favorited
            
            # Add favorite
            favorite_id = f"favorite_{int(time.time())}"
            now = datetime.now()
            
            cursor.execute('''
                INSERT INTO hub_favorites (id, user_id, tenant_id, tile_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (favorite_id, user_id, tenant_id, tile_id, now.isoformat()))
            conn.commit()
            
            # Create activity event
            self.create_activity_event(
                user_id=user_id,
                tenant_id=tenant_id,
                activity_type=ActivityType.FAVORITE_ADDED,
                target_id=tile_id,
                target_type="tile",
                description="Added tile to favorites"
            )
            
            logger.info(f"Added favorite: {tile_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add favorite: {e}")
            return False
    
    def remove_favorite(self, tile_id: str) -> bool:
        """Remove tile from favorites"""
        try:
            user_id = getattr(g, 'user_id', 'system')
            tenant_id = getattr(g, 'tenant_id', 'default')
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM hub_favorites 
                    WHERE user_id = ? AND tenant_id = ? AND tile_id = ?
                ''', (user_id, tenant_id, tile_id))
                conn.commit()
                
                # Create activity event
                self.create_activity_event(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    activity_type=ActivityType.FAVORITE_REMOVED,
                    target_id=tile_id,
                    target_type="tile",
                    description="Removed tile from favorites"
                )
                
                logger.info(f"Removed favorite: {tile_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove favorite: {e}")
            return False
    
    def get_favorites(self, user_id: str = None, tenant_id: str = None) -> List[HubFavorite]:
        """Get user favorites"""
        try:
            if not user_id:
                user_id = getattr(g, 'user_id', 'system')
            if not tenant_id:
                tenant_id = getattr(g, 'tenant_id', 'default')
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM hub_favorites 
                    WHERE user_id = ? AND tenant_id = ?
                    ORDER BY created_at DESC
                ''', (user_id, tenant_id))
                rows = cursor.fetchall()
                
                return [HubFavorite(
                    id=row[0],
                    user_id=row[1],
                    tenant_id=row[2],
                    tile_id=row[3],
                    created_at=datetime.fromisoformat(row[4])
                ) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get favorites: {e}")
            return []
    
    def create_api_token(self, name: str, permissions: List[str], 
                        expires_days: int = 365) -> Optional[Dict[str, str]]:
        """Create a new API token"""
        try:
            user_id = getattr(g, 'user_id', 'system')
            tenant_id = getattr(g, 'tenant_id', 'default')
            
            # Generate token
            token = py_secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Calculate expiry
            expires_at = None
            if expires_days > 0:
                expires_at = datetime.now() + timedelta(days=expires_days)
            
            token_id = f"token_{int(time.time())}"
            now = datetime.now()
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO api_tokens 
                    (id, user_id, tenant_id, name, token_hash, permissions, expires_at, 
                     active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    token_id,
                    user_id,
                    tenant_id,
                    name,
                    token_hash,
                    json.dumps(permissions),
                    expires_at.isoformat() if expires_at else None,
                    True,
                    now.isoformat(),
                    now.isoformat()
                ))
                conn.commit()
                
                # Create activity event
                self.create_activity_event(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    activity_type=ActivityType.TOKEN_CREATED,
                    target_id=token_id,
                    target_type="token",
                    description=f"Created API token: {name}"
                )
                
                logger.info(f"Created API token: {token_id}")
                return {
                    'id': token_id,
                    'name': name,
                    'token': token,  # Only shown once
                    'expires_at': expires_at.isoformat() if expires_at else None
                }
                
        except Exception as e:
            logger.error(f"Failed to create API token: {e}")
            return None
    
    def validate_api_token(self, token: str) -> Optional[ApiToken]:
        """Validate API token"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM api_tokens 
                    WHERE token_hash = ? AND active = TRUE
                ''', (token_hash,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                token_obj = ApiToken(
                    id=row[0],
                    user_id=row[1],
                    tenant_id=row[2],
                    name=row[3],
                    token_hash=row[4],
                    permissions=json.loads(row[5]) if row[5] else [],
                    last_used=datetime.fromisoformat(row[6]) if row[6] else None,
                    expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    active=bool(row[8]),
                    created_at=datetime.fromisoformat(row[9]),
                    updated_at=datetime.fromisoformat(row[10])
                )
                
                # Check if token is expired
                if token_obj.expires_at and datetime.now() > token_obj.expires_at:
                    logger.warning(f"API token expired: {token_obj.id}")
                    return None
                
                # Update last used
                cursor.execute('''
                    UPDATE api_tokens 
                    SET last_used = ?, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), datetime.now().isoformat(), token_obj.id))
                conn.commit()
                
                return token_obj
                
        except Exception as e:
            logger.error(f"Failed to validate API token: {e}")
            return None
    
    def revoke_api_token(self, token_id: str) -> bool:
        """Revoke API token"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE api_tokens 
                    SET active = FALSE, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), token_id))
                conn.commit()
                
                # Create activity event
                self.create_activity_event(
                    user_id=getattr(g, 'user_id', 'system'),
                    tenant_id=getattr(g, 'tenant_id', 'default'),
                    activity_type=ActivityType.TOKEN_REVOKED,
                    target_id=token_id,
                    target_type="token",
                    description="Revoked API token"
                )
                
                logger.info(f"Revoked API token: {token_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to revoke API token: {e}")
            return False
    
    def create_share_link(self, tile_id: str, expires_hours: int = 72, max_uses: int = 1) -> Optional[Dict[str, str]]:
        """Create a share link for a tile"""
        try:
            user_id = getattr(g, 'user_id', 'system')
            tenant_id = getattr(g, 'tenant_id', 'default')
            
            # Generate share token
            share_token = py_secrets.token_urlsafe(16)
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            share_id = f"share_{int(time.time())}"
            now = datetime.now()
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO share_links 
                    (id, user_id, tenant_id, tile_id, share_token, expires_at, max_uses, 
                     current_uses, active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    share_id,
                    user_id,
                    tenant_id,
                    tile_id,
                    share_token,
                    expires_at.isoformat(),
                    max_uses,
                    0,
                    True,
                    now.isoformat()
                ))
                conn.commit()
                
                # Create activity event
                self.create_activity_event(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    activity_type=ActivityType.SHARE_LINK_CREATED,
                    target_id=tile_id,
                    target_type="tile",
                    description="Created share link"
                )
                
                logger.info(f"Created share link: {share_id}")
                return {
                    'id': share_id,
                    'share_token': share_token,
                    'expires_at': expires_at.isoformat(),
                    'max_uses': max_uses
                }
                
        except Exception as e:
            logger.error(f"Failed to create share link: {e}")
            return None
    
    def validate_share_link(self, share_token: str) -> Optional[Dict[str, Any]]:
        """Validate share link"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM share_links 
                    WHERE share_token = ? AND active = TRUE
                ''', (share_token,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                share_id, user_id, tenant_id, tile_id, token, expires_at, max_uses, current_uses, active, created_at = row
                expires_at = datetime.fromisoformat(expires_at)
                
                # Check if expired
                if datetime.now() > expires_at:
                    logger.warning(f"Share link expired: {share_id}")
                    return None
                
                # Check usage limit
                if current_uses >= max_uses:
                    logger.warning(f"Share link usage limit exceeded: {share_id}")
                    return None
                
                # Increment usage
                cursor.execute('''
                    UPDATE share_links 
                    SET current_uses = current_uses + 1
                    WHERE id = ?
                ''', (share_id,))
                conn.commit()
                
                # Get tile info
                tile = self.get_tile(tile_id)
                
                return {
                    'share_id': share_id,
                    'tile': tile,
                    'expires_at': expires_at.isoformat(),
                    'max_uses': max_uses,
                    'current_uses': current_uses + 1
                }
                
        except Exception as e:
            logger.error(f"Failed to validate share link: {e}")
            return None
    
    def create_activity_event(self, user_id: str, tenant_id: str, activity_type: ActivityType,
                             target_id: str, target_type: str, description: str,
                             metadata: Dict[str, Any] = None) -> ActivityEvent:
        """Create an activity event"""
        event_id = f"event_{int(time.time())}"
        now = datetime.now()
        
        event = ActivityEvent(
            id=event_id,
            user_id=user_id,
            tenant_id=tenant_id,
            activity_type=activity_type,
            target_id=target_id,
            target_type=target_type,
            description=description,
            metadata=metadata or {},
            created_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_events 
                    (id, user_id, tenant_id, activity_type, target_id, target_type, 
                     description, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.id,
                    event.user_id,
                    event.tenant_id,
                    event.activity_type.value,
                    event.target_id,
                    event.target_type,
                    event.description,
                    json.dumps(event.metadata),
                    event.created_at.isoformat()
                ))
                conn.commit()
                
                logger.info(f"Created activity event: {event_id}")
                return event
                
        except Exception as e:
            logger.error(f"Failed to create activity event: {e}")
            raise
    
    def get_activity_feed(self, tenant_id: str = None, limit: int = 50) -> List[ActivityEvent]:
        """Get activity feed"""
        try:
            if not tenant_id:
                tenant_id = getattr(g, 'tenant_id', 'default')
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM activity_events 
                    WHERE tenant_id = ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (tenant_id, limit))
                rows = cursor.fetchall()
                
                return [ActivityEvent(
                    id=row[0],
                    user_id=row[1],
                    tenant_id=row[2],
                    activity_type=ActivityType(row[3]),
                    target_id=row[4],
                    target_type=row[5],
                    description=row[6],
                    metadata=json.loads(row[7]) if row[7] else {},
                    created_at=datetime.fromisoformat(row[8])
                ) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get activity feed: {e}")
            return []
    
    def get_branding_settings(self, tenant_id: str) -> Optional[BrandingSettings]:
        """Get branding settings for tenant"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM branding_settings WHERE tenant_id = ?', (tenant_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return BrandingSettings(
                    id=row[0],
                    tenant_id=row[1],
                    logo_url=row[2],
                    primary_color=row[3],
                    secondary_color=row[4],
                    theme=row[5],
                    custom_css=row[6],
                    domain=row[7],
                    domain_verified=bool(row[8]),
                    created_at=datetime.fromisoformat(row[9]),
                    updated_at=datetime.fromisoformat(row[10])
                )
                
        except Exception as e:
            logger.error(f"Failed to get branding settings: {e}")
            return None
    
    def update_branding_settings(self, tenant_id: str, **kwargs) -> bool:
        """Update branding settings"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Check if settings exist
                cursor.execute('SELECT id FROM branding_settings WHERE tenant_id = ?', (tenant_id,))
                row = cursor.fetchone()
                
                if row:
                    # Update existing
                    updates = []
                    params = []
                    
                    for key, value in kwargs.items():
                        updates.append(f"{key} = ?")
                        params.append(value)
                    
                    updates.append("updated_at = ?")
                    params.append(datetime.now().isoformat())
                    params.append(tenant_id)
                    
                    cursor.execute(f'''
                        UPDATE branding_settings 
                        SET {', '.join(updates)}
                        WHERE tenant_id = ?
                    ''', params)
                else:
                    # Create new
                    settings_id = f"branding_{int(time.time())}"
                    now = datetime.now()
                    
                    cursor.execute('''
                        INSERT INTO branding_settings 
                        (id, tenant_id, logo_url, primary_color, secondary_color, theme, 
                         custom_css, domain, domain_verified, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        settings_id,
                        tenant_id,
                        kwargs.get('logo_url', ''),
                        kwargs.get('primary_color', '#007bff'),
                        kwargs.get('secondary_color', '#6c757d'),
                        kwargs.get('theme', 'light'),
                        kwargs.get('custom_css', ''),
                        kwargs.get('domain', ''),
                        kwargs.get('domain_verified', False),
                        now.isoformat(),
                        now.isoformat()
                    ))
                
                conn.commit()
                logger.info(f"Updated branding settings for tenant: {tenant_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update branding settings: {e}")
            return False

# Global instance
access_hub = AccessHub()
