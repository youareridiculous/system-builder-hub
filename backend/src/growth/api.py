"""
Growth Intelligence API endpoints for SBH
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import logging
import uuid
import json
import sqlite3
from contextlib import contextmanager
from src.events import log_event

logger = logging.getLogger(__name__)

# Create blueprint
growth_bp = Blueprint('growth', __name__, url_prefix='/api/growth')

@contextmanager
def db_conn():
    """Get database connection using current_app config"""
    db_path = current_app.config.get("DATABASE", "system_builder_hub.db")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()

# Event logging is now handled by centralized logger

def write_growth_metric(tenant_id: str, module: str, metric: str, value: float, metadata: Dict[str, Any] = None):
    """Write a growth metric to the database"""
    try:
        with db_conn() as db:
            # Ensure growth_metrics table exists
            db.execute("""
                CREATE TABLE IF NOT EXISTS growth_metrics (
                    id TEXT PRIMARY KEY,
                    date DATE NOT NULL,
                    tenant_id TEXT NOT NULL,
                    module TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            metric_id = str(uuid.uuid4())
            today = date.today()
            metadata_json = json.dumps(metadata) if metadata else None
            
            db.execute("""
                INSERT INTO growth_metrics (id, date, tenant_id, module, metric, value, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (metric_id, today, tenant_id, module, metric, value, metadata_json))
            
            db.commit()
        
    except Exception as e:
        logger.error(f"Failed to write growth metric: {e}")

@growth_bp.route('/metrics', methods=['GET'])
def get_growth_metrics():
    """Get growth metrics for a date range"""
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        tenant_id = request.args.get('tenant_id')
        module = request.args.get('module')
        
        if not from_date or not to_date:
            return jsonify({
                "success": False,
                "error": "from and to dates are required (YYYY-MM-DD format)"
            }), 400
        
        with db_conn() as db:
            query = """
                SELECT date, tenant_id, module, metric, value, metadata, created_at
                FROM growth_metrics 
                WHERE date BETWEEN ? AND ?
            """
            params = [from_date, to_date]
            
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            
            if module:
                query += " AND module = ?"
                params.append(module)
            
            query += " ORDER BY date DESC, created_at DESC"
            
            result = db.execute(query, params).fetchall()
            
            metrics = []
            for row in result:
                metrics.append({
                    "date": row[0],
                    "tenant_id": row[1],
                    "module": row[2],
                    "metric": row[3],
                    "value": row[4],
                    "metadata": json.loads(row[5]) if row[5] else None,
                    "created_at": row[6]
                })
            
            return jsonify({
                "success": True,
                "data": {
                    "metrics": metrics,
                    "count": len(metrics),
                    "from_date": from_date,
                    "to_date": to_date
                }
            })
        
    except Exception as e:
        logger.error(f"Failed to get growth metrics: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@growth_bp.route('/insights', methods=['GET'])
def get_growth_insights():
    """Get growth insights and analytics"""
    try:
        tenant_id = request.args.get('tenant_id')
        
        with db_conn() as db:
            # Get recent metrics (last 30 days)
            thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
            
            query = """
                SELECT metric, SUM(value) as total_value, COUNT(*) as count
                FROM growth_metrics 
                WHERE date >= ?
            """
            params = [thirty_days_ago]
            
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            
            query += " GROUP BY metric ORDER BY total_value DESC"
            
            result = db.execute(query, params).fetchall()
            
            # Calculate insights
            insights = {
                "period": "last_30_days",
                "metrics_summary": {},
                "conversion_rates": {},
                "churn_risk": [],
                "top_modules": [],
                "alerts": []
            }
            
            # Process metrics
            for row in result:
                metric, total_value, count = row
                insights["metrics_summary"][metric] = {
                    "total": total_value,
                    "count": count,
                    "average": total_value / count if count > 0 else 0
                }
            
            # Calculate conversion rates
            trials = insights["metrics_summary"].get("trial_started", {}).get("total", 0)
            subscriptions = insights["metrics_summary"].get("subscribed", {}).get("total", 0)
            
            if trials > 0:
                conversion_rate = (subscriptions / trials) * 100
                insights["conversion_rates"]["trial_to_paid"] = round(conversion_rate, 2)
            
            # Check for churn risk (trials expiring soon)
            expiring_trials_query = """
                SELECT tenant_id, module, metadata
                FROM sbh_events 
                WHERE event_type = 'trial_started' 
                AND created_at >= datetime('now', '-14 days')
            """
            
            if tenant_id:
                expiring_trials_query += " AND tenant_id = ?"
                expiring_trials_result = db.execute(expiring_trials_query, [tenant_id]).fetchall()
            else:
                expiring_trials_result = db.execute(expiring_trials_query).fetchall()
            
            for row in expiring_trials_result:
                tenant, module, metadata_str = row
                if metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                        trial_days = metadata.get("days", 14)
                        created_at = datetime.fromisoformat(metadata.get("created_at", ""))
                        expiry_date = created_at + timedelta(days=trial_days)
                        
                        if expiry_date.date() <= date.today() + timedelta(days=2):
                            insights["churn_risk"].append({
                                "tenant_id": tenant,
                                "module": module,
                                "expires": expiry_date.isoformat(),
                                "days_left": (expiry_date.date() - date.today()).days
                            })
                    except:
                        pass
            
            # Generate alerts
            if insights["churn_risk"]:
                insights["alerts"].append({
                    "type": "trial_expiring",
                    "message": f"Trials expiring soon for {len(insights['churn_risk'])} tenants",
                    "severity": "warning"
                })
            
            return jsonify({
                "success": True,
                "data": insights
            })
        
    except Exception as e:
        logger.error(f"Failed to get growth insights: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@growth_bp.route('/rollup', methods=['POST'])
def trigger_daily_rollup():
    """Trigger daily metrics rollup (manual for now)"""
    try:
        from src.growth.rollup import DailyRollupService
        
        rollup_service = DailyRollupService()
        result = rollup_service.run_daily_rollup()
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Daily rollup failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
