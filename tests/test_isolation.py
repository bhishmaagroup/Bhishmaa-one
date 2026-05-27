import os
import sys
import unittest
from io import BytesIO
from werkzeug.datastructures import FileStorage

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import create_app, db
from app.models.core import Organization, User, Branch, Role
from app.models.inventory import Product
from app.middleware.isolation import verify_tenant_boundary
from app.core.security import validate_file_upload

class TestIsolationAndSecurity(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Ensure database structures exist
        db.create_all()
        
        # Create Test Organization A and its branches/users
        self.org_a = Organization(name="Test Org A", subdomain="org-a")
        db.session.add(self.org_a)
        db.session.commit()
        
        self.branch_a1 = Branch(organization_id=self.org_a.id, name="Branch A1", code="a1")
        self.branch_a2 = Branch(organization_id=self.org_a.id, name="Branch A2", code="a2")
        db.session.add_all([self.branch_a1, self.branch_a2])
        db.session.commit()
        
        self.user_a1 = User(
            username="user_a1",
            email="user_a1@example.com",
            first_name="User",
            last_name="A1",
            organization_id=self.org_a.id,
            branch_id=self.branch_a1.id
        )
        self.user_a1.set_password("password123")
        db.session.add(self.user_a1)
        db.session.commit()
        
        # Create Test Organization B
        self.org_b = Organization(name="Test Org B", subdomain="org-b")
        db.session.add(self.org_b)
        db.session.commit()
        
        self.branch_b = Branch(organization_id=self.org_b.id, name="Branch B", code="b1")
        db.session.add(self.branch_b)
        db.session.commit()
        
    def tearDown(self):
        db.session.rollback()
        # Clean test records
        User.query.filter(User.username.like("user_%")).delete(synchronize_session=False)
        Product.query.filter(Product.name.like("Test Product%")).delete(synchronize_session=False)
        Branch.query.delete()
        Organization.query.delete()
        db.session.commit()
        self.app_context.pop()

    def test_tenant_boundary_verification(self):
        """Verify that verify_tenant_boundary detects cross-tenant and cross-branch data access."""
        # Log in as User A1 (from Org A, Branch A1)
        with self.client:
            self.client.post('/auth/login', data={
                'username': 'user_a1',
                'password': 'password123'
            })
            
            # Create a mock product belonging to Org A, Branch A1
            product_a = Product(
                organization_id=self.org_a.id,
                tenant_id=self.org_a.id,
                branch_id=self.branch_a1.id,
                name="Test Product A"
            )
            
            # Create a mock product belonging to Org B
            product_b = Product(
                organization_id=self.org_b.id,
                tenant_id=self.org_b.id,
                branch_id=self.branch_b.id,
                name="Test Product B"
            )
            
            # Verify Product A belongs to user context: should not raise error
            self.assertTrue(verify_tenant_boundary(product_a))
            
            # Verify Product B (cross-tenant): should raise 403 Forbidden
            from werkzeug.exceptions import Forbidden
            with self.assertRaises(Forbidden):
                verify_tenant_boundary(product_b)
                
            # Create product belonging to Org A but Branch A2 (cross-branch)
            product_a2 = Product(
                organization_id=self.org_a.id,
                tenant_id=self.org_a.id,
                branch_id=self.branch_a2.id,
                name="Test Product A2"
            )
            
            # Since user_a1 is restricted to Branch A1, accessing Branch A2 should raise 403
            with self.assertRaises(Forbidden):
                verify_tenant_boundary(product_a2)

    def test_file_upload_signature_hardening(self):
        """Verify that validate_file_upload blocks fake files and path traversal attempts."""
        # 1. Valid PNG upload with correct signature
        valid_png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        valid_file = FileStorage(
            stream=BytesIO(valid_png_content),
            filename="photo.png",
            content_type="image/png"
        )
        is_valid, msg = validate_file_upload(valid_file)
        self.assertTrue(is_valid)
        self.assertIsNone(msg)
        
        # 2. Fake PNG upload (disguised python script)
        fake_png_content = b'import os; os.system("whoami")'
        fake_file = FileStorage(
            stream=BytesIO(fake_png_content),
            filename="malicious.png",
            content_type="image/png"
        )
        is_valid, msg = validate_file_upload(fake_file)
        self.assertFalse(is_valid)
        self.assertIn("signature mismatch", msg)
        
        # 3. Path traversal filename block
        traversal_file = FileStorage(
            stream=BytesIO(valid_png_content),
            filename="../../malicious.png",
            content_type="image/png"
        )
        is_valid, msg = validate_file_upload(traversal_file)
        self.assertFalse(is_valid)
        self.assertIn("path sequence", msg.lower())

if __name__ == '__main__':
    unittest.main()
