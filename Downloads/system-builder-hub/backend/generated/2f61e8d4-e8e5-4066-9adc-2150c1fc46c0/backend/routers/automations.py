import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from db import get_db
from models import AutomationRule, AutomationRuleCreate, AutomationRuleUpdate, AutomationRun
from providers.provider_factory import ProviderFactory
from routers.auth import check_permission, UserWithRoles

router = APIRouter(tags=["automations"])

# In-memory cache to prevent duplicate rule execution
rule_execution_cache = {}

def check_conditions(conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Check if conditions are met for rule execution"""
    if not conditions:
        return True
    
    # Check pipeline/stage conditions
    if 'pipeline_id' in conditions and context.get('deal'):
        if context['deal'].get('pipeline_id') != conditions['pipeline_id']:
            return False
    
    if 'stage' in conditions and context.get('deal'):
        if conditions.get('stage_operator') == 'equals':
            if context['deal'].get('stage') != conditions['stage']:
                return False
        elif conditions.get('stage_operator') == 'in':
            if context['deal'].get('stage') not in conditions['stage']:
                return False
    
    # Check contact conditions
    if 'contact_has_email' in conditions and context.get('contact'):
        if conditions['contact_has_email'] and not context['contact'].get('email'):
            return False
    
    if 'contact_has_phone' in conditions and context.get('contact'):
        if conditions['contact_has_phone'] and not context['contact'].get('phone'):
            return False
    
    # Check account conditions
    if 'account_id' in conditions and context.get('contact'):
        if context['contact'].get('account_id') != conditions['account_id']:
            return False
    
    # Check date/time conditions
    if 'business_hours_only' in conditions and conditions['business_hours_only']:
        now = datetime.now()
        if now.weekday() >= 5 or now.hour < 9 or now.hour > 17:  # Weekend or outside 9-5
            return False
    
    return True

async def execute_actions(actions: List[Dict[str, Any]], context: Dict[str, Any], rule_id: int):
    """Execute automation actions"""
    conn = get_db()
    cursor = conn.cursor()
    
    for action in actions:
        try:
            action_type = action.get('type')
            
            if action_type == 'send_email_template':
                template_id = action.get('template_id')
                contact_id = context.get('contact_id')
                
                if template_id and contact_id:
                    # Get template
                    cursor.execute("SELECT * FROM templates WHERE id = ? AND type = 'email'", (template_id,))
                    template = cursor.fetchone()
                    if template:
                        # Build context for template rendering
                        from routers.templates import build_context, render_template
                        template_context = build_context(contact_id=contact_id)
                        rendered_subject, rendered_body = render_template(
                            template['body'], template['subject'], template_context
                        )
                        
                        # Send email
                        email_provider = ProviderFactory.get_email_provider()
                        result = email_provider.send_email(
                            to_email=template_context.get('contact.email', 'test@example.com'),
                            subject=rendered_subject,
                            body=rendered_body
                        )
                        
                        # Log communication
                        cursor.execute("""
                            INSERT INTO communication_history 
                            (contact_id, type, direction, provider, subject, content, status, provider_message_id)
                            VALUES (?, 'email', 'outbound', ?, ?, ?, ?, ?)
                        """, (
                            contact_id,
                            ProviderFactory.get_provider_status()['email'],
                            rendered_subject,
                            rendered_body,
                            result.get('status', 'sent'),
                            result.get('provider_message_id')
                        ))
            
            elif action_type == 'send_sms_template':
                template_id = action.get('template_id')
                contact_id = context.get('contact_id')
                
                if template_id and contact_id:
                    # Get template
                    cursor.execute("SELECT * FROM templates WHERE id = ? AND type = 'sms'", (template_id,))
                    template = cursor.fetchone()
                    if template:
                        # Build context for template rendering
                        from routers.templates import build_context, render_template
                        template_context = build_context(contact_id=contact_id)
                        rendered_subject, rendered_body = render_template(
                            template['body'], template['subject'], template_context
                        )
                        
                        # Send SMS
                        sms_provider = ProviderFactory.get_sms_provider()
                        result = sms_provider.send_sms(
                            to_phone=template_context.get('contact.phone', '+1234567890'),
                            message=rendered_body
                        )
                        
                        # Log communication
                        cursor.execute("""
                            INSERT INTO communication_history 
                            (contact_id, type, direction, provider, content, status, provider_message_id)
                            VALUES (?, 'sms', 'outbound', ?, ?, ?, ?)
                        """, (
                            contact_id,
                            ProviderFactory.get_provider_status()['sms'],
                            rendered_body,
                            result.get('status', 'sent'),
                            result.get('provider_message_id')
                        ))
            
            elif action_type == 'create_activity':
                activity_data = {
                    'type': action.get('activity_type', 'task'),
                    'subject': action.get('subject', 'Automated Activity'),
                    'description': action.get('description', ''),
                    'contact_id': context.get('contact_id'),
                    'deal_id': context.get('deal_id'),
                    'completed': False
                }
                
                # Calculate due date offset
                if 'due_date_offset' in action:
                    offset = action['due_date_offset']
                    if offset.endswith('d'):
                        days = int(offset[:-1])
                        activity_data['due_date'] = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
                    elif offset.endswith('h'):
                        hours = int(offset[:-1])
                        activity_data['due_date'] = (datetime.now() + timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M')
                
                cursor.execute("""
                    INSERT INTO activities (type, subject, description, contact_id, deal_id, due_date, completed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    activity_data['type'],
                    activity_data['subject'],
                    activity_data['description'],
                    activity_data['contact_id'],
                    activity_data['deal_id'],
                    activity_data.get('due_date'),
                    activity_data['completed']
                ))
            
            elif action_type == 'move_deal_stage':
                deal_id = context.get('deal_id')
                new_stage = action.get('stage')
                
                if deal_id and new_stage:
                    cursor.execute("UPDATE deals SET stage = ? WHERE id = ?", (new_stage, deal_id))
            
            elif action_type == 'wait':
                # Simple wait - in a real implementation, this would use a proper job queue
                wait_seconds = action.get('seconds', 0)
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
        
        except Exception as e:
            # Log the error
            cursor.execute("""
                INSERT INTO automation_runs (rule_id, triggered_at, payload, status, message)
                VALUES (?, ?, ?, ?, ?)
            """, (
                rule_id,
                datetime.now(),
                json.dumps(context),
                'failed',
                str(e)
            ))
            conn.commit()
            raise
    
    conn.commit()
    conn.close()

