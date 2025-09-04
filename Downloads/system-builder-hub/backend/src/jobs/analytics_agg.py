"""
Analytics aggregation background jobs
"""
import logging
import time
from datetime import date, datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.db_core import get_session
from src.analytics.models import AnalyticsEvent, AnalyticsDailyUsage
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)
analytics_service = AnalyticsService()

def rollup_daily_usage_job(rollup_date_str: str) -> Dict[str, Any]:
    """Rollup daily usage from Redis to database"""
    start_time = time.time()
    
    try:
        rollup_date = date.fromisoformat(rollup_date_str)
        
        logger.info(f"Starting daily usage rollup for {rollup_date}")
        
        # Get all tenants
        session = get_session()
        tenant_ids = session.query(AnalyticsEvent.tenant_id).distinct().all()
        tenant_ids = [str(tid[0]) for tid in tenant_ids]
        
        total_metrics = 0
        
        for tenant_id in tenant_ids:
            # Get Redis counters for this tenant and date
            redis_metrics = _get_redis_metrics_for_date(tenant_id, rollup_date)
            
            for metric, count in redis_metrics.items():
                # Upsert into analytics_daily_usage
                usage = session.query(AnalyticsDailyUsage).filter(
                    AnalyticsDailyUsage.tenant_id == tenant_id,
                    AnalyticsDailyUsage.date == rollup_date,
                    AnalyticsDailyUsage.metric == metric
                ).first()
                
                if usage:
                    usage.count = count
                else:
                    usage = AnalyticsDailyUsage(
                        tenant_id=tenant_id,
                        date=rollup_date,
                        metric=metric,
                        count=count
                    )
                    session.add(usage)
                
                total_metrics += 1
        
        session.commit()
        
        # Emit Prometheus metrics
        duration = time.time() - start_time
        _emit_rollup_metrics(duration, total_metrics)
        
        logger.info(f"Completed daily usage rollup for {rollup_date}: {total_metrics} metrics")
        
        return {
            'success': True,
            'date': rollup_date_str,
            'total_metrics': total_metrics,
            'duration': duration
        }
        
    except Exception as e:
        logger.error(f"Error in daily usage rollup for {rollup_date_str}: {e}")
        return {
            'success': False,
            'error': str(e),
            'date': rollup_date_str
        }

def _get_redis_metrics_for_date(tenant_id: str, rollup_date: date) -> Dict[str, int]:
    """Get all Redis metrics for a tenant and date"""
    metrics = {}
    
    try:
        from src.redis_core import redis_available, get_redis
        
        if not redis_available():
            return metrics
        
        redis_client = get_redis()
        date_str = rollup_date.strftime('%Y%m%d')
        pattern = f"analytics:{tenant_id}:*:{date_str}"
        
        # Scan for keys matching pattern
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            
            for key in keys:
                # Extract metric from key
                parts = key.decode('utf-8').split(':')
                if len(parts) >= 4:
                    metric = parts[2]
                    count = redis_client.get(key)
                    if count:
                        metrics[metric] = int(count)
            
            if cursor == 0:
                break
        
        return metrics
        
    except ImportError:
        return metrics
    except Exception as e:
        logger.warning(f"Error getting Redis metrics for tenant {tenant_id}: {e}")
        return metrics

def _emit_rollup_metrics(duration: float, total_metrics: int) -> None:
    """Emit Prometheus metrics for rollup job"""
    try:
        from src.obs.metrics import get_rollup_runs_counter, get_rollup_duration_histogram
        
        # Increment counter
        counter = get_rollup_runs_counter()
        counter.inc()
        
        # Record duration
        histogram = get_rollup_duration_histogram()
        histogram.observe(duration)
        
    except ImportError:
        pass  # Prometheus not available
    except Exception as e:
        logger.warning(f"Error emitting rollup metrics: {e}")

# RQ job wrapper
def rollup_daily_usage_job_wrapper(rollup_date_str: str):
    """Wrapper for RQ job"""
    return rollup_daily_usage_job(rollup_date_str)
