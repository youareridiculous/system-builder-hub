"""
Daily KPI Calculator Plugin
"""
from datetime import datetime, timedelta
from src.ext.sdk import job, route, PluginContext

@job("calculate_daily_kpis", schedule="0 1 * * *")
def calculate_daily_kpis_job(ctx: PluginContext):
    """Calculate daily KPIs"""
    try:
        # Get yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')
        
        # Calculate KPIs
        kpis = {
            'date': date_str,
            'total_users': 0,
            'active_users': 0,
            'total_projects': 0,
            'total_builds': 0,
            'successful_builds': 0,
            'failed_builds': 0
        }
        
        # Get user count
        users = ctx.db.query('users', limit=1000)
        kpis['total_users'] = len(users)
        
        # Get active users (users with activity in last 7 days)
        active_users = ctx.db.query('users', {'last_active': {'$gte': (datetime.now() - timedelta(days=7)).isoformat()}}, limit=1000)
        kpis['active_users'] = len(active_users)
        
        # Get project count
        projects = ctx.db.query('projects', limit=1000)
        kpis['total_projects'] = len(projects)
        
        # Get build statistics
        builds = ctx.db.query('builds', {'created_at': {'$gte': date_str}}, limit=1000)
        kpis['total_builds'] = len(builds)
        
        successful_builds = [b for b in builds if b.get('status') == 'success']
        kpis['successful_builds'] = len(successful_builds)
        kpis['failed_builds'] = kpis['total_builds'] - kpis['successful_builds']
        
        # Calculate success rate
        if kpis['total_builds'] > 0:
            kpis['success_rate'] = (kpis['successful_builds'] / kpis['total_builds']) * 100
        else:
            kpis['success_rate'] = 0
        
        # Emit KPI event
        ctx.emit("analytics.daily_kpis", kpis)
        
        # Store in analytics (if we had write permission)
        # ctx.db.insert('analytics', kpis)
        
        print(f"Daily KPIs calculated for {date_str}: {kpis}")
        
        return {
            "success": True,
            "kpis": kpis,
            "date": date_str
        }
        
    except Exception as e:
        print(f"Error calculating daily KPIs: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@route("/kpis", methods=["GET"])
def get_kpis_route(ctx: PluginContext):
    """Get latest KPIs"""
    try:
        # Get date from query params
        date = ctx.request.get('date')
        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # In a real implementation, this would query the analytics table
        # For now, return mock data
        kpis = {
            'date': date,
            'total_users': 150,
            'active_users': 120,
            'total_projects': 45,
            'total_builds': 89,
            'successful_builds': 82,
            'failed_builds': 7,
            'success_rate': 92.1
        }
        
        return {
            "success": True,
            "data": kpis
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@route("/ping", methods=["GET"])
def ping_route(ctx: PluginContext):
    """Health check endpoint"""
    return {
        "status": "ok",
        "plugin": "daily-kpi",
        "tenant": ctx.tenant_id
    }
