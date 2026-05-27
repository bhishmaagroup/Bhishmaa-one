import os
import sys
import unittest
from datetime import datetime, date

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import create_app, db
from app.models.core import Organization, User
from app.models.billing import Invoice
from app.models.inventory import Product
from app.models.crm import Customer
from app.blueprints.dashboard.widgets import generate_kpi_widgets, get_critical_alerts
from app.blueprints.dashboard.analytics import get_sales_revenue_trend, get_recent_transactions


class TestDashboardDataLayer(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Get or create a test organization
        self.org = Organization.query.filter_by(subdomain="test-dash").first()
        if not self.org:
            self.org = Organization(name="Test Dash Org", subdomain="test-dash")
            db.session.add(self.org)
            db.session.commit()
            
        # Clean existing test data for this org
        Invoice.query.filter_by(organization_id=self.org.id).delete()
        Product.query.filter_by(organization_id=self.org.id).delete()
        Customer.query.filter_by(organization_id=self.org.id).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.app_context.pop()

    def test_empty_dashboard_kpis(self):
        """Verify that dashboard KPI widgets return zero/empty structures when no data exists."""
        widgets = generate_kpi_widgets(self.org.id)
        
        self.assertEqual(len(widgets), 4)
        
        # Today's Sales KPI should be zero
        sales_kpi = next(w for w in widgets if w['title'] == "Today's Sales")
        self.assertIn("0.00", sales_kpi['value'])
        
        # Low stock KPI should be zero
        low_stock_kpi = next(w for w in widgets if w['title'] == "Low Stock Items")
        self.assertEqual(low_stock_kpi['value'], "0 items")
        self.assertEqual(low_stock_kpi['color'], "success")

    def test_populated_dashboard_kpis(self):
        """Verify that dashboard KPIs populate correctly with real database entries."""
        # 1. Create a product
        prod1 = Product(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            name="Dashboard Test Product",
            sku="DASH-PROD-01",
            current_stock=2.0,
            min_stock_alert=5.0
        )
        db.session.add(prod1)
        
        # 2. Create a customer
        cust1 = Customer(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            name="Dashboard Client"
        )
        db.session.add(cust1)
        
        # 3. Create an invoice
        inv1 = Invoice(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            invoice_number="INV-DASH-101",
            customer_name="Dashboard Client",
            total_amount=5500.50,
            invoice_date=date.today()
        )
        db.session.add(inv1)
        db.session.commit()
        
        widgets = generate_kpi_widgets(self.org.id)
        
        # Today's Sales
        sales_kpi = next(w for w in widgets if w['title'] == "Today's Sales")
        self.assertIn("5,500.50", sales_kpi['value'])
        
        # Low Stock Items
        low_stock_kpi = next(w for w in widgets if w['title'] == "Low Stock Items")
        self.assertEqual(low_stock_kpi['value'], "1 item")
        self.assertEqual(low_stock_kpi['color'], "warning")
        
        # Products
        prod_kpi = next(w for w in widgets if w['title'] == "Products")
        self.assertEqual(prod_kpi['value'], "1 items")
        self.assertIn("1 active customer", prod_kpi['change'])

    def test_dashboard_alerts(self):
        """Verify that get_critical_alerts queries low stock products and pending invoices."""
        # Create low stock product
        prod = Product(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            name="Low Stock Item",
            sku="L-SKU",
            current_stock=1.0,
            min_stock_alert=3.0
        )
        db.session.add(prod)
        
        # Create pending/unpaid invoice
        inv = Invoice(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            invoice_number="INV-PEND",
            customer_name="Test Cust",
            total_amount=1000.00,
            payment_status="Pending",
            amount_paid=0.00
        )
        db.session.add(inv)
        db.session.commit()
        
        alerts = get_critical_alerts(self.org.id)
        
        self.assertEqual(len(alerts), 2)
        self.assertTrue(any(a['type'] == "warning" and "Low Stock Item" in a['title'] for a in alerts))
        self.assertTrue(any(a['type'] == "danger" and "INV-PEND" in a['title'] for a in alerts))

    def test_recent_transactions(self):
        """Verify that recent transactions return real invoice dict lists formatted for the view."""
        inv = Invoice(
            organization_id=self.org.id,
            tenant_id=self.org.id,
            invoice_number="INV-REC",
            customer_name="Recent Cust",
            total_amount=120.00,
            payment_mode="Card",
            status="Paid"
        )
        db.session.add(inv)
        db.session.commit()
        
        txs = get_recent_transactions(self.org.id)
        
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['invoice_id'], "INV-REC")
        self.assertEqual(txs[0]['client_name'], "Recent Cust")
        self.assertIn("Recent Cust", txs[0]['client_name'])
        self.assertIn("Card", txs[0]['tax_info'])
        self.assertEqual(txs[0]['status'], "Paid")


if __name__ == '__main__':
    unittest.main()
