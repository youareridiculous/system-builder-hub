"""
AWS adapters for custom domains (ACM, ALB, Route53)
"""
import os
import logging
import boto3
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class ACMAdapter:
    """AWS Certificate Manager adapter"""
    
    def __init__(self, region: str = None):
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        try:
            self.client = boto3.client('acm', region_name=self.region)
        except NoCredentialsError:
            logger.warning("AWS credentials not found for ACM")
            self.client = None
    
    def request_certificate(self, domain_name: str, validation_method: str = 'DNS') -> Optional[str]:
        """Request ACM certificate"""
        if not self.client:
            logger.warning("ACM client not available")
            return None
        
        try:
            response = self.client.request_certificate(
                DomainName=domain_name,
                ValidationMethod=validation_method,
                SubjectAlternativeNames=[domain_name]
            )
            return response['CertificateArn']
        except ClientError as e:
            logger.error(f"Error requesting ACM certificate: {e}")
            return None
    
    def get_certificate_status(self, certificate_arn: str) -> Optional[str]:
        """Get certificate status"""
        if not self.client:
            return None
        
        try:
            response = self.client.describe_certificate(CertificateArn=certificate_arn)
            return response['Certificate']['Status']
        except ClientError as e:
            logger.error(f"Error getting certificate status: {e}")
            return None
    
    def get_validation_records(self, certificate_arn: str) -> List[Dict]:
        """Get DNS validation records"""
        if not self.client:
            return []
        
        try:
            response = self.client.describe_certificate(CertificateArn=certificate_arn)
            certificate = response['Certificate']
            
            validation_records = []
            for validation in certificate.get('DomainValidationOptions', []):
                if validation['ValidationMethod'] == 'DNS':
                    validation_domain = validation['ResourceRecord']['Name']
                    validation_value = validation['ResourceRecord']['Value']
                    validation_records.append({
                        'name': validation_domain,
                        'value': validation_value,
                        'type': 'CNAME'
                    })
            
            return validation_records
        except ClientError as e:
            logger.error(f"Error getting validation records: {e}")
            return []
    
    def delete_certificate(self, certificate_arn: str) -> bool:
        """Delete certificate"""
        if not self.client:
            return False
        
        try:
            self.client.delete_certificate(CertificateArn=certificate_arn)
            return True
        except ClientError as e:
            logger.error(f"Error deleting certificate: {e}")
            return False

class ALBAdapter:
    """Application Load Balancer adapter"""
    
    def __init__(self, region: str = None):
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        try:
            self.client = boto3.client('elbv2', region_name=self.region)
        except NoCredentialsError:
            logger.warning("AWS credentials not found for ALB")
            self.client = None
    
    def get_load_balancers(self) -> List[Dict]:
        """Get load balancers"""
        if not self.client:
            return []
        
        try:
            response = self.client.describe_load_balancers()
            return response['LoadBalancers']
        except ClientError as e:
            logger.error(f"Error getting load balancers: {e}")
            return []
    
    def get_listeners(self, load_balancer_arn: str) -> List[Dict]:
        """Get listeners for load balancer"""
        if not self.client:
            return []
        
        try:
            response = self.client.describe_listeners(LoadBalancerArn=load_balancer_arn)
            return response['Listeners']
        except ClientError as e:
            logger.error(f"Error getting listeners: {e}")
            return []
    
    def create_listener_rule(self, listener_arn: str, hostname: str, target_group_arn: str, priority: int) -> Optional[str]:
        """Create host-based listener rule"""
        if not self.client:
            return None
        
        try:
            response = self.client.create_rule(
                ListenerArn=listener_arn,
                Priority=priority,
                Conditions=[
                    {
                        'Field': 'host-header',
                        'Values': [hostname]
                    }
                ],
                Actions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': target_group_arn
                    }
                ]
            )
            return response['Rules'][0]['RuleArn']
        except ClientError as e:
            logger.error(f"Error creating listener rule: {e}")
            return None
    
    def delete_listener_rule(self, rule_arn: str) -> bool:
        """Delete listener rule"""
        if not self.client:
            return False
        
        try:
            self.client.delete_rule(RuleArn=rule_arn)
            return True
        except ClientError as e:
            logger.error(f"Error deleting listener rule: {e}")
            return False
    
    def get_rules(self, listener_arn: str) -> List[Dict]:
        """Get rules for listener"""
        if not self.client:
            return []
        
        try:
            response = self.client.describe_rules(ListenerArn=listener_arn)
            return response['Rules']
        except ClientError as e:
            logger.error(f"Error getting rules: {e}")
            return []

class Route53Adapter:
    """Route53 adapter"""
    
    def __init__(self, hosted_zone_id: str = None):
        self.hosted_zone_id = hosted_zone_id or os.environ.get('ROUTE53_HOSTED_ZONE_ID')
        try:
            self.client = boto3.client('route53')
        except NoCredentialsError:
            logger.warning("AWS credentials not found for Route53")
            self.client = None
    
    def create_txt_record(self, hostname: str, value: str) -> bool:
        """Create TXT record"""
        if not self.client or not self.hosted_zone_id:
            return False
        
        try:
            response = self.client.change_resource_record_sets(
                HostedZoneId=self.hosted_zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': hostname,
                                'Type': 'TXT',
                                'TTL': 300,
                                'ResourceRecords': [
                                    {'Value': f'"{value}"'}
                                ]
                            }
                        }
                    ]
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Error creating TXT record: {e}")
            return False
    
    def verify_txt_record(self, hostname: str, expected_value: str) -> bool:
        """Verify TXT record exists"""
        if not self.client or not self.hosted_zone_id:
            return False
        
        try:
            response = self.client.list_resource_record_sets(
                HostedZoneId=self.hosted_zone_id,
                StartRecordName=hostname,
                StartRecordType='TXT'
            )
            
            for record in response['ResourceRecordSets']:
                if record['Name'] == hostname and record['Type'] == 'TXT':
                    for rr in record['ResourceRecords']:
                        if expected_value in rr['Value']:
                            return True
            return False
        except ClientError as e:
            logger.error(f"Error verifying TXT record: {e}")
            return False
