"""
Organization Operations & Management System
Priority 12: Team Collaboration & Org Management Layer
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid


class OrgRole(Enum):
    """Organization role types"""
    OWNER = "owner"
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    QA = "qa"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class ProjectStatus(Enum):
    """Project status"""
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class InvitationStatus(Enum):
    """Invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


@dataclass
class Organization:
    """Organization entity"""
    organization_id: str
    name: str
    description: str
    owner_id: str
    created_at: datetime
    settings: Dict[str, Any]
    branding: Dict[str, Any]
    license_info: Dict[str, Any]
    member_count: int = 0
    project_count: int = 0
    system_count: int = 0


@dataclass
class OrganizationMember:
    """Organization member"""
    member_id: str
    organization_id: str
    user_id: str
    role: OrgRole
    joined_at: datetime
    invited_by: str
    permissions: Dict[str, Any]
    is_active: bool = True
    last_active: Optional[datetime] = None


@dataclass
class Project:
    """Project entity for grouping systems"""
    project_id: str
    organization_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime
    status: ProjectStatus
    members: List[str]
    systems: List[str]
    settings: Dict[str, Any]
    due_date: Optional[datetime] = None


@dataclass
class MemberInvitation:
    """Member invitation"""
    invitation_id: str
    organization_id: str
    email: str
    role: OrgRole
    invited_by: str
    invited_at: datetime
    expires_at: datetime
    status: InvitationStatus
    message: Optional[str] = None


@dataclass
class OrgDashboard:
    """Organization dashboard data"""
    organization_id: str
    total_members: int
    active_members: int
    total_projects: int
    active_projects: int
    total_systems: int
    recent_activity: List[Dict[str, Any]]
    system_distribution: Dict[str, int]
    member_activity: List[Dict[str, Any]]
    project_status: Dict[str, int]


