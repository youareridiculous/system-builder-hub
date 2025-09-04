from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query
from db import get_db
from routers.auth import check_permission, UserWithRoles

router = APIRouter(tags=["analytics"])

@router.get("/communications/summary")
async def get_communications_summary(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: UserWithRoles = Depends(check_permission("analytics.read"))
):
    """Get communications analytics summary"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build date filter
    date_filter = ""
    params = []
    if from_date:
        date_filter += " AND DATE(created_at) >= ?"
        params.append(from_date)
    if to_date:
        date_filter += " AND DATE(created_at) <= ?"
        params.append(to_date)
    
    # Get totals by type
    cursor.execute(f"""
        SELECT type, COUNT(*) as count, 
               SUM(CASE WHEN status = 'sent' OR status = 'delivered' THEN 1 ELSE 0 END) as successful,
               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM communication_history 
        WHERE 1=1 {date_filter}
        GROUP BY type
    """, params)
    
    type_summary = {}
    total_communications = 0
    total_successful = 0
    total_failed = 0
    
    for row in cursor.fetchall():
        type_summary[row['type']] = {
            'count': row['count'],
            'successful': row['successful'],
            'failed': row['failed'],
            'success_rate': round((row['successful'] / row['count']) * 100, 1) if row['count'] > 0 else 0
        }
        total_communications += row['count']
        total_successful += row['successful']
        total_failed += row['failed']
    
    # Get status breakdown
    cursor.execute(f"""
        SELECT status, COUNT(*) as count
        FROM communication_history 
        WHERE 1=1 {date_filter}
        GROUP BY status
    """, params)
    
    status_breakdown = {row['status']: row['count'] for row in cursor.fetchall()}
    
    # Get daily volume
    cursor.execute(f"""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM communication_history 
        WHERE 1=1 {date_filter}
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
    """, params)
    
    daily_volume = [{'date': row['date'], 'count': row['count']} for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'summary': {
            'total_communications': total_communications,
            'total_successful': total_successful,
            'total_failed': total_failed,
            'overall_success_rate': round((total_successful / total_communications) * 100, 1) if total_communications > 0 else 0
        },
        'by_type': type_summary,
        'by_status': status_breakdown,
        'daily_volume': daily_volume
    }

@router.get("/pipeline/summary")
async def get_pipeline_summary(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    pipeline_id: Optional[int] = None,
    current_user: UserWithRoles = Depends(check_permission("analytics.read"))
):
    """Get pipeline analytics summary"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build date filter
    date_filter = ""
    params = []
    if from_date:
        date_filter += " AND DATE(created_at) >= ?"
        params.append(from_date)
    if to_date:
        date_filter += " AND DATE(created_at) <= ?"
        params.append(to_date)
    
    pipeline_filter = ""
    if pipeline_id:
        pipeline_filter = " AND pipeline_id = ?"
        params.append(pipeline_id)
    
    # Get deals by stage
    cursor.execute(f"""
        SELECT stage, COUNT(*) as count, SUM(amount) as total_amount
        FROM deals 
        WHERE 1=1 {date_filter} {pipeline_filter}
        GROUP BY stage
    """, params)
    
    stage_summary = {}
    total_deals = 0
    total_value = 0
    
    for row in cursor.fetchall():
        stage_summary[row['stage']] = {
            'count': row['count'],
            'total_amount': row['total_amount'] or 0,
            'avg_amount': round((row['total_amount'] or 0) / row['count'], 2) if row['count'] > 0 else 0
        }
        total_deals += row['count']
        total_value += (row['total_amount'] or 0)
    
    # Get win rate (closed_won vs closed_lost)
    cursor.execute(f"""
        SELECT 
            SUM(CASE WHEN stage = 'closed_won' THEN 1 ELSE 0 END) as won,
            SUM(CASE WHEN stage = 'closed_lost' THEN 1 ELSE 0 END) as lost
        FROM deals 
        WHERE stage IN ('closed_won', 'closed_lost') {date_filter} {pipeline_filter}
    """, params)
    
    win_data = cursor.fetchone()
    won_deals = win_data['won'] or 0
    lost_deals = win_data['lost'] or 0
    total_closed = won_deals + lost_deals
    win_rate = round((won_deals / total_closed) * 100, 1) if total_closed > 0 else 0
    
    # Get average stage duration (basic calculation)
    cursor.execute(f"""
        SELECT stage, AVG(JULIANDAY('now') - JULIANDAY(created_at)) as avg_days
        FROM deals 
        WHERE 1=1 {date_filter} {pipeline_filter}
        GROUP BY stage
    """, params)
    
    stage_duration = {row['stage']: round(row['avg_days'], 1) for row in cursor.fetchall()}
    
    # Get velocity (avg days from create to closed_won)
    cursor.execute(f"""
        SELECT AVG(JULIANDAY('now') - JULIANDAY(created_at)) as avg_velocity
        FROM deals 
        WHERE stage = 'closed_won' {date_filter} {pipeline_filter}
    """, params)
    
    velocity_data = cursor.fetchone()
    avg_velocity = round(velocity_data['avg_velocity'], 1) if velocity_data['avg_velocity'] else 0
    
    conn.close()
    
    return {
        'summary': {
            'total_deals': total_deals,
            'total_value': total_value,
            'avg_deal_value': round(total_value / total_deals, 2) if total_deals > 0 else 0,
            'win_rate': win_rate,
            'avg_velocity_days': avg_velocity
        },
        'by_stage': stage_summary,
        'stage_duration': stage_duration,
        'win_loss': {
            'won': won_deals,
            'lost': lost_deals,
            'total_closed': total_closed
        }
    }

