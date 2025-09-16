"""
System Licensing - Monetization and license management
"""

import json
import secrets as py_secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import sqlite3


class LicenseType(Enum):
    """License types"""
    MIT = "mit"
    GPL = "gpl"
    APACHE = "apache"
    COMMERCIAL = "commercial"
    CUSTOM = "custom"


class LicenseStatus(Enum):
    """License status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    TRIAL = "trial"


class PricingModel(Enum):
    """Pricing models"""
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    USAGE_BASED = "usage_based"
    REVENUE_SHARE = "revenue_share"


@dataclass
class License:
    """License entity"""
    license_id: str
    system_id: str
    license_type: LicenseType
    status: LicenseStatus
    owner_id: str
    organization_id: str
    terms: Dict[str, Any]
    restrictions: List[str]
    expires_at: str = None
    created_at: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SystemTemplate:
    """System template for monetization"""
    template_id: str
    name: str
    description: str
    system_id: str
    pricing_model: PricingModel
    price: float
    currency: str
    license_type: LicenseType
    features: List[str]
    limitations: List[str]
    is_published: bool = False
    created_at: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LicenseViolation:
    """License violation record"""
    violation_id: str
    license_id: str
    violation_type: str
    description: str
    severity: str  # low, medium, high, critical
    detected_at: str = None
    resolved_at: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LicenseUsage:
    """License usage tracking"""
    usage_id: str
    license_id: str
    user_id: str
    action: str
    timestamp: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


class SystemLicensing:
    """System licensing and monetization management"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "system_licensing.db"
        self.licenses_dir = base_dir / "licenses"
        self.templates_dir = base_dir / "system_templates"
        
        # Create directories
        self.licenses_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize data storage
        self.licenses: Dict[str, License] = {}
        self.templates: Dict[str, SystemTemplate] = {}
        self.violations: Dict[str, List[LicenseViolation]] = {}
        self.usage_logs: Dict[str, List[LicenseUsage]] = {}
        
        self._init_database()
        self._load_data()

    def _init_database(self):
        """Initialize the database with tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Licenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                license_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                license_type TEXT NOT NULL,
                status TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                terms TEXT NOT NULL,
                restrictions TEXT NOT NULL,
                expires_at TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # System templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_templates (
                template_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                system_id TEXT NOT NULL,
                pricing_model TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                license_type TEXT NOT NULL,
                features TEXT NOT NULL,
                limitations TEXT NOT NULL,
                is_published BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # License violations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS license_violations (
                violation_id TEXT PRIMARY KEY,
                license_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                resolved_at TEXT,
                metadata TEXT,
                FOREIGN KEY (license_id) REFERENCES licenses (license_id)
            )
        """)

        # License usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS license_usage (
                usage_id TEXT PRIMARY KEY,
                license_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (license_id) REFERENCES licenses (license_id)
            )
        """)

        conn.commit()
        conn.close()

    def _load_data(self):
        """Load existing data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load licenses
        cursor.execute("SELECT * FROM licenses")
        for row in cursor.fetchall():
            license_obj = License(
                license_id=row[0],
                system_id=row[1],
                license_type=LicenseType(row[2]),
                status=LicenseStatus(row[3]),
                owner_id=row[4],
                organization_id=row[5],
                terms=json.loads(row[6]),
                restrictions=json.loads(row[7]),
                expires_at=row[8],
                created_at=row[9],
                metadata=json.loads(row[10]) if row[10] else {}
            )
            self.licenses[license_obj.license_id] = license_obj

        # Load templates
        cursor.execute("SELECT * FROM system_templates")
        for row in cursor.fetchall():
            template = SystemTemplate(
                template_id=row[0],
                name=row[1],
                description=row[2],
                system_id=row[3],
                pricing_model=PricingModel(row[4]),
                price=row[5],
                currency=row[6],
                license_type=LicenseType(row[7]),
                features=json.loads(row[8]),
                limitations=json.loads(row[9]),
                is_published=bool(row[10]),
                created_at=row[11],
                metadata=json.loads(row[12]) if row[12] else {}
            )
            self.templates[template.template_id] = template

        conn.close()

    def create_license(self, system_id: str, license_type: LicenseType, owner_id: str,
                      organization_id: str, terms: Dict[str, Any], restrictions: List[str],
                      expires_at: str = None) -> License:
        """Create a new license"""
        license_id = f"license_{py_secrets.token_hex(8)}"
        
        license_obj = License(
            license_id=license_id,
            system_id=system_id,
            license_type=license_type,
            status=LicenseStatus.ACTIVE,
            owner_id=owner_id,
            organization_id=organization_id,
            terms=terms,
            restrictions=restrictions,
            expires_at=expires_at
        )
        
        self._save_license(license_obj)
        self.licenses[license_id] = license_obj
        
        # Generate license file
        self._generate_license_file(license_obj)
        
        return license_obj

    def create_system_template(self, name: str, description: str, system_id: str,
                             pricing_model: PricingModel, price: float, currency: str,
                             license_type: LicenseType, features: List[str],
                             limitations: List[str]) -> SystemTemplate:
        """Create a new system template for monetization"""
        template_id = f"template_{py_secrets.token_hex(8)}"
        
        template = SystemTemplate(
            template_id=template_id,
            name=name,
            description=description,
            system_id=system_id,
            pricing_model=pricing_model,
            price=price,
            currency=currency,
            license_type=license_type,
            features=features,
            limitations=limitations
        )
        
        self._save_template(template)
        self.templates[template_id] = template
        
        return template

    def publish_template(self, template_id: str) -> bool:
        """Publish a system template"""
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        template.is_published = True
        
        self._save_template(template)
        return True

    def check_license_compliance(self, license_id: str, action: str, user_id: str) -> bool:
        """Check if an action complies with license terms"""
        if license_id not in self.licenses:
            return False
        
        license_obj = self.licenses[license_id]
        
        # Check if license is active
        if license_obj.status != LicenseStatus.ACTIVE:
            return False
        
        # Check if license is expired
        if license_obj.expires_at and datetime.fromisoformat(license_obj.expires_at) < datetime.utcnow():
            self._update_license_status(license_id, LicenseStatus.EXPIRED)
            return False
        
        # Check restrictions
        for restriction in license_obj.restrictions:
            if restriction.lower() in action.lower():
                self._record_violation(license_id, "restriction_violation", 
                                     f"Action '{action}' violates restriction: {restriction}")
                return False
        
        # Log usage
        self._log_usage(license_id, user_id, action)
        
        return True

    def inject_license_metadata(self, system_id: str, license_id: str) -> Dict[str, Any]:
        """Inject license metadata into system exports"""
        if license_id not in self.licenses:
            return {}
        
        license_obj = self.licenses[license_id]
        
        metadata = {
            "license_id": license_id,
            "license_type": license_obj.license_type.value,
            "owner_id": license_obj.owner_id,
            "organization_id": license_obj.organization_id,
            "terms": license_obj.terms,
            "restrictions": license_obj.restrictions,
            "expires_at": license_obj.expires_at,
            "created_at": license_obj.created_at,
            "license_hash": self._generate_license_hash(license_obj)
        }
        
        return metadata

    def generate_license_file(self, license_id: str) -> str:
        """Generate license file content"""
        if license_id not in self.licenses:
            return ""
        
        license_obj = self.licenses[license_id]
        
        if license_obj.license_type == LicenseType.MIT:
            return self._generate_mit_license(license_obj)
        elif license_obj.license_type == LicenseType.GPL:
            return self._generate_gpl_license(license_obj)
        elif license_obj.license_type == LicenseType.APACHE:
            return self._generate_apache_license(license_obj)
        elif license_obj.license_type == LicenseType.COMMERCIAL:
            return self._generate_commercial_license(license_obj)
        else:
            return self._generate_custom_license(license_obj)

    def _generate_mit_license(self, license_obj: License) -> str:
        """Generate MIT license content"""
        return f"""MIT License

Copyright (c) {datetime.now().year} {license_obj.terms.get('copyright_holder', 'System Builder Hub')}

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
SOFTWARE.

Additional Terms:
{chr(10).join(f"- {restriction}" for restriction in license_obj.restrictions)}

License ID: {license_obj.license_id}
Expires: {license_obj.expires_at or 'Never'}
"""

    def _generate_gpl_license(self, license_obj: License) -> str:
        """Generate GPL license content"""
        return f"""GNU General Public License v3.0

Copyright (c) {datetime.now().year} {license_obj.terms.get('copyright_holder', 'System Builder Hub')}

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Additional Terms:
{chr(10).join(f"- {restriction}" for restriction in license_obj.restrictions)}

License ID: {license_obj.license_id}
Expires: {license_obj.expires_at or 'Never'}
"""

    def _generate_apache_license(self, license_obj: License) -> str:
        """Generate Apache license content"""
        return f"""Apache License 2.0

Copyright (c) {datetime.now().year} {license_obj.terms.get('copyright_holder', 'System Builder Hub')}

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Additional Terms:
{chr(10).join(f"- {restriction}" for restriction in license_obj.restrictions)}

License ID: {license_obj.license_id}
Expires: {license_obj.expires_at or 'Never'}
"""

    def _generate_commercial_license(self, license_obj: License) -> str:
        """Generate commercial license content"""
        return f"""Commercial License Agreement

Copyright (c) {datetime.now().year} {license_obj.terms.get('copyright_holder', 'System Builder Hub')}

This software is licensed under a commercial license agreement.

License Terms:
{chr(10).join(f"- {term}" for term in license_obj.terms.get('terms', []))}

Restrictions:
{chr(10).join(f"- {restriction}" for restriction in license_obj.restrictions)}

License ID: {license_obj.license_id}
Owner: {license_obj.owner_id}
Organization: {license_obj.organization_id}
Expires: {license_obj.expires_at or 'Never'}

For licensing inquiries, please contact: {license_obj.terms.get('contact_email', 'licensing@systembuilderhub.com')}
"""

    def _generate_custom_license(self, license_obj: License) -> str:
        """Generate custom license content"""
        return f"""Custom License Agreement

Copyright (c) {datetime.now().year} {license_obj.terms.get('copyright_holder', 'System Builder Hub')}

This software is licensed under a custom license agreement.

License Terms:
{chr(10).join(f"- {term}" for term in license_obj.terms.get('terms', []))}

Restrictions:
{chr(10).join(f"- {restriction}" for restriction in license_obj.restrictions)}

License ID: {license_obj.license_id}
Owner: {license_obj.owner_id}
Organization: {license_obj.organization_id}
Expires: {license_obj.expires_at or 'Never'}

Custom Terms:
{license_obj.terms.get('custom_terms', 'No additional custom terms specified.')}
"""

    def _generate_license_file(self, license_obj: License):
        """Generate license file on disk"""
        license_content = self.generate_license_file(license_obj.license_id)
        
        license_file = self.licenses_dir / f"{license_obj.license_id}.txt"
        with open(license_file, 'w') as f:
            f.write(license_content)

    def _generate_license_hash(self, license_obj: License) -> str:
        """Generate hash for license verification"""
        content = f"{license_obj.license_id}{license_obj.system_id}{license_obj.owner_id}{license_obj.created_at}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _record_violation(self, license_id: str, violation_type: str, description: str):
        """Record a license violation"""
        violation_id = f"violation_{py_secrets.token_hex(8)}"
        
        violation = LicenseViolation(
            violation_id=violation_id,
            license_id=license_id,
            violation_type=violation_type,
            description=description,
            severity="medium"
        )
        
        self._save_violation(violation)
        
        if license_id not in self.violations:
            self.violations[license_id] = []
        self.violations[license_id].append(violation)

    def _log_usage(self, license_id: str, user_id: str, action: str):
        """Log license usage"""
        usage_id = f"usage_{py_secrets.token_hex(8)}"
        
        usage = LicenseUsage(
            usage_id=usage_id,
            license_id=license_id,
            user_id=user_id,
            action=action
        )
        
        self._save_usage(usage)
        
        if license_id not in self.usage_logs:
            self.usage_logs[license_id] = []
        self.usage_logs[license_id].append(usage)

    def _update_license_status(self, license_id: str, status: LicenseStatus):
        """Update license status"""
        if license_id in self.licenses:
            license_obj = self.licenses[license_id]
            license_obj.status = status
            self._save_license(license_obj)

    def _save_license(self, license_obj: License):
        """Save license to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO licenses 
            (license_id, system_id, license_type, status, owner_id, organization_id,
             terms, restrictions, expires_at, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            license_obj.license_id, license_obj.system_id, license_obj.license_type.value,
            license_obj.status.value, license_obj.owner_id, license_obj.organization_id,
            json.dumps(license_obj.terms), json.dumps(license_obj.restrictions),
            license_obj.expires_at, license_obj.created_at, json.dumps(license_obj.metadata)
        ))
        
        conn.commit()
        conn.close()

    def _save_template(self, template: SystemTemplate):
        """Save template to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO system_templates 
            (template_id, name, description, system_id, pricing_model, price, currency,
             license_type, features, limitations, is_published, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template.template_id, template.name, template.description, template.system_id,
            template.pricing_model.value, template.price, template.currency,
            template.license_type.value, json.dumps(template.features),
            json.dumps(template.limitations), template.is_published, template.created_at,
            json.dumps(template.metadata)
        ))
        
        conn.commit()
        conn.close()

    def _save_violation(self, violation: LicenseViolation):
        """Save violation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO license_violations 
            (violation_id, license_id, violation_type, description, severity,
             detected_at, resolved_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            violation.violation_id, violation.license_id, violation.violation_type,
            violation.description, violation.severity, violation.detected_at,
            violation.resolved_at, json.dumps(violation.metadata)
        ))
        
        conn.commit()
        conn.close()

    def _save_usage(self, usage: LicenseUsage):
        """Save usage to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO license_usage 
            (usage_id, license_id, user_id, action, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            usage.usage_id, usage.license_id, usage.user_id, usage.action,
            usage.timestamp, json.dumps(usage.metadata)
        ))
        
        conn.commit()
        conn.close()

    def get_license(self, license_id: str) -> Optional[License]:
        """Get license by ID"""
        return self.licenses.get(license_id)

    def get_template(self, template_id: str) -> Optional[SystemTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)

    def get_published_templates(self) -> List[SystemTemplate]:
        """Get all published templates"""
        return [t for t in self.templates.values() if t.is_published]

    def get_license_violations(self, license_id: str) -> List[LicenseViolation]:
        """Get violations for a license"""
        return self.violations.get(license_id, [])

    def get_license_usage(self, license_id: str) -> List[LicenseUsage]:
        """Get usage logs for a license"""
        return self.usage_logs.get(license_id, [])

    def revoke_license(self, license_id: str) -> bool:
        """Revoke a license"""
        if license_id not in self.licenses:
            return False
        
        self._update_license_status(license_id, LicenseStatus.REVOKED)
        return True

    def renew_license(self, license_id: str, new_expires_at: str) -> bool:
        """Renew a license"""
        if license_id not in self.licenses:
            return False
        
        license_obj = self.licenses[license_id]
        license_obj.expires_at = new_expires_at
        license_obj.status = LicenseStatus.ACTIVE
        
        self._save_license(license_obj)
        return True

    def search_templates(self, query: str) -> List[SystemTemplate]:
        """Search templates by name and description"""
        query_lower = query.lower()
        results = []
        
        for template in self.templates.values():
            if (query_lower in template.name.lower() or 
                query_lower in template.description.lower()):
                results.append(template)
        
        return results
