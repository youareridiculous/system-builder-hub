"""
Domain lifecycle service
"""
import os
import uuid
import logging
import dns.resolver
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from src.db_core import get_session
from src.domains.models import CustomDomain
from src.domains.aws import ACMAdapter, ALBAdapter, Route53Adapter

logger = logging.getLogger(__name__)

class DomainService:
    """Domain lifecycle service"""
    
    def __init__(self):
        self.acm = ACMAdapter()
        self.alb = ALBAdapter()
        self.route53 = Route53Adapter()
        self.shared_domain = os.environ.get('SHARED_DOMAIN', 'myapp.com')
        self.auto_verify = os.environ.get('FEATURE_DEV_AUTO_VERIFY_DOMAINS', 'false').lower() == 'true'
    
    def create_domain(self, tenant_id: str, hostname: str) -> Dict:
        """Create a new custom domain"""
        try:
            session = get_session()
            
            # Check if domain already exists
            existing = session.query(CustomDomain).filter(
                CustomDomain.hostname == hostname
            ).first()
            
            if existing:
                raise ValueError(f"Domain {hostname} already exists")
            
            # Generate verification token
            verification_token = str(uuid.uuid4())
            
            # Create domain record
            domain = CustomDomain(
                tenant_id=tenant_id,
                hostname=hostname,
                status='pending',
                verification_token=verification_token
            )
            
            session.add(domain)
            session.commit()
            
            logger.info(f"Created domain {hostname} for tenant {tenant_id}")
            
            return {
                'id': str(domain.id),
                'hostname': domain.hostname,
                'status': domain.status,
                'verification_token': domain.verification_token,
                'required_dns': self._get_required_dns_records(hostname, verification_token)
            }
            
        except Exception as e:
            logger.error(f"Error creating domain {hostname}: {e}")
            raise
    
    def _get_required_dns_records(self, hostname: str, token: str) -> List[Dict]:
        """Get required DNS records for domain verification"""
        return [
            {
                'type': 'TXT',
                'name': hostname,
                'value': f'sbh-verify={token}',
                'description': 'Domain verification record'
            }
        ]
    
    def dns_txt_name(self, hostname: str) -> str:
        """Get DNS TXT record name for verification"""
        return f"_acme-challenge.{hostname}"
    
    def verify_domain(self, hostname: str) -> Dict:
        """Verify domain ownership and request ACM certificate"""
        try:
            session = get_session()
            
            # Get domain record
            domain = session.query(CustomDomain).filter(
                CustomDomain.hostname == hostname
            ).first()
            
            if not domain:
                raise ValueError(f"Domain {hostname} not found")
            
            if domain.status != 'pending':
                raise ValueError(f"Domain {hostname} is not in pending status")
            
            # Verify TXT record
            if not self._verify_txt_record(hostname, domain.verification_token):
                raise ValueError(f"TXT record verification failed for {hostname}")
            
            # Request ACM certificate
            certificate_arn = self.acm.request_certificate(hostname)
            if not certificate_arn:
                raise ValueError(f"Failed to request ACM certificate for {hostname}")
            
            # Update domain status
            domain.status = 'verifying'
            domain.acm_arn = certificate_arn
            session.commit()
            
            # Get ACM validation records
            validation_records = self.acm.get_validation_records(certificate_arn)
            
            logger.info(f"Domain {hostname} verification started, ACM certificate requested")
            
            return {
                'hostname': domain.hostname,
                'status': domain.status,
                'acm_arn': domain.acm_arn,
                'validation_records': validation_records
            }
            
        except Exception as e:
            logger.error(f"Error verifying domain {hostname}: {e}")
            raise
    
    def _verify_txt_record(self, hostname: str, token: str) -> bool:
        """Verify TXT record exists"""
        if self.auto_verify:
            logger.info(f"Auto-verifying TXT record for {hostname} (dev mode)")
            return True
        
        try:
            # Try Route53 first
            if self.route53.verify_txt_record(hostname, f'sbh-verify={token}'):
                return True
            
            # Fallback to DNS resolver
            resolver = dns.resolver.Resolver()
            txt_records = resolver.resolve(hostname, 'TXT')
            
            for record in txt_records:
                if f'sbh-verify={token}' in str(record):
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error verifying TXT record for {hostname}: {e}")
            return False
    
    def activate_domain(self, hostname: str) -> Dict:
        """Activate domain by polling ACM and creating ALB rule"""
        try:
            session = get_session()
            
            # Get domain record
            domain = session.query(CustomDomain).filter(
                CustomDomain.hostname == hostname
            ).first()
            
            if not domain:
                raise ValueError(f"Domain {hostname} not found")
            
            if domain.status != 'verifying':
                raise ValueError(f"Domain {hostname} is not in verifying status")
            
            if not domain.acm_arn:
                raise ValueError(f"No ACM certificate ARN for {hostname}")
            
            # Check certificate status
            cert_status = self.acm.get_certificate_status(domain.acm_arn)
            if cert_status != 'ISSUED':
                raise ValueError(f"Certificate not issued yet, status: {cert_status}")
            
            # Create ALB rule
            listener_arn = os.environ.get('ALB_LISTENER_HTTPS_ARN')
            if not listener_arn:
                # Auto-discover listener
                listener_arn = self._discover_https_listener()
            
            if not listener_arn:
                raise ValueError("Could not find HTTPS listener")
            
            # Get target group ARN
            target_group_arn = self._get_target_group_arn()
            if not target_group_arn:
                raise ValueError("Could not find target group")
            
            # Create host-based rule
            rule_arn = self.alb.create_listener_rule(
                listener_arn, hostname, target_group_arn, priority=100
            )
            
            if not rule_arn:
                raise ValueError("Failed to create ALB rule")
            
            # Update domain status
            domain.status = 'active'
            session.commit()
            
            logger.info(f"Domain {hostname} activated successfully")
            
            return {
                'hostname': domain.hostname,
                'status': domain.status,
                'rule_arn': rule_arn
            }
            
        except Exception as e:
            logger.error(f"Error activating domain {hostname}: {e}")
            raise
    
    def _discover_https_listener(self) -> Optional[str]:
        """Auto-discover HTTPS listener"""
        try:
            load_balancers = self.alb.get_load_balancers()
            
            for lb in load_balancers:
                listeners = self.alb.get_listeners(lb['LoadBalancerArn'])
                
                for listener in listeners:
                    if listener['Port'] == 443:
                        return listener['ListenerArn']
            
            return None
            
        except Exception as e:
            logger.error(f"Error discovering HTTPS listener: {e}")
            return None
    
    def _get_target_group_arn(self) -> Optional[str]:
        """Get target group ARN"""
        try:
            # This would need to be configured or auto-discovered
            # For now, return None and let the caller handle it
            return None
        except Exception as e:
            logger.error(f"Error getting target group ARN: {e}")
            return None
    
    def delete_domain(self, hostname: str) -> bool:
        """Delete domain and clean up resources"""
        try:
            session = get_session()
            
            # Get domain record
            domain = session.query(CustomDomain).filter(
                CustomDomain.hostname == hostname
            ).first()
            
            if not domain:
                raise ValueError(f"Domain {hostname} not found")
            
            # Delete ALB rule if active
            if domain.status == 'active':
                # This would need to store rule ARN in the domain record
                # For now, just mark as pending
                domain.status = 'pending'
            
            # Delete ACM certificate if exists
            if domain.acm_arn:
                self.acm.delete_certificate(domain.acm_arn)
            
            # Delete domain record
            session.delete(domain)
            session.commit()
            
            logger.info(f"Domain {hostname} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting domain {hostname}: {e}")
            return False
    
    def get_tenant_domains(self, tenant_id: str) -> List[Dict]:
        """Get all domains for a tenant"""
        try:
            session = get_session()
            
            domains = session.query(CustomDomain).filter(
                CustomDomain.tenant_id == tenant_id
            ).all()
            
            result = []
            for domain in domains:
                domain_data = {
                    'id': str(domain.id),
                    'hostname': domain.hostname,
                    'status': domain.status,
                    'created_at': domain.created_at.isoformat(),
                    'updated_at': domain.updated_at.isoformat()
                }
                
                # Add required DNS records for pending domains
                if domain.status == 'pending':
                    domain_data['required_dns'] = self._get_required_dns_records(
                        domain.hostname, domain.verification_token
                    )
                
                # Add validation records for verifying domains
                if domain.status == 'verifying' and domain.acm_arn:
                    domain_data['validation_records'] = self.acm.get_validation_records(domain.acm_arn)
                
                result.append(domain_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting domains for tenant {tenant_id}: {e}")
            return []
    
    def resolve_tenant_by_hostname(self, hostname: str) -> Optional[str]:
        """Resolve tenant ID by hostname"""
        try:
            session = get_session()
            
            domain = session.query(CustomDomain).filter(
                CustomDomain.hostname == hostname,
                CustomDomain.status == 'active'
            ).first()
            
            return str(domain.tenant_id) if domain else None
            
        except Exception as e:
            logger.error(f"Error resolving tenant for hostname {hostname}: {e}")
            return None
