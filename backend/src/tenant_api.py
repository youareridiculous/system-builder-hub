"""
Tenant management API endpoints
"""
import logging
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.db_core import get_session
from src.tenancy.models import Tenant, TenantUser
from src.tenancy.decorators import require_tenant, tenant_owner, tenant_admin, tenant_member_role
from src.tenancy.context import get_current_tenant, get_current_tenant_id
from src.auth_api import require_auth, get_current_user
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)
bp = Blueprint('tenant_api', __name__, url_prefix='/api/tenants')

@bp.route('', methods=['POST'])
@require_auth
def create_tenant():
    """Create a new tenant"""
    try:
        data = request.get_json()
        name = data.get('name')
        slug = data.get('slug')
        
        if not name or not slug:
            return jsonify({'error': 'Name and slug are required'}), 400
        
        # Validate slug format
        import re
        if not re.match(r'^[a-z0-9-]{1,63}$', slug):
            return jsonify({'error': 'Invalid slug format. Use lowercase letters, numbers, and hyphens only.'}), 400
        
        session = get_session()
        
        # Check if slug already exists
        existing = session.query(Tenant).filter(Tenant.slug == slug).first()
        if existing:
            return jsonify({'error': 'Tenant slug already exists'}), 409
        
        # Create tenant
        tenant = Tenant(
            slug=slug,
            name=name,
            plan='free',
            status='active'
        )
        session.add(tenant)
        session.flush()  # Get the ID
        
        # Add creator as owner
        user_id = g.user_id
        tenant_user = TenantUser(
            tenant_id=tenant.id,
            user_id=user_id,
            role='owner'
        )
        session.add(tenant_user)
        session.commit()
        
        logger.info(f"Created tenant {slug} with owner {user_id}")
        
        return jsonify({
            'success': True,
            'tenant': {
                'id': str(tenant.id),
                'slug': tenant.slug,
                'name': tenant.name,
                'plan': tenant.plan,
                'status': tenant.status
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/me', methods=['GET'])
@require_auth
def get_user_tenants():
    """Get tenants for current user"""
    try:
        user_id = g.user_id
        session = get_session()
        
        # Get user's tenant memberships
        memberships = session.query(TenantUser).filter(
            TenantUser.user_id == user_id
        ).all()
        
        tenants = []
        for membership in memberships:
            tenant = membership.tenant
            tenants.append({
                'id': str(tenant.id),
                'slug': tenant.slug,
                'name': tenant.name,
                'plan': tenant.plan,
                'status': tenant.status,
                'role': membership.role
            })
        
        return jsonify({
            'success': True,
            'tenants': tenants
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user tenants: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/invite', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def invite_user():
    """Invite user to tenant"""
    try:
        data = request.get_json()
        email = data.get('email')
        role = data.get('role', 'member')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        if role not in ['owner', 'admin', 'member', 'viewer']:
            return jsonify({'error': 'Invalid role'}), 400
        
        tenant = get_current_tenant()
        session = get_session()
        
        # Check if user exists
        from auth_api import get_user_by_email
        user = get_user_by_email(session, email)
        
        if not user:
            # Create user if they don't exist (dev mode)
            from auth_api import create_user
            user = create_user(session, email, 'temp-password', 'user')
            logger.info(f"Created new user {email} for tenant invitation")
        
        # Check if user is already a member
        existing_membership = session.query(TenantUser).filter(
            TenantUser.tenant_id == tenant.id,
            TenantUser.user_id == user['id']
        ).first()
        
        if existing_membership:
            # Update role
            existing_membership.role = role
            session.commit()
            logger.info(f"Updated role for user {email} in tenant {tenant.slug} to {role}")
        else:
            # Create new membership
            tenant_user = TenantUser(
                tenant_id=tenant.id,
                user_id=user['id'],
                role=role
            )
            session.add(tenant_user)
            session.commit()
            logger.info(f"Invited user {email} to tenant {tenant.slug} with role {role}")
        
        # TODO: Send email invitation (implement in next iteration)
        
        return jsonify({
            'success': True,
            'message': f'User {email} invited to tenant with role {role}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error inviting user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/members', methods=['GET'])
@require_auth
@require_tenant()
@tenant_member_role()
def get_tenant_members():
    """Get members of current tenant"""
    try:
        tenant = get_current_tenant()
        session = get_session()
        
        # Get tenant memberships with user details
        memberships = session.query(TenantUser).filter(
            TenantUser.tenant_id == tenant.id
        ).all()
        
        members = []
        for membership in memberships:
            user = membership.user
            members.append({
                'id': str(user.id),
                'email': user.email,
                'role': membership.role,
                'joined_at': membership.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'members': members
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting tenant members: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/current', methods=['GET'])
@require_auth
@require_tenant()
def get_current_tenant_info():
    """Get current tenant information"""
    try:
        tenant = get_current_tenant()
        
        return jsonify({
            'success': True,
            'tenant': {
                'id': str(tenant.id),
                'slug': tenant.slug,
                'name': tenant.name,
                'plan': tenant.plan,
                'status': tenant.status
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting current tenant: {e}")
        return jsonify({'error': 'Internal server error'}), 500
