import unittest
from venture_os.entity.model import Entity, EntityKind
from venture_os.rbac.model import User, Role
from venture_os.repo.memory import MemoryEntityRepo
from venture_os.security.guards import can_read_entity, can_write_entity
from venture_os.service.entity_service import create_entity, get_entity, update_entity, archive_entity
from venture_os.service.query_service import list_entities, search_entities
from venture_os.linkage.relations import link_contact_to_company, link_deal_to_company
from venture_os.service.company_service import get_company_summary


class VentureOSTests(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures with properly instantiated User objects."""
        self.repo = MemoryEntityRepo()
        self.tenant_id = "test_tenant"
        
        # Create admin user with all required fields
        self.admin = User(
            id="admin_1",
            tenant_id=self.tenant_id,
            email="admin@test.com",
            name="Admin User",
            roles=[Role.ADMIN]
        )
        
        # Create viewer user with all required fields
        self.viewer = User(
            id="viewer_1", 
            tenant_id=self.tenant_id,
            email="viewer@test.com",
            name="Viewer User",
            roles=[Role.VIEWER]
        )
        
        # Create user from different tenant for cross-tenant tests
        self.other_tenant_user = User(
            id="other_1",
            tenant_id="other_tenant",
            email="other@test.com", 
            name="Other User",
            roles=[Role.VIEWER]
        )

    def test_create_get_update_archive_flow(self):
        """Test CRUD + archive flow with proper User objects."""
        # Create entity
        res = create_entity(
            self.admin, 
            self.repo, 
            tenant_id=self.tenant_id,
            kind="company", 
            name="Test Company",
            metadata={"id": "c_1"}
        )
        self.assertTrue(hasattr(res, "data"), "Create should return ServiceOk")

        # Get entity
        res = get_entity(self.admin, self.repo, tenant_id=self.tenant_id, entity_id="c_1")
        self.assertTrue(hasattr(res, "data"), "Get should return ServiceOk")

        # Update entity
        res = update_entity(
            self.admin, 
            self.repo, 
            tenant_id=self.tenant_id,
            entity_id="c_1", 
            patch={"name": "New Name", "tags": ["tag1"]}
        )
        self.assertTrue(hasattr(res, "data"), "Update should return ServiceOk")

        # Update entity as viewer (should fail)
        res = update_entity(
            self.viewer, 
            self.repo, 
            tenant_id=self.tenant_id,
            entity_id="c_1", 
            patch={"name": "Another Name"}
        )
        self.assertTrue(hasattr(res, "reason"), "Viewer update should return ServiceErr")

        # Archive entity
        res = archive_entity(self.admin, self.repo, tenant_id=self.tenant_id, entity_id="c_1")
        self.assertTrue(hasattr(res, "data"), "Archive should return ServiceOk")

    def test_list_and_search(self):
        """Test list and search functionality."""
        # Seed 2 companies + 1 deal
        create_entity(
            self.admin, 
            self.repo, 
            tenant_id=self.tenant_id,
            kind="company", 
            name="Acme Corp",
            metadata={"id": "acme_1"}
        )
        create_entity(
            self.admin, 
            self.repo, 
            tenant_id=self.tenant_id,
            kind="company", 
            name="Beta LLC",
            metadata={"id": "beta_1"}
        )
        create_entity(
            self.admin, 
            self.repo, 
            tenant_id=self.tenant_id,
            kind="deal", 
            name="Deal 1",
            metadata={"id": "deal_1"}
        )

        # List entities
        res = list_entities(self.admin, self.repo, tenant_id=self.tenant_id, limit=3)
        self.assertTrue(hasattr(res, "data"), "List should return ServiceOk")
        if hasattr(res, "data"):
            self.assertGreaterEqual(len(res.data.items), 3)

        # Search entities
        res = search_entities(self.admin, self.repo, tenant_id=self.tenant_id, q="acme")
        self.assertTrue(hasattr(res, "data"), "Search should return ServiceOk")
        if hasattr(res, "data"):
            self.assertIn("Acme Corp", [entity.name for entity in res.data.items])

        # List entities by kind
        res = list_entities(self.admin, self.repo, tenant_id=self.tenant_id, kind="deal")
        self.assertTrue(hasattr(res, "data"), "List by kind should return ServiceOk")
        if hasattr(res, "data"):
            self.assertTrue(all(entity.kind == "deal" for entity in res.data.items))

    def test_linkage_and_company_summary(self):
        """Test linkage and company summary functionality."""
        # Seed company c_1, contact p_1, deal d_1
        create_entity(
            self.admin, 
            self.repo, 
            tenant_id=self.tenant_id,
            kind="company", 
            name="Test Company",
            metadata={"id": "c_1"}
        )
        create_entity(
            self.admin, 
            self.repo, 
            tenant_id=self.tenant_id,
            kind="contact", 
            name="Test Contact",
            metadata={"id": "p_1"}
        )
        create_entity(
            self.admin, 
            self.repo, 
            tenant_id=self.tenant_id,
            kind="deal", 
            name="Test Deal",
            metadata={"id": "d_1"}
        )

        # Link contact/deal to company
        link_contact_to_company(self.admin, self.repo, tenant_id=self.tenant_id, contact_id="p_1", company_id="c_1")
        link_deal_to_company(self.admin, self.repo, tenant_id=self.tenant_id, deal_id="d_1", company_id="c_1")

        # Get company summary
        res = get_company_summary(self.admin, self.repo, tenant_id=self.tenant_id, company_id="c_1")
        self.assertTrue(hasattr(res, "data"), "Summary should return ServiceOk")
        if hasattr(res, "data"):
            summary = res.data
            self.assertTrue(hasattr(summary, "contacts"), "Summary should have contacts")
            self.assertTrue(hasattr(summary, "deals"), "Summary should have deals")
            self.assertEqual(len(summary.contacts), 1)
            self.assertEqual(len(summary.deals), 1)

        # Repeat as viewer
        res = get_company_summary(self.viewer, self.repo, tenant_id=self.tenant_id, company_id="c_1")
        self.assertTrue(hasattr(res, "data"), "Viewer summary should return ServiceOk")
        if hasattr(res, "data"):
            summary = res.data
            self.assertTrue(hasattr(summary, "contacts"), "Viewer summary should have contacts")
            self.assertTrue(hasattr(summary, "deals"), "Viewer summary should have deals")
            self.assertEqual(len(summary.contacts), 1)
            self.assertEqual(len(summary.deals), 1)

    def test_rbac_guards_basic(self):
        """Test RBAC guards with proper User objects."""
        # Build an Entity
        entity = Entity(
            id="test_entity",
            tenant_id=self.tenant_id,
            name="Test Entity", 
            kind="company"
        )

        # Assert RBAC guards
        self.assertTrue(can_read_entity(self.admin, entity).allow, "Admin should read")
        self.assertTrue(can_write_entity(self.admin, entity).allow, "Admin should write")
        self.assertTrue(can_read_entity(self.viewer, entity).allow, "Viewer should read")
        self.assertFalse(can_write_entity(self.viewer, entity).allow, "Viewer should not write")
        self.assertFalse(can_read_entity(self.other_tenant_user, entity).allow, "Cross-tenant should not read")
        self.assertFalse(can_write_entity(self.other_tenant_user, entity).allow, "Cross-tenant should not write")


if __name__ == "__main__":
    unittest.main()