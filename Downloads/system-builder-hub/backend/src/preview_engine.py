#!/usr/bin/env python3
"""
Priority 30: Real-Time Multi-Device Preview Engine
Live, interactive preview environments with device presets, hot reload, and visual QA.
"""

import os
import json
import uuid
import logging
import threading
import time
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Generator
from pathlib import Path
from dataclasses import dataclass, asdict
import base64
import hashlib

from flask import request, jsonify, Response, current_app, g
from config import config

logger = logging.getLogger(__name__)

@dataclass
class DevicePreset:
    """Device preset configuration"""
    name: str
    width: int
    height: int
    user_agent: str
    device_scale_factor: float
    is_mobile: bool
    has_touch: bool
    orientation: str = 'portrait'

@dataclass
class PreviewSession:
    """Preview session configuration"""
    id: str
    system_id: str
    version_id: Optional[str]
    preview_url: str
    status: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    device_config: DevicePreset
    metadata: Dict[str, Any]

class PreviewEngine:
    """Real-time multi-device preview engine"""
    
    def __init__(self):
        self.sessions: Dict[str, PreviewSession] = {}
        self.device_presets = self._initialize_device_presets()
        self.active_previews = 0
        self.max_concurrency = config.PREVIEW_MAX_CONCURRENCY
        self.lock = threading.Lock()
    
    def _initialize_device_presets(self) -> Dict[str, DevicePreset]:
        """Initialize device presets"""
        return {
            'iphone': DevicePreset(
                name='iPhone',
                width=375,
                height=812,
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                device_scale_factor=3.0,
                is_mobile=True,
                has_touch=True
            ),
            'ipad': DevicePreset(
                name='iPad',
                width=768,
                height=1024,
                user_agent='Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                device_scale_factor=2.0,
                is_mobile=True,
                has_touch=True
            ),
            'pixel': DevicePreset(
                name='Pixel',
                width=411,
                height=823,
                user_agent='Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                device_scale_factor=2.75,
                is_mobile=True,
                has_touch=True
            ),
            'laptop': DevicePreset(
                name='Laptop',
                width=1366,
                height=768,
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False
            ),
            'desktop': DevicePreset(
                name='Desktop',
                width=1920,
                height=1080,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False
            ),
            'ultrawide': DevicePreset(
                name='Ultrawide',
                width=2560,
                height=1080,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False
            )
        }
    
    def create_preview_session(self, system_id: str, version_id: Optional[str] = None,
                              device_preset: str = 'desktop', ttl_minutes: int = None) -> PreviewSession:
        """Create a new preview session"""
        with self.lock:
            # Check concurrency limits
            if self.active_previews >= self.max_concurrency:
                raise Exception(f"Maximum preview concurrency reached ({self.max_concurrency})")
            
            # Generate session ID
            session_id = f"preview_{system_id}_{uuid.uuid4().hex[:8]}"
            
            # Get device preset
            if device_preset not in self.device_presets:
                device_preset = 'desktop'
            
            device_config = self.device_presets[device_preset]
            
            # Set TTL
            if ttl_minutes is None:
                ttl_minutes = config.PREVIEW_TTL_MINUTES
            
            # Create preview URL
            preview_url = f"https://preview-{system_id}-{session_id[:8]}.system-builder-hub.com"
            
            # Create session
            session = PreviewSession(
                id=session_id,
                system_id=system_id,
                version_id=version_id,
                preview_url=preview_url,
                status='starting',
                created_by=request.headers.get('X-User-ID', 'unknown'),
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=ttl_minutes),
                device_config=device_config,
                metadata={
                    'device_preset': device_preset,
                    'ttl_minutes': ttl_minutes,
                    'created_from_ip': request.remote_addr
                }
            )
            
            # Store session
            self.sessions[session_id] = session
            self.active_previews += 1
            
            # Start preview environment
            self._start_preview_environment(session)
            
            # Save to database
            self._save_session_to_db(session)
            
            logger.info(f"Created preview session: {session_id}")
            return session
    
    def _start_preview_environment(self, session: PreviewSession):
        """Start the preview environment"""
        try:
            # This would start the actual preview environment
            # For now, we'll simulate it
            session.status = 'running'
            
            # Start hot reload monitoring
            threading.Thread(
                target=self._monitor_hot_reload,
                args=(session,),
                daemon=True
            ).start()
            
            logger.info(f"Preview environment started: {session.id}")
            
        except Exception as e:
            session.status = 'failed'
            logger.error(f"Failed to start preview environment: {e}")
            raise
    
    def _monitor_hot_reload(self, session: PreviewSession):
        """Monitor for hot reload changes"""
        try:
            while session.status == 'running':
                # Check for file changes
                # This would integrate with your file watching system
                time.sleep(1)
                
                # Check if session has expired
                if datetime.now() > session.expires_at:
                    self.stop_preview_session(session.id)
                    break
                    
        except Exception as e:
            logger.error(f"Hot reload monitoring failed: {e}")
    
    def stop_preview_session(self, session_id: str) -> bool:
        """Stop a preview session"""
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            session.status = 'stopped'
            
            # Clean up resources
            self._cleanup_preview_environment(session)
            
            # Remove from active sessions
            del self.sessions[session_id]
            self.active_previews = max(0, self.active_previews - 1)
            
            # Update database
            self._update_session_in_db(session)
            
            logger.info(f"Stopped preview session: {session_id}")
            return True
    
    def _cleanup_preview_environment(self, session: PreviewSession):
        """Clean up preview environment resources"""
        try:
            # This would clean up containers, processes, etc.
            logger.info(f"Cleaned up preview environment: {session.id}")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def get_session(self, session_id: str) -> Optional[PreviewSession]:
        """Get a preview session"""
        return self.sessions.get(session_id)
    
    def update_device_config(self, session_id: str, device_config: Dict[str, Any]) -> bool:
        """Update device configuration for a session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Update device configuration
        for key, value in device_config.items():
            if hasattr(session.device_config, key):
                setattr(session.device_config, key, value)
        
        # Update database
        self._update_session_in_db(session)
        
        logger.info(f"Updated device config for session: {session_id}")
        return True
    
    def take_screenshot(self, session_id: str, route: str = '/') -> Dict[str, Any]:
        """Take a screenshot of the preview"""
        session = self.get_session(session_id)
        if not session:
            raise Exception("Preview session not found")
        
        try:
            # This would use Playwright or similar to take screenshots
            # For now, we'll simulate it
            
            screenshot_data = {
                'session_id': session_id,
                'route': route,
                'device_preset': session.device_config.name,
                'width': session.device_config.width,
                'height': session.device_config.height,
                'timestamp': datetime.now().isoformat(),
                'screenshot_url': f"/api/preview/screenshots/{session_id}_{hashlib.md5(route.encode()).hexdigest()[:8]}.png"
            }
            
            # Save screenshot metadata
            self._save_screenshot_metadata(screenshot_data)
            
            logger.info(f"Screenshot taken for session {session_id} at route {route}")
            return screenshot_data
            
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            raise
    
    def compare_screenshots(self, baseline_session_id: str, compare_session_id: str, 
                           route: str = '/') -> Dict[str, Any]:
        """Compare screenshots between sessions"""
        try:
            # Take screenshots
            baseline_screenshot = self.take_screenshot(baseline_session_id, route)
            compare_screenshot = self.take_screenshot(compare_session_id, route)
            
            # This would implement actual image comparison
            # For now, we'll simulate it
            
            comparison_result = {
                'baseline_session': baseline_session_id,
                'compare_session': compare_session_id,
                'route': route,
                'similarity_score': 0.95,  # Simulated
                'differences_found': False,
                'diff_image_url': f"/api/preview/diffs/{baseline_session_id}_{compare_session_id}_{hashlib.md5(route.encode()).hexdigest()[:8]}.png",
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Screenshot comparison completed: {comparison_result['similarity_score']}")
            return comparison_result
            
        except Exception as e:
            logger.error(f"Screenshot comparison failed: {e}")
            raise
    
    def get_preview_logs(self, session_id: str, service: str = 'app') -> Generator[Dict[str, Any], None, None]:
        """Get preview logs as SSE stream"""
        session = self.get_session(session_id)
        if not session:
            return
        
        # Simulate log generation
        log_levels = ['INFO', 'WARN', 'ERROR']
        log_messages = [
            f"Preview environment started for {session.system_id}",
            f"Device preset: {session.device_config.name}",
            f"Viewport: {session.device_config.width}x{session.device_config.height}",
            f"Hot reload monitoring active",
            f"File change detected - reloading...",
            f"Preview environment ready"
        ]
        
        for i, message in enumerate(log_messages):
            log_event = {
                'type': 'log',
                'level': log_levels[i % len(log_levels)],
                'message': message,
                'service': service,
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id
            }
            
            yield log_event
            time.sleep(1)  # Simulate log generation delay
    
    def _save_session_to_db(self, session: PreviewSession):
        """Save session to database"""
        try:
            from database import get_db_session
            from sqlalchemy import text
            
            with get_db_session() as db_session:
                db_session.execute(text("""
                    INSERT INTO preview_sessions 
                    (id, system_id, version_id, preview_url, status, created_by, created_at, expires_at, metadata)
                    VALUES (:id, :system_id, :version_id, :preview_url, :status, :created_by, :created_at, :expires_at, :metadata)
                """), {
                    'id': session.id,
                    'system_id': session.system_id,
                    'version_id': session.version_id,
                    'preview_url': session.preview_url,
                    'status': session.status,
                    'created_by': session.created_by,
                    'created_at': session.created_at,
                    'expires_at': session.expires_at,
                    'metadata': json.dumps(session.metadata)
                })
                
        except Exception as e:
            logger.error(f"Failed to save session to database: {e}")
    
    def _update_session_in_db(self, session: PreviewSession):
        """Update session in database"""
        try:
            from database import get_db_session
            from sqlalchemy import text
            
            with get_db_session() as db_session:
                db_session.execute(text("""
                    UPDATE preview_sessions 
                    SET status = :status, metadata = :metadata
                    WHERE id = :id
                """), {
                    'id': session.id,
                    'status': session.status,
                    'metadata': json.dumps(session.metadata)
                })
                
        except Exception as e:
            logger.error(f"Failed to update session in database: {e}")
    
    def _save_screenshot_metadata(self, screenshot_data: Dict[str, Any]):
        """Save screenshot metadata"""
        # This would save screenshot metadata to database
        pass
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        with self.lock:
            expired_sessions = []
            for session_id, session in self.sessions.items():
                if datetime.now() > session.expires_at:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self.stop_preview_session(session_id)
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

# Global preview engine
preview_engine = PreviewEngine()

# Background task to clean up expired sessions
def cleanup_preview_sessions_task():
    """Background task to clean up expired preview sessions"""
    while True:
        try:
            preview_engine.cleanup_expired_sessions()
            time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Preview session cleanup failed: {e}")
            time.sleep(300)  # Wait 5 minutes on error