class OrganizationOperations:
    """Organization Operations & Management System"""
    
    def __init__(self, base_dir: str, access_control, system_delivery, llm_factory):
        self.base_dir = base_dir
        self.access_control = access_control
        self.system_delivery = system_delivery
        self.llm_factory = llm_factory
        self.db_path = f"{base_dir}/org_operations.db"
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize organization database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    organization_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    settings TEXT,
                    branding TEXT,
                    license_info TEXT,
                    member_count INTEGER DEFAULT 0,
                    project_count INTEGER DEFAULT 0,
                    system_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS organization_members (
                    member_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    joined_at TEXT NOT NULL,
                    invited_by TEXT NOT NULL,
                    permissions TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_active TEXT,
                    FOREIGN KEY (organization_id) REFERENCES organizations (organization_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    members TEXT,
                    systems TEXT,
                    settings TEXT,
                    due_date TEXT,
                    FOREIGN KEY (organization_id) REFERENCES organizations (organization_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS member_invitations (
                    invitation_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL,
                    invited_by TEXT NOT NULL,
                    invited_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    FOREIGN KEY (organization_id) REFERENCES organizations (organization_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS org_activity_log (
                    log_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (organization_id) REFERENCES organizations (organization_id)
                )
            """)
            
            conn.commit()
    
    def create_organization(self, name: str, description: str, owner_id: str,
                          settings: Dict[str, Any] = None, branding: Dict[str, Any] = None,
                          license_info: Dict[str, Any] = None) -> Organization:
        """Create a new organization"""
        organization_id = str(uuid.uuid4())
        now = datetime.now()
        
        org = Organization(
            organization_id=organization_id,
            name=name,
            description=description,
            owner_id=owner_id,
            created_at=now,
            settings=settings or {},
            branding=branding or {},
            license_info=license_info or {}
        )
        
        # Save organization
        self._save_organization(org)
        
        # Add owner as first member
        self.add_member(organization_id, owner_id, OrgRole.OWNER, owner_id)
        
        # Log activity
        self._log_activity(organization_id, owner_id, "organization_created", {
            "organization_name": name
        })
        
        return org
    
    def add_member(self, organization_id: str, user_id: str, role: OrgRole, 
                  invited_by: str, permissions: Dict[str, Any] = None) -> OrganizationMember:
        """Add a member to the organization"""
        member_id = str(uuid.uuid4())
        now = datetime.now()
        
        member = OrganizationMember(
            member_id=member_id,
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            joined_at=now,
            invited_by=invited_by,
            permissions=permissions or self._get_default_permissions(role)
        )
        
        # Save member
        self._save_member(member)
        
        # Update organization member count
        self._update_org_member_count(organization_id)
        
        # Log activity
        self._log_activity(organization_id, invited_by, "member_added", {
            "user_id": user_id,
            "role": role.value
        })
        
        return member
    
    def remove_member(self, organization_id: str, user_id: str, removed_by: str) -> bool:
        """Remove a member from the organization"""
        # Check if user can remove members
        if not self._can_manage_members(removed_by, organization_id):
            raise PermissionError(f"User {removed_by} cannot remove members")
        
        # Get member info
        member = self.get_member(organization_id, user_id)
        if not member:
            return False
        
        # Check if trying to remove owner
        if member.role == OrgRole.OWNER:
            raise PermissionError("Cannot remove organization owner")
        
        # Remove member
        self._remove_member(organization_id, user_id)
        
        # Update organization member count
        self._update_org_member_count(organization_id)
        
        # Log activity
        self._log_activity(organization_id, removed_by, "member_removed", {
            "user_id": user_id,
            "role": member.role.value
        })
        
        return True
    
    def update_member_role(self, organization_id: str, user_id: str, new_role: OrgRole, 
                          updated_by: str) -> bool:
        """Update member role"""
        # Check if user can update roles
        if not self._can_manage_members(updated_by, organization_id):
            raise PermissionError(f"User {updated_by} cannot update member roles")
        
        # Get member
        member = self.get_member(organization_id, user_id)
        if not member:
            return False
        
        # Check if trying to change owner role
        if member.role == OrgRole.OWNER:
            raise PermissionError("Cannot change organization owner role")
        
        # Update role
        member.role = new_role
        member.permissions = self._get_default_permissions(new_role)
        self._save_member(member)
        
        # Log activity
        self._log_activity(organization_id, updated_by, "member_role_updated", {
            "user_id": user_id,
            "old_role": member.role.value,
            "new_role": new_role.value
        })
        
        return True
    
    def invite_member(self, organization_id: str, email: str, role: OrgRole, 
                     invited_by: str, message: str = None, expires_days: int = 7) -> MemberInvitation:
        """Invite a new member to the organization"""
        # Check if user can invite members
        if not self._can_invite_members(invited_by, organization_id):
            raise PermissionError(f"User {invited_by} cannot invite members")
        
        invitation_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(days=expires_days)
        
        invitation = MemberInvitation(
            invitation_id=invitation_id,
            organization_id=organization_id,
            email=email,
            role=role,
            invited_by=invited_by,
            invited_at=now,
            expires_at=expires_at,
            status=InvitationStatus.PENDING,
            message=message
        )
        
        # Save invitation
        self._save_invitation(invitation)
        
        # Log activity
        self._log_activity(organization_id, invited_by, "member_invited", {
            "email": email,
            "role": role.value
        })
        
        return invitation
    
    def accept_invitation(self, invitation_id: str, user_id: str) -> bool:
        """Accept a member invitation"""
        invitation = self.get_invitation(invitation_id)
        if not invitation:
            return False
        
        # Check if invitation is still valid
        if invitation.status != InvitationStatus.PENDING:
            return False
        
        if datetime.now() > invitation.expires_at:
            invitation.status = InvitationStatus.EXPIRED
            self._save_invitation(invitation)
            return False
        
        # Add member
        self.add_member(invitation.organization_id, user_id, invitation.role, invitation.invited_by)
        
        # Update invitation status
        invitation.status = InvitationStatus.ACCEPTED
        self._save_invitation(invitation)
        
        return True
    
    def create_project(self, organization_id: str, name: str, description: str, 
                      created_by: str, members: List[str] = None, 
                      settings: Dict[str, Any] = None) -> Project:
        """Create a new project"""
        # Check if user can create projects
        if not self._can_create_projects(created_by, organization_id):
            raise PermissionError(f"User {created_by} cannot create projects")
        
        project_id = str(uuid.uuid4())
        now = datetime.now()
        
        project = Project(
            project_id=project_id,
            organization_id=organization_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=now,
            status=ProjectStatus.ACTIVE,
            members=members or [created_by],
            systems=[],
            settings=settings or {}
        )
        
        # Save project
        self._save_project(project)
        
        # Update organization project count
        self._update_org_project_count(organization_id)
        
        # Log activity
        self._log_activity(organization_id, created_by, "project_created", {
            "project_name": name,
            "project_id": project_id
        })
        
        return project
    
    def add_system_to_project(self, project_id: str, system_id: str, added_by: str) -> bool:
        """Add a system to a project"""
        project = self.get_project(project_id)
        if not project:
            return False
        
        # Check if user can modify project
        if not self._can_modify_project(added_by, project):
            raise PermissionError(f"User {added_by} cannot modify this project")
        
        # Add system to project
        if system_id not in project.systems:
            project.systems.append(system_id)
            self._save_project(project)
            
            # Update organization system count
            self._update_org_system_count(project.organization_id)
            
            # Log activity
            self._log_activity(project.organization_id, added_by, "system_added_to_project", {
                "project_id": project_id,
                "system_id": system_id
            })
        
        return True
    
    def get_organization_dashboard(self, organization_id: str) -> OrgDashboard:
        """Get organization dashboard data"""
        org = self.get_organization(organization_id)
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        
        # Get member statistics
        members = self.get_organization_members(organization_id)
        active_members = [m for m in members if m.is_active]
        
        # Get project statistics
        projects = self.get_organization_projects(organization_id)
        active_projects = [p for p in projects if p.status == ProjectStatus.ACTIVE]
        
        # Get system distribution
        system_distribution = self._get_system_distribution(organization_id)
        
        # Get recent activity
        recent_activity = self._get_recent_activity(organization_id, limit=20)
        
        # Get member activity
        member_activity = self._get_member_activity(organization_id)
        
        # Get project status distribution
        project_status = {}
        for project in projects:
            status = project.status.value
            project_status[status] = project_status.get(status, 0) + 1
        
        return OrgDashboard(
            organization_id=organization_id,
            total_members=len(members),
            active_members=len(active_members),
            total_projects=len(projects),
            active_projects=len(active_projects),
            total_systems=org.system_count,
            recent_activity=recent_activity,
            system_distribution=system_distribution,
            member_activity=member_activity,
            project_status=project_status
        )
    
    def get_organization(self, organization_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM organizations WHERE organization_id = ?
            """, (organization_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_organization(row)
            return None
    
    def get_member(self, organization_id: str, user_id: str) -> Optional[OrganizationMember]:
        """Get organization member"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM organization_members 
                WHERE organization_id = ? AND user_id = ?
            """, (organization_id, user_id))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_member(row)
            return None
    
    def get_organization_members(self, organization_id: str) -> List[OrganizationMember]:
        """Get all organization members"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM organization_members 
                WHERE organization_id = ? AND is_active = TRUE
                ORDER BY joined_at
            """, (organization_id,))
            
            return [self._row_to_member(row) for row in cursor.fetchall()]
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM projects WHERE project_id = ?
            """, (project_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_project(row)
            return None
    
    def get_organization_projects(self, organization_id: str) -> List[Project]:
        """Get all organization projects"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM projects 
                WHERE organization_id = ?
                ORDER BY created_at DESC
            """, (organization_id,))
            
            return [self._row_to_project(row) for row in cursor.fetchall()]
    
    def get_invitation(self, invitation_id: str) -> Optional[MemberInvitation]:
        """Get invitation by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM member_invitations WHERE invitation_id = ?
            """, (invitation_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_invitation(row)
            return None
    
    def get_pending_invitations(self, organization_id: str) -> List[MemberInvitation]:
        """Get pending invitations for organization"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM member_invitations 
                WHERE organization_id = ? AND status = 'pending'
                ORDER BY invited_at DESC
            """, (organization_id,))
            
            return [self._row_to_invitation(row) for row in cursor.fetchall()]
    
    def update_organization_settings(self, organization_id: str, settings: Dict[str, Any], 
                                   updated_by: str) -> bool:
        """Update organization settings"""
        # Check if user can update settings
        if not self._can_update_settings(updated_by, organization_id):
            raise PermissionError(f"User {updated_by} cannot update organization settings")
        
        org = self.get_organization(organization_id)
        if not org:
            return False
        
        # Update settings
        org.settings.update(settings)
        self._save_organization(org)
        
        # Log activity
        self._log_activity(organization_id, updated_by, "settings_updated", {
            "updated_settings": list(settings.keys())
        })
        
        return True
    
    def update_organization_branding(self, organization_id: str, branding: Dict[str, Any], 
                                   updated_by: str) -> bool:
        """Update organization branding"""
        # Check if user can update branding
        if not self._can_update_branding(updated_by, organization_id):
            raise PermissionError(f"User {updated_by} cannot update organization branding")
        
        org = self.get_organization(organization_id)
        if not org:
            return False
        
        # Update branding
        org.branding.update(branding)
        self._save_organization(org)
        
        # Log activity
        self._log_activity(organization_id, updated_by, "branding_updated", {
            "updated_branding": list(branding.keys())
        })
        
        return True
    
    def _get_default_permissions(self, role: OrgRole) -> Dict[str, Any]:
        """Get default permissions for a role"""
        permissions = {
            OrgRole.OWNER: {
                "manage_organization": True,
                "manage_members": True,
                "manage_projects": True,
                "manage_systems": True,
                "view_analytics": True,
                "manage_billing": True
            },
            OrgRole.ADMIN: {
                "manage_organization": False,
                "manage_members": True,
                "manage_projects": True,
                "manage_systems": True,
                "view_analytics": True,
                "manage_billing": False
            },
            OrgRole.PROJECT_MANAGER: {
                "manage_organization": False,
                "manage_members": False,
                "manage_projects": True,
                "manage_systems": True,
                "view_analytics": True,
                "manage_billing": False
            },
            OrgRole.ARCHITECT: {
                "manage_organization": False,
                "manage_members": False,
                "manage_projects": False,
                "manage_systems": True,
                "view_analytics": True,
                "manage_billing": False
            },
            OrgRole.DEVELOPER: {
                "manage_organization": False,
                "manage_members": False,
                "manage_projects": False,
                "manage_systems": True,
                "view_analytics": False,
                "manage_billing": False
            },
            OrgRole.QA: {
                "manage_organization": False,
                "manage_members": False,
                "manage_projects": False,
                "manage_systems": False,
                "view_analytics": False,
                "manage_billing": False
            },
            OrgRole.REVIEWER: {
                "manage_organization": False,
                "manage_members": False,
                "manage_projects": False,
                "manage_systems": False,
                "view_analytics": False,
                "manage_billing": False
            },
            OrgRole.VIEWER: {
                "manage_organization": False,
                "manage_members": False,
                "manage_projects": False,
                "manage_systems": False,
                "view_analytics": False,
                "manage_billing": False
            }
        }
        
        return permissions.get(role, {})
    
    def _can_manage_members(self, user_id: str, organization_id: str) -> bool:
        """Check if user can manage members"""
        member = self.get_member(organization_id, user_id)
        if not member:
            return False
        
        return member.role in [OrgRole.OWNER, OrgRole.ADMIN]
    
    def _can_invite_members(self, user_id: str, organization_id: str) -> bool:
        """Check if user can invite members"""
        member = self.get_member(organization_id, user_id)
        if not member:
            return False
        
        return member.role in [OrgRole.OWNER, OrgRole.ADMIN]
    
    def _can_create_projects(self, user_id: str, organization_id: str) -> bool:
        """Check if user can create projects"""
        member = self.get_member(organization_id, user_id)
        if not member:
            return False
        
        return member.role in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.PROJECT_MANAGER]
    
    def _can_modify_project(self, user_id: str, project: Project) -> bool:
        """Check if user can modify project"""
        member = self.get_member(project.organization_id, user_id)
        if not member:
            return False
        
        return (member.role in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.PROJECT_MANAGER] or
                user_id in project.members)
    
    def _can_update_settings(self, user_id: str, organization_id: str) -> bool:
        """Check if user can update settings"""
        member = self.get_member(organization_id, user_id)
        if not member:
            return False
        
        return member.role in [OrgRole.OWNER, OrgRole.ADMIN]
    
    def _can_update_branding(self, user_id: str, organization_id: str) -> bool:
        """Check if user can update branding"""
        member = self.get_member(organization_id, user_id)
        if not member:
            return False
        
        return member.role in [OrgRole.OWNER, OrgRole.ADMIN]
    
    def _save_organization(self, org: Organization):
        """Save organization to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO organizations 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                org.organization_id, org.name, org.description, org.owner_id,
                org.created_at.isoformat(), json.dumps(org.settings),
                json.dumps(org.branding), json.dumps(org.license_info),
                org.member_count, org.project_count, org.system_count
            ))
            conn.commit()
    
    def _save_member(self, member: OrganizationMember):
        """Save member to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO organization_members 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                member.member_id, member.organization_id, member.user_id,
                member.role.value, member.joined_at.isoformat(),
                member.invited_by, json.dumps(member.permissions),
                member.is_active, member.last_active.isoformat() if member.last_active else None
            ))
            conn.commit()
    
    def _save_project(self, project: Project):
        """Save project to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO projects 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.project_id, project.organization_id, project.name,
                project.description, project.created_by, project.created_at.isoformat(),
                project.status.value, json.dumps(project.members),
                json.dumps(project.systems), json.dumps(project.settings),
                project.due_date.isoformat() if project.due_date else None
            ))
            conn.commit()
    
    def _save_invitation(self, invitation: MemberInvitation):
        """Save invitation to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO member_invitations 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invitation.invitation_id, invitation.organization_id,
                invitation.email, invitation.role.value, invitation.invited_by,
                invitation.invited_at.isoformat(), invitation.expires_at.isoformat(),
                invitation.status.value, invitation.message
            ))
            conn.commit()
    
    def _remove_member(self, organization_id: str, user_id: str):
        """Remove member from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM organization_members 
                WHERE organization_id = ? AND user_id = ?
            """, (organization_id, user_id))
            conn.commit()
    
    def _update_org_member_count(self, organization_id: str):
        """Update organization member count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM organization_members 
                WHERE organization_id = ? AND is_active = TRUE
            """, (organization_id,))
            count = cursor.fetchone()[0]
            
            conn.execute("""
                UPDATE organizations SET member_count = ? WHERE organization_id = ?
            """, (count, organization_id))
            conn.commit()
    
    def _update_org_project_count(self, organization_id: str):
        """Update organization project count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM projects WHERE organization_id = ?
            """, (organization_id,))
            count = cursor.fetchone()[0]
            
            conn.execute("""
                UPDATE organizations SET project_count = ? WHERE organization_id = ?
            """, (count, organization_id))
            conn.commit()
    
    def _update_org_system_count(self, organization_id: str):
        """Update organization system count"""
        # This would integrate with system_delivery to get actual count
        # For now, just increment
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE organizations SET system_count = system_count + 1 
                WHERE organization_id = ?
            """, (organization_id,))
            conn.commit()
    
    def _log_activity(self, organization_id: str, user_id: str, action: str, details: Dict[str, Any]):
        """Log organization activity"""
        log_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO org_activity_log 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                log_id, organization_id, user_id, action,
                now.isoformat(), json.dumps(details)
            ))
            conn.commit()
    
    def _get_system_distribution(self, organization_id: str) -> Dict[str, int]:
        """Get system distribution by type"""
        # This would integrate with system_delivery
        # For now, return empty dict
        return {}
    
    def _get_recent_activity(self, organization_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent organization activity"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM org_activity_log 
                WHERE organization_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (organization_id, limit))
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    "log_id": row[0],
                    "user_id": row[2],
                    "action": row[3],
                    "timestamp": row[4],
                    "details": json.loads(row[5]) if row[5] else {}
                })
            
            return activities
    
    def _get_member_activity(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get member activity statistics"""
        # This would calculate member activity based on recent actions
        # For now, return empty list
        return []
    
    def _row_to_organization(self, row) -> Organization:
        """Convert database row to Organization object"""
        return Organization(
            organization_id=row[0],
            name=row[1],
            description=row[2],
            owner_id=row[3],
            created_at=datetime.fromisoformat(row[4]),
            settings=json.loads(row[5]) if row[5] else {},
            branding=json.loads(row[6]) if row[6] else {},
            license_info=json.loads(row[7]) if row[7] else {},
            member_count=row[8],
            project_count=row[9],
            system_count=row[10]
        )
    
    def _row_to_member(self, row) -> OrganizationMember:
        """Convert database row to OrganizationMember object"""
        return OrganizationMember(
            member_id=row[0],
            organization_id=row[1],
            user_id=row[2],
            role=OrgRole(row[3]),
            joined_at=datetime.fromisoformat(row[4]),
            invited_by=row[5],
            permissions=json.loads(row[6]) if row[6] else {},
            is_active=row[7],
            last_active=datetime.fromisoformat(row[8]) if row[8] else None
        )
    
    def _row_to_project(self, row) -> Project:
        """Convert database row to Project object"""
        return Project(
            project_id=row[0],
            organization_id=row[1],
            name=row[2],
            description=row[3],
            created_by=row[4],
            created_at=datetime.fromisoformat(row[5]),
            status=ProjectStatus(row[6]),
            members=json.loads(row[7]) if row[7] else [],
            systems=json.loads(row[8]) if row[8] else [],
            settings=json.loads(row[9]) if row[9] else {},
            due_date=datetime.fromisoformat(row[10]) if row[10] else None
        )
    
    def _row_to_invitation(self, row) -> MemberInvitation:
        """Convert database row to MemberInvitation object"""
        return MemberInvitation(
            invitation_id=row[0],
            organization_id=row[1],
            email=row[2],
            role=OrgRole(row[3]),
            invited_by=row[4],
            invited_at=datetime.fromisoformat(row[5]),
            expires_at=datetime.fromisoformat(row[6]),
            status=InvitationStatus(row[7]),
            message=row[8]
        )
