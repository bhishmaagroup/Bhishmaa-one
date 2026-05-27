import os
import sys
import unittest
from datetime import datetime

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import create_app, db
from app.models.core import Organization, User, PlatformUser, AuditLog
from app.blueprints.platform.services import (
    authenticate_platform_user, create_organization_from_platform,
    suspend_organization_from_platform
)

class TestSaaSPlatformLayer(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Ensure tables are created
        db.create_all()
        
        # Seed test platform user
        self.platform_username = "test_platform_admin"
        self.platform_password = "test_platform_pass"
        self.platform_email = "test_platform_admin@bhishmaa.one"
        
        self.p_user = PlatformUser.query.filter_by(username=self.platform_username).first()
        if not self.p_user:
            self.p_user = PlatformUser(
                username=self.platform_username,
                email=self.platform_email,
                first_name="Test",
                last_name="Admin",
                role="platform_owner"
            )
            self.p_user.set_password(self.platform_password)
            db.session.add(self.p_user)
            db.session.commit()
            
        # Seed standard tenant organization and user for testing boundary controls
        self.org_subdomain = "test-tenant-boundary"
        self.org = Organization.query.filter_by(subdomain=self.org_subdomain).first()
        if not self.org:
            self.org = Organization(name="Test Tenant Boundary", subdomain=self.org_subdomain)
            db.session.add(self.org)
            db.session.commit()
            
        self.tenant_username = "test_tenant_user"
        self.tenant_password = "test_tenant_pass"
        self.tenant_user = User.query.filter_by(username=self.tenant_username).first()
        if not self.tenant_user:
            self.tenant_user = User(
                username=self.tenant_username,
                email="test_tenant_user@example.com",
                first_name="Tenant",
                last_name="Employee",
                organization_id=self.org.id
            )
            self.tenant_user.set_password(self.tenant_password)
            db.session.add(self.tenant_user)
            db.session.commit()

    def tearDown(self):
        # Clean up seeded entries
        db.session.rollback()
        db.drop_all()
        self.app_context.pop()

    def test_platform_user_authentication(self):
        """Verify that platform users can authenticate with correct credentials."""
        # Valid credentials
        user = authenticate_platform_user(self.platform_username, self.platform_password)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, self.platform_username)
        
        # Invalid credentials
        user_bad = authenticate_platform_user(self.platform_username, "wrongpass")
        self.assertIsNone(user_bad)

    def test_unauthenticated_platform_access(self):
        """Verify unauthenticated users cannot access platform administration routes."""
        routes = ['/platform/dashboard', '/platform/organizations']
        for route in routes:
            response = self.client.get(route)
            # Should redirect to platform login page
            self.assertEqual(response.status_code, 302)
            self.assertIn('/platform/login', response.location)

    def test_tenant_user_blocked_from_platform(self):
        """Verify tenant users are blocked from accessing the SaaS Platform portal."""
        # Log in as a tenant user
        with self.client:
            self.client.post('/auth/login', data={
                'username': self.tenant_username,
                'password': self.tenant_password
            })
            
            # Attempt to access platform routes
            response = self.client.get('/platform/dashboard')
            # Should redirect to platform login page due to lack of PlatformUser session type
            self.assertEqual(response.status_code, 302)
            self.assertIn('/platform/login', response.location)

    def test_platform_user_blocked_from_tenant_erp(self):
        """Verify platform users are blocked from accessing tenant ERP workflows."""
        # Log in as platform user
        with self.client:
            self.client.post('/platform/login', data={
                'username': self.platform_username,
                'password': self.platform_password
            })
            
            # Attempt to access tenant-specific dashboard
            response = self.client.get('/')
            # Should return 403 Forbidden because platform user has no tenant permissions
            self.assertEqual(response.status_code, 403)

    def test_tenant_onboarding_and_suspension_services(self):
        """Verify onboarding of new tenant and suspension status toggling."""
        onboard_data = {
            'name': "New Onboarded Org",
            'subdomain': "new-onboard",
            'plan_name': "Premium",
            'owner_username': "new_org_owner",
            'owner_email': "owner@newonboard.com",
            'owner_first_name': "Onboard",
            'owner_last_name': "Owner",
            'owner_password': "securepassword123"
        }
        
        # 1. Onboard Tenant
        new_org = create_organization_from_platform(
            data=onboard_data,
            creator_platform_user_id=self.p_user.id,
            ip_address="127.0.0.1",
            user_agent="PyTest"
        )
        
        self.assertIsNotNone(new_org)
        self.assertEqual(new_org.name, "New Onboarded Org")
        self.assertEqual(new_org.plan_name, "Premium")
        
        # Confirm audit log was created for registration
        audit = AuditLog.query.filter_by(action="TENANT_REGISTERED").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.organization_id, new_org.id)
        self.assertEqual(audit.platform_user_id, self.p_user.id)
        
        # 2. Toggle Suspension (Suspend)
        suspended_org = suspend_organization_from_platform(
            org_id=new_org.id,
            modifier_platform_user_id=self.p_user.id,
            ip_address="127.0.0.1",
            user_agent="PyTest"
        )
        self.assertFalse(suspended_org.is_active)
        
        # Confirm audit log was created for suspension
        audit_suspend = AuditLog.query.filter_by(action="TENANT_SUSPENDED").first()
        self.assertIsNotNone(audit_suspend)
        self.assertEqual(audit_suspend.organization_id, new_org.id)
        
        # Clean up created org and owner user from this test block
        owner_user = User.query.filter_by(username="new_org_owner").first()
        if owner_user:
            db.session.delete(owner_user)
        db.session.delete(new_org)
        db.session.commit()

if __name__ == '__main__':
    unittest.main()
