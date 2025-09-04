# Custom Domains Guide

This document explains how to set up and manage custom domains for your SBH tenants, including both shared subdomains and fully custom domains with automatic SSL certificates.

## Overview

SBH supports two types of custom domains:

1. **Shared Subdomains**: `tenant.myapp.com` (subdomain on our shared domain)
2. **Custom Domains**: `app.tenant.com` or `tenant.com` (your own domain)

Both types get automatic HTTPS via AWS Certificate Manager (ACM) and are routed through our Application Load Balancer.

## Domain Lifecycle

### 1. Domain Creation
- Tenant adds domain via UI or API
- System generates verification token
- Domain status: `pending`

### 2. Domain Verification
- Tenant adds TXT record to DNS
- System verifies ownership
- Requests ACM certificate
- Domain status: `verifying`

### 3. Domain Activation
- ACM certificate is issued
- System creates ALB host-based rule
- Domain becomes live
- Domain status: `active`

## Setup Instructions

### Shared Subdomains (tenant.myapp.com)

#### 1. Add Domain
```bash
# Via API
curl -X POST https://myapp.com/api/domains \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: acme" \
  -d '{"hostname": "acme.myapp.com"}'

# Via UI
# Navigate to /ui/domains and click "Add Domain"
```

#### 2. Verify Domain
The system will provide a TXT record to add to your DNS:

```
TXT acme.myapp.com "sbh-verify=abc123-def456-ghi789"
```

#### 3. Complete Setup
- Add the TXT record to your DNS
- Click "Verify" in the UI
- Wait for ACM certificate validation
- Click "Activate" to make the domain live

### Custom Domains (app.tenant.com)

#### 1. Add Domain
```bash
curl -X POST https://myapp.com/api/domains \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: acme" \
  -d '{"hostname": "app.acme.com"}'
```

#### 2. DNS Configuration
You'll need to configure two sets of DNS records:

**Step 1: Domain Verification**
```
TXT app.acme.com "sbh-verify=abc123-def456-ghi789"
```

**Step 2: SSL Certificate Validation**
After verification, you'll get CNAME records like:
```
CNAME _acme-challenge.app.acme.com abc123.acm-validations.aws.com
```

#### 3. Point Domain to SBH
```
CNAME app.acme.com your-app.elasticbeanstalk.com
```

## DNS Provider Instructions

### Route53 (AWS)

#### 1. Create Hosted Zone
```bash
aws route53 create-hosted-zone \
  --name acme.com \
  --caller-reference $(date +%s)
```

#### 2. Update Nameservers
Update your domain registrar to use the Route53 nameservers.

#### 3. Add Records
```bash
# Verification record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "app.acme.com",
        "Type": "TXT",
        "TTL": 300,
        "ResourceRecords": [{"Value": "\"sbh-verify=abc123-def456-ghi789\""}]
      }
    }]
  }'

# Point to SBH
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "app.acme.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "your-app.elasticbeanstalk.com"}]
      }
    }]
  }'
```

### Cloudflare

#### 1. Add Domain
- Add your domain to Cloudflare
- Update nameservers at your registrar

#### 2. Add Records
- **TXT Record**: `app.acme.com` → `sbh-verify=abc123-def456-ghi789`
- **CNAME Record**: `app.acme.com` → `your-app.elasticbeanstalk.com`
- **CNAME Record**: `_acme-challenge.app.acme.com` → `abc123.acm-validations.aws.com`

#### 3. SSL/TLS Settings
- Set SSL/TLS encryption mode to "Full"
- Enable "Always Use HTTPS"

### GoDaddy

#### 1. Access DNS Management
- Log into GoDaddy
- Go to Domain Management
- Click "DNS" for your domain

#### 2. Add Records
- **TXT Record**: `app.acme.com` → `sbh-verify=abc123-def456-ghi789`
- **CNAME Record**: `app.acme.com` → `your-app.elasticbeanstalk.com`
- **CNAME Record**: `_acme-challenge.app.acme.com` → `abc123.acm-validations.aws.com`

## API Reference

### Create Domain
```http
POST /api/domains
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "hostname": "app.acme.com"
}
```

**Response:**
```json
{
  "success": true,
  "domain": {
    "id": "domain-123",
    "hostname": "app.acme.com",
    "status": "pending",
    "verification_token": "abc123-def456-ghi789",
    "required_dns": [
      {
        "type": "TXT",
        "name": "app.acme.com",
        "value": "sbh-verify=abc123-def456-ghi789"
      }
    ]
  }
}
```

