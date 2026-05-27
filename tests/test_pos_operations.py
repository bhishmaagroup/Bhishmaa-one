import os
import sys
import unittest
from datetime import datetime, date
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import create_app, db
from app.models.core import Organization, User, Branch
from app.models.billing import Invoice
from app.models.inventory import Product, BranchStock, StockTransfer, StockTransferItem
from app.blueprints.pos.services import (
    open_register_session, close_register_session, get_active_register_session,
    get_or_create_branch_stock, create_stock_transfer, approve_stock_transfer, cancel_stock_transfer
)
from app.blueprints.pos.utils import generate_barcode_base64, generate_qrcode_base64
from app.blueprints.inventory.services import deduct_stock_from_invoice


class TestPOSOperations(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create Organization
        self.org = Organization(name="Test POS Org", subdomain="test-pos")
        db.session.add(self.org)
        db.session.commit()

        # Create Branches
        self.branchA = Branch(organization_id=self.org.id, name="Branch Alpha", code="B-ALPHA")
        self.branchB = Branch(organization_id=self.org.id, name="Branch Beta", code="B-BETA")
        db.session.add(self.branchA)
        db.session.add(self.branchB)
        db.session.commit()

        # Create User linked to Branch A
        self.user = User(
            username="poscashier",
            email="cashier@test.com",
            first_name="POS",
            last_name="Cashier",
            organization_id=self.org.id,
            branch_id=self.branchA.id
        )
        self.user.set_password("pospassword")
        db.session.add(self.user)
        db.session.commit()

        # Create Product
        self.product = Product(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            name="POS Test Product",
            sku="POS-TEST-SKU",
            current_stock=20.0
        )
        db.session.add(self.product)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.app_context.pop()

    def test_barcode_and_qr_generation(self):
        """Verify that barcode/QR utilities generate non-empty base64 strings."""
        barcode_str = generate_barcode_base64("123456789")
        qrcode_str = generate_qrcode_base64("https://bhishmaa.one")

        self.assertTrue(isinstance(barcode_str, str))
        self.assertTrue(len(barcode_str) > 0)
        self.assertTrue(isinstance(qrcode_str, str))
        self.assertTrue(len(qrcode_str) > 0)

    def test_register_session_flow(self):
        """Test the full shift flow: opening, processing invoices, expected totals, and settlement mismatch."""
        # 1. Open shift
        session = open_register_session(self.user.id, self.branchA.id, 'Counter-01', 1000.00)
        self.assertEqual(session.status, 'Open')
        self.assertEqual(float(session.opening_balance), 1000.00)

        # 2. Add cash invoice
        invoice = Invoice(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            branch_id=self.branchA.id,
            register_session_id=session.id,
            invoice_number="INV-POS-01",
            customer_name="POS Walk-in",
            total_amount=500.50,
            amount_paid=500.50,
            payment_mode="Cash",
            status="Paid"
        )
        db.session.add(invoice)
        db.session.commit()

        # 3. Add UPI invoice
        invoice_upi = Invoice(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            branch_id=self.branchA.id,
            register_session_id=session.id,
            invoice_number="INV-POS-02",
            customer_name="POS UPI Client",
            total_amount=250.00,
            amount_paid=250.00,
            payment_mode="UPI",
            status="Paid"
        )
        db.session.add(invoice_upi)
        db.session.commit()

        # 4. Close shift and reconcile with mismatch
        # Expected cash in drawer = 1000.00 (opening) + 500.50 (cash sale) = 1500.50
        # Simulating that actual cash collected was 1495.50 (₹5 short)
        settled_session = close_register_session(session.id, 1495.50, "₹5 discrepancy note")
        
        self.assertEqual(settled_session.status, 'Closed')
        self.assertEqual(float(settled_session.total_cash_sales), 500.50)
        self.assertEqual(float(settled_session.total_upi_sales), 250.00)
        self.assertEqual(settled_session.expected_cash, 1500.50)
        self.assertEqual(settled_session.mismatch_amount, -5.00)

    def test_branch_stock_deduction_isolation(self):
        """Confirm that stock deducted from Branch A's stock record does not affect Branch B."""
        # Initialize branch stocks
        bs_a = get_or_create_branch_stock(self.branchA.id, self.product.id, self.org.id)
        bs_a.current_stock = Decimal('10.00')
        
        bs_b = get_or_create_branch_stock(self.branchB.id, self.product.id, self.org.id)
        bs_b.current_stock = Decimal('15.00')
        db.session.commit()

        # Deduct 4 items from Branch A
        items = [{'product_name': self.product.name, 'quantity': 4.0}]
        deduct_stock_from_invoice(self.org.id, items, branch_id=self.branchA.id)

        # Retrieve updated stock levels
        updated_a = BranchStock.query.filter_by(branch_id=self.branchA.id, product_id=self.product.id).first()
        updated_b = BranchStock.query.filter_by(branch_id=self.branchB.id, product_id=self.product.id).first()

        self.assertEqual(float(updated_a.current_stock), 6.00)
        self.assertEqual(float(updated_b.current_stock), 15.00)  # Branch B should remain untouched!

    def test_stock_transfers(self):
        """Test stock transfer requests: verify stocks are unchanged during pending status, and updated upon approval."""
        # 1. Initialize stocks
        bs_a = get_or_create_branch_stock(self.branchA.id, self.product.id, self.org.id)
        bs_a.current_stock = Decimal('12.00')
        
        bs_b = get_or_create_branch_stock(self.branchB.id, self.product.id, self.org.id)
        bs_b.current_stock = Decimal('2.00')
        db.session.commit()

        # 2. Request transfer of 5 units from A to B
        transfer = create_stock_transfer(
            from_branch_id=self.branchA.id,
            to_branch_id=self.branchB.id,
            items_list=[{'product_id': self.product.id, 'quantity': 5.0}],
            user_id=self.user.id,
            notes="Transferring surplus stock"
        )
        self.assertEqual(transfer.status, 'Pending')

        # Stock levels should still be unchanged (Pending)
        bs_a_check = BranchStock.query.filter_by(branch_id=self.branchA.id, product_id=self.product.id).first()
        bs_b_check = BranchStock.query.filter_by(branch_id=self.branchB.id, product_id=self.product.id).first()
        self.assertEqual(float(bs_a_check.current_stock), 12.00)
        self.assertEqual(float(bs_b_check.current_stock), 2.00)

        # 3. Approve transfer
        approve_stock_transfer(transfer.id, self.user.id)
        self.assertEqual(transfer.status, 'Approved')

        # Stock levels must reflect transfer adjustments
        bs_a_final = BranchStock.query.filter_by(branch_id=self.branchA.id, product_id=self.product.id).first()
        bs_b_final = BranchStock.query.filter_by(branch_id=self.branchB.id, product_id=self.product.id).first()
        self.assertEqual(float(bs_a_final.current_stock), 7.00)
        self.assertEqual(float(bs_b_final.current_stock), 7.00)

    def test_invoice_edit_and_payment_update(self):
        """Test updating an unpaid invoice to partial and paid states."""
        # 1. Create a draft unpaid invoice
        invoice = Invoice(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            branch_id=self.branchA.id,
            invoice_number="INV-EDIT-01",
            customer_name="Edit Client",
            total_amount=Decimal('1000.00'),
            amount_paid=Decimal('0.00'),
            payment_mode="Cash",
            status="Unpaid"
        )
        db.session.add(invoice)
        db.session.commit()

        # Import update_invoice service
        from app.blueprints.billing.services import update_invoice

        # 2. Update customer name and mark as partially paid (₹400)
        update_data = {
            'customer_name': 'Edit Client Updated',
            'status': 'Partial',
            'amount_paid': 400.00,
            'payment_mode': 'UPI'
        }
        updated_inv = update_invoice(invoice.id, self.org.id, update_data, self.user.id)

        self.assertEqual(updated_inv.customer_name, 'Edit Client Updated')
        self.assertEqual(updated_inv.status, 'Partial')
        self.assertEqual(float(updated_inv.amount_paid), 400.00)
        self.assertEqual(updated_inv.payment_mode, 'UPI')

        # Verify a Payment record was logged for ₹400
        payment = updated_inv.payments.first()
        self.assertIsNotNone(payment)
        self.assertEqual(float(payment.amount), 400.00)
        self.assertEqual(payment.payment_method, 'UPI')

        # 3. Mark as fully paid
        update_data_full = {
            'status': 'Paid',
            'amount_paid': 1000.00
        }
        updated_inv_full = update_invoice(invoice.id, self.org.id, update_data_full, self.user.id)
        self.assertEqual(updated_inv_full.status, 'Paid')
        self.assertEqual(float(updated_inv_full.amount_paid), 1000.00)

        # Verify that another Payment record was logged for the diff (₹600)
        all_payments = updated_inv_full.payments.all()
        self.assertEqual(len(all_payments), 2)
        total_payment_amount = sum(float(p.amount) for p in all_payments)
        self.assertEqual(total_payment_amount, 1000.00)


if __name__ == '__main__':
    unittest.main()

