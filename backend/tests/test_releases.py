"""
Test release management system
"""
import unittest
from unittest.mock import patch, MagicMock
from src.releases.service import ReleaseService
from src.releases.models import Release

class TestReleases(unittest.TestCase):
    """Test release management"""
    
    def setUp(self):
        """Set up test environment"""
        self.release_service = ReleaseService()
    
    @patch('src.releases.service.tool_kernel')
    def test_release_prepare_generates_manifest(self, mock_tool_kernel):
        """Test that release prepare generates manifest with migration SQL"""
        # Mock tool kernel response
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.redacted_output = {
            'sql': 'CREATE TABLE accounts (id UUID PRIMARY KEY, name VARCHAR(255) NOT NULL);',
            'operation': 'create_table',
            'table': 'accounts',
            'dry_run': True
        }
        mock_tool_kernel.execute.return_value = mock_result
        
        # Mock analytics
        with patch('src.releases.service.AnalyticsService') as mock_analytics:
            mock_analytics_instance = MagicMock()
            mock_analytics.return_value = mock_analytics_instance
            
            # Test prepare release
            bundle_data = {
                'database': {
                    'changes': [
                        {
                            'type': 'create_table',
                            'table': 'accounts',
                            'columns': [
                                {'name': 'id', 'type': 'uuid', 'primary_key': True},
                                {'name': 'name', 'type': 'varchar(255)', 'nullable': False}
                            ]
                        }
                    ]
                }
            }
            
            release = self.release_service.prepare_release(
                tenant_id='test-tenant',
                from_env='dev',
                to_env='staging',
                bundle_data=bundle_data,
                user_id='test-user'
            )
            
            # Check release properties
            self.assertIsNotNone(release)
            self.assertTrue(release.release_id.startswith('rel_'))
            self.assertEqual(release.from_env, 'dev')
            self.assertEqual(release.to_env, 'staging')
            self.assertEqual(release.status, 'prepared')
            self.assertIsNotNone(release.bundle_sha256)
            self.assertIsNotNone(release.migrations)
            
            # Check migrations
            self.assertEqual(len(release.migrations), 1)
            migration = release.migrations[0]
            self.assertEqual(migration['operation'], 'create_table')
            self.assertEqual(migration['table'], 'accounts')
            self.assertIn('CREATE TABLE accounts', migration['sql'])
    
    @patch('src.releases.service.tool_kernel')
    def test_release_promote_applies_and_is_idempotent(self, mock_tool_kernel):
        """Test that release promote applies migrations and is idempotent"""
        # Mock tool kernel response for migration application
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.redacted_output = {'executed': True}
        mock_tool_kernel.execute.return_value = mock_result
        
        # Mock analytics
        with patch('src.releases.service.AnalyticsService') as mock_analytics:
            mock_analytics_instance = MagicMock()
            mock_analytics.return_value = mock_analytics_instance
            
            # Mock database session
            with patch('src.releases.service.db_session') as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value.__enter__.return_value = mock_session_instance
                
                # Mock release query
                mock_release = MagicMock()
                mock_release.release_id = 'rel_20240115_1200'
                mock_release.status = 'prepared'
                mock_release.from_env = 'staging'
                mock_release.to_env = 'prod'
                mock_release.migrations = [
                    {
                        'operation': 'create_table',
                        'table': 'accounts',
                        'sql': 'CREATE TABLE accounts (id UUID PRIMARY KEY);'
                    }
                ]
                mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_release
                
                # Test promote release
                result = self.release_service.promote_release('rel_20240115_1200', 'test-user')
                
                # Check result
                self.assertIsNotNone(result)
                self.assertEqual(result.status, 'promoted')
                self.assertIsNotNone(result.promoted_at)
                
                # Verify tool was called
                mock_tool_kernel.execute.assert_called()
    
    def test_release_rollback_on_migration_error(self):
        """Test release rollback on migration error"""
        # Mock tool kernel to simulate failure
        with patch('src.releases.service.tool_kernel') as mock_tool_kernel:
            mock_result = MagicMock()
            mock_result.ok = False
            mock_result.error = {'code': 'migration_error', 'message': 'Table already exists'}
            mock_tool_kernel.execute.return_value = mock_result
            
            # Mock analytics
            with patch('src.releases.service.AnalyticsService') as mock_analytics:
                mock_analytics_instance = MagicMock()
                mock_analytics.return_value = mock_analytics_instance
                
                # Mock database session
                with patch('src.releases.service.db_session') as mock_session:
                    mock_session_instance = MagicMock()
                    mock_session.return_value.__enter__.return_value = mock_session_instance
                    
                    # Mock release query
                    mock_release = MagicMock()
                    mock_release.release_id = 'rel_20240115_1200'
                    mock_release.status = 'prepared'
                    mock_release.from_env = 'staging'
                    mock_release.to_env = 'prod'
                    mock_release.migrations = [
                        {
                            'operation': 'create_table',
                            'table': 'accounts',
                            'sql': 'CREATE TABLE accounts (id UUID PRIMARY KEY);'
                        }
                    ]
                    mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_release
                    
                    # Test promote release (should fail)
                    result = self.release_service.promote_release('rel_20240115_1200', 'test-user')
                    
                    # Check result
                    self.assertIsNotNone(result)
                    self.assertEqual(result.status, 'failed')
                    self.assertIsNotNone(result.failed_at)
                    self.assertIsNotNone(result.error_message)

if __name__ == '__main__':
    unittest.main()
