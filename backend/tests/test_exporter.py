"""
Export service tests
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from io import BytesIO
from src.exporter.service import ExportService
from src.exporter.models import ExportBundle, ExportManifest, ExportFile, ExportDiff

class TestExporter(unittest.TestCase):
    """Test export functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = ExportService()
    
    def test_materialize_bundle_minimal_ok(self):
        """Test materializing bundle contains expected files"""
        with patch.object(self.service, '_get_builder_state') as mock_get_state:
            mock_get_state.return_value = {
                'project_id': 'test-project',
                'tenant_id': 'test-tenant',
                'nodes': [
                    {
                        'id': 'ui_page_main',
                        'type': 'ui_page',
                        'name': 'main',
                        'config': {'title': 'Main Page'}
                    }
                ],
                'connections': []
            }
            
            bundle = self.service.materialize_build(
                project_id='test-project',
                tenant_id='test-tenant',
                include_runtime=True
            )
            
            # Check manifest
            self.assertIsInstance(bundle.manifest, ExportManifest)
            self.assertEqual(bundle.manifest.project_id, 'test-project')
            self.assertEqual(bundle.manifest.tenant_id, 'test-tenant')
            
            # Check files
            self.assertGreater(len(bundle.files), 0)
            self.assertIn('app/__init__.py', bundle.files)
            self.assertIn('requirements.txt', bundle.files)
            self.assertIn('wsgi.py', bundle.files)
            self.assertIn('Dockerfile', bundle.files)
    
    def test_zip_is_deterministic(self):
        """Test ZIP creation is deterministic"""
        # Create a simple bundle
        manifest = ExportManifest(
            project_id='test-project',
            tenant_id='test-tenant',
            export_timestamp=datetime.utcnow(),
            sbh_version='1.0.0',
            files=[],
            total_size=0,
            checksum='',
            metadata={}
        )
        
        bundle = ExportBundle(manifest=manifest, files={})
        bundle.add_file('test1.txt', 'content1')
        bundle.add_file('test2.txt', 'content2')
        
        # Create ZIP twice
        zip1 = self.service.zip_bundle(bundle)
        zip2 = self.service.zip_bundle(bundle)
        
        # Should be identical
        self.assertEqual(zip1.getvalue(), zip2.getvalue())
    
    def test_diff_bundle_detects_changes(self):
        """Test bundle diff detects changes"""
        # Create two manifests
        manifest1 = ExportManifest(
            project_id='test-project',
            tenant_id='test-tenant',
            export_timestamp=datetime.utcnow(),
            sbh_version='1.0.0',
            files=[],
            total_size=0,
            checksum='',
            metadata={}
        )
        
        manifest2 = ExportManifest(
            project_id='test-project',
            tenant_id='test-tenant',
            export_timestamp=datetime.utcnow(),
            sbh_version='1.0.0',
            files=[],
            total_size=0,
            checksum='',
            metadata={}
        )
        
        # Add files to manifests
        file1 = ExportFile(
            path='test1.txt',
            content='content1',
            size=8,
            sha256='hash1',
            mtime=datetime.utcnow()
        )
        
        file2 = ExportFile(
            path='test2.txt',
            content='content2',
            size=8,
            sha256='hash2',
            mtime=datetime.utcnow()
        )
        
        file3 = ExportFile(
            path='test1.txt',
            content='content1_modified',
            size=16,
            sha256='hash3',
            mtime=datetime.utcnow()
        )
        
        manifest1.files = [file1]
        manifest2.files = [file2, file3]
        
        # Generate diff
        diff = self.service.diff_bundle(manifest1, manifest2)
        
        # Check results
        self.assertIn('test2.txt', diff.added)
        self.assertIn('test1.txt', diff.changed)
        self.assertEqual(diff.total_added, 1)
        self.assertEqual(diff.total_changed, 1)
        self.assertEqual(diff.total_removed, 0)
    
    def test_export_bundle_validation(self):
        """Test export bundle validation"""
        manifest = ExportManifest(
            project_id='test-project',
            tenant_id='test-tenant',
            export_timestamp=datetime.utcnow(),
            sbh_version='1.0.0',
            files=[],
            total_size=0,
            checksum='',
            metadata={}
        )
        
        bundle = ExportBundle(manifest=manifest, files={})
        
        # Test file addition
        bundle.add_file('test.txt', 'content')
        self.assertIn('test.txt', bundle.files)
        self.assertEqual(len(bundle.manifest.files), 1)
        
        # Test checksum update
        bundle.update_checksum()
        self.assertNotEqual(bundle.manifest.checksum, '')
    
    def test_export_service_configuration(self):
        """Test export service configuration"""
        # Test default configuration
        self.assertEqual(self.service.sbh_version, '1.0.0')
        self.assertEqual(self.service.max_archive_size, 200 * 1024 * 1024)
        self.assertTrue(self.service.include_infra)
        
        # Test with environment variables
        with patch.dict('os.environ', {
            'EXPORT_MAX_SIZE_MB': '100',
            'EXPORT_INCLUDE_INFRA': 'false'
        }):
            service = ExportService()
            self.assertEqual(service.max_archive_size, 100 * 1024 * 1024)
            self.assertFalse(service.include_infra)

if __name__ == '__main__':
    unittest.main()
