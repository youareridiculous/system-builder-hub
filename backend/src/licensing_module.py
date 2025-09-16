import sqlite3
import json
import threading
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
import os
import re

class LicenseType(Enum):
    MIT = "mit"
    AGPL = "agpl"
    COMMERCIAL = "commercial"
    CUSTOM = "custom"
    PROPRIETARY = "proprietary"
    APACHE_2 = "apache_2"
    GPL_3 = "gpl_3"
    BSD_3 = "bsd_3"

class LicenseStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"

class EnforcementLevel(Enum):
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    DRM = "drm"

@dataclass
class License:
    license_id: str
    license_key: str
    listing_id: str
    buyer_id: str
    buyer_organization_id: str
    license_type: LicenseType
    status: LicenseStatus
    issued_at: str
    expires_at: Optional[str]
    max_uses: Optional[int]
    current_uses: int
    enforcement_level: EnforcementLevel
    watermark_enabled: bool
    resale_prevention: bool
    metadata: Dict[str, Any]

@dataclass
class LicenseViolation:
    violation_id: str
    license_id: str
    violation_type: str
    description: str
    detected_at: str
    severity: str
    action_taken: str
    metadata: Dict[str, Any]

@dataclass
class LicenseTemplate:
    license_type: LicenseType
    name: str
    description: str
    template_content: str
    terms: List[str]
    restrictions: List[str]
    permissions: List[str]

