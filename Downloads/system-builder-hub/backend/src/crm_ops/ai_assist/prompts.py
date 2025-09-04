"""
Prompt templates for AI Assist
"""
from typing import Dict, Any

class PromptTemplates:
    """Prompt templates for AI Assist functionality"""
    
    def get_summary_prompt(self, entity_type: str, entity_data: Dict[str, Any]) -> str:
        """Get summary prompt for entity"""
        if entity_type == 'contact':
            return self._get_contact_summary_prompt(entity_data)
        elif entity_type == 'deal':
            return self._get_deal_summary_prompt(entity_data)
        elif entity_type == 'task':
            return self._get_task_summary_prompt(entity_data)
        else:
            return self._get_generic_summary_prompt(entity_type, entity_data)
    
    def get_email_draft_prompt(self, contact_data: Dict[str, Any], goal: str) -> str:
        """Get email draft prompt"""
        return f"""
You are a professional business communication assistant. Draft a follow-up email for the following contact:

Contact Information:
- Name: {contact_data.get('name', 'Unknown')}
- Email: {contact_data.get('email', 'Unknown')}
- Company: {contact_data.get('company', 'Unknown')}
- Tags: {', '.join(contact_data.get('tags', []))}

Goal: {goal}

Please draft a professional, friendly email that:
1. Is personalized to the contact
2. Achieves the stated goal
3. Is concise and actionable
4. Maintains a professional tone
5. Includes a clear call-to-action

Format the response as a complete email with subject line and body.
"""
    
    def get_nba_prompt(self, entity_type: str, entity_data: Dict[str, Any]) -> str:
        """Get next best actions prompt"""
        if entity_type == 'contact':
            return self._get_contact_nba_prompt(entity_data)
        elif entity_type == 'deal':
            return self._get_deal_nba_prompt(entity_data)
        else:
            return self._get_generic_nba_prompt(entity_type, entity_data)
    
    def _get_contact_summary_prompt(self, contact_data: Dict[str, Any]) -> str:
        """Get contact summary prompt"""
        return f"""
Please provide a concise summary of this contact:

Contact: {contact_data.get('name', 'Unknown')}
Email: {contact_data.get('email', 'Unknown')}
Company: {contact_data.get('company', 'Unknown')}
Phone: {contact_data.get('phone', 'Unknown')}
Tags: {', '.join(contact_data.get('tags', []))}
Created: {contact_data.get('created_at', 'Unknown')}

Custom Fields: {contact_data.get('custom_fields', {})}

Please provide:
1. A brief overview of the contact
2. Key information and context
3. Any notable details or patterns
4. Suggested next steps

Keep the summary professional and actionable.
"""
    
    def _get_deal_summary_prompt(self, deal_data: Dict[str, Any]) -> str:
        """Get deal summary prompt"""
        return f"""
Please provide a concise summary of this deal:

Deal: {deal_data.get('title', 'Unknown')}
Value: ${deal_data.get('value', 0):,}
Stage: {deal_data.get('pipeline_stage', 'Unknown')}
Status: {deal_data.get('status', 'Unknown')}
Expected Close: {deal_data.get('expected_close_date', 'Unknown')}
Notes: {deal_data.get('notes', 'None')}

Please provide:
1. A brief overview of the deal
2. Current status and progress
3. Key risks and opportunities
4. Recommended next steps
5. Timeline considerations

Keep the summary professional and actionable.
"""
    
    def _get_task_summary_prompt(self, task_data: Dict[str, Any]) -> str:
        """Get task summary prompt"""
        return f"""
Please provide a concise summary of this task:

Task: {task_data.get('title', 'Unknown')}
Status: {task_data.get('status', 'Unknown')}
Priority: {task_data.get('priority', 'Unknown')}
Due Date: {task_data.get('due_date', 'Unknown')}
Description: {task_data.get('description', 'None')}

Please provide:
1. A brief overview of the task
2. Current status and progress
3. Priority and urgency assessment
4. Dependencies or blockers
5. Recommended next steps

Keep the summary professional and actionable.
"""
    
    def _get_generic_summary_prompt(self, entity_type: str, entity_data: Dict[str, Any]) -> str:
        """Get generic summary prompt"""
        return f"""
Please provide a concise summary of this {entity_type}:

Entity Data: {entity_data}

Please provide:
1. A brief overview of the {entity_type}
2. Key information and context
3. Any notable details or patterns
4. Suggested next steps

Keep the summary professional and actionable.
"""
    
    def _get_contact_nba_prompt(self, contact_data: Dict[str, Any]) -> str:
        """Get contact next best actions prompt"""
        return f"""
Based on this contact information, suggest the next best actions:

Contact: {contact_data.get('name', 'Unknown')}
Email: {contact_data.get('email', 'Unknown')}
Company: {contact_data.get('company', 'Unknown')}
Tags: {', '.join(contact_data.get('tags', []))}
Created: {contact_data.get('created_at', 'Unknown')}

Please suggest 3-5 specific, actionable next steps such as:
1. Schedule a follow-up call
2. Send a personalized email
3. Create a task for research
4. Update deal status
5. Schedule a meeting

For each action, provide:
- Action type (create_task, send_email, schedule_activity, update_deal)
- Title/Subject
- Description
- Priority (low, medium, high)
- Due date (if applicable)

Format as JSON array of action objects.
"""
    
    def _get_deal_nba_prompt(self, deal_data: Dict[str, Any]) -> str:
        """Get deal next best actions prompt"""
        return f"""
Based on this deal information, suggest the next best actions:

Deal: {deal_data.get('title', 'Unknown')}
Value: ${deal_data.get('value', 0):,}
Stage: {deal_data.get('pipeline_stage', 'Unknown')}
Status: {deal_data.get('status', 'Unknown')}
Expected Close: {deal_data.get('expected_close_date', 'Unknown')}

Please suggest 3-5 specific, actionable next steps such as:
1. Schedule a proposal meeting
2. Send follow-up materials
3. Create a task for contract review
4. Update deal stage
5. Schedule a demo

For each action, provide:
- Action type (create_task, send_email, schedule_activity, update_deal)
- Title/Subject
- Description
- Priority (low, medium, high)
- Due date (if applicable)

Format as JSON array of action objects.
"""
    
    def _get_generic_nba_prompt(self, entity_type: str, entity_data: Dict[str, Any]) -> str:
        """Get generic next best actions prompt"""
        return f"""
Based on this {entity_type} information, suggest the next best actions:

Entity Data: {entity_data}

Please suggest 3-5 specific, actionable next steps.

For each action, provide:
- Action type (create_task, send_email, schedule_activity, update_deal)
- Title/Subject
- Description
- Priority (low, medium, high)
- Due date (if applicable)

Format as JSON array of action objects.
"""
