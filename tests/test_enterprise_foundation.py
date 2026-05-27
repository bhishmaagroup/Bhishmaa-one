import os
import sys
import unittest
from flask import Flask
from flask_login import login_user
from werkzeug.exceptions import HTTPException

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import create_app, db
from app.models.core import Organization, User, Branch
from app.models.inventory import Product
from app.models.organizations import OrganizationSubscription
from app.middleware.isolation import enforce_tenant_isolation
from app.repositories.user import UserRepository
from app.repositories.inventory import InventoryRepository


class TestEnterpriseFoundation(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create Tenant A & B
        self.orgA = Organization(name="Tenant Alpha", subdomain="tenant-a")
        self.orgB = Organization(name="Tenant Beta", subdomain="tenant-b")
        db.session.add(self.orgA)
        db.session.add(self.orgB)
        db.session.commit()

        # Create User in Tenant A
        self.userA = User(
            username="user_alpha",
            email="alpha@tenant.com",
            organization_id=self.orgA.id
        )
        self.userA.set_password("password")
        db.session.add(self.userA)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.app_context.pop()

    def test_parameter_injection_isolation(self):
        """Verify that requests trying to inject mismatched organization IDs are blocked with 403."""
        # 1. Test clean request (matching organization)
        with self.app.test_request_context('/dashboard?org_id=' + str(self.orgA.id)):
            login_user(self.userA)
            # Should run without raising any HTTPExceptions
            try:
                enforce_tenant_isolation()
            except HTTPException:
                self.fail("enforce_tenant_isolation raised HTTPException on matching org_id")

        # 2. Test query parameter mismatch (trying to inject Tenant B's ID)
        with self.app.test_request_context('/dashboard?org_id=' + str(self.orgB.id)):
            login_user(self.userA)
            with self.assertRaises(HTTPException) as ctx:
                enforce_tenant_isolation()
            self.assertEqual(ctx.exception.code, 403)

        # 3. Test JSON body parameter mismatch
        with self.app.test_request_context('/api/invoices', method='POST', json={'organization_id': str(self.orgB.id)}):
            login_user(self.userA)
            with self.assertRaises(HTTPException) as ctx:
                enforce_tenant_isolation()
            self.assertEqual(ctx.exception.code, 403)

    def test_repository_tenant_scoping(self):
        """Verify that Repository classes automatically scope and isolate queries to the active tenant."""
        # Create a product in Org A and Org B
        prod_a = Product(
            organization_id=self.orgA.id,
            tenant_id=self.orgA.id,
            name="Org A Product",
            sku="SKU-A"
        )
        prod_b = Product(
            organization_id=self.orgB.id,
            tenant_id=self.orgB.id,
            name="Org B Product",
            sku="SKU-B"
        )
        db.session.add(prod_a)
        db.session.add(prod_b)
        db.session.commit()

        # Under context of User A (Org A)
        with self.app.test_request_context('/'):
            login_user(self.userA)
            
            repo = InventoryRepository()
            products = repo.find_all()
            
            # Should only fetch Org A's product
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0].name, "Org A Product")
            self.assertEqual(products[0].sku, "SKU-A")

    def test_subscription_quota_feature_checks(self):
        """Verify that allowed features and validity check methods resolve correctly."""
        sub = OrganizationSubscription(
            organization_id=self.orgA.id,
            plan_name="Premium",
            max_users=10,
            allowed_features='["pos", "inventory", "hrm"]',
            status="Active"
        )
        db.session.add(sub)
        db.session.commit()

        self.assertTrue(sub.is_valid())
        self.assertTrue(sub.has_feature("pos"))
        self.assertTrue(sub.has_feature("hrm"))
        self.assertFalse(sub.has_feature("workflow"))  # Not in the allowed list

        # Expire or change status and confirm feature check fails
        sub.status = "Expired"
        db.session.commit()
        self.assertFalse(sub.has_feature("pos"))


if __name__ == '__main__':
    unittest.main()
