"""
Tests for CRM Frontend Scaffold functionality
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from src.scaffold import scaffold_crm_flagship, get_build_path


class TestCRMFrontendScaffold:
    """Test CRM frontend scaffold functionality"""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection"""
        # No need to mock get_db_connection for frontend tests
        yield None

    @pytest.fixture
    def temp_generated_dir(self, tmp_path, monkeypatch):
        """Create temporary generated directory"""
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()
        monkeypatch.setenv('GENERATED_ROOT', str(generated_dir))
        return generated_dir

    def test_crm_frontend_scaffold_creates_nextjs_structure(self, temp_generated_dir, mock_db_connection):
        """Test that CRM frontend scaffold creates Next.js structure"""
        build_id = "test-crm-frontend"
        build_data = {
            "name": "CRM Flagship",
            "description": "Production CRM starter",
            "template": "crm_flagship"
        }

        # Run scaffold
        result = scaffold_crm_flagship(build_id, build_data)

        # Check build path
        build_path = get_build_path(build_id)
        assert os.path.exists(build_path)

        # Check frontend structure
        frontend_path = os.path.join(build_path, 'frontend')
        assert os.path.exists(frontend_path)
        assert os.path.exists(os.path.join(frontend_path, 'app'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'components'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'lib'))

        # Check package.json
        package_json_path = os.path.join(frontend_path, 'package.json')
        assert os.path.exists(package_json_path)
        
        with open(package_json_path, 'r') as f:
            package_json = json.load(f)
        
        assert package_json['name'] == 'crm-flagship-frontend'
        assert 'next' in package_json['dependencies']
        assert 'react' in package_json['dependencies']
        assert 'lucide-react' in package_json['dependencies']

        # Check .sbhrc.json
        sbhrc_path = os.path.join(frontend_path, '.sbhrc.json')
        assert os.path.exists(sbhrc_path)
        
        with open(sbhrc_path, 'r') as f:
            sbhrc = json.load(f)
        
        assert sbhrc['build_id'] == build_id

        # Check Next.js config files
        assert os.path.exists(os.path.join(frontend_path, 'next.config.mjs'))
        assert os.path.exists(os.path.join(frontend_path, 'tailwind.config.js'))
        assert os.path.exists(os.path.join(frontend_path, 'postcss.config.js'))

        # Check app structure
        assert os.path.exists(os.path.join(frontend_path, 'app', 'globals.css'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'layout.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'page.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'lib', 'api.ts'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'lib', 'utils.ts'))

        # Check components
        assert os.path.exists(os.path.join(frontend_path, 'app', 'components', 'Nav.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'components', 'Card.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'components', 'Pill.tsx'))

        # Check pages
        assert os.path.exists(os.path.join(frontend_path, 'app', 'accounts', 'page.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'accounts', '[id]', 'page.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'contacts', 'page.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'contacts', '[id]', 'page.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'deals', 'page.tsx'))
        assert os.path.exists(os.path.join(frontend_path, 'app', 'activities', 'page.tsx'))

        # Check README
        assert os.path.exists(os.path.join(frontend_path, 'README.md'))

    def test_crm_frontend_package_json_scripts(self, temp_generated_dir, mock_db_connection):
        """Test that package.json has correct scripts"""
        build_id = "test-crm-scripts"
        build_data = {"name": "CRM", "template": "crm_flagship"}

        scaffold_crm_flagship(build_id, build_data)

        frontend_path = os.path.join(get_build_path(build_id), 'frontend')
        package_json_path = os.path.join(frontend_path, 'package.json')
        
        with open(package_json_path, 'r') as f:
            package_json = json.load(f)
        
        scripts = package_json['scripts']
        assert 'dev' in scripts
        assert 'build' in scripts
        assert 'start' in scripts
        assert 'lint' in scripts

    def test_crm_frontend_api_ts_uses_serve_base(self, temp_generated_dir, mock_db_connection):
        """Test that lib/api.ts uses /serve/<id>/api base"""
        build_id = "test-crm-api"
        build_data = {"name": "CRM", "template": "crm_flagship"}

        scaffold_crm_flagship(build_id, build_data)

        frontend_path = os.path.join(get_build_path(build_id), 'frontend')
        api_ts_path = os.path.join(frontend_path, 'app', 'lib', 'api.ts')
        
        with open(api_ts_path, 'r') as f:
            api_content = f.read()
        
        assert '/serve/' in api_content
        assert '/api' in api_content
        assert 'getHealth' in api_content
        assert 'getAccounts' in api_content
        assert 'getContacts' in api_content
        assert 'getDeals' in api_content
        assert 'getActivities' in api_content

    def test_crm_frontend_components_exist(self, temp_generated_dir, mock_db_connection):
        """Test that all required components are created"""
        build_id = "test-crm-components"
        build_data = {"name": "CRM", "template": "crm_flagship"}

        scaffold_crm_flagship(build_id, build_data)

        frontend_path = os.path.join(get_build_path(build_id), 'frontend')
        components_path = os.path.join(frontend_path, 'app', 'components')
        
        # Check component files exist
        component_files = ['Nav.tsx', 'Card.tsx', 'Pill.tsx']
        for component in component_files:
            component_path = os.path.join(components_path, component)
            assert os.path.exists(component_path)
            
            with open(component_path, 'r') as f:
                content = f.read()
                assert 'export function' in content

    def test_crm_frontend_pages_exist(self, temp_generated_dir, mock_db_connection):
        """Test that all required pages are created"""
        build_id = "test-crm-pages"
        build_data = {"name": "CRM", "template": "crm_flagship"}

        scaffold_crm_flagship(build_id, build_data)

        frontend_path = os.path.join(get_build_path(build_id), 'frontend')
        app_path = os.path.join(frontend_path, 'app')
        
        # Check page files exist
        page_files = [
            'page.tsx',  # Dashboard
            'accounts/page.tsx',
            'accounts/[id]/page.tsx',
            'contacts/page.tsx',
            'contacts/[id]/page.tsx',
            'deals/page.tsx',
            'activities/page.tsx'
        ]
        
        for page in page_files:
            page_path = os.path.join(app_path, page)
            assert os.path.exists(page_path)
            
            with open(page_path, 'r') as f:
                content = f.read()
                assert 'export default' in content

    def test_crm_frontend_manifest_includes_frontend_port(self, temp_generated_dir, mock_db_connection):
        """Test that manifest.json includes frontend port"""
        build_id = "test-crm-manifest"
        build_data = {"name": "CRM", "template": "crm_flagship"}

        scaffold_crm_flagship(build_id, build_data)

        build_path = get_build_path(build_id)
        manifest_path = os.path.join(build_path, 'manifest.json')
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        assert 'ports' in manifest
        assert 'frontend' in manifest['ports']
        assert manifest['ports']['frontend'] == 3000
        assert manifest['ports']['backend'] == 8000
