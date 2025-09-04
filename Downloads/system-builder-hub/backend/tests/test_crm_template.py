"""
Tests for CRM Flagship template integration
"""
import unittest
from unittest.mock import patch, MagicMock
import json
import os

class TestCRMTemplate(unittest.TestCase):
    """Test CRM Flagship template integration"""
    
    def test_templates_api_includes_crm_flagship(self):
        """Test that /api/templates includes CRM Flagship template"""
        from src.builds_api import get_templates
        
        with patch('src.builds_api.request'):
            with patch('src.builds_api.jsonify') as mock_jsonify:
                get_templates()
                
                # Verify jsonify was called
                mock_jsonify.assert_called_once()
                
                # Get the templates that were returned
                templates = mock_jsonify.call_args[0][0]
                
                # Find CRM Flagship template
                crm_template = None
                for template in templates:
                    if template.get('id') == 'crm_flagship':
                        crm_template = template
                        break
                
                # Verify CRM template exists
                self.assertIsNotNone(crm_template, "CRM Flagship template not found in templates")
                
                # Verify required fields
                self.assertEqual(crm_template['name'], 'CRM Flagship')
                self.assertEqual(crm_template['category'], 'Business Apps')
                self.assertEqual(crm_template['complexity'], 'advanced')
                
                # Verify modules
                self.assertIn('modules', crm_template)
                modules = crm_template['modules']
                self.assertGreaterEqual(len(modules), 6, "CRM template should have at least 6 modules")
                
                # Verify specific modules exist
                module_names = [m['name'] for m in modules]
                expected_modules = ['Accounts', 'Contacts', 'Deals', 'Pipelines', 'Activities', 'Permissions']
                for expected_module in expected_modules:
                    self.assertIn(expected_module, module_names, f"Module {expected_module} not found in CRM template")
                
                # Verify LLM recommendations
                self.assertIn('llm_recommendations', crm_template)
                llm_rec = crm_template['llm_recommendations']
                self.assertIn('default_prompt', llm_rec)
                self.assertIn('models', llm_rec)
                
                # Verify UI configuration
                self.assertIn('ui', crm_template)
                ui_config = crm_template['ui']
                self.assertEqual(ui_config['cta'], 'Launch CRM')
                self.assertEqual(ui_config['icon'], 'building-2')
                self.assertEqual(ui_config['accent'], '#2563eb')
    
    def test_template_file_exists(self):
        """Test that CRM template file exists"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'marketplace', 
            'crm_flagship', 
            'template.json'
        )
        
        self.assertTrue(os.path.exists(template_path), f"Template file not found: {template_path}")
        
        # Verify template file is valid JSON
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        # Verify required fields
        self.assertEqual(template_data['id'], 'crm_flagship')
        self.assertEqual(template_data['name'], 'CRM Flagship')
        self.assertIn('modules', template_data)
        self.assertIn('llm_recommendations', template_data)
        self.assertIn('ui', template_data)
    
    def test_template_loader_fallback(self):
        """Test that template loader falls back to hardcoded templates when marketplace is empty"""
        from src.builds_api import get_templates
        
        with patch('src.builds_api.os.path.exists', return_value=False):
            with patch('src.builds_api.request'):
                with patch('src.builds_api.jsonify') as mock_jsonify:
                    get_templates()
                    
                    templates = mock_jsonify.call_args[0][0]
                    
                    # Should include fallback templates
                    self.assertGreater(len(templates), 0, "Should return fallback templates")
                    
                    # Should include CRM Flagship in fallback
                    crm_template = None
                    for template in templates:
                        if template.get('id') == 'crm_flagship':
                            crm_template = template
                            break
                    
                    self.assertIsNotNone(crm_template, "CRM Flagship should be in fallback templates")
    
    def test_template_sorting(self):
        """Test that CRM Flagship appears first in template list"""
        from src.builds_api import get_templates
        
        with patch('src.builds_api.request'):
            with patch('src.builds_api.jsonify') as mock_jsonify:
                get_templates()
                
                templates = mock_jsonify.call_args[0][0]
                
                # CRM Flagship should be first
                if templates:
                    first_template = templates[0]
                    self.assertEqual(first_template['id'], 'crm_flagship', 
                                   "CRM Flagship should appear first in template list")
    
    def test_crm_template_llm_recommendations(self):
        """Test that CRM template has proper LLM recommendations for prefill"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'marketplace', 
            'crm_flagship', 
            'template.json'
        )
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        # Verify LLM recommendations exist
        self.assertIn('llm_recommendations', template_data)
        llm_rec = template_data['llm_recommendations']
        
        # Verify default prompt exists and is not empty
        self.assertIn('default_prompt', llm_rec)
        self.assertIsInstance(llm_rec['default_prompt'], str)
        self.assertGreater(len(llm_rec['default_prompt']), 0)
        
        # Verify models list exists and is not empty
        self.assertIn('models', llm_rec)
        self.assertIsInstance(llm_rec['models'], list)
        self.assertGreater(len(llm_rec['models']), 0)
        
        # Verify the prompt contains CRM-specific content
        prompt = llm_rec['default_prompt'].lower()
        self.assertIn('crm', prompt)
        self.assertIn('accounts', prompt)
        self.assertIn('contacts', prompt)
        self.assertIn('deals', prompt)
        self.assertIn('pipelines', prompt)
        self.assertIn('activities', prompt)
        self.assertIn('permissions', prompt)

if __name__ == '__main__':
    unittest.main()
