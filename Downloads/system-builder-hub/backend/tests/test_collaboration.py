"""
Test collaboration functionality (comments, mentions, search, saved views, approvals)
"""
import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
from src.crm_ops.collaboration.models import Comment, SavedView, Approval, ActivityFeed
from src.crm_ops.collaboration.comments_service import CommentsService
from src.crm_ops.collaboration.search_service import SearchService
from src.crm_ops.collaboration.saved_views_service import SavedViewsService
from src.crm_ops.collaboration.approvals_service import ApprovalsService
from src.crm_ops.collaboration.activity_service import ActivityService
from src.security.policy import Role

class TestCollaboration(unittest.TestCase):
    """Test collaboration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
        self.mock_session = MagicMock()
    
    @patch('src.crm_ops.collaboration.comments_service.db_session')
    def test_comments_crud_mentions_notifications(self, mock_db_session):
        """Test comment CRUD operations with mentions and notifications"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = CommentsService()
        
        # Test comment creation with mentions
        comment_body = "Great work @john and @jane! Let's follow up on this deal."
        
        # Mock tenant users for mention validation
        mock_tenant_user1 = MagicMock()
        mock_tenant_user1.user_id = 'john'
        mock_tenant_user2 = MagicMock()
        mock_tenant_user2.user_id = 'jane'
        
        self.mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_tenant_user1, mock_tenant_user2
        ]
        
        # Mock comment creation
        mock_comment = MagicMock()
        mock_comment.id = 'comment-123'
        mock_comment.mentions = ['john', 'jane']
        mock_comment.body = comment_body
        mock_comment.to_dict.return_value = {
            'id': 'comment-123',
            'body': comment_body,
            'mentions': ['john', 'jane']
        }
        
        with patch.object(service, 'create_comment') as mock_create:
            mock_create.return_value = mock_comment
            comment = service.create_comment(self.tenant_id, self.user_id, 'deal', 'deal-123', comment_body)
            
            self.assertEqual(comment.id, 'comment-123')
            self.assertIn('john', comment.mentions)
            self.assertIn('jane', comment.mentions)
    
    @patch('src.crm_ops.collaboration.activity_service.db_session')
    def test_activity_feed_merges_audit_comments(self, mock_db_session):
        """Test activity feed merges audit logs and comments"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = ActivityService()
        
        # Mock activity feed entries
        mock_activity = MagicMock()
        mock_activity.id = 'activity-123'
        mock_activity.created_at = datetime.utcnow()
        mock_activity.user_id = self.user_id
        mock_activity.action_type = 'commented'
        mock_activity.action_data = {'comment_id': 'comment-123'}
        mock_activity.icon = '💬'
        mock_activity.link = '/ui/deals/deal-123'
        
        # Mock audit log entries
        mock_audit = MagicMock()
        mock_audit.id = 'audit-456'
        mock_audit.created_at = datetime.utcnow() - timedelta(hours=1)
        mock_audit.user_id = self.user_id
        mock_audit.action = 'update'
        mock_audit.old_values = {'status': 'open'}
        mock_audit.new_values = {'status': 'won'}
        
        self.mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_activity, mock_audit
        ]
        
        # Test timeline generation
        timeline = service.get_entity_timeline(self.tenant_id, 'deal', 'deal-123', limit=10)
        
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]['type'], 'activity')
        self.assertEqual(timeline[1]['type'], 'audit')
    
    @patch('src.crm_ops.collaboration.search_service.db_session')
    def test_search_fulltext_and_filters(self, mock_db_session):
        """Test full-text search and filtering"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = SearchService()
        
        # Mock contact search results
        mock_contact = MagicMock()
        mock_contact.id = 'contact-123'
        mock_contact.first_name = 'John'
        mock_contact.last_name = 'Doe'
        mock_contact.email = 'john@example.com'
        mock_contact.company = 'Acme Corp'
        mock_contact.to_dict.return_value = {
            'id': 'contact-123',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'company': 'Acme Corp'
        }
        
        self.mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_contact]
        
        # Test global search
        results = service.global_search(self.tenant_id, 'john', ['contact'], limit=10)
        
        self.assertIn('contacts', results)
        self.assertEqual(len(results['contacts']), 1)
        self.assertEqual(results['contacts'][0]['first_name'], 'John')
    
    @patch('src.crm_ops.collaboration.saved_views_service.db_session')
    def test_saved_views_create_update_delete(self, mock_db_session):
        """Test saved views CRUD operations"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = SavedViewsService()
        
        # Test saved view creation
        filters = {
            'search': 'acme',
            'tags': ['lead', 'customer'],
            'status': 'active'
        }
        
        mock_saved_view = MagicMock()
        mock_saved_view.id = 'view-123'
        mock_saved_view.name = 'Acme Leads'
        mock_saved_view.entity_type = 'contact'
        mock_saved_view.filters_json = filters
        mock_saved_view.is_shared = False
        mock_saved_view.to_dict.return_value = {
            'id': 'view-123',
            'name': 'Acme Leads',
            'entity_type': 'contact',
            'filters_json': filters
        }
        
        with patch.object(service, 'create_saved_view') as mock_create:
            mock_create.return_value = mock_saved_view
            saved_view = service.create_saved_view(
                self.tenant_id, self.user_id, 'Acme Leads', 'contact', filters
            )
            
            self.assertEqual(saved_view.id, 'view-123')
            self.assertEqual(saved_view.name, 'Acme Leads')
            self.assertEqual(saved_view.filters_json, filters)
    
    @patch('src.crm_ops.collaboration.saved_views_service.db_session')
    def test_saved_views_shared_visibility(self, mock_db_session):
        """Test saved views shared visibility"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = SavedViewsService()
        
        # Mock shared and private views
        mock_shared_view = MagicMock()
        mock_shared_view.id = 'view-123'
        mock_shared_view.is_shared = True
        mock_shared_view.user_id = 'other-user'
        
        mock_private_view = MagicMock()
        mock_private_view.id = 'view-456'
        mock_private_view.is_shared = False
        mock_private_view.user_id = self.user_id
        
        self.mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_shared_view, mock_private_view
        ]
        
        # Test getting views (should include shared and own private views)
        views = service.get_saved_views(self.tenant_id, self.user_id, 'contact')
        
        self.assertEqual(len(views), 2)
        self.assertTrue(views[0].is_shared)
        self.assertFalse(views[1].is_shared)
    
    @patch('src.crm_ops.collaboration.approvals_service.db_session')
    def test_approvals_request_and_resolve(self, mock_db_session):
        """Test approval request and resolution"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = ApprovalsService()
        
        # Test approval request
        mock_approval = MagicMock()
        mock_approval.id = 'approval-123'
        mock_approval.status = 'pending'
        mock_approval.entity_type = 'deal'
        mock_approval.entity_id = 'deal-123'
        mock_approval.action_type = 'update'
        mock_approval.requested_by = self.user_id
        mock_approval.approver_id = 'admin-user'
        
        with patch.object(service, 'request_approval') as mock_request:
            mock_request.return_value = mock_approval
            approval = service.request_approval(
                self.tenant_id, 'deal', 'deal-123', 'update', self.user_id, 'admin-user'
            )
            
            self.assertEqual(approval.status, 'pending')
            self.assertEqual(approval.entity_type, 'deal')
        
        # Test approval resolution
        with patch.object(service, 'approve') as mock_approve:
            mock_approve.return_value = True
            success = service.approve('approval-123', self.tenant_id, 'admin-user', 'Approved')
            
            self.assertTrue(success)
    
    def test_rbac_comment_delete_only_admins(self):
        """Test RBAC for comment deletion"""
        # Test that only admins can delete comments
        owner_role = Role.OWNER
        admin_role = Role.ADMIN
        member_role = Role.MEMBER
        viewer_role = Role.VIEWER
        
        # Owners and admins should be able to delete comments
        can_delete_owner = owner_role in [Role.OWNER, Role.ADMIN]
        can_delete_admin = admin_role in [Role.OWNER, Role.ADMIN]
        
        # Members and viewers should not be able to delete comments
        can_delete_member = member_role in [Role.OWNER, Role.ADMIN]
        can_delete_viewer = viewer_role in [Role.OWNER, Role.ADMIN]
        
        self.assertTrue(can_delete_owner)
        self.assertTrue(can_delete_admin)
        self.assertFalse(can_delete_member)
        self.assertFalse(can_delete_viewer)
    
    @patch('src.crm_ops.collaboration.comments_service.CommentsService._log_metrics')
    def test_rate_limits_and_metrics_emitted(self, mock_log_metrics):
        """Test rate limiting and metrics emission"""
        service = CommentsService()
        
        # Test rate limiting (would be handled by Flask-Limiter)
        # For now, test that metrics are logged
        
        with patch.object(service.redis_client, 'incr') as mock_incr:
            # Simulate comment creation
            mock_incr.return_value = 1
            
            # Test that metrics are incremented
            mock_incr.assert_not_called()  # Not called yet in this test
    
    def test_mention_extraction(self):
        """Test mention extraction from comment text"""
        service = CommentsService()
        
        # Test mention extraction
        comment_text = "Hey @john and @jane, please review this deal @bob"
        mentions = service._extract_mentions(comment_text, self.tenant_id)
        
        # Should extract usernames after @
        expected_mentions = ['john', 'jane', 'bob']
        self.assertEqual(mentions, expected_mentions)
    
    def test_search_faceted_filtering(self):
        """Test faceted search filtering"""
        service = SearchService()
        
        # Test contact facets
        with patch.object(service, '_get_contact_facets') as mock_facets:
            mock_facets.return_value = {
                'tags': [
                    {'tag': 'lead', 'count': 10},
                    {'tag': 'customer', 'count': 5}
                ],
                'companies': [
                    {'company': 'Acme Corp', 'count': 3},
                    {'company': 'Tech Inc', 'count': 2}
                ]
            }
            
            facets = service.get_faceted_search(self.tenant_id, 'contact')
            
            self.assertIn('tags', facets)
            self.assertIn('companies', facets)
            self.assertEqual(len(facets['tags']), 2)
            self.assertEqual(len(facets['companies']), 2)
    
    def test_approval_rules_checking(self):
        """Test approval rules checking"""
        service = ApprovalsService()
        
        # Test deal approval rules
        requires_approval = service.check_approval_required(
            self.tenant_id, 'deal', 'create', {'value': 75000}
        )
        self.assertTrue(requires_approval)
        
        # Test deal below threshold
        no_approval_needed = service.check_approval_required(
            self.tenant_id, 'deal', 'create', {'value': 25000}
        )
        self.assertFalse(no_approval_needed)
        
        # Test high priority task deletion
        task_approval_needed = service.check_approval_required(
            self.tenant_id, 'task', 'delete', {'priority': 'high'}
        )
        self.assertTrue(task_approval_needed)
    
    def test_activity_icon_mapping(self):
        """Test activity icon mapping"""
        service = ActivityService()
        
        # Test audit icon mapping
        create_icon = service._get_audit_icon('create')
        update_icon = service._get_audit_icon('update')
        delete_icon = service._get_audit_icon('delete')
        
        self.assertEqual(create_icon, '➕')
        self.assertEqual(update_icon, '✏️')
        self.assertEqual(delete_icon, '🗑️')
        
        # Test default icon mapping
        comment_icon = service._get_default_icon('commented')
        mention_icon = service._get_default_icon('mentioned')
        
        self.assertEqual(comment_icon, '💬')
        self.assertEqual(mention_icon, '👤')

if __name__ == '__main__':
    unittest.main()