async def execute_rule(rule_id: int, trigger: str, context: Dict[str, Any]):
    """Execute a single automation rule"""
    # Check for duplicate execution (within 1 minute)
    cache_key = f"{rule_id}_{trigger}_{context.get('entity_id')}"
    if cache_key in rule_execution_cache:
        last_execution = rule_execution_cache[cache_key]
        if datetime.now() - last_execution < timedelta(minutes=1):
            return  # Skip duplicate execution
    
    rule_execution_cache[cache_key] = datetime.now()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get rule
    cursor.execute("SELECT * FROM automation_rules WHERE id = ? AND is_enabled = TRUE", (rule_id,))
    rule = cursor.fetchone()
    if not rule:
        conn.close()
        return
    
    # Parse conditions and actions
    conditions = json.loads(rule['conditions']) if rule['conditions'] else {}
    actions = json.loads(rule['actions']) if rule['actions'] else []
    
    # Check conditions
    if not check_conditions(conditions, context):
        # Log skipped execution
        cursor.execute("""
            INSERT INTO automation_runs (rule_id, triggered_at, payload, status, message)
            VALUES (?, ?, ?, ?, ?)
        """, (
            rule_id,
            datetime.now(),
            json.dumps(context),
            'skipped',
            'Conditions not met'
        ))
        conn.commit()
        conn.close()
        return
    
    # Execute actions
    try:
        await execute_actions(actions, context, rule_id)
        
        # Log successful execution
        cursor.execute("""
            INSERT INTO automation_runs (rule_id, triggered_at, payload, status, message)
            VALUES (?, ?, ?, ?, ?)
        """, (
            rule_id,
            datetime.now(),
            json.dumps(context),
            'success',
            'Rule executed successfully'
        ))
        
        # Update last run time
        cursor.execute("UPDATE automation_rules SET last_run_at = ? WHERE id = ?", (datetime.now(), rule_id))
        
    except Exception as e:
        # Log failed execution
        cursor.execute("""
            INSERT INTO automation_runs (rule_id, triggered_at, payload, status, message)
            VALUES (?, ?, ?, ?, ?)
        """, (
            rule_id,
            datetime.now(),
            json.dumps(context),
            'failed',
            str(e)
        ))
    
    conn.commit()
    conn.close()

