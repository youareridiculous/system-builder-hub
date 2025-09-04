# App Scripts Guide

This document explains how to create and manage scheduled background jobs (App Scripts) in SBH plugins.

## Overview

App Scripts allow you to run scheduled background tasks within your plugins. These scripts can:

- **Schedule Tasks**: Run on CRON schedules
- **Process Data**: Handle batch operations
- **Generate Reports**: Create periodic reports
- **Clean Up Data**: Remove old or temporary data
- **Sync External Services**: Synchronize with external APIs
- **Send Notifications**: Send scheduled notifications

## Creating App Scripts

### Basic Script Structure

```python
from src.ext.sdk import job, PluginContext

@job("daily_cleanup", schedule="0 2 * * *")
def daily_cleanup_job(ctx: PluginContext):
    """Daily cleanup task"""
    try:
        # Your cleanup logic here
        cleaned_records = cleanup_old_data()
        
        # Log results
        print(f"Cleaned {cleaned_records} old records")
        
        # Emit event for tracking
        ctx.emit("cleanup.completed", {
            "records_cleaned": cleaned_records,
            "job_name": "daily_cleanup"
        })
        
        return {
            "status": "success",
            "records_cleaned": cleaned_records
        }
        
    except Exception as e:
        print(f"Error in daily cleanup: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
```

### Job Decorator

The `@job` decorator defines a scheduled job:

```python
@job("job_name", schedule="cron_expression")
def job_function(ctx: PluginContext):
    # Job logic here
    pass
```

#### Parameters

- **job_name**: Unique name for the job
- **schedule**: CRON expression for scheduling

### CRON Schedule Format

Jobs use standard CRON format:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday=0)
│ │ │ │ │
* * * * *
```

#### Common Schedules

```python
# Every minute
@job("minute_job", schedule="* * * * *")

# Every hour
@job("hourly_job", schedule="0 * * * *")

# Every day at 2 AM
@job("daily_job", schedule="0 2 * * *")

# Every Monday at 9 AM
@job("weekly_job", schedule="0 9 * * 1")

# Every 1st of month at midnight
@job("monthly_job", schedule="0 0 1 * *")

# Every 15 minutes
@job("quarterly_job", schedule="*/15 * * * *")

# Every 2 hours
@job("bi_hourly_job", schedule="0 */2 * * *")
```

## Job Context

### PluginContext Features

The job context provides access to system resources:

```python
@job("data_processor", schedule="0 3 * * *")
def process_data_job(ctx: PluginContext):
    # Access secrets
    api_key = ctx.secrets.get("API_KEY")
    
    # Make HTTP requests
    response = ctx.http.get("https://api.example.com/data")
    
    # Use LLM services
    result = ctx.llm.run("Analyze this data: ...")
    
    # Access files
    files = ctx.files.list("uploads/")
    
    # Query database (read-only)
    records = ctx.db.query("users", {"active": True})
    
    # Emit events
    ctx.emit("job.completed", {"job_name": "data_processor"})
