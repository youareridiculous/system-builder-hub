"""
Growth automation and lifecycle management
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)

class GrowthAutomation:
    """Growth automation and lifecycle management"""
    
    def __init__(self):
        self.db = None
        self.automation_enabled = False  # Default conservative
    
    def get_db_session(self):
        """Get database session"""
        from flask import current_app
        import sqlite3
        db_path = current_app.config.get("DATABASE", "system_builder_hub.db")
        return sqlite3.connect(db_path)
    
    def check_trial_expiry(self, days_ahead: int = 2) -> List[Dict[str, Any]]:
        """Check for trials expiring soon"""
        try:
            db = self.get_db_session()
            
            # Get trials that will expire in the next N days
            expiry_date = date.today() + timedelta(days=days_ahead)
            
            query = """
                SELECT tenant_id, module, details, created_at
                FROM sbh_events 
                WHERE event_type = 'trial_started'
                AND created_at >= datetime('now', '-30 days')
            """
            
            trials = db.execute(query).fetchall()
            
            expiring_trials = []
            for trial in trials:
                tenant_id, module, details_str, created_at = trial
                
                try:
                    details = json.loads(details_str) if details_str else {}
                    trial_days = details.get("days", 14)
                    created_date = datetime.fromisoformat(created_at.split()[0]).date()
                    trial_expiry = created_date + timedelta(days=trial_days)
                    
                    if trial_expiry <= expiry_date:
                        expiring_trials.append({
                            "tenant_id": tenant_id,
                            "module": module,
                            "expires": trial_expiry.isoformat(),
                            "days_left": (trial_expiry - date.today()).days,
                            "created_at": created_at
                        })
                except Exception as e:
                    logger.warning(f"Failed to parse trial details: {e}")
            
            return expiring_trials
            
        except Exception as e:
            logger.error(f"Failed to check trial expiry: {e}")
            return []
    
    def suggest_upgrades(self, usage_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Suggest upgrades based on usage patterns"""
        try:
            db = self.get_db_session()
            
            # Get recent API usage by tenant/module
            query = """
                SELECT tenant_id, module, COUNT(*) as api_calls
                FROM sbh_events 
                WHERE event_type IN ('cobuilder_intent', 'cobuilder_action_completed')
                AND created_at >= datetime('now', '-7 days')
                GROUP BY tenant_id, module
                HAVING api_calls > 100
            """
            
            high_usage = db.execute(query).fetchall()
            
            upgrade_suggestions = []
            for usage in high_usage:
                tenant_id, module, api_calls = usage
                
                # Check current subscription
                sub_query = """
                    SELECT details FROM sbh_events 
                    WHERE event_type = 'subscribed' 
                    AND tenant_id = ? 
                    AND module = ?
                    ORDER BY created_at DESC LIMIT 1
                """
                
                current_sub = db.execute(sub_query, [tenant_id, module]).fetchone()
                
                if current_sub:
                    try:
                        details = json.loads(current_sub[0]) if current_sub[0] else {}
                        current_plan = details.get("plan", "starter")
                        
                        # Suggest upgrade if on starter plan with high usage
                        if current_plan == "starter" and api_calls > 500:
                            upgrade_suggestions.append({
                                "tenant_id": tenant_id,
                                "module": module,
                                "current_plan": current_plan,
                                "suggested_plan": "professional",
                                "reason": f"High API usage: {api_calls} calls in 7 days",
                                "api_calls": api_calls
                            })
                    except:
                        pass
            
            return upgrade_suggestions
            
        except Exception as e:
            logger.error(f"Failed to suggest upgrades: {e}")
            return []
    
    def trigger_trial_nudge(self, tenant_id: str, module: str) -> Dict[str, Any]:
        """Trigger a trial nudge for a specific tenant/module"""
        try:
            if not self.automation_enabled:
                return {
                    "action": "trial_nudge",
                    "status": "disabled",
                    "message": "Growth automation is disabled"
                }
            
            # Log the nudge event
            db = self.get_db_session()
            
            import uuid
            event_id = str(uuid.uuid4())
            
            db.execute("""
                INSERT INTO sbh_events (event_id, event_type, tenant_id, message, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                event_id, 
                "trial_nudge_sent", 
                tenant_id, 
                f"Trial nudge sent for {module}",
                json.dumps({
                    "module": module,
                    "nudge_type": "trial_expiry",
                    "sent_at": datetime.utcnow().isoformat()
                })
            ))
            
            db.commit()
            
            return {
                "action": "trial_nudge",
                "status": "sent",
                "tenant_id": tenant_id,
                "module": module,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger trial nudge: {e}")
            return {
                "action": "trial_nudge",
                "status": "error",
                "error": str(e)
            }
    
    def trigger_upgrade_suggestion(self, tenant_id: str, module: str, suggested_plan: str) -> Dict[str, Any]:
        """Trigger an upgrade suggestion for a specific tenant/module"""
        try:
            if not self.automation_enabled:
                return {
                    "action": "upgrade_suggestion",
                    "status": "disabled",
                    "message": "Growth automation is disabled"
                }
            
            # Log the upgrade suggestion
            db = self.get_db_session()
            
            import uuid
            event_id = str(uuid.uuid4())
            
            db.execute("""
                INSERT INTO sbh_events (event_id, event_type, tenant_id, message, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                event_id, 
                "upgrade_suggestion_sent", 
                tenant_id, 
                f"Upgrade suggestion sent for {module} to {suggested_plan}",
                json.dumps({
                    "module": module,
                    "suggested_plan": suggested_plan,
                    "sent_at": datetime.utcnow().isoformat()
                })
            ))
            
            db.commit()
            
            return {
                "action": "upgrade_suggestion",
                "status": "sent",
                "tenant_id": tenant_id,
                "module": module,
                "suggested_plan": suggested_plan,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger upgrade suggestion: {e}")
            return {
                "action": "upgrade_suggestion",
                "status": "error",
                "error": str(e)
            }
    
    def run_automation_cycle(self) -> Dict[str, Any]:
        """Run a complete automation cycle"""
        try:
            if not self.automation_enabled:
                return {
                    "status": "disabled",
                    "message": "Growth automation is disabled"
                }
            
            results = {
                "trial_nudges": [],
                "upgrade_suggestions": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Check for expiring trials
            expiring_trials = self.check_trial_expiry(days_ahead=2)
            for trial in expiring_trials:
                nudge_result = self.trigger_trial_nudge(trial["tenant_id"], trial["module"])
                results["trial_nudges"].append(nudge_result)
            
            # Check for upgrade opportunities
            upgrade_suggestions = self.suggest_upgrades()
            for suggestion in upgrade_suggestions:
                upgrade_result = self.trigger_upgrade_suggestion(
                    suggestion["tenant_id"], 
                    suggestion["module"], 
                    suggestion["suggested_plan"]
                )
                results["upgrade_suggestions"].append(upgrade_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Automation cycle failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
