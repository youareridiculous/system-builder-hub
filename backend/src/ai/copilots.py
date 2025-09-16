"""
AI Copilot service for CRM/Ops Template
"""
import logging
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.ai.models import AIConversation, AIMessage
from src.ai.schemas import (
    CopilotRequest, CopilotResponse, ToolCall, ToolResult, 
    ConversationContext, AVAILABLE_AGENTS
)
from src.llm.orchestration import LLMOrchestration
from src.tools.kernel import ToolKernel
from src.crm_ops.collaboration.activity_service import ActivityService

logger = logging.getLogger(__name__)

class CopilotService:
    """Service for AI copilot operations"""
    
    def __init__(self):
        self.llm_orchestration = LLMOrchestration()
        self.tool_kernel = ToolKernel()
        self.activity_service = ActivityService()
    
    def ask_copilot(self, request: CopilotRequest) -> CopilotResponse:
        """Ask copilot a question"""
        try:
            # Validate agent
            if request.agent not in AVAILABLE_AGENTS:
                raise ValueError(f"Invalid agent: {request.agent}")
            
            # Get or create conversation
            conversation = self._get_or_create_conversation(
                request.tenant_id, request.user_id, request.agent, 
                request.conversation_id, request.message
            )
            
            # Get conversation context
            context = self._get_conversation_context(conversation.id, request.tenant_id)
            
            # Add user message
            user_message = self._add_message(
                conversation.id, 'user', request.message, 
                tokens_in=self._count_tokens(request.message)
            )
            
            # Generate copilot response with tool calling
            response = self._generate_copilot_response(context, request)
            
            # Add assistant message
            assistant_message = self._add_message(
                conversation.id, 'assistant', response.reply,
                tokens_out=self._count_tokens(response.reply),
                tool_calls=response.tool_calls
            )
            
            # Update conversation
            conversation.last_message_at = user_message.created_at
            conversation.title = self._generate_conversation_title(request.message)
            
            with db_session() as session:
                session.add(conversation)
                session.commit()
            
            # Log audit event
            self._log_audit_event('copilot.reply', {
                'conversation_id': str(conversation.id),
                'agent': request.agent,
                'tokens_in': user_message.tokens_in,
                'tokens_out': assistant_message.tokens_out,
                'tools_used': len(response.tool_calls or [])
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error in copilot ask: {e}")
            raise
    
    def _get_or_create_conversation(self, tenant_id: str, user_id: str, agent: str, 
                                   conversation_id: Optional[str], message: str) -> AIConversation:
        """Get existing conversation or create new one"""
        with db_session() as session:
            if conversation_id:
                conversation = session.query(AIConversation).filter(
                    AIConversation.id == conversation_id,
                    AIConversation.tenant_id == tenant_id,
                    AIConversation.user_id == user_id
                ).first()
                
                if conversation:
                    return conversation
            
            # Create new conversation
            conversation = AIConversation(
                tenant_id=tenant_id,
                user_id=user_id,
                agent=agent,
                title=self._generate_conversation_title(message)
            )
            
            session.add(conversation)
            session.commit()
            
            return conversation
    
    def _get_conversation_context(self, conversation_id: str, tenant_id: str) -> ConversationContext:
        """Get conversation context with messages"""
        with db_session() as session:
            conversation = session.query(AIConversation).filter(
                AIConversation.id == conversation_id
            ).first()
            
            messages = session.query(AIMessage).filter(
                AIMessage.conversation_id == conversation_id
            ).order_by(AIMessage.created_at).all()
            
            return ConversationContext(
                conversation_id=str(conversation.id),
                messages=[msg.to_dict() for msg in messages],
                agent=conversation.agent,
                user_id=conversation.user_id,
                tenant_id=tenant_id
            )
    
    def _generate_copilot_response(self, context: ConversationContext, request: CopilotRequest) -> CopilotResponse:
        """Generate copilot response with tool calling"""
        # Build system prompt
        system_prompt = self._build_system_prompt(request.agent, context)
        
        # Build user prompt
        user_prompt = self._build_user_prompt(request, context)
        
        # Get available tools
        available_tools = self._get_available_tools(request.agent, request.tools)
        
        # Generate response with tool calling
        response = self.llm_orchestration.generate_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=available_tools,
            context={
                'tenant_id': request.tenant_id,
                'user_id': request.user_id,
                'conversation_id': context.conversation_id
            }
        )
        
        # Execute tool calls if any
        tool_results = []
        if response.tool_calls:
            tool_results = self._execute_tool_calls(response.tool_calls, request.tenant_id, request.user_id)
        
        # Generate final response
        final_response = self._generate_final_response(
            response.content, tool_results, context, request
        )
        
        return CopilotResponse(
            conversation_id=context.conversation_id,
            reply=final_response,
            actions=self._extract_actions(tool_results),
            references=self._extract_references(tool_results),
            metrics={
                'tokens_in': self._count_tokens(user_prompt),
                'tokens_out': self._count_tokens(final_response),
                'latency_ms': 0  # Would be calculated in real implementation
            },
            tool_calls=response.tool_calls
        )
    
    def _build_system_prompt(self, agent: str, context: ConversationContext) -> str:
        """Build system prompt for copilot"""
        agent_info = AVAILABLE_AGENTS[agent]
        
        return f"""You are the {agent_info['name']}, an AI assistant specialized in {agent_info['description']}.

Your capabilities include:
- Reading and analyzing CRM data (contacts, deals, tasks, projects)
- Proposing next best actions
- Creating tasks, activities, and calendar events
- Drafting emails and messages
- Running automations and workflows
- Answering "how do I..." questions with step-by-step guidance

Guidelines:
1. Always be helpful and professional
2. Use available tools to access real data when needed
3. Propose specific, actionable next steps
4. Provide context and explanations for your recommendations
5. Respect user permissions and data access rights
6. If you don't know something, say so and suggest how to find out

Current conversation context:
- Agent: {agent}
- User: {context.user_id}
- Tenant: {context.tenant_id}
- Conversation ID: {context.conversation_id}"""
    
    def _build_user_prompt(self, request: CopilotRequest, context: ConversationContext) -> str:
        """Build user prompt with conversation history"""
        # Add conversation history
        history = ""
        for message in context.messages[-10:]:  # Last 10 messages
            role = message['role']
            content = message['content']
            history += f"{role.upper()}: {content}\n"
        
        # Add current message
        current_message = f"USER: {request.message}"
        
        # Add context if provided
        context_info = ""
        if request.context:
            context_info = f"\nContext: {json.dumps(request.context, indent=2)}\n"
        
        return f"{history}{context_info}{current_message}"
    
    def _get_available_tools(self, agent: str, tools_config: Optional[Dict[str, bool]]) -> List[Dict[str, Any]]:
        """Get available tools for agent"""
        # Default tools for all agents
        base_tools = [
            {
                'name': 'read_contacts',
                'description': 'Read contact information',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'filters': {'type': 'object', 'description': 'Filter criteria'},
                        'limit': {'type': 'integer', 'description': 'Maximum number of contacts'}
                    }
                }
            },
            {
                'name': 'read_deals',
                'description': 'Read deal information',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'filters': {'type': 'object', 'description': 'Filter criteria'},
                        'limit': {'type': 'integer', 'description': 'Maximum number of deals'}
                    }
                }
            },
            {
                'name': 'read_tasks',
                'description': 'Read task information',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'filters': {'type': 'object', 'description': 'Filter criteria'},
                        'limit': {'type': 'integer', 'description': 'Maximum number of tasks'}
                    }
                }
            },
            {
                'name': 'create_task',
                'description': 'Create a new task',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'title': {'type': 'string', 'description': 'Task title'},
                        'description': {'type': 'string', 'description': 'Task description'},
                        'assignee_id': {'type': 'string', 'description': 'Assignee user ID'},
                        'priority': {'type': 'string', 'enum': ['low', 'medium', 'high']},
                        'due_date': {'type': 'string', 'description': 'Due date (ISO format)'}
                    },
                    'required': ['title']
                }
            },
            {
                'name': 'schedule_activity',
                'description': 'Schedule a calendar activity',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'title': {'type': 'string', 'description': 'Activity title'},
                        'start_time': {'type': 'string', 'description': 'Start time (ISO format)'},
                        'end_time': {'type': 'string', 'description': 'End time (ISO format)'},
                        'attendees': {'type': 'array', 'items': {'type': 'string'}},
                        'description': {'type': 'string', 'description': 'Activity description'}
                    },
                    'required': ['title', 'start_time', 'end_time']
                }
            },
            {
                'name': 'draft_email',
                'description': 'Draft an email',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'to': {'type': 'string', 'description': 'Recipient email'},
                        'subject': {'type': 'string', 'description': 'Email subject'},
                        'body': {'type': 'string', 'description': 'Email body'},
                        'contact_id': {'type': 'string', 'description': 'Related contact ID'}
                    },
                    'required': ['to', 'subject', 'body']
                }
            }
        ]
        
        # Agent-specific tools
        agent_tools = {
            'sales': [
                {
                    'name': 'update_deal',
                    'description': 'Update deal information',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'deal_id': {'type': 'string', 'description': 'Deal ID'},
                            'updates': {'type': 'object', 'description': 'Fields to update'}
                        },
                        'required': ['deal_id', 'updates']
                    }
                }
            ],
            'ops': [
                {
                    'name': 'read_projects',
                    'description': 'Read project information',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'filters': {'type': 'object', 'description': 'Filter criteria'},
                            'limit': {'type': 'integer', 'description': 'Maximum number of projects'}
                        }
                    }
                }
            ],
            'success': [
                {
                    'name': 'read_activities',
                    'description': 'Read activity information',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'filters': {'type': 'object', 'description': 'Filter criteria'},
                            'limit': {'type': 'integer', 'description': 'Maximum number of activities'}
                        }
                    }
                }
            ],
            'builder': [
                {
                    'name': 'read_automations',
                    'description': 'Read automation rules',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'filters': {'type': 'object', 'description': 'Filter criteria'},
                            'limit': {'type': 'integer', 'description': 'Maximum number of automations'}
                        }
                    }
                },
                {
                    'name': 'test_automation',
                    'description': 'Test an automation rule',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'automation_id': {'type': 'string', 'description': 'Automation ID'},
                            'test_data': {'type': 'object', 'description': 'Test data'}
                        },
                        'required': ['automation_id']
                    }
                }
            ]
        }
        
        # Combine base tools with agent-specific tools
        all_tools = base_tools + agent_tools.get(agent, [])
        
        # Filter based on tools configuration
        if tools_config:
            enabled_tools = [tool for tool in all_tools if tools_config.get(tool['name'], True)]
            return enabled_tools
        
        return all_tools
    
    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]], tenant_id: str, user_id: str) -> List[ToolResult]:
        """Execute tool calls"""
        results = []
        
        for tool_call in tool_calls:
            try:
                tool_name = tool_call['name']
                arguments = tool_call.get('arguments', {})
                
                # Execute tool via tool kernel
                result = self.tool_kernel.execute_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    context={
                        'tenant_id': tenant_id,
                        'user_id': user_id
                    }
                )
                
                results.append(ToolResult(
                    tool_call_id=tool_call.get('id', ''),
                    result=result,
                    error=None
                ))
                
            except Exception as e:
                logger.error(f"Error executing tool {tool_call.get('name')}: {e}")
                results.append(ToolResult(
                    tool_call_id=tool_call.get('id', ''),
                    result=None,
                    error=str(e)
                ))
        
        return results
    
    def _generate_final_response(self, initial_response: str, tool_results: List[ToolResult], 
                                context: ConversationContext, request: CopilotRequest) -> str:
        """Generate final response incorporating tool results"""
        if not tool_results:
            return initial_response
        
        # Build tool results summary
        tool_summary = "Based on the information I found:\n\n"
        
        for result in tool_results:
            if result.error:
                tool_summary += f"⚠️ Error: {result.error}\n\n"
            else:
                tool_summary += f"✅ {result.result}\n\n"
        
        # Generate final response with tool results
        final_prompt = f"""Previous response: {initial_response}

Tool results:
{tool_summary}

Please provide a comprehensive response incorporating the tool results above. Be specific and actionable."""

        final_response = self.llm_orchestration.generate(
            prompt=final_prompt,
            context={
                'tenant_id': request.tenant_id,
                'user_id': request.user_id,
                'conversation_id': context.conversation_id
            }
        )
        
        return final_response
    
    def _add_message(self, conversation_id: str, role: str, content: str, 
                     tokens_in: int = 0, tokens_out: int = 0, tool_calls: Optional[List[Dict[str, Any]]] = None) -> AIMessage:
        """Add message to conversation"""
        with db_session() as session:
            message = AIMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                tool_calls=tool_calls or []
            )
            
            session.add(message)
            session.commit()
            
            return message
    
    def _generate_conversation_title(self, message: str) -> str:
        """Generate conversation title from first message"""
        # Simple title generation - in production, use LLM
        words = message.split()[:5]
        return " ".join(words) + ("..." if len(message.split()) > 5 else "")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        # Simple token counting - in production, use proper tokenizer
        return len(text.split())
    
    def _extract_actions(self, tool_results: List[ToolResult]) -> List[Dict[str, Any]]:
        """Extract actions from tool results"""
        actions = []
        
        for result in tool_results:
            if result.result and not result.error:
                actions.append({
                    'type': 'tool_executed',
                    'result': result.result,
                    'tool_call_id': result.tool_call_id
                })
        
        return actions
    
    def _extract_references(self, tool_results: List[ToolResult]) -> List[Dict[str, Any]]:
        """Extract references from tool results"""
        references = []
        
        for result in tool_results:
            if result.result and not result.error:
                if isinstance(result.result, dict) and 'references' in result.result:
                    references.extend(result.result['references'])
        
        return references
    
    def _log_audit_event(self, event_type: str, metadata: Dict[str, Any]):
        """Log audit event"""
        try:
            self.activity_service.create_activity_entry(
                session=None,  # Would be passed in real implementation
                tenant_id=metadata.get('tenant_id'),
                user_id=metadata.get('user_id'),
                entity_type='ai_conversation',
                entity_id=metadata.get('conversation_id'),
                action_type=event_type,
                action_data=metadata
            )
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
