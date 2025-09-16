"""
Transform for task.overdue webhook
Formats task overdue alerts for ops team
"""
from typing import Dict, Any
from datetime import datetime, timedelta

def transform(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform task.overdue event data for ops team
    
    Args:
        event_data: Original event data from SBH CRM
        
    Returns:
        Transformed data for ops alert
    """
    task = event_data.get('task', {})
    
    # Calculate overdue duration
    due_date = task.get('due_date')
    overdue_days = 0
    if due_date:
        try:
            due_date_obj = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            overdue_days = (datetime.utcnow() - due_date_obj).days
        except:
            overdue_days = 1
    
    # Transform to ops alert format
    transformed = {
        "alert_type": "task_overdue",
        "alert_id": f"task_overdue_{task.get('id')}",
        "severity": "high" if overdue_days > 3 else "medium",
        "task_id": task.get('id'),
        "task_title": task.get('title'),
        "task_description": task.get('description'),
        "assignee_id": task.get('assignee_id'),
        "assignee_name": task.get('assignee_name'),
        "project_id": task.get('project_id'),
        "project_name": task.get('project_name'),
        "priority": task.get('priority', 'medium'),
        "due_date": due_date,
        "overdue_days": overdue_days,
        "status": task.get('status'),
        "created_at": task.get('created_at'),
        "updated_at": task.get('updated_at')
    }
    
    # Add context information
    transformed["context"] = {
        "tenant_id": event_data.get('tenant_id'),
        "created_by": task.get('created_by'),
        "alert_timestamp": event_data.get('timestamp'),
        "source_system": "SBH CRM"
    }
    
    # Add action suggestions
    transformed["actions"] = [
        {
            "action": "mark_complete",
            "url": f"/tasks/{task.get('id')}/complete",
            "description": "Mark task as complete"
        },
        {
            "action": "update_due_date",
            "url": f"/tasks/{task.get('id')}/edit",
            "description": "Update due date"
        },
        {
            "action": "reassign",
            "url": f"/tasks/{task.get('id')}/reassign",
            "description": "Reassign task"
        }
    ]
    
    return transformed
