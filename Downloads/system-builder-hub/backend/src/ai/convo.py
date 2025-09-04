"""
Conversational analytics service for CRM/Ops Template
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from src.database import db_session
from src.ai.schemas import AnalyticsQuery, AnalyticsResponse, AnalyticsChart
from src.ai.models import Contact, Deal, Task, Project, Activity
from src.llm.orchestration import LLMOrchestration

logger = logging.getLogger(__name__)

class ConversationalAnalyticsService:
    """Service for conversational analytics"""
    
    def __init__(self):
        self.llm_orchestration = LLMOrchestration()
    
    def query_analytics(self, query: AnalyticsQuery) -> AnalyticsResponse:
        """Process conversational analytics query"""
        try:
            # Parse query intent
            intent = self._parse_query_intent(query.question)
            
            # Execute analytics based on intent
            if intent['type'] == 'pipeline_metrics':
                return self._get_pipeline_metrics(query, intent)
            elif intent['type'] == 'win_rate_analysis':
                return self._get_win_rate_analysis(query, intent)
            elif intent['type'] == 'contact_growth':
                return self._get_contact_growth(query, intent)
            elif intent['type'] == 'task_throughput':
                return self._get_task_throughput(query, intent)
            elif intent['type'] == 'activity_sla':
                return self._get_activity_sla(query, intent)
            elif intent['type'] == 'custom_query':
                return self._execute_custom_query(query, intent)
            else:
                return self._get_general_analytics(query, intent)
                
        except Exception as e:
            logger.error(f"Error in conversational analytics: {e}")
            raise
    
    def _parse_query_intent(self, question: str) -> Dict[str, Any]:
        """Parse query intent using LLM"""
        prompt = f"""Analyze this analytics question and extract the intent:

Question: "{question}"

Return a JSON object with:
- type: The type of analysis needed (pipeline_metrics, win_rate_analysis, contact_growth, task_throughput, activity_sla, custom_query)
- metrics: List of specific metrics to calculate
- time_range: Time range for the analysis
- filters: Any filters to apply
- drill_down: Whether to enable drill-down capabilities

Examples:
- "What's this week's forecast?" → {{"type": "pipeline_metrics", "metrics": ["forecast"], "time_range": "week"}}
- "Show me win rates by stage" → {{"type": "win_rate_analysis", "metrics": ["win_rate"], "drill_down": true}}
- "How many contacts did we add this month?" → {{"type": "contact_growth", "metrics": ["contact_count"], "time_range": "month"}}