@router.get("/", response_model=List[AutomationRule])
async def list_automation_rules(
    current_user: UserWithRoles = Depends(check_permission("automations.read"))
):
    """List all automation rules"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM automation_rules ORDER BY created_at DESC")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rules

@router.get("/{rule_id}", response_model=AutomationRule)
async def get_automation_rule(
    rule_id: int,
    current_user: UserWithRoles = Depends(check_permission("automations.read"))
):
    """Get a specific automation rule"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,))
    rule = cursor.fetchone()
    conn.close()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    
    return dict(rule)

@router.post("/", response_model=AutomationRule)
async def create_automation_rule(
    rule: AutomationRuleCreate,
    current_user: UserWithRoles = Depends(check_permission("automations.write"))
):
    """Create a new automation rule"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO automation_rules (name, trigger, conditions, actions)
        VALUES (?, ?, ?, ?)
    """, (
        rule.name,
        rule.trigger,
        json.dumps(rule.conditions) if rule.conditions else None,
        json.dumps(rule.actions) if rule.actions else None
    ))
    
    rule_id = cursor.lastrowid
    conn.commit()
    
    # Return the created rule
    cursor.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,))
    created_rule = dict(cursor.fetchone())
    conn.close()
    
    return created_rule

@router.put("/{rule_id}", response_model=AutomationRule)
async def update_automation_rule(
    rule_id: int, 
    rule: AutomationRuleUpdate,
    current_user: UserWithRoles = Depends(check_permission("automations.write"))
):
    """Update an automation rule"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build update fields
    update_fields = []
    params = []
    
    if rule.name is not None:
        update_fields.append("name = ?")
        params.append(rule.name)
    
    if rule.is_enabled is not None:
        update_fields.append("is_enabled = ?")
        params.append(rule.is_enabled)
    
    if rule.conditions is not None:
        update_fields.append("conditions = ?")
        params.append(json.dumps(rule.conditions))
    
    if rule.actions is not None:
        update_fields.append("actions = ?")
        params.append(json.dumps(rule.actions))
    
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(rule_id)
    
    query = f"UPDATE automation_rules SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    
    # Return updated rule
    cursor.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,))
    updated_rule = dict(cursor.fetchone())
    conn.close()
    
    return updated_rule

@router.delete("/{rule_id}")
async def delete_automation_rule(
    rule_id: int,
    current_user: UserWithRoles = Depends(check_permission("automations.delete"))
):
    """Delete an automation rule"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM automation_rules WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()
    return {"message": "Automation rule deleted"}

@router.get("/{rule_id}/runs", response_model=List[AutomationRun])
async def get_automation_runs(rule_id: int, limit: int = 50):
    """Get execution history for an automation rule"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM automation_runs 
        WHERE rule_id = ? 
        ORDER BY triggered_at DESC 
        LIMIT ?
    """, (rule_id, limit))
    runs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return runs

@router.post("/{rule_id}/test")
async def test_automation_rule(rule_id: int, context: Dict[str, Any]):
    """Test an automation rule with provided context"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get rule
    cursor.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,))
    rule = cursor.fetchone()
    if not rule:
        conn.close()
        raise HTTPException(status_code=404, detail="Automation rule not found")
    
    # Parse conditions and actions
    conditions = json.loads(rule['conditions']) if rule['conditions'] else {}
    actions = json.loads(rule['actions']) if rule['actions'] else []
    
    # Check conditions
    conditions_met = check_conditions(conditions, context)
    
    conn.close()
    
    return {
        "rule_id": rule_id,
        "rule_name": rule['name'],
        "conditions_met": conditions_met,
        "actions_count": len(actions),
        "actions": actions if conditions_met else [],
        "context": context
    }

@router.post("/trigger/{trigger}")
async def trigger_automation_rules(trigger: str, context: Dict[str, Any], background_tasks: BackgroundTasks):
    """Trigger automation rules for a specific event"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Find rules that match this trigger
    cursor.execute("SELECT id FROM automation_rules WHERE trigger = ? AND is_enabled = TRUE", (trigger,))
    rule_ids = [row['id'] for row in cursor.fetchall()]
    conn.close()
    
    # Execute rules in background
    for rule_id in rule_ids:
        background_tasks.add_task(execute_rule, rule_id, trigger, context)
    
    return {
        "message": f"Triggered {len(rule_ids)} automation rules",
        "trigger": trigger,
        "rules_count": len(rule_ids)
    }
