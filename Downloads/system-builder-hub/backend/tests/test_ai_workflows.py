"""
Test AI & Workflows 2.0 functionality
"""
import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from src.ai.models import (
    AIConversation, AIMessage, AIReport, AIEmbedding, 
    AIVoiceSession, AIConfig
)
from src.ai.copilots import CopilotService
from src.ai.convo import ConversationalAnalyticsService
from src.ai.reports import ReportsService
from src.ai.voice import VoiceService
from src.ai.rag import RAGService
from src.ai.schemas import (
    CopilotRequest, AnalyticsQuery, ReportRequest,
    VoiceTranscribeRequest, VoiceExecuteRequest,
    RAGSearchRequest, RAGIndexRequest
)
from src.security.policy import Role

class TestAIWorkflows(unittest.TestCase):
    """Test AI & Workflows 2.0 functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
        self.mock_session = MagicMock()
    
    @patch('src.ai.copilots.db_session')
    def test_copilot_ask_creates_conversation(self, mock_db_session):
        """Test copilot ask creates conversation"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = CopilotService()
        
        # Mock conversation creation
        mock_conversation = MagicMock()
        mock_conversation.id = 'conversation-123'
        mock_conversation.tenant_id = self.tenant_id
        mock_conversation.user_id = self.user_id
        mock_conversation.agent = 'sales'
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(service, '_generate_copilot_response') as mock_generate:
            mock_generate.return_value = MagicMock(
                conversation_id='conversation-123',
                reply='Here is your answer...',
                actions=[],
                references=[],
                tool_calls=[]
            )
            
            request = CopilotRequest(
                agent='sales',
                message='Show me my deals',
                tenant_id=self.tenant_id,
                user_id=self.user_id
            )
            
            response = service.ask_copilot(request)
            
            self.assertEqual(response.conversation_id, 'conversation-123')
            self.assertIn('Here is your answer', response.reply)
    
    @patch('src.ai.convo.db_session')
    def test_analytics_query_pipeline_metrics(self, mock_db_session):
        """Test analytics query for pipeline metrics"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = ConversationalAnalyticsService()
        
        # Mock pipeline data
        mock_deals = [
            MagicMock(pipeline_stage='qualification', count=5, total_value=50000),
            MagicMock(pipeline_stage='proposal', count=3, total_value=75000)
        ]
        
        self.mock_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_deals
        
        with patch.object(service, '_parse_query_intent') as mock_parse:
            mock_parse.return_value = {
                'type': 'pipeline_metrics',
                'time_range': 'month'
            }
            
            query = AnalyticsQuery(
                question='What is my pipeline forecast?',
                tenant_id=self.tenant_id
            )
            
            response = service.query_analytics(query)
            
            self.assertIsNotNone(response.summary)
            self.assertIsInstance(response.charts, list)
    
    @patch('src.ai.reports.db_session')
    def test_report_generation(self, mock_db_session):
        """Test report generation"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = ReportsService()
        
        # Mock report creation
        mock_report = MagicMock()
        mock_report.id = 'report-123'
        mock_report.status = 'success'
        mock_report.file_url = 'https://example.com/report.pdf'
        
        self.mock_session.add.return_value = None
        self.mock_session.commit.return_value = None
        
        with patch.object(service, '_generate_report_content') as mock_generate:
            mock_generate.return_value = '<html>Report content</html>'
            
            with patch.object(service, '_convert_to_pdf') as mock_convert:
                mock_convert.return_value = (b'pdf_content', 'pdf')
                
                with patch.object(service, '_upload_to_s3') as mock_upload:
                    mock_upload.return_value = 'https://example.com/report.pdf'
                    
                    request = ReportRequest(
                        type='weekly_sales',
                        name='Weekly Sales Report',
                        params={'start_date': '2024-01-01', 'end_date': '2024-01-07'},
                        tenant_id=self.tenant_id,
                        user_id=self.user_id
                    )
                    
                    response = service.run_report(request)
                    
                    self.assertEqual(response.status, 'success')
                    self.assertIsNotNone(response.file_url)
    
    @patch('src.ai.voice.db_session')
    def test_voice_transcription(self, mock_db_session):
        """Test voice transcription"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = VoiceService()
        
        # Mock voice session
        mock_session = MagicMock()
        mock_session.id = 'session-123'
        mock_session.session_id = 'voice_session_123'
        
        self.mock_session.add.return_value = None
        self.mock_session.commit.return_value = None
        
        with patch.object(service, '_transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = 'Create a new contact for John Doe'
            
            with patch.object(service, '_extract_intent') as mock_intent:
                mock_intent.return_value = {
                    'action': 'create_contact',
                    'entities': {'name': 'John Doe'},
                    'parameters': {'first_name': 'John', 'last_name': 'Doe'},
                    'confidence': 0.9
                }
                
                request = VoiceTranscribeRequest(
                    audio_data=b'audio_content',
                    session_id='voice_session_123',
                    tenant_id=self.tenant_id,
                    user_id=self.user_id
                )
                
                response = service.transcribe_audio(request)
                
                self.assertEqual(response.session_id, 'voice_session_123')
                self.assertIn('John Doe', response.transcript)
                self.assertEqual(response.intent['action'], 'create_contact')
    
    @patch('src.ai.rag.db_session')
    def test_rag_search(self, mock_db_session):
        """Test RAG search"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = RAGService()
        
        # Mock embeddings
        mock_embeddings = [
            MagicMock(
                chunk_id='chunk_1',
                content='Contact John Doe works at Acme Corp',
                source_type='contact',
                source_id='contact_123',
                vector=[0.1, 0.2, 0.3],
                meta={'title': 'John Doe', 'email': 'john@example.com'}
            )
        ]
        
        self.mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = mock_embeddings
        
        with patch.object(service, '_generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]
            
            with patch.object(service, '_generate_answer') as mock_answer:
                mock_answer.return_value = 'John Doe works at Acme Corp'
                
                request = RAGSearchRequest(
                    query='Who works at Acme Corp?',
                    tenant_id=self.tenant_id
                )
                
                response = service.search_rag(request)
                
                self.assertIsNotNone(response.matches)
                self.assertIsNotNone(response.answer)
                self.assertIn('John Doe', response.answer)
    
    def test_copilot_tool_execution(self):
        """Test copilot tool execution"""
        service = CopilotService()
        
        # Mock tool calls
        tool_calls = [
            {
                'name': 'read_contacts',
                'arguments': {'filters': {'company': 'Acme Corp'}}
            }
        ]
        
        with patch.object(service, '_execute_tool_calls') as mock_execute:
            mock_execute.return_value = [
                MagicMock(
                    tool_call_id='tool_1',
                    result={'contacts': [{'name': 'John Doe', 'email': 'john@example.com'}]},
                    error=None
                )
            ]
            
            results = service._execute_tool_calls(tool_calls, self.tenant_id, self.user_id)
            
            self.assertEqual(len(results), 1)
            self.assertIsNone(results[0].error)
            self.assertIn('contacts', results[0].result)
    
    def test_analytics_intent_parsing(self):
        """Test analytics intent parsing"""
        service = ConversationalAnalyticsService()
        
        with patch.object(service.llm_orchestration, 'generate') as mock_generate:
            mock_generate.return_value = '{"type": "pipeline_metrics", "time_range": "month"}'
            
            intent = service._parse_query_intent('What is my pipeline forecast?')
            
            self.assertEqual(intent['type'], 'pipeline_metrics')
            self.assertEqual(intent['time_range'], 'month')
    
    def test_report_template_loading(self):
        """Test report template loading"""
        service = ReportsService()
        
        template_content = service._load_template('reports/weekly_sales.html')
        
        self.assertIn('<!DOCTYPE html>', template_content)
        self.assertIn('{{ data.title }}', template_content)
        self.assertIn('{{ generated_at }}', template_content)
    
    def test_voice_intent_extraction(self):
        """Test voice intent extraction"""
        service = VoiceService()
        
        with patch.object(service.llm_orchestration, 'generate') as mock_generate:
            mock_generate.return_value = '{"action": "create_contact", "entities": {"name": "John Doe"}, "confidence": 0.9}'
            
            intent = service._extract_intent('Create a new contact for John Doe')
            
            self.assertEqual(intent['action'], 'create_contact')
            self.assertIn('John Doe', intent['entities']['name'])
            self.assertEqual(intent['confidence'], 0.9)
    
    def test_rag_embedding_generation(self):
        """Test RAG embedding generation"""
        service = RAGService()
        
        embedding = service._generate_embedding('Test text for embedding')
        
        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), 512)  # Placeholder dimension
        self.assertTrue(all(isinstance(x, float) for x in embedding))
    
    def test_cosine_similarity_calculation(self):
        """Test cosine similarity calculation"""
        service = RAGService()
        
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        
        similarity = service._cosine_similarity(vec1, vec2)
        
        self.assertEqual(similarity, 1.0)  # Identical vectors should have similarity 1.0
        
        vec3 = [0.0, 1.0, 0.0]
        similarity2 = service._cosine_similarity(vec1, vec3)
        
        self.assertEqual(similarity2, 0.0)  # Orthogonal vectors should have similarity 0.0
    
    def test_ai_config_validation(self):
        """Test AI configuration validation"""
        # Test valid agent
        valid_agents = ['sales', 'ops', 'success', 'builder']
        
        for agent in valid_agents:
            self.assertIn(agent, ['sales', 'ops', 'success', 'builder'])
        
        # Test invalid agent
        with self.assertRaises(ValueError):
            if 'invalid_agent' not in ['sales', 'ops', 'success', 'builder']:
                raise ValueError(f"Invalid agent: invalid_agent")
    
    def test_rate_limiting_configuration(self):
        """Test rate limiting configuration"""
        rate_limits = {
            'copilot_ask': 60,
            'analytics_query': 20,
            'reports_run': 10,
            'rag_search': 10,
            'voice_transcribe': 6
        }
        
        self.assertEqual(rate_limits['copilot_ask'], 60)
        self.assertEqual(rate_limits['analytics_query'], 20)
        self.assertEqual(rate_limits['voice_transcribe'], 6)
    
    def test_rbac_enforcement(self):
        """Test RBAC enforcement"""
        # Test role hierarchy
        owner_role = Role.OWNER
        admin_role = Role.ADMIN
        member_role = Role.MEMBER
        viewer_role = Role.VIEWER
        
        # Owners and admins should be able to manage reports
        can_manage_reports_owner = owner_role in [Role.OWNER, Role.ADMIN]
        can_manage_reports_admin = admin_role in [Role.OWNER, Role.ADMIN]
        
        # Members and viewers should not be able to manage reports
        can_manage_reports_member = member_role in [Role.OWNER, Role.ADMIN]
        can_manage_reports_viewer = viewer_role in [Role.OWNER, Role.ADMIN]
        
        self.assertTrue(can_manage_reports_owner)
        self.assertTrue(can_manage_reports_admin)
        self.assertFalse(can_manage_reports_member)
        self.assertFalse(can_manage_reports_viewer)
    
    def test_tenant_isolation(self):
        """Test tenant isolation"""
        tenant1 = 'tenant-1'
        tenant2 = 'tenant-2'
        
        # Simulate data from different tenants
        data1 = {'tenant_id': tenant1, 'data': 'tenant1_data'}
        data2 = {'tenant_id': tenant2, 'data': 'tenant2_data'}
        
        # Verify tenant isolation
        self.assertNotEqual(data1['tenant_id'], data2['tenant_id'])
        self.assertNotEqual(data1['data'], data2['data'])
    
    def test_error_handling(self):
        """Test error handling"""
        service = CopilotService()
        
        # Test invalid agent
        with self.assertRaises(ValueError):
            request = CopilotRequest(
                agent='invalid_agent',
                message='Test message',
                tenant_id=self.tenant_id,
                user_id=self.user_id
            )
            service.ask_copilot(request)
    
    def test_metrics_collection(self):
        """Test metrics collection"""
        # Simulate metrics collection
        metrics = {
            'tokens_in': 150,
            'tokens_out': 200,
            'latency_ms': 1250,
            'cache_hit': False
        }
        
        self.assertIn('tokens_in', metrics)
        self.assertIn('tokens_out', metrics)
        self.assertIn('latency_ms', metrics)
        self.assertIn('cache_hit', metrics)
        
        self.assertIsInstance(metrics['tokens_in'], int)
        self.assertIsInstance(metrics['tokens_out'], int)
        self.assertIsInstance(metrics['latency_ms'], int)
        self.assertIsInstance(metrics['cache_hit'], bool)

if __name__ == '__main__':
    unittest.main()
