from datetime import datetime, date
from sqlalchemy import func
from app.core.extensions import db
from app.models.core import User
from app.models.billing import Invoice
from app.models.inventory import Product
from app.models.crm import Customer
from app.blueprints.dashboard.utils import format_inr_currency

def generate_kpi_widgets(organization_id):
    """
    Generates dynamic KPI widget dictionaries based on real organization metrics.
    """
    today = date.today()
    
    # Today's sales total
    today_sales = db.session.query(func.coalesce(func.sum(Invoice.total_amount), 0)).filter(
        Invoice.organization_id == organization_id,
        Invoice.is_deleted == False,
        Invoice.invoice_date == today
    ).scalar()
    
    # Total products count
    product_count = Product.query.filter_by(
        organization_id=organization_id, 
        is_deleted=False
    ).count()
    
    # Active customers count
    customer_count = Customer.query.filter_by(
        organization_id=organization_id, 
        is_deleted=False
    ).count()
    
    # Low stock alerts count
    low_stock_count = Product.query.filter(
        Product.organization_id == organization_id,
        Product.is_deleted == False,
        Product.current_stock < Product.min_stock_alert
    ).count()
    
    # Active staff count
    staff_count = User.query.filter_by(
        organization_id=organization_id, 
        is_active=True,
        is_deleted=False
    ).count()
    
    widgets = [
        {
            'title': "Today's Sales",
            'value': format_inr_currency(float(today_sales)),
            'change': f"As of {today.strftime('%d %b %Y')}",
            'color': 'primary',
            'icon': 'receipt'
        },
        {
            'title': 'Low Stock Items',
            'value': f"{low_stock_count} item{'s' if low_stock_count != 1 else ''}",
            'change': 'Needs restocking' if low_stock_count > 0 else 'All stocked',
            'color': 'warning' if low_stock_count > 0 else 'success',
            'icon': 'exclamation-triangle' if low_stock_count > 0 else 'check-circle'
        },
        {
            'title': 'Products',
            'value': f"{product_count} items",
            'change': f"{customer_count} active customers",
            'color': 'success',
            'icon': 'box-seam'
        },
        {
            'title': 'Active Staff',
            'value': f"{staff_count} users",
            'change': 'All accounts active',
            'color': 'info',
            'icon': 'people'
        }
    ]
    return widgets

def get_critical_alerts(organization_id):
    """
    Returns list of real critical system and operational alerts for organization.
    """
    alerts = []
    
    # Query low stock products (limit 5)
    low_stock_products = Product.query.filter(
        Product.organization_id == organization_id,
        Product.is_deleted == False,
        Product.current_stock < Product.min_stock_alert
    ).limit(5).all()
    
    for prod in low_stock_products:
        alerts.append({
            'title': prod.name,
            'description': f"Low stock alert: Only {prod.current_stock} {prod.get_unit_symbol()} left.",
            'type': "warning",
            'icon': "exclamation-triangle-fill"
        })
        
    # Query unpaid/pending invoices (limit 3)
    pending_invoices = Invoice.query.filter(
        Invoice.organization_id == organization_id,
        Invoice.is_deleted == False,
        Invoice.payment_status.in_(['Pending', 'Partial'])
    ).order_by(Invoice.created_at.desc()).limit(3).all()
    
    for inv in pending_invoices:
        alerts.append({
            'title': f"Bill {inv.invoice_number} Pending",
            'description': f"Pending balance: ₹{inv.get_pending_amount():.2f} from {inv.customer_name}.",
            'type': "danger",
            'icon': "clock-fill"
        })
        
    return alerts

