"""
Test Enterprise Stack template and features
"""
import unittest
from unittest.mock import patch, MagicMock
from src.market.templates.enterprise_stack import create_enterprise_stack_template

class TestEnterpriseStack(unittest.TestCase):
    """Test Enterprise Stack template"""
    
    def test_template_appears_and_plans(self):
        """Test that enterprise stack template appears and plans correctly"""
        # Create template
        template = create_enterprise_stack_template()
        
        # Check basic properties
        self.assertEqual(template.slug, 'enterprise-stack')
        self.assertEqual(template.title, 'Enterprise Stack')
        self.assertEqual(template.subscription_required, 'pro')
        self.assertTrue(template.is_published)
        self.assertTrue(template.is_featured)
        
        # Check guided schema
        guided_schema = template.variants[0].guided_schema.schema
        self.assertIn('company_name', guided_schema['properties'])
        self.assertIn('primary_color', guided_schema['properties'])
        self.assertIn('enable_custom_domains', guided_schema['properties'])
        self.assertIn('plans', guided_schema['properties'])
        self.assertIn('demo_seed', guided_schema['properties'])
        
        # Check default plans
        default_plans = guided_schema['properties']['plans']['default']
        self.assertEqual(len(default_plans), 3)
        
        plan_ids = [plan['id'] for plan in default_plans]
        self.assertIn('basic', plan_ids)
        self.assertIn('pro', plan_ids)
        self.assertIn('enterprise', plan_ids)
        
        # Check builder state
        builder_state = template.variants[0].builder_state.state
        self.assertIn('models', builder_state)
        self.assertIn('database', builder_state)
        self.assertIn('apis', builder_state)
        self.assertIn('pages', builder_state)
        
        # Check required models
        models = builder_state['models']
        self.assertIn('auth', models)
        self.assertIn('payment', models)
        self.assertIn('file_store', models)
        
        # Check database tables
        tables = builder_state['database']['tables']
        table_names = [table['name'] for table in tables]
        self.assertIn('accounts', table_names)
        self.assertIn('users', table_names)
        self.assertIn('projects', table_names)
        self.assertIn('tasks', table_names)
        
        # Check APIs
        apis = builder_state['apis']
        api_paths = [api['path'] for api in apis]
        self.assertIn('/api/projects', api_paths)
        self.assertIn('/api/tasks', api_paths)
        self.assertIn('/api/users', api_paths)
        
        # Check pages
        pages = builder_state['pages']
        page_paths = [page['path'] for page in pages]
        self.assertIn('/ui/login', page_paths)
        self.assertIn('/ui/register', page_paths)
        self.assertIn('/ui/dashboard', page_paths)
        self.assertIn('/ui/projects', page_paths)
        self.assertIn('/ui/tasks', page_paths)
        self.assertIn('/ui/files', page_paths)
        self.assertIn('/ui/billing', page_paths)
        self.assertIn('/ui/admin/analytics', page_paths)
        self.assertIn('/ui/admin/domains', page_paths)
        self.assertIn('/ui/admin/integrations', page_paths)
        
        # Check feature flags
        feature_flags = builder_state['feature_flags']
        self.assertIn('custom_domains', feature_flags)
        self.assertIn('advanced_analytics', feature_flags)
        self.assertIn('api_access', feature_flags)
        self.assertIn('sso_integration', feature_flags)
        self.assertIn('dedicated_support', feature_flags)

if __name__ == '__main__':
    unittest.main()
