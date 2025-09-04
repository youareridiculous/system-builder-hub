"""
Lead Scoring AI Plugin
Uses AI to automatically score leads and add tags based on contact information
"""
import logging
import json
import re
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def extract_company_info(contact_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract company information from contact data"""
    company_info = {
        "name": contact_data.get('company', ''),
        "domain": '',
        "size": 'unknown',
        "industry": 'unknown'
    }
    
    # Extract domain from email
    email = contact_data.get('email', '')
    if email and '@' in email:
        company_info['domain'] = email.split('@')[1]
    
    # Try to extract company size from company name
    company_name = contact_data.get('company', '').lower()
    if any(word in company_name for word in ['inc', 'corp', 'llc', 'ltd']):
        company_info['size'] = 'enterprise'
    elif any(word in company_name for word in ['startup', 'small']):
        company_info['size'] = 'small'
    
    return company_info

def calculate_base_score(contact_data: Dict[str, Any]) -> int:
    """Calculate base score from contact data"""
    score = 0
    
    # Email completeness
    if contact_data.get('email'):
        score += 10
        if '@' in contact_data.get('email', ''):
            score += 5
    
    # Phone completeness
    if contact_data.get('phone'):
        score += 10
    
    # Company information
    if contact_data.get('company'):
        score += 15
    
    # Name completeness
    if contact_data.get('first_name') and contact_data.get('last_name'):
        score += 10
    
    # Job title
    if contact_data.get('job_title'):
        score += 10
    
    # LinkedIn profile
    if contact_data.get('linkedin_url'):
        score += 15
    
    # Tags
    tags = contact_data.get('tags', [])
    if 'hot_lead' in tags:
        score += 20
    if 'qualified' in tags:
        score += 15
    if 'decision_maker' in tags:
        score += 25
    
    return min(score, 100)  # Cap at 100

@hook("contact.created")
def score_new_contact(event_data: Dict[str, Any], ctx) -> None:
    """Score a new contact when created"""
    try:
        contact = event_data.get('contact', {})
        contact_id = contact.get('id')
        
        if not contact_id:
            logger.warning("No contact ID found in event data")
            return
        
        # Get full contact data
        contact_data = ctx.db.query(
            "SELECT * FROM contacts WHERE id = %s AND tenant_id = %s",
            [contact_id, ctx.tenant_id]
        )
        
        if not contact_data:
            logger.warning(f"Contact {contact_id} not found")
            return
        
        contact_info = contact_data[0]
        
        # Calculate base score
        base_score = calculate_base_score(contact_info)
        
        # Use AI to enhance scoring
        ai_score = await score_contact_with_ai(contact_info, ctx)
        
        # Combine scores (70% AI, 30% base)
        final_score = int((ai_score * 0.7) + (base_score * 0.3))
        
        # Determine tags based on score
        tags = determine_tags(final_score, contact_info)
        
        # Update contact with score and tags
        ctx.db.execute(
            "UPDATE contacts SET lead_score = %s, tags = %s, updated_at = %s WHERE id = %s",
            [final_score, json.dumps(tags), datetime.utcnow(), contact_id]
        )
        
        logger.info(f"Contact {contact_id} scored: {final_score}/100, tags: {tags}")
        
        # Track analytics
        ctx.analytics.track("lead_scored", {
            "contact_id": contact_id,
            "score": final_score,
            "tags": tags,
            "tenant_id": ctx.tenant_id
        })
        
        # Emit webhook if score is high
        if final_score >= 80:
            ctx.emit("lead.hot_lead", {
                "contact_id": contact_id,
                "score": final_score,
                "tags": tags
            })
        
    except Exception as e:
        logger.error(f"Error scoring contact {contact_id}: {e}")
        raise

async def score_contact_with_ai(contact_info: Dict[str, Any], ctx) -> int:
    """Use AI to score a contact"""
    try:
        # Get scoring prompt from secrets
        prompt_template = ctx.secrets.get("LEAD_SCORING_PROMPT", """
        Analyze this contact information and provide a lead score from 0-100.
        
        Contact Information:
        - Name: {first_name} {last_name}
        - Email: {email}
        - Company: {company}
        - Job Title: {job_title}
        - Phone: {phone}
        - LinkedIn: {linkedin_url}
        - Tags: {tags}
        
        Scoring Criteria:
        - Email quality and domain reputation
        - Company size and industry relevance
        - Job title seniority and decision-making power
        - Contact completeness and professional presence
        - Existing tags and lead indicators
        
        Return only a JSON object with:
        {{
            "score": <0-100>,
            "reasoning": "<brief explanation>",
            "suggested_tags": ["tag1", "tag2"]
        }}
        """)
        
        # Prepare contact data for AI
        contact_data = {
            "first_name": contact_info.get('first_name', ''),
            "last_name": contact_info.get('last_name', ''),
            "email": contact_info.get('email', ''),
            "company": contact_info.get('company', ''),
            "job_title": contact_info.get('job_title', ''),
            "phone": contact_info.get('phone', ''),
            "linkedin_url": contact_info.get('linkedin_url', ''),
            "tags": ', '.join(contact_info.get('tags', []))
        }
        
        # Format prompt
        prompt = prompt_template.format(**contact_data)
        
        # Call LLM
        response = await ctx.llm.run(prompt, {
            "max_tokens": 200,
            "temperature": 0.3
        })
        
        # Parse response
        try:
            result = json.loads(response)
            score = result.get('score', 50)
            return max(0, min(100, score))  # Ensure score is 0-100
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI response, using fallback score")
            return 50
        
    except Exception as e:
        logger.error(f"Error in AI scoring: {e}")
        return 50  # Fallback score

def determine_tags(score: int, contact_info: Dict[str, Any]) -> List[str]:
    """Determine tags based on score and contact information"""
    tags = []
    
    # Score-based tags
    if score >= 90:
        tags.extend(['hot_lead', 'priority'])
    elif score >= 75:
        tags.extend(['qualified', 'warm_lead'])
    elif score >= 50:
        tags.extend(['prospect', 'cold_lead'])
    else:
        tags.append('unqualified')
    
    # Company size tags
    company_name = contact_info.get('company', '').lower()
    if any(word in company_name for word in ['inc', 'corp', 'enterprise']):
        tags.append('enterprise')
    elif any(word in company_name for word in ['startup', 'small']):
        tags.append('startup')
    
    # Job title tags
    job_title = contact_info.get('job_title', '').lower()
    if any(word in job_title for word in ['ceo', 'cto', 'founder', 'president']):
        tags.append('decision_maker')
    elif any(word in job_title for word in ['manager', 'director', 'vp']):
        tags.append('influencer')
    
    # Industry tags (basic detection)
    company_name = contact_info.get('company', '').lower()
    if any(word in company_name for word in ['tech', 'software', 'saas']):
        tags.append('technology')
    elif any(word in company_name for word in ['finance', 'bank', 'insurance']):
        tags.append('financial')
    elif any(word in company_name for word in ['health', 'medical']):
        tags.append('healthcare')
    
    return list(set(tags))  # Remove duplicates

@hook("contact.updated")
def rescore_updated_contact(event_data: Dict[str, Any], ctx) -> None:
    """Re-score a contact when updated"""
    try:
        contact = event_data.get('contact', {})
        contact_id = contact.get('id')
        
        if not contact_id:
            return
        
        # Only re-score if important fields changed
        changed_fields = event_data.get('changed_fields', [])
        important_fields = ['email', 'company', 'job_title', 'phone', 'linkedin_url', 'tags']
        
        if any(field in changed_fields for field in important_fields):
            # Re-score the contact
            score_new_contact(event_data, ctx)
        
    except Exception as e:
        logger.error(f"Error re-scoring contact {contact_id}: {e}")
        raise

@route("/ping", methods=["GET"])
def ping(ctx) -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok", "plugin": "lead-scoring-ai", "timestamp": datetime.utcnow().isoformat()}

@route("/score", methods=["POST"])
def score_contact_manual(ctx) -> Dict[str, Any]:
    """Manually score a contact"""
    try:
        data = ctx.request.get_json()
        contact_id = data.get('contact_id')
        
        if not contact_id:
            return {"error": "contact_id is required"}
        
        # Get contact data
        contact_data = ctx.db.query(
            "SELECT * FROM contacts WHERE id = %s AND tenant_id = %s",
            [contact_id, ctx.tenant_id]
        )
        
        if not contact_data:
            return {"error": "Contact not found"}
        
        contact_info = contact_data[0]
        
        # Calculate score
        base_score = calculate_base_score(contact_info)
        ai_score = await score_contact_with_ai(contact_info, ctx)
        final_score = int((ai_score * 0.7) + (base_score * 0.3))
        tags = determine_tags(final_score, contact_info)
        
        # Update contact
        ctx.db.execute(
            "UPDATE contacts SET lead_score = %s, tags = %s, updated_at = %s WHERE id = %s",
            [final_score, json.dumps(tags), datetime.utcnow(), contact_id]
        )
        
        return {
            "success": True,
            "contact_id": contact_id,
            "score": final_score,
            "tags": tags
        }
        
    except Exception as e:
        return {"error": f"Error scoring contact: {str(e)}"}

@job("batch_lead_scoring")
def batch_score_leads(ctx) -> None:
    """Re-score all leads nightly"""
    try:
        # Get all contacts without scores or with old scores
        contacts = ctx.db.query(
            "SELECT id FROM contacts WHERE tenant_id = %s AND (lead_score IS NULL OR updated_at < %s)",
            [ctx.tenant_id, datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)]
        )
        
        logger.info(f"Re-scoring {len(contacts)} contacts")
        
        for contact in contacts:
            try:
                # Create event data for scoring
                event_data = {"contact": {"id": contact['id']}}
                score_new_contact(event_data, ctx)
            except Exception as e:
                logger.error(f"Error scoring contact {contact['id']}: {e}")
                continue
        
        logger.info("Batch lead scoring completed")
        
    except Exception as e:
        logger.error(f"Error in batch lead scoring: {e}")
        raise

@hook("plugin.installed")
def on_install(ctx) -> None:
    """Plugin installation hook"""
    logger.info(f"Lead Scoring AI plugin installed for tenant {ctx.tenant_id}")
    
    # Set default scoring prompt if not provided
    if not ctx.secrets.get("LEAD_SCORING_PROMPT"):
        ctx.secrets.set("LEAD_SCORING_PROMPT", """
        Analyze this contact information and provide a lead score from 0-100.
        
        Contact Information:
        - Name: {first_name} {last_name}
        - Email: {email}
        - Company: {company}
        - Job Title: {job_title}
        - Phone: {phone}
        - LinkedIn: {linkedin_url}
        - Tags: {tags}
        
        Scoring Criteria:
        - Email quality and domain reputation
        - Company size and industry relevance
        - Job title seniority and decision-making power
        - Contact completeness and professional presence
        - Existing tags and lead indicators
        
        Return only a JSON object with:
        {{
            "score": <0-100>,
            "reasoning": "<brief explanation>",
            "suggested_tags": ["tag1", "tag2"]
        }}
        """)
    
    # Set default score thresholds if not provided
    if not ctx.secrets.get("SCORE_THRESHOLDS"):
        ctx.secrets.set("SCORE_THRESHOLDS", json.dumps({
            "hot_lead": 90,
            "qualified": 75,
            "prospect": 50,
            "unqualified": 25
        }))

@hook("plugin.uninstalled")
def on_uninstall(ctx) -> None:
    """Plugin uninstallation hook"""
    logger.info(f"Lead Scoring AI plugin uninstalled for tenant {ctx.tenant_id}")
    
    # Clean up any plugin-specific data
    # (In this case, no cleanup needed)
