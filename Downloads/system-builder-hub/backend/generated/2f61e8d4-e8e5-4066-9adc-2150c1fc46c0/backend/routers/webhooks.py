import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends, Query
from db import get_db
from routers.automations import trigger_automation_rules
from routers.auth import check_permission, UserWithRoles

router = APIRouter(tags=["webhooks"])

@router.post("/sendgrid")
async def sendgrid_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle SendGrid webhook events"""
    try:
        # Get the raw body
        body = await request.body()
        events = json.loads(body)
        
        # Process each event
        for event in events:
            await process_sendgrid_event(event, background_tasks)
        
        return {"status": "success", "processed_events": len(events)}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {str(e)}")

async def process_sendgrid_event(event: Dict[str, Any], background_tasks: BackgroundTasks):
    """Process a single SendGrid event"""
    event_type = event.get('event')
    message_id = event.get('sg_message_id')
    email = event.get('email')
    timestamp = event.get('timestamp')
    
    if not message_id:
        return
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Find the communication record by provider_message_id
        cursor.execute("""
            SELECT id, contact_id, type, status 
            FROM communication_history 
            WHERE provider_message_id = ?
        """, (message_id,))
        
        comm_record = cursor.fetchone()
        if not comm_record:
            # Log unknown message
            cursor.execute("""
                INSERT INTO communication_history 
                (type, direction, provider, content, status, provider_message_id, created_at)
                VALUES ('email', 'outbound', 'sendgrid', ?, ?, ?, ?)
            """, (
                f"Unknown message: {message_id}",
                event_type,
                message_id,
                timestamp
            ))
            conn.commit()
            return
        
        # Update communication status based on event type
        new_status = None
        delivered_at = None
        opened_at = None
        failed_reason = None
        
        if event_type == 'delivered':
            new_status = 'delivered'
            delivered_at = timestamp
        elif event_type == 'open':
            new_status = 'opened'
            opened_at = timestamp
        elif event_type == 'bounce':
            new_status = 'failed'
            failed_reason = 'bounced'
        elif event_type == 'dropped':
            new_status = 'failed'
            failed_reason = 'dropped'
        elif event_type == 'spamreport':
            new_status = 'failed'
            failed_reason = 'spam'
        
        if new_status:
            update_fields = ["status = ?"]
            params = [new_status]
            
            if delivered_at:
                update_fields.append("delivered_at = ?")
                params.append(delivered_at)
            
            if opened_at:
                update_fields.append("opened_at = ?")
                params.append(opened_at)
            
            if failed_reason:
                update_fields.append("failed_reason = ?")
                params.append(failed_reason)
            
            params.append(comm_record['id'])
            
            query = f"UPDATE communication_history SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            
            # Trigger automation if status changed
            if new_status in ['delivered', 'failed', 'opened']:
                context = {
                    'communication_id': comm_record['id'],
                    'contact_id': comm_record['contact_id'],
                    'type': comm_record['type'],
                    'status': new_status,
                    'event_type': event_type,
                    'provider': 'sendgrid'
                }
                
                background_tasks.add_task(
                    trigger_automation_rules, 
                    'communication.status_updated', 
                    context
                )
        
        conn.commit()
    
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@router.post("/twilio/sms")
async def twilio_sms_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Twilio SMS webhook events"""
    try:
        form_data = await request.form()
        
        message_sid = form_data.get('MessageSid')
        message_status = form_data.get('MessageStatus')
        to_number = form_data.get('To')
        from_number = form_data.get('From')
        error_code = form_data.get('ErrorCode')
        error_message = form_data.get('ErrorMessage')
        
        if not message_sid:
            raise HTTPException(status_code=400, detail="Missing MessageSid")
        
        await process_twilio_sms_event({
            'message_sid': message_sid,
            'status': message_status,
            'to': to_number,
            'from': from_number,
            'error_code': error_code,
            'error_message': error_message
        }, background_tasks)
        
        return {"status": "success"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {str(e)}")

async def process_twilio_sms_event(event: Dict[str, Any], background_tasks: BackgroundTasks):
    """Process a single Twilio SMS event"""
    message_sid = event.get('message_sid')
    status = event.get('status')
    error_code = event.get('error_code')
    error_message = event.get('error_message')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Find the communication record by provider_message_id
        cursor.execute("""
            SELECT id, contact_id, type, status 
            FROM communication_history 
            WHERE provider_message_id = ?
        """, (message_sid,))
        
        comm_record = cursor.fetchone()
        if not comm_record:
            return
        
        # Map Twilio status to our status
        new_status = None
        failed_reason = None
        
        if status == 'delivered':
            new_status = 'delivered'
        elif status == 'failed':
            new_status = 'failed'
            failed_reason = f"Twilio error: {error_code} - {error_message}" if error_code else 'failed'
        elif status == 'sent':
            new_status = 'sent'
        
        if new_status:
            update_fields = ["status = ?"]
            params = [new_status]
            
            if new_status == 'delivered':
                update_fields.append("delivered_at = CURRENT_TIMESTAMP")
            
            if failed_reason:
                update_fields.append("failed_reason = ?")
                params.append(failed_reason)
            
            params.append(comm_record['id'])
            
            query = f"UPDATE communication_history SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            
            # Trigger automation if status changed
            if new_status in ['delivered', 'failed']:
                context = {
                    'communication_id': comm_record['id'],
                    'contact_id': comm_record['contact_id'],
                    'type': comm_record['type'],
                    'status': new_status,
                    'event_type': status,
                    'provider': 'twilio'
                }
                
                background_tasks.add_task(
                    trigger_automation_rules, 
                    'communication.status_updated', 
                    context
                )
        
        conn.commit()
    
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@router.post("/twilio/voice")
async def twilio_voice_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Twilio Voice webhook events"""
    try:
        form_data = await request.form()
        
        call_sid = form_data.get('CallSid')
        call_status = form_data.get('CallStatus')
        call_duration = form_data.get('CallDuration')
        recording_url = form_data.get('RecordingUrl')
        recording_sid = form_data.get('RecordingSid')
        
        if not call_sid:
            raise HTTPException(status_code=400, detail="Missing CallSid")
        
        await process_twilio_voice_event({
            'call_sid': call_sid,
            'status': call_status,
            'duration': call_duration,
            'recording_url': recording_url,
            'recording_sid': recording_sid
        }, background_tasks)
        
        return {"status": "success"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {str(e)}")

async def process_twilio_voice_event(event: Dict[str, Any], background_tasks: BackgroundTasks):
    """Process a single Twilio Voice event"""
    call_sid = event.get('call_sid')
    status = event.get('status')
    duration = event.get('duration')
    recording_url = event.get('recording_url')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Find the communication record by provider_message_id
        cursor.execute("""
            SELECT id, contact_id, type, status 
            FROM communication_history 
            WHERE provider_message_id = ?
        """, (call_sid,))
        
        comm_record = cursor.fetchone()
        if not comm_record:
            return
        
        # Map Twilio status to our status
        new_status = None
        
        if status == 'completed':
            new_status = 'completed'
        elif status == 'failed':
            new_status = 'failed'
        elif status == 'busy':
            new_status = 'failed'
        elif status == 'no-answer':
            new_status = 'failed'
        elif status == 'answered':
            new_status = 'answered'
        
        if new_status:
            update_fields = ["status = ?"]
            params = [new_status]
            
            if duration:
                update_fields.append("duration = ?")
                params.append(int(duration))
            
            if recording_url:
                update_fields.append("recording_url = ?")
                params.append(recording_url)
            
            params.append(comm_record['id'])
            
            query = f"UPDATE communication_history SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            
            # Trigger automation if status changed
            if new_status in ['completed', 'failed', 'answered']:
                context = {
                    'communication_id': comm_record['id'],
                    'contact_id': comm_record['contact_id'],
                    'type': comm_record['type'],
                    'status': new_status,
                    'event_type': status,
                    'provider': 'twilio',
                    'duration': duration,
                    'recording_url': recording_url
                }
                
                background_tasks.add_task(
                    trigger_automation_rules, 
                    'communication.status_updated', 
                    context
                )
        
        conn.commit()
    
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@router.get("/test")
async def test_webhook():
    """Test endpoint to verify webhook connectivity"""
    return {
        "status": "success",
        "message": "Webhook endpoint is working",
        "timestamp": "2025-08-30T00:00:00Z"
    }

@router.get("/events")
async def get_webhook_events(
    provider: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserWithRoles = Depends(check_permission("webhooks.read"))
):
    """Get webhook events with filters"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build filters
    where_clause = "WHERE 1=1"
    params = []
    
    if provider:
        where_clause += " AND provider = ?"
        params.append(provider)
    
    if event_type:
        where_clause += " AND event_type = ?"
        params.append(event_type)
    
    if status:
        where_clause += " AND status = ?"
        params.append(status)
    
    if from_date:
        where_clause += " AND DATE(created_at) >= ?"
        params.append(from_date)
    
    if to_date:
        where_clause += " AND DATE(created_at) <= ?"
        params.append(to_date)
    
    # Get total count
    cursor.execute(f"SELECT COUNT(*) as count FROM webhook_events {where_clause}", params)
    total_count = cursor.fetchone()['count']
    
    # Get events
    cursor.execute(f"""
        SELECT 
            id, provider, event_type, status, resource_id, 
            communication_id, contact_id, error_message,
            raw_payload, created_at
        FROM webhook_events 
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, params + [limit, offset])
    
    events = []
    for row in cursor.fetchall():
        events.append({
            'id': row['id'],
            'provider': row['provider'],
            'event_type': row['event_type'],
            'status': row['status'],
            'resource_id': row['resource_id'],
            'communication_id': row['communication_id'],
            'contact_id': row['contact_id'],
            'error_message': row['error_message'],
            'raw_payload': row['raw_payload'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return {
        'events': events,
        'total_count': total_count,
        'limit': limit,
        'offset': offset
    }

@router.post("/events/{event_id}/replay")
async def replay_webhook_event(
    event_id: int,
    current_user: UserWithRoles = Depends(check_permission("webhooks.replay"))
):
    """Replay a webhook event (dry-run)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get the event
    cursor.execute("""
        SELECT * FROM webhook_events WHERE id = ?
    """, (event_id,))
    
    event = cursor.fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook event not found")
    
    try:
        # Parse the original payload
        payload = json.loads(event['raw_payload'])
        
        # Replay the event processing (dry-run)
        if event['provider'] == 'sendgrid':
            result = await process_sendgrid_event(payload, None, dry_run=True)
        elif event['provider'] == 'twilio':
            result = await process_twilio_event(payload, None, dry_run=True)
        else:
            result = {"status": "unknown_provider"}
        
        # Log the replay
        cursor.execute("""
            INSERT INTO webhook_events (
                provider, event_type, status, resource_id, 
                communication_id, contact_id, error_message, 
                raw_payload, is_replay
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event['provider'], event['event_type'], 'replayed',
            event['resource_id'], event['communication_id'], 
            event['contact_id'], None, event['raw_payload'], True
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "original_event_id": event_id,
            "replay_result": result
        }
        
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")

# Helper function for dry-run processing
async def process_sendgrid_event(event: Dict[str, Any], background_tasks, dry_run: bool = False):
    """Process SendGrid event (dry-run support)"""
    if dry_run:
        return {
            "status": "dry_run",
            "event_type": event.get('event'),
            "message_id": event.get('sg_message_id'),
            "email": event.get('email')
        }
    
    # Original processing logic here
    # ... (existing implementation)
    pass

async def process_twilio_event(event: Dict[str, Any], background_tasks, dry_run: bool = False):
    """Process Twilio event (dry-run support)"""
    if dry_run:
        return {
            "status": "dry_run",
            "event_type": event.get('EventType'),
            "message_sid": event.get('MessageSid'),
            "to": event.get('To')
        }
    
    # Original processing logic here
    # ... (existing implementation)
    pass