@router.get("/activities/summary")
async def get_activities_summary(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: UserWithRoles = Depends(check_permission("analytics.read"))
):
    """Get activities analytics summary"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build date filter
    date_filter = ""
    params = []
    if from_date:
        date_filter += " AND DATE(created_at) >= ?"
        params.append(from_date)
    if to_date:
        date_filter += " AND DATE(created_at) <= ?"
        params.append(to_date)
    
    # Get activities by type
    cursor.execute(f"""
        SELECT type, COUNT(*) as count,
               SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed,
               SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) as pending
        FROM activities 
        WHERE 1=1 {date_filter}
        GROUP BY type
    """, params)
    
    type_summary = {}
    total_activities = 0
    total_completed = 0
    total_pending = 0
    
    for row in cursor.fetchall():
        type_summary[row['type']] = {
            'count': row['count'],
            'completed': row['completed'],
            'pending': row['pending'],
            'completion_rate': round((row['completed'] / row['count']) * 100, 1) if row['count'] > 0 else 0
        }
        total_activities += row['count']
        total_completed += row['completed']
        total_pending += row['pending']
    
    # Get completion rate over time
    cursor.execute(f"""
        SELECT DATE(created_at) as date, 
               COUNT(*) as created,
               SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
        FROM activities 
        WHERE 1=1 {date_filter}
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
    """, params)
    
    daily_completion = [
        {
            'date': row['date'],
            'created': row['created'],
            'completed': row['completed'],
            'completion_rate': round((row['completed'] / row['created']) * 100, 1) if row['created'] > 0 else 0
        }
        for row in cursor.fetchall()
    ]
    
    # Get overdue activities
    cursor.execute(f"""
        SELECT COUNT(*) as overdue_count
        FROM activities 
        WHERE completed = 0 AND due_date < DATE('now') {date_filter}
    """, params)
    
    overdue_data = cursor.fetchone()
    overdue_count = overdue_data['overdue_count'] or 0
    
    conn.close()
    
    return {
        'summary': {
            'total_activities': total_activities,
            'total_completed': total_completed,
            'total_pending': total_pending,
            'overall_completion_rate': round((total_completed / total_activities) * 100, 1) if total_activities > 0 else 0,
            'overdue_count': overdue_count
        },
        'by_type': type_summary,
        'daily_completion': daily_completion
    }

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    current_user: UserWithRoles = Depends(check_permission("analytics.read"))
):
    """Get high-level dashboard overview"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get quick counts
    cursor.execute("SELECT COUNT(*) as count FROM accounts")
    total_accounts = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM contacts")
    total_contacts = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM deals WHERE stage NOT IN ('closed_won', 'closed_lost')")
    open_deals = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM activities WHERE completed = 0")
    pending_activities = cursor.fetchone()['count']
    
    # Get recent communications
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM communication_history 
        WHERE DATE(created_at) = DATE('now')
    """)
    today_communications = cursor.fetchone()['count']
    
    # Get recent activities
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM activities 
        WHERE DATE(created_at) = DATE('now')
    """)
    today_activities = cursor.fetchone()['count']
    
    # Get pipeline value
    cursor.execute("SELECT SUM(amount) as total FROM deals WHERE stage NOT IN ('closed_lost')")
    pipeline_value = cursor.fetchone()['total'] or 0
    
    conn.close()
    
    return {
        'quick_stats': {
            'total_accounts': total_accounts,
            'total_contacts': total_contacts,
            'open_deals': open_deals,
            'pending_activities': pending_activities,
            'pipeline_value': pipeline_value
        },
        'today': {
            'communications': today_communications,
            'activities': today_activities
        }
    }

