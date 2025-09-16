# Observability Guide

This document describes the observability features in SBH and how to configure them for production deployment.

## Overview

SBH includes comprehensive observability features:

- **Structured Logging**: JSON logs with request IDs and context
- **Prometheus Metrics**: Application and business metrics
- **Error Reporting**: Sentry integration for error tracking
- **Distributed Tracing**: OpenTelemetry integration
- **Audit Logging**: Database-backed audit trail
- **Health Monitoring**: Enhanced health checks

## Structured Logging

### Configuration

```bash
# Environment variables
LOG_LEVEL=INFO                # DEBUG|INFO|WARNING|ERROR
LOG_JSON=true                 # JSON logs to stdout
REQUEST_ID_HEADER=X-Request-Id
```

### Features

- **Request Tracking**: Each request gets a unique ID
- **Context Enrichment**: User ID, IP, method, path, status, duration
- **JSON Format**: Structured logs for easy parsing
- **CloudWatch Integration**: Automatic log collection on EB

### Log Format

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "info",
  "event": "Request completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/auth/login",
  "status": 200,
  "duration_ms": 45.2,
  "user_id": 123
}
```

### CloudWatch Logs

Elastic Beanstalk automatically collects stdout/stderr to CloudWatch Logs:

1. **Log Group**: `/aws/elasticbeanstalk/your-app-name/var/log/eb-docker/containers/eb-current-app/`
2. **Log Stream**: Container-specific streams
3. **Retention**: Configurable (default: 7 days)

**Viewing Logs:**
```bash
# AWS CLI
aws logs tail /aws/elasticbeanstalk/your-app-name/var/log/eb-docker/containers/eb-current-app/ --follow

# CloudWatch Console
# Navigate to Logs > Log groups > your-app-name
```

## Prometheus Metrics

### Configuration

```bash
PROMETHEUS_METRICS_ENABLED=true
```

### Available Metrics

#### HTTP Metrics
- `http_requests_total{method,endpoint,status}` - Request count
- `http_request_duration_seconds_bucket{endpoint}` - Request duration

#### Business Metrics
- `builder_generate_total{mode}` - Build generations (sync/async)
- `rate_limit_hits_total{endpoint}` - Rate limit hits
- `jobs_enqueued_total{queue,type}` - Background jobs
- `audit_events_total{type,action}` - Audit events

#### System Metrics
- `active_users` - Number of active users
- `builds_in_progress` - Builds in progress

### Scraping Options

#### Option 1: EB Sidecar Container
```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    image: sbh:latest
    ports:
      - "5001:5001"
  
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
```

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sbh'
    static_configs:
      - targets: ['app:5001']
    metrics_path: '/metrics'
```

#### Option 2: CloudWatch Agent + Prometheus
```bash
# Install CloudWatch Agent
sudo yum install -y amazon-cloudwatch-agent

# Configure agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

#### Option 3: External Prometheus Server
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'sbh'
    static_configs:
      - targets: ['your-eb-domain.com:5001']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Sentry Error Reporting

### Configuration

```bash
SENTRY_DSN=https://your-key@your-org.ingest.sentry.io/project-id
SENTRY_ENVIRONMENT=production
```

### Setup Steps

1. **Create Sentry Project**:
   - Go to [sentry.io](https://sentry.io)
   - Create new project
   - Select Flask framework
   - Copy DSN

2. **Configure Environment**:
   ```bash
   # EB Environment Variables
   SENTRY_DSN=https://your-key@your-org.ingest.sentry.io/project-id
   SENTRY_ENVIRONMENT=production
   ```

3. **Features**:
   - Automatic error capture
   - Request context
   - User context
   - Performance monitoring
   - Release tracking

### Error Context

Sentry automatically captures:
- Request details (method, path, headers)
- User information (if authenticated)
- Stack traces
- Environment information

## OpenTelemetry Tracing

### Configuration

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=sbh
```

### Setup Options

#### Option 1: Local Development
```yaml
# docker-compose.yml
services:
  otel-collector:
    image: otel/opentelemetry-collector:latest
    ports:
      - "4317:4317"
      - "4318:4318"
    volumes:
      - ./otel-config.yml:/etc/otel-collector-config.yaml
    command: ["--config", "/etc/otel-collector-config.yaml"]
```

```yaml
# otel-config.yml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:

exporters:
  logging:
    loglevel: debug

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging]
```

#### Option 2: AWS X-Ray
```yaml
# otel-config.yml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:

exporters:
  otlp:
    endpoint: "https://traces.{region}.amazonaws.com:443"
    headers:
      "x-amzn-xray-segment-name": "sbh"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp]
```

### Instrumented Operations