```

## Job Examples

### Data Cleanup Job

```python
@job("cleanup_old_files", schedule="0 1 * * *")
def cleanup_old_files_job(ctx: PluginContext):
    """Clean up files older than 30 days"""
    try:
        from datetime import datetime, timedelta
        
        # Get files older than 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        files = ctx.files.list("temp/")
        
        deleted_count = 0
        for file_info in files:
            file_date = datetime.fromisoformat(file_info['last_modified'])
            if file_date < cutoff_date:
                if ctx.files.delete(file_info['key']):
                    deleted_count += 1
        
        # Log results
        print(f"Deleted {deleted_count} old files")
        
        # Emit event
        ctx.emit("cleanup.files_completed", {
            "files_deleted": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        })
        
        return {
            "status": "success",
            "files_deleted": deleted_count
        }
        
    except Exception as e:
        print(f"Error cleaning up files: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
```

### Report Generation Job

```python
@job("generate_daily_report", schedule="0 6 * * *")
def generate_daily_report_job(ctx: PluginContext):
    """Generate daily activity report"""
    try:
        from datetime import datetime, timedelta
        
        # Get yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')
        
        # Collect data
        users = ctx.db.query("users", limit=1000)
        projects = ctx.db.query("projects", limit=1000)
        builds = ctx.db.query("builds", {"created_at": {"$gte": date_str}}, limit=1000)
        
        # Generate report
        report = {
            "date": date_str,
            "total_users": len(users),
            "total_projects": len(projects),
            "total_builds": len(builds),
            "successful_builds": len([b for b in builds if b.get('status') == 'success']),
            "failed_builds": len([b for b in builds if b.get('status') == 'failed'])
        }
        
        # Save report
        report_json = json.dumps(report, indent=2)
        filename = f"reports/daily_{date_str}.json"
        ctx.files.upload(filename, report_json, "application/json")
        
        # Send notification
        ctx.emit("report.generated", {
            "report_type": "daily",
            "date": date_str,
            "filename": filename
        })
        
        return {
            "status": "success",
            "report": report,
            "filename": filename
        }
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
```

### External API Sync Job

```python
@job("sync_external_data", schedule="*/30 * * * *")
def sync_external_data_job(ctx: PluginContext):
    """Sync data from external API every 30 minutes"""
    try:
        # Get API credentials
        api_key = ctx.secrets.get("EXTERNAL_API_KEY")
        api_url = ctx.secrets.get("EXTERNAL_API_URL")
        
        if not api_key or not api_url:
            return {
                "status": "error",
                "error": "Missing API credentials"
            }
        
        # Fetch data from external API
        headers = {"Authorization": f"Bearer {api_key}"}
        response = ctx.http.get(f"{api_url}/data", headers=headers)
        
        if response.get('status_code') != 200:
            return {
                "status": "error",
                "error": f"API request failed: {response.get('error')}"
            }
        
        data = response.get('json', [])
        
        # Process data
        processed_count = 0
        for item in data:
            # Process each item
            processed_count += 1
        
        # Emit event
        ctx.emit("sync.completed", {
            "items_processed": processed_count,
            "source": "external_api"
        })
        
        return {
            "status": "success",
            "items_processed": processed_count
        }
        
    except Exception as e:
        print(f"Error syncing external data: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
```

### Notification Job

```python
@job("send_weekly_digest", schedule="0 9 * * 1")
def send_weekly_digest_job(ctx: PluginContext):
    """Send weekly digest email every Monday at 9 AM"""
    try:
        from datetime import datetime, timedelta
        
        # Get last week's data
        week_ago = datetime.now() - timedelta(days=7)
        
        # Collect weekly statistics
        new_users = ctx.db.query("users", {"created_at": {"$gte": week_ago.isoformat()}}, limit=1000)
        new_projects = ctx.db.query("projects", {"created_at": {"$gte": week_ago.isoformat()}}, limit=1000)
        builds = ctx.db.query("builds", {"created_at": {"$gte": week_ago.isoformat()}}, limit=1000)
        
        # Generate digest
        digest = {
            "period": "weekly",
            "start_date": week_ago.strftime('%Y-%m-%d'),
            "end_date": datetime.now().strftime('%Y-%m-%d'),
            "new_users": len(new_users),
            "new_projects": len(new_projects),
            "total_builds": len(builds),
            "successful_builds": len([b for b in builds if b.get('status') == 'success'])
        }
        
        # Send digest email
        email_template = ctx.secrets.get("WEEKLY_DIGEST_TEMPLATE")
        if email_template:
            # In a real implementation, this would send the email
            print(f"Weekly digest: {digest}")
        
        # Emit event
        ctx.emit("digest.sent", {
            "digest_type": "weekly",
            "recipients": ["admin@example.com"],
            "digest": digest
        })
        
        return {
            "status": "success",
            "digest": digest
        }
        
    except Exception as e:
        print(f"Error sending weekly digest: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
```

## Job Management

### Manual Execution

Run a job immediately via API:

```bash
curl -X POST https://api.example.com/api/plugins/<plugin_id>/jobs/<job_name>/run-now \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>"
```

### Job Status

Check job status and history:

```python
# Job status is tracked in the database
# You can query job execution history
jobs = ctx.db.query("plugin_jobs", {"plugin_installation_id": "your_plugin_id"})
```

### Job Configuration

Configure jobs in your plugin manifest:

```json
{
  "slug": "my-plugin",
  "name": "My Plugin",
  "jobs": [
    {
      "name": "daily_cleanup",
      "schedule": "0 2 * * *"
    },
    {
      "name": "hourly_sync",
      "schedule": "0 * * * *"
    }
  ]
}
```

## Best Practices

### Error Handling

```python
@job("robust_job", schedule="0 3 * * *")
def robust_job(ctx: PluginContext):
    """Job with robust error handling"""
    try:
        # Main job logic
        result = perform_main_task()
        
        # Log success
        print(f"Job completed successfully: {result}")
        
        return {
            "status": "success",
            "result": result
        }
        
    except Exception as e:
        # Log error
        print(f"Job failed: {e}")
        
        # Emit error event
        ctx.emit("job.failed", {
            "job_name": "robust_job",
            "error": str(e)
        })
        
        return {
            "status": "error",
            "error": str(e)
        }
```

### Resource Management

```python
@job("efficient_job", schedule="0 4 * * *")
def efficient_job(ctx: PluginContext):
    """Job with efficient resource usage"""
    try:
        # Process data in batches
        batch_size = 100
        offset = 0
        
        while True:
            # Get batch of data
            batch = ctx.db.query("users", limit=batch_size, offset=offset)
            
            if not batch:
                break
            
            # Process batch
            for user in batch:
                process_user(user)
            
            offset += batch_size
            
            # Check memory usage
            if not ctx.check_memory_usage():
                print("Memory limit approaching, stopping job")
                break
        
        return {
            "status": "success",
            "processed_count": offset
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### Monitoring and Logging

```python
@job("monitored_job", schedule="0 5 * * *")
def monitored_job(ctx: PluginContext):
    """Job with comprehensive monitoring"""
    start_time = datetime.now()
    
    try:
        # Emit job started event
        ctx.emit("job.started", {
            "job_name": "monitored_job",
            "start_time": start_time.isoformat()
        })
        
        # Perform job
        result = perform_job_task()
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        # Emit job completed event
        ctx.emit("job.completed", {
            "job_name": "monitored_job",
            "duration_seconds": duration,
            "result": result
        })
        
        return {
            "status": "success",
            "duration_seconds": duration,
            "result": result
        }
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        
        # Emit job failed event
        ctx.emit("job.failed", {
            "job_name": "monitored_job",
            "duration_seconds": duration,
            "error": str(e)
        })
        
        return {
            "status": "error",
            "duration_seconds": duration,
            "error": str(e)
        }
```

## Troubleshooting

### Common Issues

#### Job Not Running
- Check CRON schedule syntax
- Verify plugin is enabled
- Check job function exists
- Review error logs

#### Job Timeout
- Optimize job performance
- Process data in smaller batches
- Reduce memory usage
- Consider breaking into smaller jobs

#### Permission Errors
- Check required permissions in manifest
- Verify secret access
- Review database permissions
- Check file system access

#### Memory Issues
- Monitor memory usage
- Process data in batches
- Clean up resources
- Use streaming for large datasets

### Debug Commands

```bash
# Run job manually
curl -X POST https://api.example.com/api/plugins/<id>/jobs/<name>/run-now \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>"

# Check job status
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/plugins/<id>/jobs

# View job logs
# Check application logs for job execution events
```

### Job Metrics

Monitor job performance with metrics:

- `job_executions_total`: Total job executions
- `job_duration_seconds`: Job execution duration
- `job_success_rate`: Job success rate
- `job_memory_usage`: Job memory usage

## Examples

### Complete Plugin with Jobs

```python
# main.py
from src.ext.sdk import job, route, PluginContext

@job("daily_cleanup", schedule="0 2 * * *")
def daily_cleanup_job(ctx: PluginContext):
    """Daily cleanup task"""
    # Cleanup logic here
    return {"status": "success"}

@job("hourly_sync", schedule="0 * * * *")
def hourly_sync_job(ctx: PluginContext):
    """Hourly sync task"""
    # Sync logic here
    return {"status": "success"}

@route("/jobs/status", methods=["GET"])
def job_status_route(ctx: PluginContext):
    """Get job status"""
    return {
        "jobs": [
            {"name": "daily_cleanup", "schedule": "0 2 * * *"},
            {"name": "hourly_sync", "schedule": "0 * * * *"}
        ]
    }
```

### Job with External API

```python
@job("sync_github_repos", schedule="0 6 * * *")
def sync_github_repos_job(ctx: PluginContext):
    """Sync GitHub repositories daily"""
    try:
        # Get GitHub token
        github_token = ctx.secrets.get("GITHUB_TOKEN")
        if not github_token:
            return {"status": "error", "error": "Missing GitHub token"}
        
        # Fetch repositories
        headers = {"Authorization": f"token {github_token}"}
        response = ctx.http.get("https://api.github.com/user/repos", headers=headers)
        
        if response.get('status_code') != 200:
            return {"status": "error", "error": "GitHub API request failed"}
        
        repos = response.get('json', [])
        
        # Process repositories
        for repo in repos:
            process_repository(repo)
        
        return {
            "status": "success",
            "repos_synced": len(repos)
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
```