@router.get("/communications/time-series")
async def get_communications_time_series(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: UserWithRoles = Depends(check_permission("analytics.read"))
):
    """Get communications success rate over time (daily)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build date filter
    date_filter = ""
    params = []
    if from_date:
        date_filter += " AND DATE(created_at) >= ?"
        params.append(from_date)
    if to_date:
        date_filter += " AND DATE(created_at) <= ?"
        params.append(to_date)
    
    # Get daily success rates
    cursor.execute(f"""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'sent' OR status = 'delivered' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM communication_history 
        WHERE 1=1 {date_filter}
        GROUP BY DATE(created_at)
        ORDER BY date
    """, params)
    
    time_series = []
    for row in cursor.fetchall():
        success_rate = round((row['successful'] / row['total']) * 100, 1) if row['total'] > 0 else 0
        time_series.append({
            'date': row['date'],
            'total': row['total'],
            'successful': row['successful'],
            'failed': row['failed'],
            'success_rate': success_rate
        })
    
    conn.close()
    return time_series

@router.get("/pipeline/velocity")
async def get_pipeline_velocity(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: UserWithRoles = Depends(check_permission("analytics.read"))
):
    """Get pipeline stage velocity and stuck deals"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build date filter
    date_filter = ""
    params = []
    if from_date:
        date_filter += " AND DATE(updated_at) >= ?"
        params.append(from_date)
    if to_date:
        date_filter += " AND DATE(updated_at) <= ?"
        params.append(to_date)
    
    # Get average days per stage
    cursor.execute(f"""
        SELECT 
            stage,
            AVG(JULIANDAY(updated_at) - JULIANDAY(created_at)) as avg_days,
            COUNT(*) as deal_count
        FROM deals 
        WHERE stage NOT IN ('closed_won', 'closed_lost') {date_filter}
        GROUP BY stage
    """, params)
    
    stage_velocity = []
    for row in cursor.fetchall():
        stage_velocity.append({
            'stage': row['stage'],
            'avg_days': round(row['avg_days'], 1) if row['avg_days'] else 0,
            'deal_count': row['deal_count']
        })
    
    # Get stuck deals (more than 30 days in current stage)
    cursor.execute(f"""
        SELECT 
            id, name, stage, amount, 
            JULIANDAY('now') - JULIANDAY(updated_at) as days_in_stage
        FROM deals 
        WHERE stage NOT IN ('closed_won', 'closed_lost')
        AND JULIANDAY('now') - JULIANDAY(updated_at) > 30
        ORDER BY days_in_stage DESC
        LIMIT 10
    """)
    
    stuck_deals = []
    for row in cursor.fetchall():
        stuck_deals.append({
            'id': row['id'],
            'name': row['name'],
            'stage': row['stage'],
            'amount': row['amount'],
            'days_in_stage': round(row['days_in_stage'], 0)
        })
    
    conn.close()
    return {
        'stage_velocity': stage_velocity,
        'stuck_deals': stuck_deals
    }

@router.get("/activities/heatmap")
async def get_activities_heatmap(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: UserWithRoles = Depends(check_permission("analytics.read"))
):
    """Get activities heatmap by weekday and hour"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build date filter
    date_filter = ""
    params = []
    if from_date:
        date_filter += " AND DATE(created_at) >= ?"
        params.append(from_date)
    if to_date:
        date_filter += " AND DATE(created_at) <= ?"
        params.append(to_date)
    
    # Get activities by weekday and hour
    cursor.execute(f"""
        SELECT 
            strftime('%w', created_at) as weekday,
            strftime('%H', created_at) as hour,
            COUNT(*) as count
        FROM activities 
        WHERE 1=1 {date_filter}
        GROUP BY weekday, hour
        ORDER BY weekday, hour
    """, params)
    
    heatmap_data = {}
    for row in cursor.fetchall():
        weekday = int(row['weekday'])
        hour = int(row['hour'])
        if weekday not in heatmap_data:
            heatmap_data[weekday] = {}
        heatmap_data[weekday][hour] = row['count']
    
    # Convert to array format for frontend
    heatmap_array = []
    for weekday in range(7):
        for hour in range(24):
            count = heatmap_data.get(weekday, {}).get(hour, 0)
            heatmap_array.append({
                'weekday': weekday,
                'hour': hour,
                'count': count
            })
    
    conn.close()
    return heatmap_array

@router.get("/accounts/top")
async def get_top_accounts(
    limit: int = Query(10, ge=1, le=50),
    current_user: UserWithRoles = Depends(check_permission("analytics.read"))
):
    """Get top accounts by open deal amount"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            a.id, a.name, a.industry,
            SUM(d.amount) as total_open_amount,
            COUNT(d.id) as deal_count
        FROM accounts a
        LEFT JOIN deals d ON a.id = d.account_id AND d.stage NOT IN ('closed_lost')
        GROUP BY a.id, a.name, a.industry
        HAVING total_open_amount > 0
        ORDER BY total_open_amount DESC
        LIMIT ?
    """, (limit,))
    
    top_accounts = []
    for row in cursor.fetchall():
        top_accounts.append({
            'id': row['id'],
            'name': row['name'],
            'industry': row['industry'],
            'total_open_amount': row['total_open_amount'],
            'deal_count': row['deal_count']
        })
    
    conn.close()
    return top_accounts
