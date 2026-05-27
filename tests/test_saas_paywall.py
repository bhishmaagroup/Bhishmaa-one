import os
import sys
import unittest
import json
from datetime import datetime, date

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import create_app, db
from app.models.core import Organization, User, PlatformUser, Role, Permission
from app.models.organizations import OrganizationSubscription
from app.blueprints.users.services import create_staff_member

class TestSaaSPaywall(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create database schema
        db.create_all()
        
        # Seed basic roles and permissions
        self.owner_role = Role(name='Owner', description='Company Owner')
        self.staff_role = Role(name='Staff', description='Normal Staff')
        
        self.hrm_permission = Permission(name='can_manage_hrm', description='Manage HRM')
        self.dash_permission = Permission(name='can_view_dashboard', description='View Dashboard')
        
        self.owner_role.permissions.append(self.hrm_permission)
        self.owner_role.permissions.append(self.dash_permission)
        
        db.session.add(self.owner_role)
        db.session.add(self.staff_role)
        db.session.add(self.hrm_permission)
        db.session.add(self.dash_permission)
        db.session.commit()
        
        # Seed test platform user
        self.platform_username = "paywall_platform_admin"
        self.platform_password = "paywall_platform_pass"
        self.p_user = PlatformUser(
            username=self.platform_username,
            email="platform_admin@bhishmaa.one",
            first_name="Platform",
            last_name="Admin",
            role="platform_owner",
            is_active=True
        )
        self.p_user.set_password(self.platform_password)
        db.session.add(self.p_user)
        db.session.commit()
        
        # Seed test organization
        self.org = Organization(name="Paywall Test Org", subdomain="paywall-test", plan_name="Free")
        db.session.add(self.org)
        db.session.commit()
        
        # Seed Owner User
        self.owner_user = User(
            username="test_owner",
            email="owner@paywall.com",
            first_name="Org",
            last_name="Owner",
            organization_id=self.org.id
        )
        self.owner_user.set_password("ownerpassword123")
        self.owner_user.roles.append(self.owner_role)
        db.session.add(self.owner_user)
        db.session.commit()
        
        # Create subscription record
        self.sub = OrganizationSubscription(
            organization_id=self.org.id,
            plan_name="Free",
            status="Active",
            max_users=2,
            max_storage_gb=1.0,
            allowed_features=json.dumps(['dashboard', 'billing'])
        )
        db.session.add(self.sub)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.app_context.pop()

    def test_user_quota_gating(self):
        """Assert that adding users above the subscription limit raises a ValueError."""
        # Current user count is 1 (owner_user). Subscription max_users is 2.
        
        # 1. Adding a 2nd user (within limit) should succeed
        user2_data = {
            'username': "staff_user2",
            'email': "staff2@paywall.com",
            'first_name': "Staff",
            'last_name': "Two",
            'roles': [str(self.staff_role.id)],
            'phone': "1234567890",
            'address': "123 Street",
            'designation': "Assistant",
            'department': "Sales",
            'basic_salary': 15000.0
        }
        user2 = create_staff_member(self.org.id, user2_data)
        self.assertIsNotNone(user2)
        self.assertEqual(User.query.filter_by(organization_id=self.org.id, is_deleted=False).count(), 2)
        
        # 2. Adding a 3rd user (limit is 2) should fail and raise ValueError
        user3_data = {
            'username': "staff_user3",
            'email': "staff3@paywall.com",
            'first_name': "Staff",
            'last_name': "Three",
            'roles': [str(self.staff_role.id)]
        }
        with self.assertRaises(ValueError) as context:
            create_staff_member(self.org.id, user3_data)
        self.assertIn("User quota limit reached", str(context.exception))

        # 3. Increase limit and verify we can now create the 3rd user
        self.sub.max_users = 3
        db.session.commit()
        user3 = create_staff_member(self.org.id, user3_data)
        self.assertIsNotNone(user3)
        self.assertEqual(User.query.filter_by(organization_id=self.org.id, is_deleted=False).count(), 3)

    def test_feature_subscription_gating(self):
        """Assert that gated blueprint routes return 402 if feature is locked."""
        # The subscription currently only allows 'dashboard' and 'billing'.
        # Try accessing 'hrm' blueprint route '/hrm/attendance' as tenant owner.
        with self.client:
            self.client.post('/auth/login', data={
                'username': "test_owner",
                'password': "ownerpassword123"
            })
            
            response = self.client.get('/hrm/attendance')
            self.assertEqual(response.status_code, 402)
            
            # Now update the subscription to allow 'hrm'
            self.sub.allowed_features = json.dumps(['dashboard', 'billing', 'hrm'])
            db.session.commit()
            
            # Re-requesting the same gated route should succeed (200 OK)
            response = self.client.get('/hrm/attendance')
            self.assertEqual(response.status_code, 200)

    def test_super_admin_impersonation_flow(self):
        """Verify the full impersonation startup and reversion lifecycle."""
        # 1. Log in as platform user
        with self.client:
            login_response = self.client.post('/platform/login', data={
                'username': self.platform_username,
                'password': self.platform_password
            })
            self.assertEqual(login_response.status_code, 302)
            
            # 2. Trigger Impersonation POST /platform/impersonate/<org_id>
            impersonate_response = self.client.post(f'/platform/impersonate/{self.org.id}', follow_redirects=True)
            self.assertIn("Impersonating session: logged in as", impersonate_response.text)
            self.assertIn("test_owner", impersonate_response.text)
            
            # 3. Verify target identity is tenant owner and platform user ID is saved in session
            from flask import session
            self.assertEqual(session.get('impersonator_platform_user_id'), self.p_user.id)
            
            # 4. End Impersonation (GET /platform/stop-impersonate)
            stop_response = self.client.get('/platform/stop-impersonate', follow_redirects=True)
            self.assertEqual(stop_response.status_code, 200)
            self.assertIn("Identity restored to Platform Administrator", stop_response.text)
            
            # 5. Verify impersonator session ID is popped and platform user is back in session
            self.assertNotIn('impersonator_platform_user_id', session)

if __name__ == '__main__':
    unittest.main()