Intent:"""

        response = self.llm_orchestration.generate(prompt)
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            
            intent = json.loads(json_str)
            return intent
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            # Fallback to general analytics
            return {
                'type': 'custom_query',
                'metrics': ['general'],
                'time_range': 'month'
            }
    
    def _get_pipeline_metrics(self, query: AnalyticsQuery, intent: Dict[str, Any]) -> AnalyticsResponse:
        """Get pipeline metrics"""
        with db_session() as session:
            # Get time range
            time_range = self._get_time_range(intent.get('time_range', 'month'))
            
            # Get pipeline data
            pipeline_data = session.query(
                Deal.pipeline_stage,
                func.count(Deal.id).label('count'),
                func.sum(Deal.value).label('total_value')
            ).filter(
                Deal.tenant_id == query.tenant_id,
                Deal.created_at >= time_range['start'],
                Deal.created_at <= time_range['end']
            ).group_by(Deal.pipeline_stage).all()
            
            # Build charts
            charts = []
            
            # Pipeline stage chart
            stage_data = [{'stage': item.pipeline_stage, 'count': item.count, 'value': item.total_value} for item in pipeline_data]
            charts.append(AnalyticsChart(
                type='bar',
                title='Pipeline by Stage',
                data=stage_data,
                config={'x': 'stage', 'y': 'count'}
            ))
            
            # Value chart
            charts.append(AnalyticsChart(
                type='pie',
                title='Pipeline Value by Stage',
                data=stage_data,
                config={'nameKey': 'stage', 'dataKey': 'value'}
            ))
            
            # Generate summary
            total_deals = sum(item.count for item in pipeline_data)
            total_value = sum(item.total_value or 0 for item in pipeline_data)
            
            summary = f"Pipeline Overview ({time_range['label']}):\n"
            summary += f"• Total Deals: {total_deals}\n"
            summary += f"• Total Value: ${total_value:,.0f}\n"
            summary += f"• Average Deal Size: ${total_value/total_deals:,.0f}" if total_deals > 0 else "• Average Deal Size: $0"
            
            return AnalyticsResponse(
                summary=summary,
                charts=[chart.__dict__ for chart in charts],
                tables=[{
                    'columns': ['Stage', 'Count', 'Total Value'],
                    'rows': [[item.pipeline_stage, item.count, f"${item.total_value:,.0f}"] for item in pipeline_data]
                }]
            )
    
    def _get_win_rate_analysis(self, query: AnalyticsQuery, intent: Dict[str, Any]) -> AnalyticsResponse:
        """Get win rate analysis"""
        with db_session() as session:
            # Get time range
            time_range = self._get_time_range(intent.get('time_range', 'quarter'))
            
            # Get win/loss data
            win_loss_data = session.query(
                Deal.status,
                func.count(Deal.id).label('count'),
                func.sum(Deal.value).label('total_value')
            ).filter(
                Deal.tenant_id == query.tenant_id,
                Deal.created_at >= time_range['start'],
                Deal.created_at <= time_range['end'],
                Deal.status.in_(['won', 'lost'])
            ).group_by(Deal.status).all()
            
            # Calculate win rate
            total_deals = sum(item.count for item in win_loss_data)
            won_deals = sum(item.count for item in win_loss_data if item.status == 'won')
            win_rate = (won_deals / total_deals * 100) if total_deals > 0 else 0
            
            # Build charts
            charts = []
            
            # Win/Loss chart
            win_loss_chart_data = [{'status': item.status, 'count': item.count, 'value': item.total_value} for item in win_loss_data]
            charts.append(AnalyticsChart(
                type='pie',
                title='Win/Loss Distribution',
                data=win_loss_chart_data,
                config={'nameKey': 'status', 'dataKey': 'count'}
            ))
            
            # Win rate trend (would need historical data)
            charts.append(AnalyticsChart(
                type='line',
                title='Win Rate Trend',
                data=[{'period': 'Current', 'win_rate': win_rate}],
                config={'x': 'period', 'y': 'win_rate'}
            ))
            
            # Generate summary
            summary = f"Win Rate Analysis ({time_range['label']}):\n"
            summary += f"• Total Deals: {total_deals}\n"
            summary += f"• Won Deals: {won_deals}\n"
            summary += f"• Win Rate: {win_rate:.1f}%\n"
            summary += f"• Total Value Won: ${sum(item.total_value or 0 for item in win_loss_data if item.status == 'won'):,.0f}"
            
            return AnalyticsResponse(
                summary=summary,
                charts=[chart.__dict__ for chart in charts],
                tables=[{
                    'columns': ['Status', 'Count', 'Total Value'],
                    'rows': [[item.status, item.count, f"${item.total_value:,.0f}"] for item in win_loss_data]
                }]
            )
    
    def _get_contact_growth(self, query: AnalyticsQuery, intent: Dict[str, Any]) -> AnalyticsResponse:
        """Get contact growth metrics"""
        with db_session() as session:
            # Get time range
            time_range = self._get_time_range(intent.get('time_range', 'month'))
            
            # Get contact growth data
            contact_data = session.query(
                func.date_trunc('week', Contact.created_at).label('week'),
                func.count(Contact.id).label('count')
            ).filter(
                Contact.tenant_id == query.tenant_id,
                Contact.created_at >= time_range['start'],
                Contact.created_at <= time_range['end']
            ).group_by(func.date_trunc('week', Contact.created_at)).order_by('week').all()
            
            # Build charts
            charts = []
            
            # Contact growth chart
            growth_data = [{'week': item.week.strftime('%Y-%m-%d'), 'count': item.count} for item in contact_data]
            charts.append(AnalyticsChart(
                type='line',
                title='Contact Growth',
                data=growth_data,
                config={'x': 'week', 'y': 'count'}
            ))
            
            # Generate summary
            total_contacts = sum(item.count for item in contact_data)
            avg_per_week = total_contacts / len(contact_data) if contact_data else 0
            
            summary = f"Contact Growth ({time_range['label']}):\n"
            summary += f"• Total New Contacts: {total_contacts}\n"
            summary += f"• Average per Week: {avg_per_week:.1f}\n"
            summary += f"• Growth Trend: {'Increasing' if len(contact_data) > 1 and contact_data[-1].count > contact_data[0].count else 'Stable'}"
            
            return AnalyticsResponse(
                summary=summary,
                charts=[chart.__dict__ for chart in charts],
                tables=[{
                    'columns': ['Week', 'New Contacts'],
                    'rows': [[item.week.strftime('%Y-%m-%d'), item.count] for item in contact_data]
                }]
            )
    
    def _get_task_throughput(self, query: AnalyticsQuery, intent: Dict[str, Any]) -> AnalyticsResponse:
        """Get task throughput metrics"""
        with db_session() as session:
            # Get time range
            time_range = self._get_time_range(intent.get('time_range', 'month'))
            
            # Get task data
            task_data = session.query(
                Task.status,
                func.count(Task.id).label('count')
            ).filter(
                Task.tenant_id == query.tenant_id,
                Task.created_at >= time_range['start'],
                Task.created_at <= time_range['end']
            ).group_by(Task.status).all()
            
            # Get completion rate
            total_tasks = sum(item.count for item in task_data)
            completed_tasks = sum(item.count for item in task_data if item.status == 'done')
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Build charts
            charts = []
            
            # Task status chart
            status_data = [{'status': item.status, 'count': item.count} for item in task_data]
            charts.append(AnalyticsChart(
                type='bar',
                title='Tasks by Status',
                data=status_data,
                config={'x': 'status', 'y': 'count'}
            ))
            
            # Completion rate chart
            charts.append(AnalyticsChart(
                type='pie',
                title='Task Completion Rate',
                data=[{'status': 'Completed', 'count': completed_tasks}, {'status': 'Pending', 'count': total_tasks - completed_tasks}],
                config={'nameKey': 'status', 'dataKey': 'count'}
            ))
            
            # Generate summary
            summary = f"Task Throughput ({time_range['label']}):\n"
            summary += f"• Total Tasks: {total_tasks}\n"
            summary += f"• Completed Tasks: {completed_tasks}\n"
            summary += f"• Completion Rate: {completion_rate:.1f}%\n"
            summary += f"• Pending Tasks: {total_tasks - completed_tasks}"
            
            return AnalyticsResponse(
                summary=summary,
                charts=[chart.__dict__ for chart in charts],
                tables=[{
                    'columns': ['Status', 'Count'],
                    'rows': [[item.status, item.count] for item in task_data]
                }]
            )
    
    def _get_activity_sla(self, query: AnalyticsQuery, intent: Dict[str, Any]) -> AnalyticsResponse:
        """Get activity SLA metrics"""
        with db_session() as session:
            # Get time range
            time_range = self._get_time_range(intent.get('time_range', 'month'))
            
            # Get activity data
            activity_data = session.query(
                Activity.type,
                func.count(Activity.id).label('count'),
                func.avg(func.extract('epoch', Activity.completed_at - Activity.created_at)).label('avg_duration')
            ).filter(
                Activity.tenant_id == query.tenant_id,
                Activity.created_at >= time_range['start'],
                Activity.created_at <= time_range['end'],
                Activity.completed_at.isnot(None)
            ).group_by(Activity.type).all()
            
            # Build charts
            charts = []
            
            # Activity type chart
            type_data = [{'type': item.type, 'count': item.count, 'avg_duration': item.avg_duration or 0} for item in activity_data]
            charts.append(AnalyticsChart(
                type='bar',
                title='Activities by Type',
                data=type_data,
                config={'x': 'type', 'y': 'count'}
            ))
            
            # Average duration chart
            charts.append(AnalyticsChart(
                type='bar',
                title='Average Duration by Activity Type',
                data=type_data,
                config={'x': 'type', 'y': 'avg_duration'}
            ))
            
            # Generate summary
            total_activities = sum(item.count for item in activity_data)
            avg_duration = sum(item.avg_duration or 0 for item in activity_data) / len(activity_data) if activity_data else 0
            
            summary = f"Activity SLA Analysis ({time_range['label']}):\n"
            summary += f"• Total Activities: {total_activities}\n"
            summary += f"• Average Duration: {avg_duration/3600:.1f} hours\n"
            summary += f"• Activity Types: {len(activity_data)}"
            
            return AnalyticsResponse(
                summary=summary,
                charts=[chart.__dict__ for chart in charts],
                tables=[{
                    'columns': ['Type', 'Count', 'Avg Duration (hours)'],
                    'rows': [[item.type, item.count, f"{(item.avg_duration or 0)/3600:.1f}"] for item in activity_data]
                }]
            )
    
    def _execute_custom_query(self, query: AnalyticsQuery, intent: Dict[str, Any]) -> AnalyticsResponse:
        """Execute custom analytics query"""
        # This would use a more sophisticated query builder
        # For now, return a general response
        
        summary = f"Custom Analytics Query:\n"
        summary += f"• Question: {query.question}\n"
        summary += f"• Intent: {intent.get('type', 'unknown')}\n"
        summary += f"• Time Range: {intent.get('time_range', 'month')}"
        
        return AnalyticsResponse(
            summary=summary,
            charts=[],
            tables=[]
        )
    
    def _get_general_analytics(self, query: AnalyticsQuery, intent: Dict[str, Any]) -> AnalyticsResponse:
        """Get general analytics overview"""
        with db_session() as session:
            # Get basic metrics
            contact_count = session.query(Contact).filter(Contact.tenant_id == query.tenant_id).count()
            deal_count = session.query(Deal).filter(Deal.tenant_id == query.tenant_id).count()
            task_count = session.query(Task).filter(Task.tenant_id == query.tenant_id).count()
            project_count = session.query(Project).filter(Project.tenant_id == query.tenant_id).count()
            
            summary = f"General Analytics Overview:\n"
            summary += f"• Total Contacts: {contact_count}\n"
            summary += f"• Total Deals: {deal_count}\n"
            summary += f"• Total Tasks: {task_count}\n"
            summary += f"• Total Projects: {project_count}"
            
            # Create overview chart
            overview_data = [
                {'metric': 'Contacts', 'count': contact_count},
                {'metric': 'Deals', 'count': deal_count},
                {'metric': 'Tasks', 'count': task_count},
                {'metric': 'Projects', 'count': project_count}
            ]
            
            charts = [AnalyticsChart(
                type='bar',
                title='Overview',
                data=overview_data,
                config={'x': 'metric', 'y': 'count'}
            )]
            
            return AnalyticsResponse(
                summary=summary,
                charts=[chart.__dict__ for chart in charts],
                tables=[{
                    'columns': ['Metric', 'Count'],
                    'rows': [[item['metric'], item['count']] for item in overview_data]
                }]
            )
    
    def _get_time_range(self, time_range: str) -> Dict[str, Any]:
        """Get time range for analytics"""
        now = datetime.utcnow()
        
        ranges = {
            'week': {
                'start': now - timedelta(days=7),
                'end': now,
                'label': 'Last 7 days'
            },
            'month': {
                'start': now - timedelta(days=30),
                'end': now,
                'label': 'Last 30 days'
            },
            'quarter': {
                'start': now - timedelta(days=90),
                'end': now,
                'label': 'Last 90 days'
            },
            'year': {
                'start': now - timedelta(days=365),
                'end': now,
                'label': 'Last 365 days'
            }
        }
        
        return ranges.get(time_range, ranges['month'])
    
    def export_to_csv(self, query: AnalyticsQuery, data: Dict[str, Any]) -> str:
        """Export analytics data to CSV"""
        # This would generate a CSV file and return the URL
        # For now, return a placeholder
        return "https://example.com/analytics/export/123.csv"