- HTTP requests
- Database operations
- File uploads/downloads
- Background jobs
- External API calls

## Audit Logging

### Database Schema

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    ip VARCHAR(45),
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(100),
    metadata JSONB
);
```

### Audited Events

#### Authentication
- User registration
- User login/logout
- Role changes

#### Payments
- Checkout creation
- Webhook processing
- Subscription changes

#### File Operations
- File uploads
- File deletions
- File downloads

#### Builder Operations
- Project saves
- Build generation
- Template usage

#### Agent Operations
- Plan generation
- Build execution
- Preview generation

### API Endpoint

```bash
# Get recent audit events (admin only)
GET /api/audit/recent?limit=100
```

Response:
```json
{
  "success": true,
  "events": [
    {
      "id": 1,
      "ts": "2024-01-15T10:30:00.123Z",
      "user_id": 123,
      "ip": "192.168.1.1",
      "action": "login",
      "target_type": "user",
      "target_id": "123",
      "metadata": {
        "email": "user@example.com",
        "user_agent": "Mozilla/5.0..."
      }
    }
  ],
  "count": 1
}
```

## Health Monitoring

### Enhanced Health Check

The `/readiness` endpoint now includes observability status:

```json
{
  "db": true,
  "migrations_applied": true,
  "db_driver": "postgresql",
  "db_url_kind": "postgresql",
  "redis": {
    "configured": true,
    "ok": true,
    "details": "ok:elasticache"
  },
  "observability": {
    "log_json": true,
    "sentry": {
      "configured": true,
      "ok": true
    },
    "otel": {
      "configured": false,
      "ok": false
    },
    "metrics": {
      "configured": true,
      "ok": true
    }
  },
  "llm": {
    "configured": true,
    "available": true
  },
  "production": {
    "is_production": true,
    "issues": []
  }
}
```

## CloudWatch Alerts

### Metric Filters

Create CloudWatch Metric Filters to monitor logs:

#### Error Rate Alert
```bash
# Filter pattern
{ $.level = "error" }

# Metric transformation
Name: ErrorCount
Value: 1
Default Value: 0
```

#### Readiness Alert
```bash
# Filter pattern
{ $.event = "readiness_alert" }

# Metric transformation
Name: ReadinessAlertCount
Value: 1
Default Value: 0
```

#### High Response Time Alert
```bash
# Filter pattern
{ $.duration_ms > 5000 }

# Metric transformation
Name: SlowRequestCount
Value: 1
Default Value: 0
```

### CloudWatch Alarms

```bash
# Create alarm for high error rate
aws cloudwatch put-metric-alarm \
  --alarm-name "SBH-HighErrorRate" \
  --alarm-description "High error rate in SBH application" \
  --metric-name "ErrorCount" \
  --namespace "SBH/Logs" \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:region:account:topic-name
```

### SNS Notifications

```bash
# Create SNS topic
aws sns create-topic --name "sbh-alerts"

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:region:account:sbh-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Best Practices

### Logging
- Use structured logging for all application events
- Include request ID in all log entries
- Redact sensitive information (passwords, tokens)
- Set appropriate log levels

### Metrics
- Monitor business-critical metrics
- Set up alerts for error rates and performance
- Use histograms for latency measurements
- Track user activity and engagement

### Error Reporting
- Configure Sentry for all environments
- Set up release tracking
- Monitor error trends
- Configure appropriate sampling rates

### Tracing
- Use tracing for performance analysis
- Instrument external service calls
- Monitor database query performance
- Track background job execution

### Audit Logging
- Log all security-relevant events
- Include user context when available
- Store audit logs securely
- Implement log retention policies

## Troubleshooting

### Common Issues

#### Metrics Not Available
- Check `PROMETHEUS_METRICS_ENABLED` environment variable
- Verify `/metrics` endpoint is accessible
- Check firewall rules for Prometheus scraping

#### Sentry Not Working
- Verify `SENTRY_DSN` is correct
- Check network connectivity to Sentry
- Verify environment configuration

#### Tracing Not Working
- Check `OTEL_EXPORTER_OTLP_ENDPOINT` configuration
- Verify collector is running and accessible
- Check OpenTelemetry SDK version compatibility

#### Audit Log Not Working
- Check database connectivity
- Verify audit table exists
- Check permissions for audit table operations

### Debug Commands

```bash
# Check metrics endpoint
curl http://localhost:5001/metrics

# Check health endpoint
curl http://localhost:5001/readiness

# Check audit endpoint
curl http://localhost:5001/api/audit/recent

# View CloudWatch logs
aws logs tail /aws/elasticbeanstalk/your-app-name/var/log/eb-docker/containers/eb-current-app/ --follow
```
