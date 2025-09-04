"""
AI reports service for CRM/Ops Template
"""
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.ai.models import AIReport
from src.ai.schemas import ReportRequest, ReportResponse, ReportTemplate, REPORT_TEMPLATES
from src.llm.orchestration import LLMOrchestration
import boto3
from jinja2 import Template

logger = logging.getLogger(__name__)

class ReportsService:
    """Service for AI report generation"""
    
    def __init__(self):
        self.llm_orchestration = LLMOrchestration()
        self.s3_client = boto3.client('s3') if os.getenv('AWS_ACCESS_KEY_ID') else None
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'sbh-reports')
    
    def run_report(self, request: ReportRequest) -> ReportResponse:
        """Run a report on-demand"""
        try:
            # Validate report type
            if request.type not in REPORT_TEMPLATES:
                raise ValueError(f"Invalid report type: {request.type}")
            
            # Create report record
            with db_session() as session:
                report = AIReport(
                    tenant_id=request.tenant_id,
                    type=request.type,
                    name=request.name,
                    params=request.params,
                    status='running',
                    created_by=request.user_id
                )
                
                session.add(report)
                session.commit()
                report_id = str(report.id)
            
            # Generate report content
            report_content = self._generate_report_content(request)
            
            # Convert to PDF (or HTML if PDF generation fails)
            file_content, file_type = self._convert_to_pdf(report_content, request.type)
            
            # Upload to S3
            file_key = f"reports/{request.tenant_id}/{report_id}.{file_type}"
            file_url = self._upload_to_s3(file_content, file_key, file_type)
            
            # Update report record
            with db_session() as session:
                report = session.query(AIReport).filter(AIReport.id == report_id).first()
                if report:
                    report.status = 'success'
                    report.file_key = file_key
                    report.file_url = file_url
                    session.commit()
            
            return ReportResponse(
                report_id=report_id,
                status='success',
                file_url=file_url,
                scheduled=False
            )
            
        except Exception as e:
            logger.error(f"Error running report: {e}")
            
            # Update report status to failed
            with db_session() as session:
                report = session.query(AIReport).filter(AIReport.id == report_id).first()
                if report:
                    report.status = 'failed'
                    report.error_message = str(e)
                    session.commit()
            
            raise
    
    def schedule_report(self, request: ReportRequest) -> ReportResponse:
        """Schedule a recurring report"""
        try:
            # Validate report type
            if request.type not in REPORT_TEMPLATES:
                raise ValueError(f"Invalid report type: {request.type}")
            
            # Validate cron expression
            if not request.scheduled_cron:
                raise ValueError("Cron expression is required for scheduled reports")
            
            # Create report record
            with db_session() as session:
                report = AIReport(
                    tenant_id=request.tenant_id,
                    type=request.type,
                    name=request.name,
                    params=request.params,
                    status='scheduled',
                    scheduled_cron=request.scheduled_cron,
                    created_by=request.user_id
                )
                
                session.add(report)
                session.commit()
                report_id = str(report.id)
            
            # Schedule the report job
            self._schedule_report_job(report_id, request.scheduled_cron)
            
            return ReportResponse(
                report_id=report_id,
                status='scheduled',
                scheduled=True,
                next_run_at=self._get_next_run_time(request.scheduled_cron)
            )
            
        except Exception as e:
            logger.error(f"Error scheduling report: {e}")
            raise
    
    def get_report_history(self, tenant_id: str, report_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get report history"""
        with db_session() as session:
            query = session.query(AIReport).filter(AIReport.tenant_id == tenant_id)
            
            if report_type:
                query = query.filter(AIReport.type == report_type)
            
            reports = query.order_by(AIReport.created_at.desc()).limit(limit).all()
            
            return [report.to_dict() for report in reports]
    
    def _generate_report_content(self, request: ReportRequest) -> str:
        """Generate report content using template"""
        template_info = REPORT_TEMPLATES[request.type]
        
        # Get report data
        report_data = self._get_report_data(request.type, request.params, request.tenant_id)
        
        # Load template
        template_path = template_info['template_path']
        template_content = self._load_template(template_path)
        
        # Render template
        template = Template(template_content)
        html_content = template.render(
            data=report_data,
            params=request.params,
            generated_at=datetime.utcnow(),
            tenant_id=request.tenant_id
        )
        
        return html_content
    
    def _get_report_data(self, report_type: str, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Get data for report"""
        with db_session() as session:
            if report_type == 'weekly_sales':
                return self._get_weekly_sales_data(session, params, tenant_id)
            elif report_type == 'pipeline_forecast':
                return self._get_pipeline_forecast_data(session, params, tenant_id)
            elif report_type == 'ops_throughput':
                return self._get_ops_throughput_data(session, params, tenant_id)
            elif report_type == 'activity_sla':
                return self._get_activity_sla_data(session, params, tenant_id)
            else:
                return {}
    
    def _get_weekly_sales_data(self, session: Session, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Get weekly sales data"""
        start_date = params.get('start_date', datetime.utcnow() - timedelta(days=7))
        end_date = params.get('end_date', datetime.utcnow())
        
        # Get deals data
        deals = session.query(Deal).filter(
            Deal.tenant_id == tenant_id,
            Deal.created_at >= start_date,
            Deal.created_at <= end_date
        ).all()
        
        # Get contacts data
        contacts = session.query(Contact).filter(
            Contact.tenant_id == tenant_id,
            Contact.created_at >= start_date,
            Contact.created_at <= end_date
        ).all()
        
        # Calculate metrics
        total_deals = len(deals)
        total_value = sum(deal.value or 0 for deal in deals)
        won_deals = [deal for deal in deals if deal.status == 'won']
        won_value = sum(deal.value or 0 for deal in won_deals)
        win_rate = (len(won_deals) / total_deals * 100) if total_deals > 0 else 0
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'metrics': {
                'total_deals': total_deals,
                'total_value': total_value,
                'won_deals': len(won_deals),
                'won_value': won_value,
                'win_rate': win_rate,
                'new_contacts': len(contacts)
            },
            'deals_by_stage': self._group_deals_by_stage(deals),
            'deals_by_owner': self._group_deals_by_owner(deals)
        }
    
    def _get_pipeline_forecast_data(self, session: Session, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Get pipeline forecast data"""
        forecast_period = params.get('forecast_period', '90d')
        days = int(forecast_period.replace('d', ''))
        
        # Get open deals
        open_deals = session.query(Deal).filter(
            Deal.tenant_id == tenant_id,
            Deal.status == 'open'
        ).all()
        
        # Calculate forecast
        total_pipeline_value = sum(deal.value or 0 for deal in open_deals)
        weighted_forecast = sum((deal.value or 0) * (deal.probability or 0.5) for deal in open_deals)
        
        return {
            'forecast_period': forecast_period,
            'metrics': {
                'total_pipeline_value': total_pipeline_value,
                'weighted_forecast': weighted_forecast,
                'deal_count': len(open_deals)
            },
            'deals_by_stage': self._group_deals_by_stage(open_deals),
            'deals_by_probability': self._group_deals_by_probability(open_deals)
        }
    
    def _get_ops_throughput_data(self, session: Session, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Get operations throughput data"""
        time_period = params.get('time_period', 'month')
        team_members = params.get('team_members', [])
        
        # Calculate time range
        if time_period == 'week':
            start_date = datetime.utcnow() - timedelta(days=7)
        elif time_period == 'month':
            start_date = datetime.utcnow() - timedelta(days=30)
        else:  # quarter
            start_date = datetime.utcnow() - timedelta(days=90)
        
        # Get tasks data
        tasks_query = session.query(Task).filter(
            Task.tenant_id == tenant_id,
            Task.created_at >= start_date
        )
        
        if team_members:
            tasks_query = tasks_query.filter(Task.assignee_id.in_(team_members))
        
        tasks = tasks_query.all()
        
        # Calculate metrics
        total_tasks = len(tasks)
        completed_tasks = len([task for task in tasks if task.status == 'done'])
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            'time_period': time_period,
            'metrics': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'completion_rate': completion_rate
            },
            'tasks_by_status': self._group_tasks_by_status(tasks),
            'tasks_by_assignee': self._group_tasks_by_assignee(tasks)
        }
    
    def _get_activity_sla_data(self, session: Session, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Get activity SLA data"""
        sla_type = params.get('sla_type', 'response_time')
        date_range = params.get('date_range', {})
        
        start_date = date_range.get('start', datetime.utcnow() - timedelta(days=30))
        end_date = date_range.get('end', datetime.utcnow())
        
        # Get activities data
        activities = session.query(Activity).filter(
            Activity.tenant_id == tenant_id,
            Activity.created_at >= start_date,
            Activity.created_at <= end_date,
            Activity.completed_at.isnot(None)
        ).all()
        
        # Calculate SLA metrics
        total_activities = len(activities)
        sla_compliant = 0
        
        for activity in activities:
            duration = (activity.completed_at - activity.created_at).total_seconds()
            if sla_type == 'response_time':
                # Assume 24-hour response SLA
                if duration <= 86400:  # 24 hours in seconds
                    sla_compliant += 1
            else:  # resolution_time
                # Assume 7-day resolution SLA
                if duration <= 604800:  # 7 days in seconds
                    sla_compliant += 1
        
        sla_compliance_rate = (sla_compliant / total_activities * 100) if total_activities > 0 else 0
        
        return {
            'sla_type': sla_type,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'metrics': {
                'total_activities': total_activities,
                'sla_compliant': sla_compliant,
                'sla_compliance_rate': sla_compliance_rate
            },
            'activities_by_type': self._group_activities_by_type(activities)
        }
    
    def _group_deals_by_stage(self, deals: List[Deal]) -> Dict[str, Any]:
        """Group deals by pipeline stage"""
        stages = {}
        for deal in deals:
            stage = deal.pipeline_stage or 'unknown'
            if stage not in stages:
                stages[stage] = {'count': 0, 'value': 0}
            stages[stage]['count'] += 1
            stages[stage]['value'] += deal.value or 0
        return stages
    
    def _group_deals_by_owner(self, deals: List[Deal]) -> Dict[str, Any]:
        """Group deals by owner"""
        owners = {}
        for deal in deals:
            owner = deal.owner_id or 'unassigned'
            if owner not in owners:
                owners[owner] = {'count': 0, 'value': 0}
            owners[owner]['count'] += 1
            owners[owner]['value'] += deal.value or 0
        return owners
    
    def _group_deals_by_probability(self, deals: List[Deal]) -> Dict[str, Any]:
        """Group deals by probability"""
        probabilities = {}
        for deal in deals:
            prob = deal.probability or 0.5
            prob_range = f"{int(prob * 100)}-{int(prob * 100) + 9}%"
            if prob_range not in probabilities:
                probabilities[prob_range] = {'count': 0, 'value': 0}
            probabilities[prob_range]['count'] += 1
            probabilities[prob_range]['value'] += deal.value or 0
        return probabilities
    
    def _group_tasks_by_status(self, tasks: List[Task]) -> Dict[str, int]:
        """Group tasks by status"""
        statuses = {}
        for task in tasks:
            status = task.status or 'unknown'
            statuses[status] = statuses.get(status, 0) + 1
        return statuses
    
    def _group_tasks_by_assignee(self, tasks: List[Task]) -> Dict[str, int]:
        """Group tasks by assignee"""
        assignees = {}
        for task in tasks:
            assignee = task.assignee_id or 'unassigned'
            assignee = assignee or 'unassigned'
            assignees[assignee] = assignees.get(assignee, 0) + 1
        return assignees
    
    def _group_activities_by_type(self, activities: List[Activity]) -> Dict[str, int]:
        """Group activities by type"""
        types = {}
        for activity in activities:
            activity_type = activity.type or 'unknown'
            types[activity_type] = types.get(activity_type, 0) + 1
        return types
    
    def _load_template(self, template_path: str) -> str:
        """Load template content"""
        # In production, this would load from a template directory
        # For now, return a basic HTML template
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{{ data.title or 'Report' }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .metrics { display: flex; justify-content: space-around; margin-bottom: 30px; }
        .metric { text-align: center; }
        .metric-value { font-size: 24px; font-weight: bold; }
        .metric-label { color: #666; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ data.title or 'Report' }}</h1>
        <p>Generated on {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
    </div>
    
    <div class="metrics">
        {% for key, value in data.metrics.items() %}
        <div class="metric">
            <div class="metric-value">{{ value }}</div>
            <div class="metric-label">{{ key.replace('_', ' ').title() }}</div>
        </div>
        {% endfor %}
    </div>
    
    {% if data.deals_by_stage %}
    <h2>Deals by Stage</h2>
    <table>
        <tr><th>Stage</th><th>Count</th><th>Value</th></tr>
        {% for stage, info in data.deals_by_stage.items() %}
        <tr><td>{{ stage }}</td><td>{{ info.count }}</td><td>${{ "{:,.0f}".format(info.value) }}</td></tr>
        {% endfor %}
    </table>
    {% endif %}
</body>
</html>
"""
    
    def _convert_to_pdf(self, html_content: str, report_type: str) -> tuple:
        """Convert HTML to PDF"""
        try:
            # Try to use WeasyPrint
            from weasyprint import HTML
            pdf_content = HTML(string=html_content).write_pdf()
            return pdf_content, 'pdf'
        except ImportError:
            try:
                # Try to use wkhtmltopdf
                import subprocess
                import tempfile
                
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
                    f.write(html_content.encode('utf-8'))
                    html_file = f.name
                
                pdf_file = html_file.replace('.html', '.pdf')
                subprocess.run(['wkhtmltopdf', html_file, pdf_file], check=True)
                
                with open(pdf_file, 'rb') as f:
                    pdf_content = f.read()
                
                # Clean up
                os.unlink(html_file)
                os.unlink(pdf_file)
                
                return pdf_content, 'pdf'
            except Exception as e:
                logger.warning(f"PDF conversion failed: {e}, falling back to HTML")
                return html_content.encode('utf-8'), 'html'
    
    def _upload_to_s3(self, content: bytes, file_key: str, file_type: str) -> str:
        """Upload file to S3"""
        if not self.s3_client:
            # Return a placeholder URL if S3 is not configured
            return f"https://example.com/reports/{file_key}"
        
        try:
            content_type = 'application/pdf' if file_type == 'pdf' else 'text/html'
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=content,
                ContentType=content_type
            )
            
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=3600  # 1 hour
            )
            
            return url
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            return f"https://example.com/reports/{file_key}"
    
    def _schedule_report_job(self, report_id: str, cron_expression: str):
        """Schedule report job"""
        # This would use Redis/RQ to schedule the job
        # For now, just log the scheduling
        logger.info(f"Scheduling report {report_id} with cron: {cron_expression}")
    
    def _get_next_run_time(self, cron_expression: str) -> datetime:
        """Get next run time from cron expression"""
        # This would parse the cron expression and calculate next run time
        # For now, return a placeholder
        return datetime.utcnow() + timedelta(days=1)
