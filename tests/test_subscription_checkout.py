import os
import sys
import unittest
import json
from datetime import datetime, date

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import create_app, db
from app.models.core import Organization, User, Role, Permission
from app.models.organizations import OrganizationSubscription
from app.models.billing import Invoice
from app.models.inventory import Product

class TestSubscriptionCheckout(unittest.TestCase):
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
        
        self.dash_permission = Permission(name='can_view_dashboard', description='View Dashboard')
        self.owner_role.permissions.append(self.dash_permission)
        
        db.session.add(self.owner_role)
        db.session.add(self.staff_role)
        db.session.add(self.dash_permission)
        db.session.commit()
        
        # Seed test organization
        self.org = Organization(name="Checkout Test Org", subdomain="checkout-test", plan_name="Free")
        db.session.add(self.org)
        db.session.commit()
        
        # Seed Owner User
        self.owner_user = User(
            username="checkout_owner",
            email="owner@checkout.com",
            first_name="Checkout",
            last_name="Owner",
            organization_id=self.org.id
        )
        self.owner_user.set_password("ownerpassword123")
        self.owner_user.roles.append(self.owner_role)
        db.session.add(self.owner_user)
        db.session.commit()
        
        # Create initial subscription record
        self.sub = OrganizationSubscription(
            organization_id=self.org.id,
            plan_name="Free",
            status="Active",
            max_users=2,
            allowed_features=json.dumps(['billing'])
        )
        db.session.add(self.sub)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.app_context.pop()

    def _login(self):
        self.client.post('/auth/login', data={
            'username': "checkout_owner",
            'password': "ownerpassword123"
        })

    def test_subscription_page_real_time_metrics(self):
        """Verify the subscription view endpoint calculates and renders real-time limits usage."""
        self._login()
        
        # Add products to test count
        p1 = Product(organization_id=self.org.id, tenant_id=self.org.id, name="Test Product 1", sku="TP1")
        p2 = Product(organization_id=self.org.id, tenant_id=self.org.id, name="Test Product 2", sku="TP2")
        db.session.add_all([p1, p2])
        
        # Add monthly invoices to test count
        inv1 = Invoice(organization_id=self.org.id, tenant_id=self.org.id, invoice_number="INV001", customer_name="Customer 1", total_amount=100.0)
        db.session.add(inv1)
        db.session.commit()
        
        response = self.client.get('/organizations/subscription')
        self.assertEqual(response.status_code, 200)
        
        # Verify the HTML body renders correct counts (1 invoice, 2 products, 1 staff member (the owner))
        html_content = response.data.decode('utf-8')
        self.assertIn("1 / 2", html_content)  # 1 staff out of 2 limit
        self.assertIn("1 / 50", html_content)  # 1 invoice out of 50 limit
        self.assertIn("2 / 20", html_content)  # 2 products out of 20 limit

    def test_checkout_endpoint_invalid_plan(self):
        """Assert that requesting an invalid plan name returns 400."""
        self._login()
        
        response = self.client.post('/organizations/subscription/checkout', 
                                   json={'plan_name': 'InvalidPlan', 'billing_cycle': 'monthly'})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid plan name", response.get_json()['error'])

    def test_checkout_endpoint_free_plan(self):
        """Assert that selecting the Free plan upgrades immediately without requiring payments."""
        self._login()
        
        # Upgrade org to Business first so we can downgrade to Free
        self.org.plan_name = "Business"
        db.session.commit()
        
        response = self.client.post('/organizations/subscription/checkout',
                                   json={'plan_name': 'Free', 'billing_cycle': 'monthly'})
        self.assertEqual(response.status_code, 200)
        res_data = response.get_json()
        self.assertTrue(res_data['success'])
        self.assertTrue(res_data['free_plan'])
        
        # Verify database updated
        self.assertEqual(self.org.plan_name, "Free")
        active_sub = OrganizationSubscription.query.filter_by(organization_id=self.org.id, status='Active').first()
        self.assertEqual(active_sub.plan_name, "Free")
        self.assertEqual(active_sub.max_users, 2)

    def test_checkout_endpoint_starter_plan_simulated(self):
        """Verify checkout order initializer generates correct pricing & simulated context."""
        self._login()
        
        # Monthly billing check
        response = self.client.post('/organizations/subscription/checkout',
                                   json={'plan_name': 'Starter', 'billing_cycle': 'monthly'})
        self.assertEqual(response.status_code, 200)
        res_data = response.get_json()
        
        self.assertTrue(res_data['simulated'])
        self.assertEqual(res_data['amount'], 99900)  # 999 INR in paise
        self.assertEqual(res_data['plan_name'], "Starter")
        self.assertEqual(res_data['billing_cycle'], "monthly")
        self.assertTrue(res_data['order_id'].startswith("order_sim_"))
        
        # Annually billing check (with 20% discount: 999 * 12 * 0.8 = 9590.4 -> 9590 INR -> 959000 paise)
        response_annual = self.client.post('/organizations/subscription/checkout',
                                          json={'plan_name': 'Starter', 'billing_cycle': 'annually'})
        self.assertEqual(response_annual.status_code, 200)
        res_data_annual = response_annual.get_json()
        self.assertEqual(res_data_annual['amount'], 959000)

    def test_callback_simulated_verification_success(self):
        """Assert simulated callback endpoint validates and processes payment upgrades."""
        self._login()
        
        # 1. Trigger checkout to register simulation context in session
        checkout_response = self.client.post('/organizations/subscription/checkout',
                                            json={'plan_name': 'Starter', 'billing_cycle': 'monthly'})
        order_id = checkout_response.get_json()['order_id']
        
        # 2. Call callback endpoint
        callback_payload = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': 'pay_sim_test123',
            'razorpay_signature': 'sig_sim_test123',
            'plan_name': 'Starter',
            'billing_cycle': 'monthly'
        }
        
        callback_response = self.client.post('/organizations/subscription/callback', json=callback_payload)
        self.assertEqual(callback_response.status_code, 200)
        self.assertTrue(callback_response.get_json()['success'])
        
        # 3. Verify DB mutations
        self.assertEqual(self.org.plan_name, "Starter")
        active_sub = OrganizationSubscription.query.filter_by(organization_id=self.org.id, status='Active').first()
        self.assertIsNotNone(active_sub)
        self.assertEqual(active_sub.plan_name, "Starter")
        self.assertEqual(active_sub.billing_cycle, "monthly")
        self.assertEqual(float(active_sub.amount_paid), 999.0)
        self.assertEqual(active_sub.max_users, 5)
        
        # Verify features list contains expected starter modules
        allowed_features = json.loads(active_sub.allowed_features)
        self.assertIn('inventory', allowed_features)
        self.assertIn('expenses', allowed_features)

    def test_callback_simulated_verification_plan_mismatch_fails(self):
        """Assert that callback returns 400 if plan name mismatches the registered order context."""
        self._login()
        
        checkout_response = self.client.post('/organizations/subscription/checkout',
                                            json={'plan_name': 'Starter', 'billing_cycle': 'monthly'})
        order_id = checkout_response.get_json()['order_id']
        
        callback_payload = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': 'pay_sim_test123',
            'razorpay_signature': 'sig_sim_test123',
            'plan_name': 'Premium',  # Mismatched plan name
            'billing_cycle': 'monthly'
        }
        
        callback_response = self.client.post('/organizations/subscription/callback', json=callback_payload)
        self.assertEqual(callback_response.status_code, 400)
        self.assertIn("Plan verification details mismatch", callback_response.get_json()['error'])

if __name__ == '__main__':
    unittest.main()
