"""
Smoke tests for UI navigation and features catalog
"""
import unittest
import requests
import json
from urllib.parse import urljoin


class TestUINavigation(unittest.TestCase):
    """Test UI navigation and features catalog"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = "http://localhost:5001"
        
    def test_features_catalog_api(self):
        """Test GET /api/features/catalog returns features for viewer role"""
        url = urljoin(self.base_url, "/ui/api/features/catalog")
        params = {"role": "viewer"}
        
        response = requests.get(url, params=params)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return features
        self.assertIn("features", data)
        self.assertIn("total", data)
        self.assertIn("role", data)
        
        # Should have at least 6 items for viewer
        self.assertGreaterEqual(data["total"], 6)
        
        # Should not contain admin-only features (features that only admin can access)
        features = data["features"]
        for feature in features:
            roles = feature.get("roles", [])
            # Features should be accessible to viewer (viewer should be in roles)
            self.assertIn("viewer", roles, f"Feature {feature['slug']} not accessible to viewer")
            
        # Should have required fields
        for feature in features:
            self.assertIn("slug", feature)
            self.assertIn("title", feature)
            self.assertIn("category", feature)
            self.assertIn("route", feature)
            self.assertIn("roles", feature)
            
    def test_features_catalog_filtering(self):
        """Test features catalog filtering by category and search"""
        url = urljoin(self.base_url, "/ui/api/features/catalog")
        
        # Test category filter
        params = {"role": "developer", "category": "core"}
        response = requests.get(url, params=params)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        for feature in data["features"]:
            self.assertEqual(feature["category"], "core")
            
        # Test search filter
        params = {"role": "developer", "q": "builder"}
        response = requests.get(url, params=params)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should find features with "builder" in title/description
        found_builder = False
        for feature in data["features"]:
            if "builder" in feature["title"].lower() or "builder" in feature["description"].lower():
                found_builder = True
                break
        self.assertTrue(found_builder)
        
    def test_ui_routes_return_200_or_unavailable(self):
        """Test UI routes return 200 or Unavailable page (not 404)"""
        routes = [
            "/ui/project-loader",
            "/ui/visual-builder", 
            "/ui/data-refinery",
            "/ui/gtm",
            "/ui/investor",
            "/ui/access-hub",
            "/ui/brain",
            "/ui/build"
        ]
        
        for route in routes:
            url = urljoin(self.base_url, route)
            response = requests.get(url)
            
            # Should not be 404
            self.assertNotEqual(response.status_code, 404, f"Route {route} returned 404")
            
            # Should be 200 (either feature page or unavailable page)
            self.assertEqual(response.status_code, 200, f"Route {route} returned {response.status_code}")
            
            # Should contain expected content
            if response.status_code == 200:
                content = response.text.lower()
                # Should contain either feature content or "unavailable"
                self.assertTrue(
                    "project loader" in content or 
                    "visual builder" in content or
                    "data refinery" in content or
                    "gtm" in content or
                    "investor" in content or
                    "access hub" in content or
                    "brain" in content or
                    "build" in content or
                    "unavailable" in content,
                    f"Route {route} content not recognized"
                )
                
    def test_feature_router_redirects(self):
        """Test /feature/<slug> redirects to proper /ui/... route"""
        # Test redirect for visual-builder
        url = urljoin(self.base_url, "/ui/feature/visual-builder")
        response = requests.get(url, allow_redirects=False)
        
        # Should redirect (302)
        self.assertEqual(response.status_code, 302)
        
        # Should redirect to /ui/visual-builder
        self.assertIn("/ui/visual-builder", response.headers.get("Location", ""))
        
    def test_feature_router_404_for_invalid(self):
        """Test /feature/<slug> returns 404 for invalid features"""
        url = urljoin(self.base_url, "/ui/feature/invalid-feature")
        response = requests.get(url)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)
        
    def test_custom_404_handler(self):
        """Test custom 404 handler returns proper page"""
        url = urljoin(self.base_url, "/nonexistent-route")
        response = requests.get(url)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)
        
        # Should contain 404 page content
        content = response.text.lower()
        self.assertIn("page not found", content)
        self.assertIn("back to dashboard", content)
        
    def test_role_based_access(self):
        """Test role-based access control"""
        # Test viewer role access
        url = urljoin(self.base_url, "/ui/api/features/catalog")
        params = {"role": "viewer"}
        response = requests.get(url, params=params)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Viewer should not see developer-only features
        for feature in data["features"]:
            if "growth-agent" in feature["slug"]:
                self.fail("Viewer should not see growth-agent feature")
                
        # Test developer role access
        params = {"role": "developer"}
        response = requests.get(url, params=params)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Developer should see more features than viewer
        developer_count = data["total"]
        
        params = {"role": "viewer"}
        response = requests.get(url, params=params)
        data = response.json()
        viewer_count = data["total"]
        
        self.assertGreater(developer_count, viewer_count)


if __name__ == "__main__":
    unittest.main()