class LicensingModule:
    """License generation, validation, and enforcement system"""
    
    def __init__(self, base_dir: str, agent_marketplace, llm_factory):
        self.base_dir = base_dir
        self.agent_marketplace = agent_marketplace
        self.llm_factory = llm_factory
        
        self.db_path = f"{base_dir}/licensing_module.db"
        self.licenses_dir = f"{base_dir}/licenses"
        
        # Initialize directories and database
        self._init_directories()
        self._init_database()
        self._load_license_templates()
        
        # Background tasks
        self.enforcement_thread = threading.Thread(target=self._enforcement_loop, daemon=True)
        self.enforcement_thread.start()
    
    def _init_directories(self):
        """Initialize licensing directories"""
        os.makedirs(self.licenses_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize licensing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create licenses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                license_id TEXT PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                listing_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                buyer_organization_id TEXT NOT NULL,
                license_type TEXT NOT NULL,
                status TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                enforcement_level TEXT NOT NULL,
                watermark_enabled BOOLEAN DEFAULT FALSE,
                resale_prevention BOOLEAN DEFAULT FALSE,
                metadata TEXT
            )
        ''')
        
        # Create violations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS license_violations (
                violation_id TEXT PRIMARY KEY,
                license_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                description TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                severity TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (license_id) REFERENCES licenses (license_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses (license_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_licenses_buyer ON licenses (buyer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_licenses_listing ON licenses (listing_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_violations_license ON license_violations (license_id)')
        
        conn.commit()
        conn.close()
    
    def _load_license_templates(self):
        """Load predefined license templates"""
        self.license_templates = {
            LicenseType.MIT: LicenseTemplate(
                license_type=LicenseType.MIT,
                name="MIT License",
                description="A permissive license that allows commercial use, modification, distribution, and private use",
                template_content=self._get_mit_template(),
                terms=["Commercial use", "Modification", "Distribution", "Private use"],
                restrictions=["Liability", "Warranty"],
                permissions=["Use", "Modify", "Distribute", "Sublicense"]
            ),
            LicenseType.AGPL: LicenseTemplate(
                license_type=LicenseType.AGPL,
                name="GNU Affero General Public License v3.0",
                description="A copyleft license that requires source code to be made available when the software is used over a network",
                template_content=self._get_agpl_template(),
                terms=["Source code availability", "Network use triggers", "Copyleft"],
                restrictions=["Proprietary use", "Network deployment without source"],
                permissions=["Use", "Modify", "Distribute", "Network use"]
            ),
            LicenseType.COMMERCIAL: LicenseTemplate(
                license_type=LicenseType.COMMERCIAL,
                name="Commercial License",
                description="A proprietary license for commercial use with restrictions",
                template_content=self._get_commercial_template(),
                terms=["Commercial use", "Single organization", "No redistribution"],
                restrictions=["Resale", "Modification", "Reverse engineering"],
                permissions=["Internal use", "Backup copies"]
            ),
            LicenseType.PROPRIETARY: LicenseTemplate(
                license_type=LicenseType.PROPRIETARY,
                name="Proprietary License",
                description="A restrictive proprietary license with strong enforcement",
                template_content=self._get_proprietary_template(),
                terms=["Single use", "No modification", "No redistribution"],
                restrictions=["All rights reserved", "No reverse engineering"],
                permissions=["Use as provided"]
            )
        }
    
    def _get_mit_template(self) -> str:
        """Get MIT license template"""
        return """MIT License

Copyright (c) {year} {copyright_holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

    def _get_agpl_template(self) -> str:
        """Get AGPL license template"""
        return """GNU AFFERO GENERAL PUBLIC LICENSE
Version 3, 19 November 2007

Copyright (C) {year} {copyright_holder}

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Additional Terms:
- If you run a modified version of this software on a server and let other users communicate with it there, your server must also allow them to download the source code corresponding to the modified version running there.
- You must prominently offer all users interacting with the software through a computer network an opportunity to receive the source code of the software."""

    def _get_commercial_template(self) -> str:
        """Get commercial license template"""
        return """COMMERCIAL LICENSE AGREEMENT

This Commercial License Agreement (the "Agreement") is entered into between {copyright_holder} ("Licensor") and {licensee} ("Licensee") effective as of {issue_date}.

1. GRANT OF LICENSE
Subject to the terms and conditions of this Agreement, Licensor grants Licensee a non-exclusive, non-transferable license to use the software solely for internal business purposes within Licensee's organization.

2. RESTRICTIONS
Licensee shall not:
- Modify, reverse engineer, decompile, or disassemble the software
- Distribute, sublicense, or transfer the software to third parties
- Use the software for commercial resale or redistribution
- Remove or alter any proprietary notices or labels

3. OWNERSHIP
The software and all intellectual property rights therein remain the exclusive property of Licensor.

4. TERM AND TERMINATION
This license is effective until {expiry_date} unless earlier terminated. Licensor may terminate this license immediately upon breach of any terms.

5. WARRANTY DISCLAIMER
THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.

6. LIMITATION OF LIABILITY
IN NO EVENT SHALL LICENSOR BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES.

License Key: {license_key}
Organization: {organization}
Issued: {issue_date}
Expires: {expiry_date}"""

    def _get_proprietary_template(self) -> str:
        """Get proprietary license template"""
        return """PROPRIETARY SOFTWARE LICENSE

Copyright (c) {year} {copyright_holder}. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited.

LICENSE TERMS:
1. This license grants the right to use the software solely as provided
2. No modification, reverse engineering, or redistribution is permitted
3. This license is non-transferable and non-sublicensable
4. Violation of these terms will result in immediate license termination

LICENSE INFORMATION:
License Key: {license_key}
Licensee: {licensee}
Organization: {organization}
Issued: {issue_date}
Expires: {expiry_date}

This software is protected by copyright laws and international treaties."""

    def generate_license_key(self, listing_id: str, license_type: LicenseType, 
                           buyer_organization_id: str) -> str:
        """Generate a unique license key"""
        # Create a unique identifier
        unique_id = f"{listing_id}_{buyer_organization_id}_{uuid.uuid4().hex[:8]}"
        
        # Generate hash-based key
        key_hash = hashlib.sha256(unique_id.encode()).hexdigest()
        
        # Format as readable key (e.g., XXXX-XXXX-XXXX-XXXX)
        formatted_key = f"{key_hash[:4]}-{key_hash[4:8]}-{key_hash[8:12]}-{key_hash[12:16]}".upper()
        
        return formatted_key
    
    def generate_license_file(self, license_type: LicenseType, title: str, 
                            author_id: str, **kwargs) -> str:
        """Generate license file content"""
        template = self.license_templates.get(license_type)
        if not template:
            raise ValueError(f"Unknown license type: {license_type}")
        
        # Get current year and author info
        year = datetime.now().year
        author_name = kwargs.get('author_name', author_id)
        
        # Fill template variables
        content = template.template_content
        content = content.replace("{year}", str(year))
        content = content.replace("{copyright_holder}", author_name)
        content = content.replace("{title}", title)
        
        # Add additional variables if provided
        for key, value in kwargs.items():
            content = content.replace(f"{{{key}}}", str(value))
        
        return content
    
    def create_license(self, listing_id: str, buyer_id: str, buyer_organization_id: str,
                      license_type: LicenseType, enforcement_level: EnforcementLevel = EnforcementLevel.BASIC,
                      expires_in_days: Optional[int] = None, max_uses: Optional[int] = None,
                      watermark_enabled: bool = False, resale_prevention: bool = False,
                      metadata: Dict[str, Any] = None) -> str:
        """Create a new license"""
        license_id = f"license_{uuid.uuid4().hex[:8]}"
        license_key = self.generate_license_key(listing_id, license_type, buyer_organization_id)
        
        # Set expiration
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
        
        license_obj = License(
            license_id=license_id,
            license_key=license_key,
            listing_id=listing_id,
            buyer_id=buyer_id,
            buyer_organization_id=buyer_organization_id,
            license_type=license_type,
            status=LicenseStatus.ACTIVE,
            issued_at=datetime.now().isoformat(),
            expires_at=expires_at,
            max_uses=max_uses,
            current_uses=0,
            enforcement_level=enforcement_level,
            watermark_enabled=watermark_enabled,
            resale_prevention=resale_prevention,
            metadata=metadata or {}
        )
        
        self._save_license(license_obj)
        return license_id
    
    def _save_license(self, license_obj: License):
        """Save license to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO licenses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            license_obj.license_id, license_obj.license_key, license_obj.listing_id,
            license_obj.buyer_id, license_obj.buyer_organization_id,
            license_obj.license_type.value, license_obj.status.value,
            license_obj.issued_at, license_obj.expires_at, license_obj.max_uses,
            license_obj.current_uses, license_obj.enforcement_level.value,
            license_obj.watermark_enabled, license_obj.resale_prevention,
            json.dumps(license_obj.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def validate_license(self, license_key: str, organization_id: str = None) -> Optional[License]:
        """Validate a license key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if organization_id:
            cursor.execute('''
                SELECT * FROM licenses 
                WHERE license_key = ? AND buyer_organization_id = ? AND status = ?
            ''', (license_key, organization_id, LicenseStatus.ACTIVE.value))
        else:
            cursor.execute('''
                SELECT * FROM licenses 
                WHERE license_key = ? AND status = ?
            ''', (license_key, LicenseStatus.ACTIVE.value))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        license_obj = self._row_to_license(row)
        
        # Check expiration
        if license_obj.expires_at and datetime.fromisoformat(license_obj.expires_at) < datetime.now():
            self._expire_license(license_obj.license_id)
            return None
        
        # Check usage limits
        if license_obj.max_uses and license_obj.current_uses >= license_obj.max_uses:
            return None
        
        return license_obj
    
    def _row_to_license(self, row) -> License:
        """Convert database row to License"""
        return License(
            license_id=row[0],
            license_key=row[1],
            listing_id=row[2],
            buyer_id=row[3],
            buyer_organization_id=row[4],
            license_type=LicenseType(row[5]),
            status=LicenseStatus(row[6]),
            issued_at=row[7],
            expires_at=row[8],
            max_uses=row[9],
            current_uses=row[10],
            enforcement_level=EnforcementLevel(row[11]),
            watermark_enabled=bool(row[12]),
            resale_prevention=bool(row[13]),
            metadata=json.loads(row[14]) if row[14] else {}
        )
    
    def _expire_license(self, license_id: str):
        """Mark license as expired"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE licenses SET status = ? WHERE license_id = ?
        ''', (LicenseStatus.EXPIRED.value, license_id))
        
        conn.commit()
        conn.close()
    
    def increment_license_usage(self, license_key: str):
        """Increment usage count for a license"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE licenses SET current_uses = current_uses + 1 WHERE license_key = ?
        ''', (license_key,))
        
        conn.commit()
        conn.close()
    
    def revoke_license(self, license_id: str, reason: str = "License revoked"):
        """Revoke a license"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE licenses SET status = ? WHERE license_id = ?
        ''', (LicenseStatus.REVOKED.value, license_id))
        
        conn.commit()
        conn.close()
        
        # Log violation
        self._log_violation(license_id, "revocation", reason, "high", "license_revoked")
    
    def get_license(self, license_id: str) -> Optional[License]:
        """Get license by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM licenses WHERE license_id = ?', (license_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_license(row)
    
    def get_user_licenses(self, user_id: str, organization_id: str = None) -> List[License]:
        """Get all licenses for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if organization_id:
            cursor.execute('''
                SELECT * FROM licenses 
                WHERE buyer_id = ? AND buyer_organization_id = ?
                ORDER BY issued_at DESC
            ''', (user_id, organization_id))
        else:
            cursor.execute('''
                SELECT * FROM licenses 
                WHERE buyer_id = ?
                ORDER BY issued_at DESC
            ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_license(row) for row in rows]
    
    def _log_violation(self, license_id: str, violation_type: str, description: str,
                      severity: str, action_taken: str, metadata: Dict[str, Any] = None):
        """Log a license violation"""
        violation_id = f"violation_{uuid.uuid4().hex[:8]}"
        
        violation = LicenseViolation(
            violation_id=violation_id,
            license_id=license_id,
            violation_type=violation_type,
            description=description,
            detected_at=datetime.now().isoformat(),
            severity=severity,
            action_taken=action_taken,
            metadata=metadata or {}
        )
        
        self._save_violation(violation)
    
    def _save_violation(self, violation: LicenseViolation):
        """Save violation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO license_violations VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            violation.violation_id, violation.license_id, violation.violation_type,
            violation.description, violation.detected_at, violation.severity,
            violation.action_taken, json.dumps(violation.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def get_license_violations(self, license_id: str = None) -> List[LicenseViolation]:
        """Get license violations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if license_id:
            cursor.execute('''
                SELECT * FROM license_violations 
                WHERE license_id = ?
                ORDER BY detected_at DESC
            ''', (license_id,))
        else:
            cursor.execute('''
                SELECT * FROM license_violations 
                ORDER BY detected_at DESC
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_violation(row) for row in rows]
    
    def _row_to_violation(self, row) -> LicenseViolation:
        """Convert database row to LicenseViolation"""
        return LicenseViolation(
            violation_id=row[0],
            license_id=row[1],
            violation_type=row[2],
            description=row[3],
            detected_at=row[4],
            severity=row[5],
            action_taken=row[6],
            metadata=json.loads(row[7]) if row[7] else {}
        )
    
    def get_license_templates(self) -> List[LicenseTemplate]:
        """Get available license templates"""
        return list(self.license_templates.values())
    
    def _enforcement_loop(self):
        """Background license enforcement monitoring"""
        while True:
            try:
                # Check for expired licenses every hour
                import time
                time.sleep(3600)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Find expired licenses
                cursor.execute('''
                    SELECT license_id FROM licenses 
                    WHERE status = ? AND expires_at < ?
                ''', (LicenseStatus.ACTIVE.value, datetime.now().isoformat()))
                
                expired_licenses = cursor.fetchall()
                
                for (license_id,) in expired_licenses:
                    self._expire_license(license_id)
                
                conn.close()
                
            except Exception as e:
                print(f"License enforcement error: {e}")
                import time
                time.sleep(60)
