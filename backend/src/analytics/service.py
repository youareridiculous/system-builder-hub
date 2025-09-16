"""
Analytics service
"""
import os
import json
import logging
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from src.db_core import get_session
from src.analytics.models import AnalyticsEvent, AnalyticsDailyUsage
from src.constants import normalize_tenant_id

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Analytics service for event tracking and usage aggregation"""
    
    def __init__(self):
        self.enabled = os.environ.get('ANALYTICS_ENABLED', 'true').lower() == 'true'
        self.max_export_rows = int(os.environ.get('ANALYTICS_MAX_EXPORT_ROWS', '50000'))
        self.quotas_enabled = os.environ.get('QUOTAS_ENABLED', 'true').lower() == 'true'
        
        # Default quotas
        default_quotas = {
            'api_requests_daily': 100000,
            'builds_daily': 200,
            'emails_daily': 5000,
            'webhooks_daily': 50000,
            'storage_gb': 50
        }
        self.default_quotas = default_quotas
    
    def track(self, tenant_id: str, event: str, user_id: Optional[str] = None, 
              source: str = 'app', props: Optional[Dict] = None, 
              ip: Optional[str] = None, request_id: Optional[str] = None) -> None:
        """Track an analytics event"""
        if not self.enabled:
            return
        
        try:
            session = get_session()
            
            # Normalize tenant_id first
            normalized_tenant_id = normalize_tenant_id(tenant_id)
            
            # Safely convert normalized tenant_id to UUID if it's a string
            safe_tenant_id = normalized_tenant_id
            if isinstance(normalized_tenant_id, str):
                try:
                    safe_tenant_id = uuid.UUID(normalized_tenant_id)
                except ValueError:
                    # This should rarely happen with normalized tenant IDs
                    logger.warning(f"Failed to convert normalized tenant_id to UUID: {normalized_tenant_id}, using system tenant")
                    safe_tenant_id = uuid.UUID('00000000-0000-0000-0000-000000000000')  # System tenant
            
            # Create event record
            analytics_event = AnalyticsEvent(
                tenant_id=safe_tenant_id,
                user_id=user_id,
                source=source,
                event=event,
                props=props or {},
                ip=ip,
                request_id=request_id
            )
            
            session.add(analytics_event)
            session.commit()
            
            # Increment Redis counter
            self._increment_redis_counter(tenant_id, event, 1)
            
            # Emit Prometheus metric
            self._emit_prometheus_event(tenant_id, event, source)
            
            logger.debug(f"Tracked event: {event} for tenant {tenant_id}")
            
        except Exception as e:
            logger.warning(f"Analytics failure ignored: {e}")
            # Never break the request path
    
    def increment_usage(self, tenant_id: str, metric: str, n: int = 1, 
                       usage_date: Optional[date] = None) -> None:
        """Increment usage counter"""
        if not self.enabled:
            return
        
        try:
            if usage_date is None:
                usage_date = date.today()
            
            # Increment Redis counter
            self._increment_redis_counter(tenant_id, metric, n, usage_date)
            
            # Emit Prometheus metric
            self._emit_prometheus_usage(tenant_id, metric, n)
            
            logger.debug(f"Incremented usage: {metric} by {n} for tenant {tenant_id}")
            
        except Exception as e:
            logger.error(f"Error incrementing usage {metric} for tenant {tenant_id}: {e}")
    
    def get_events(self, tenant_id: str, from_date: Optional[datetime] = None,
                   to_date: Optional[datetime] = None, event: Optional[str] = None,
                   source: Optional[str] = None, limit: int = 100, 
                   cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get analytics events with pagination"""
        try:
            session = get_session()
            
            query = session.query(AnalyticsEvent).filter(AnalyticsEvent.tenant_id == tenant_id)
            
            # Apply filters
            if from_date:
                query = query.filter(AnalyticsEvent.ts >= from_date)
            if to_date:
                query = query.filter(AnalyticsEvent.ts <= to_date)
            if event:
                query = query.filter(AnalyticsEvent.event == event)
            if source:
                query = query.filter(AnalyticsEvent.source == source)
            
            # Apply cursor pagination
            if cursor:
                try:
                    cursor_ts = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
                    query = query.filter(AnalyticsEvent.ts < cursor_ts)
                except ValueError:
                    pass  # Invalid cursor, ignore
            
            # Order by timestamp descending
            query = query.order_by(desc(AnalyticsEvent.ts))
            
            # Apply limit
            events = query.limit(limit + 1).all()  # Get one extra to check if more exist
            
            has_more = len(events) > limit
            if has_more:
                events = events[:-1]  # Remove the extra item
            
            # Format results
            result = []
            for event_obj in events:
                result.append({
                    'id': str(event_obj.id),
                    'user_id': event_obj.user_id,
                    'source': event_obj.source,
                    'event': event_obj.event,
                    'ts': event_obj.ts.isoformat(),
                    'props': event_obj.props or {},
                    'ip': event_obj.ip,
                    'request_id': event_obj.request_id
                })
            
            # Get next cursor
            next_cursor = None
            if has_more and events:
                next_cursor = events[-1].ts.isoformat()
            
            return {
                'events': result,
                'has_more': has_more,
                'next_cursor': next_cursor
            }
            
        except Exception as e:
            logger.error(f"Error getting events for tenant {tenant_id}: {e}")
            return {'events': [], 'has_more': False, 'next_cursor': None}
    
    def get_usage(self, tenant_id: str, from_date: Optional[date] = None,
                  to_date: Optional[date] = None, metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get usage data for metrics"""
        try:
            session = get_session()
            
            if from_date is None:
                from_date = date.today() - timedelta(days=30)
            if to_date is None:
                to_date = date.today()
            
            query = session.query(AnalyticsDailyUsage).filter(
                AnalyticsDailyUsage.tenant_id == tenant_id,
                AnalyticsDailyUsage.date >= from_date,
                AnalyticsDailyUsage.date <= to_date
            )
            
            if metrics:
                query = query.filter(AnalyticsDailyUsage.metric.in_(metrics))
            
            usage_data = query.order_by(AnalyticsDailyUsage.date).all()
            
            # Group by metric
            result = {}
            for usage in usage_data:
                if usage.metric not in result:
                    result[usage.metric] = []
                
                result[usage.metric].append({
                    'date': usage.date.isoformat(),
                    'count': usage.count,
                    'meta': usage.meta or {}
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting usage for tenant {tenant_id}: {e}")
            return {}
    
    def get_metrics(self, tenant_id: str) -> Dict[str, Dict[str, int]]:
        """Get quick metrics for KPIs"""
        try:
            today = date.today()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Common KPI metrics
            kpi_metrics = [
                'auth.user.registered', 'auth.user.login', 'builder.generate.completed',
                'apikey.request', 'files.uploaded', 'webhook.delivered', 
                'email.sent', 'payments.subscription.active'
            ]
            
            result = {}
            
            for metric in kpi_metrics:
                result[metric] = {
                    'today': self._get_metric_count(tenant_id, metric, today),
                    'week': self._get_metric_count(tenant_id, metric, week_ago, today),
                    'month': self._get_metric_count(tenant_id, metric, month_ago, today)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting metrics for tenant {tenant_id}: {e}")
            return {}
    
    def check_quota(self, tenant_id: str, metric: str, usage_date: Optional[date] = None) -> Dict[str, Any]:
        """Check if tenant has exceeded quota for a metric"""
        if not self.quotas_enabled:
            return {'exceeded': False, 'current': 0, 'limit': 0}
        
        try:
            if usage_date is None:
                usage_date = date.today()
            
            # Get current usage from Redis
            current_usage = self._get_redis_counter(tenant_id, metric, usage_date)
            
            # Get quota limit (from tenant config or defaults)
            limit = self._get_tenant_quota(tenant_id, metric)
            
            exceeded = current_usage > limit
            
            if exceeded:
                # Emit Prometheus metric
                self._emit_prometheus_quota_exceeded(tenant_id, metric)
                logger.warning(f"Quota exceeded for tenant {tenant_id}, metric {metric}: {current_usage}/{limit}")
            
            return {
                'exceeded': exceeded,
                'current': current_usage,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"Error checking quota for tenant {tenant_id}, metric {metric}: {e}")
            return {'exceeded': False, 'current': 0, 'limit': 0}
    
    def export_csv(self, tenant_id: str, from_date: Optional[datetime] = None,
                   to_date: Optional[datetime] = None, event: Optional[str] = None,
                   source: Optional[str] = None) -> str:
        """Export events to CSV"""
        try:
            # Get events (with higher limit for export)
            events_data = self.get_events(
                tenant_id=tenant_id,
                from_date=from_date,
                to_date=to_date,
                event=event,
                source=source,
                limit=self.max_export_rows
            )
            
            # Generate CSV
            csv_lines = ['timestamp,event,source,user_id,ip,request_id,properties']
            
            for event_obj in events_data['events']:
                props_str = json.dumps(event_obj['props']).replace('"', '""')
                csv_lines.append(
                    f'"{event_obj["ts"]}","{event_obj["event"]}","{event_obj["source"]}",'
                    f'"{event_obj["user_id"] or ""}","{event_obj["ip"] or ""}",'
                    f'"{event_obj["request_id"] or ""}","{props_str}"'
                )
            
            return '\n'.join(csv_lines)
            
        except Exception as e:
            logger.error(f"Error exporting CSV for tenant {tenant_id}: {e}")
            return 'timestamp,event,source,user_id,ip,request_id,properties\n'
    
    def _increment_redis_counter(self, tenant_id: str, metric: str, n: int = 1, 
                                usage_date: Optional[date] = None) -> None:
        """Increment Redis counter"""
        try:
            from src.redis_core import redis_available, get_redis
            
            if not redis_available():
                return
            
            if usage_date is None:
                usage_date = date.today()
            
            redis_client = get_redis()
            key = f"analytics:{tenant_id}:{metric}:{usage_date.strftime('%Y%m%d')}"
            redis_client.incr(key, n)
            
        except ImportError:
            pass  # Redis not available
        except Exception as e:
            logger.warning(f"Error incrementing Redis counter: {e}")
    
    def _get_redis_counter(self, tenant_id: str, metric: str, usage_date: date) -> int:
        """Get Redis counter value"""
        try:
            from src.redis_core import redis_available, get_redis
            
            if not redis_available():
                return 0
            
            redis_client = get_redis()
            key = f"analytics:{tenant_id}:{metric}:{usage_date.strftime('%Y%m%d')}"
            value = redis_client.get(key)
            
            return int(value) if value else 0
            
        except ImportError:
            return 0
        except Exception as e:
            logger.warning(f"Error getting Redis counter: {e}")
            return 0
    
    def _get_metric_count(self, tenant_id: str, metric: str, from_date: date, 
                          to_date: Optional[date] = None) -> int:
        """Get metric count from database"""
        try:
            session = get_session()
            
            query = session.query(func.count(AnalyticsEvent.id)).filter(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.event == metric,
                AnalyticsEvent.ts >= from_date
            )
            
            if to_date:
                query = query.filter(AnalyticsEvent.ts <= to_date)
            
            return query.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting metric count: {e}")
            return 0
    
    def _get_tenant_quota(self, tenant_id: str, metric: str) -> int:
        """Get tenant quota for metric"""
        # For now, use defaults. In the future, this could check tenant-specific quotas
        return self.default_quotas.get(metric, 1000)
    
    def _emit_prometheus_event(self, tenant_id: str, event: str, source: str) -> None:
        """Emit Prometheus event metric"""
        try:
            from src.obs.metrics import get_analytics_events_counter
            counter = get_analytics_events_counter()
            counter.labels(tenant=tenant_id, event=event, source=source).inc()
        except ImportError:
            pass  # Prometheus not available
        except Exception as e:
            logger.warning(f"Error emitting Prometheus event metric: {e}")
    
    def _emit_prometheus_usage(self, tenant_id: str, metric: str, n: int) -> None:
        """Emit Prometheus usage metric"""
        try:
            from src.obs.metrics import get_usage_count_counter
            counter = get_usage_count_counter()
            counter.labels(tenant=tenant_id, metric=metric).inc(n)
        except ImportError:
            pass  # Prometheus not available
        except Exception as e:
            logger.warning(f"Error emitting Prometheus usage metric: {e}")
    
    def _emit_prometheus_quota_exceeded(self, tenant_id: str, metric: str) -> None:
        """Emit Prometheus quota exceeded metric"""
        try:
            from src.obs.metrics import get_quota_exceeded_counter
            counter = get_quota_exceeded_counter()
            counter.labels(tenant=tenant_id, metric=metric).inc()
        except ImportError:
            pass  # Prometheus not available
        except Exception as e:
            logger.warning(f"Error emitting Prometheus quota exceeded metric: {e}")