### Verify Domain
```http
POST /api/domains/app.acme.com/verify
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

**Response:**
```json
{
  "success": true,
  "domain": {
    "hostname": "app.acme.com",
    "status": "verifying",
    "acm_arn": "arn:aws:acm:us-east-1:123456789012:certificate/abc123",
    "validation_records": [
      {
        "name": "_acme-challenge.app.acme.com",
        "value": "abc123.acm-validations.aws.com",
        "type": "CNAME"
      }
    ]
  }
}
```

### Activate Domain
```http
POST /api/domains/app.acme.com/activate
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

### List Domains
```http
GET /api/domains
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

### Delete Domain
```http
DELETE /api/domains/app.acme.com
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

## Environment Configuration

### Required Environment Variables
```bash
# Custom domains feature flag
FEATURE_CUSTOM_DOMAINS=true

# Shared domain
SHARED_DOMAIN=myapp.com

# AWS configuration
AWS_REGION=us-east-1
ROUTE53_HOSTED_ZONE_ID=Z1234567890

# ALB configuration (auto-detected in EB)
ALB_LISTENER_HTTPS_ARN=arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/sbh-prod/abc123/def456

# Development settings
FEATURE_DEV_AUTO_VERIFY_DOMAINS=false
ACM_CERT_VALIDATION_TIMEOUT=900
```

### IAM Permissions
Your EC2 instance profile needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "acm:RequestCertificate",
        "acm:DescribeCertificate",
        "acm:DeleteCertificate",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeRules",
        "elasticloadbalancing:CreateRule",
        "elasticloadbalancing:DeleteRule",
        "route53:ChangeResourceRecordSets",
        "route53:ListResourceRecordSets"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### 1. Domain Verification Fails
**Symptoms**: TXT record verification fails
**Solutions**:
- Check DNS propagation (can take up to 48 hours)
- Verify TXT record format: `"sbh-verify=token"`
- Use `dig TXT app.acme.com` to check DNS

#### 2. SSL Certificate Not Issued
**Symptoms**: Certificate stuck in "verifying" status
**Solutions**:
- Check ACM validation CNAME records
- Verify DNS propagation
- Check ACM console for validation errors

#### 3. Domain Not Routing
**Symptoms**: Domain resolves but shows 404
**Solutions**:
- Check ALB listener rules
- Verify target group configuration
- Check tenant resolution

#### 4. Mixed Content Errors
**Symptoms**: HTTPS warnings in browser
**Solutions**:
- Ensure all resources use HTTPS
- Check for hardcoded HTTP URLs
- Verify SSL certificate is valid

### Debug Commands

#### Check DNS Records
```bash
# Check TXT record
dig TXT app.acme.com

# Check CNAME record
dig CNAME app.acme.com

# Check ACM validation
dig CNAME _acme-challenge.app.acme.com
```

#### Check SSL Certificate
```bash
# Check certificate status
openssl s_client -connect app.acme.com:443 -servername app.acme.com

# Check certificate chain
openssl x509 -in cert.pem -text -noout
```

#### Check ALB Configuration
```bash
# List load balancers
aws elbv2 describe-load-balancers

# List listeners
aws elbv2 describe-listeners --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/sbh-prod/abc123

# List rules
aws elbv2 describe-rules --listener-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/sbh-prod/abc123/def456
```

## Rollback and Teardown

### Delete Domain
```bash
# Via API
curl -X DELETE https://myapp.com/api/domains/app.acme.com \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: acme"

# Via UI
# Navigate to /ui/domains and click "Delete" for the domain
```

### Manual Cleanup
If automatic cleanup fails:

```bash
# Delete ALB rule
aws elbv2 delete-rule --rule-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:rule/app/sbh-prod/abc123/def456

# Delete ACM certificate
aws acm delete-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123

# Remove DNS records
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [{
      "Action": "DELETE",
      "ResourceRecordSet": {
        "Name": "app.acme.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "your-app.elasticbeanstalk.com"}]
      }
    }]
  }'
```

## Support Notes

### Propagation Times
- **DNS Changes**: 5 minutes to 48 hours
- **SSL Certificate Validation**: 5-30 minutes
- **ALB Rule Creation**: 1-5 minutes

### Rate Limits
- **ACM Certificates**: 10 per day per account
- **ALB Rules**: 100 per load balancer
- **Route53 Changes**: 5 per second per hosted zone

### Best Practices
1. **Use CNAME for subdomains**: `app.acme.com` → `your-app.elasticbeanstalk.com`
2. **Use A record for apex domains**: `acme.com` → ALB IP (requires ALIAS in Route53)
3. **Enable HTTPS redirect**: Configure ALB to redirect HTTP to HTTPS
4. **Monitor certificate expiration**: ACM certificates auto-renew
5. **Test in staging first**: Use staging environment for domain testing

### Monitoring
- Monitor domain status via `/api/domains`
- Check ALB metrics for domain traffic
- Monitor ACM certificate expiration
- Set up CloudWatch alarms for domain failures
