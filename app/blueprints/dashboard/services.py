"""
Dashboard services providing real database-driven metrics for Bhishmaa One ERP.

CRITICAL RULE: All queries are filtered by organization_id to ensure multi-tenant safety.
No fake data. No mocked metrics. All metrics come from PostgreSQL/SQLite.
"""

from datetime import datetime, timedelta, date
from sqlalchemy import func, and_, or_
from app.core.extensions import db
from app.models.core import User
from app.models.billing import Invoice, InvoiceItem
from app.models.inventory import Product
from app.models.expenses import Expense
from app.models.crm import Customer
from app.blueprints.dashboard.utils import format_inr_currency
from app.blueprints.dashboard.widgets import generate_kpi_widgets, get_critical_alerts
from app.blueprints.dashboard.analytics import get_sales_revenue_trend, get_recent_transactions


class DashboardService:
    """Service providing real dashboard metrics from database."""
    
    @staticmethod
    def get_today_bills(organization_id):
        """Get total billing amount for today."""
        today = date.today()
        
        total = db.session.query(
            func.coalesce(func.sum(Invoice.total_amount), 0)
        ).filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False,
            func.date(Invoice.created_at) == today
        ).scalar()
        
        return float(total)
    
    @staticmethod
    def get_today_bills_change_percentage(organization_id):
        """Calculate percentage change from yesterday."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        today_total = db.session.query(
            func.coalesce(func.sum(Invoice.total_amount), 0)
        ).filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False,
            func.date(Invoice.created_at) == today
        ).scalar()
        
        yesterday_total = db.session.query(
            func.coalesce(func.sum(Invoice.total_amount), 0)
        ).filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False,
            func.date(Invoice.created_at) == yesterday
        ).scalar()
        
        today_total = float(today_total) or 0
        yesterday_total = float(yesterday_total) or 0
        
        if yesterday_total == 0:
            return 0
        
        percentage = ((today_total - yesterday_total) / yesterday_total) * 100
        return round(percentage, 1)
    
    @staticmethod
    def get_low_stock_count(organization_id):
        """Count products with stock below minimum threshold."""
        count = db.session.query(Product).filter(
            Product.organization_id == organization_id,
            Product.is_deleted == False,
            Product.current_stock < Product.min_stock_alert
        ).count()
        
        return count
    
    @staticmethod
    def get_low_stock_products(organization_id, limit=5):
        """Get list of low stock products."""
        products = db.session.query(Product).filter(
            Product.organization_id == organization_id,
            Product.is_deleted == False,
            Product.current_stock < Product.min_stock_alert
        ).order_by(Product.current_stock.asc()).limit(limit).all()
        
        return products
    
    @staticmethod
    def get_active_staff_count(organization_id):
        """Count active staff members in organization."""
        count = db.session.query(User).filter(
            User.organization_id == organization_id,
            User.is_active == True,
            User.is_deleted == False
        ).count()
        
        return count
    
    @staticmethod
    def get_month_expenses(organization_id):
        """Get total expenses for current month."""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        
        total = db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(
            Expense.organization_id == organization_id,
            Expense.is_deleted == False,
            Expense.date >= month_start,
            Expense.date <= today
        ).scalar()
        
        return float(total)
    
    @staticmethod
    def get_total_customers(organization_id):
        """Get count of total customers."""
        count = db.session.query(Customer).filter(
            Customer.organization_id == organization_id,
            Customer.is_deleted == False
        ).count()
        
        return count
    
    @staticmethod
    def get_total_invoices(organization_id):
        """Get count of total invoices."""
        count = db.session.query(Invoice).filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False
        ).count()
        
        return count
    
    @staticmethod
    def get_pending_payments(organization_id):
        """Get count of invoices with pending payment status."""
        count = db.session.query(Invoice).filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False,
            Invoice.status.in_(['Pending', 'Partial'])
        ).count()
        
        return count
    
    @staticmethod
    def get_recent_invoices(organization_id, limit=10):
        """Get recent invoices for display."""
        invoices = db.session.query(Invoice).filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False
        ).order_by(Invoice.created_at.desc()).limit(limit).all()
        
        return invoices
    
    @staticmethod
    def get_kpi_widgets(organization_id):
        """Get all KPI widgets with real data."""
        today_bills = DashboardService.get_today_bills(organization_id)
        today_change = DashboardService.get_today_bills_change_percentage(organization_id)
        low_stock_count = DashboardService.get_low_stock_count(organization_id)
        staff_count = DashboardService.get_active_staff_count(organization_id)
        month_expenses = DashboardService.get_month_expenses(organization_id)
        total_customers = DashboardService.get_total_customers(organization_id)
        total_invoices = DashboardService.get_total_invoices(organization_id)
        pending_payments = DashboardService.get_pending_payments(organization_id)
        
        change_indicator = f"+{today_change}% vs yesterday" if today_change >= 0 else f"{today_change}% vs yesterday"
        
        widgets = [
            {
                'title': "Today's Sales",
                'value': format_inr_currency(today_bills),
                'change': change_indicator,
                'color': 'success' if today_change >= 0 else 'danger',
                'icon': 'receipt',
                'metric': 'sales'
            },
            {
                'title': "Low Stock Items",
                'value': f"{low_stock_count} products",
                'change': "Requires attention" if low_stock_count > 0 else "All good",
                'color': 'warning' if low_stock_count > 0 else 'success',
                'icon': 'exclamation-triangle',
                'metric': 'inventory'
            },
            {
                'title': "Active Staff",
                'value': f"{staff_count} users",
                'change': "All accounts active",
                'color': 'info',
                'icon': 'people',
                'metric': 'users'
            },
            {
                'title': "Month Expenses",
                'value': format_inr_currency(month_expenses),
                'change': "Running total",
                'color': 'primary',
                'icon': 'credit-card',
                'metric': 'expenses'
            },
            {
                'title': "Total Invoices",
                'value': f"{total_invoices}",
                'change': f"{pending_payments} pending",
                'color': 'secondary',
                'icon': 'file-text',
                'metric': 'invoices'
            },
            {
                'title': "Total Customers",
                'value': f"{total_customers}",
                'change': "Active customers",
                'color': 'primary',
                'icon': 'person-lines-fill',
                'metric': 'customers'
            }
        ]
        
        return widgets
    
    @staticmethod
    def get_critical_alerts(organization_id):
        """Get real critical alerts from database."""
        alerts = []
        
        # Low stock alerts
        low_stock_products = DashboardService.get_low_stock_products(organization_id, limit=3)
        for product in low_stock_products:
            alerts.append({
                'title': product.name,
                'description': f"Low stock: Only {product.current_stock} {product.get_unit_symbol()} left (Minimum: {product.min_stock_alert})",
                'type': 'warning',
                'icon': 'exclamation-triangle-fill'
            })
        
        # Pending payments alert
        pending_count = DashboardService.get_pending_payments(organization_id)
        if pending_count > 0:
            alerts.append({
                'title': "Pending Payments",
                'description': f"{pending_count} invoice(s) awaiting payment",
                'type': 'info',
                'icon': 'cash-stack'
            })
        
        # Empty state message
        if not alerts:
            alerts.append({
                'title': "All Systems Normal",
                'description': "No critical alerts at this time",
                'type': 'success',
                'icon': 'check-circle-fill'
            })
        
        return alerts
    
    @staticmethod
    def get_sales_revenue_trend(organization_id, range_name='30days'):
        """Get real sales trend data from database."""
        today = date.today()
        
        if range_name == 'today':
            # Hourly breakdown for today
            start_date = datetime.combine(today, datetime.min.time())
            end_date = datetime.combine(today, datetime.max.time())
            
            data = db.session.query(
                func.strftime('%H:00', Invoice.created_at).label('hour'),
                func.coalesce(func.sum(Invoice.total_amount), 0).label('total')
            ).filter(
                Invoice.organization_id == organization_id,
                Invoice.is_deleted == False,
                Invoice.created_at.between(start_date, end_date)
            ).group_by('hour').order_by('hour').all()
            
            # Fill in all hours
            labels = [f"{h:02d}:00" for h in range(6, 22)]
            values = []
            data_dict = {item[0]: float(item[1]) for item in data}
            
            for label in labels:
                values.append(data_dict.get(label, 0))
            
            return {'labels': labels, 'data': values}
        
        elif range_name == '7days':
            # Last 7 days
            start_date = today - timedelta(days=7)
            
            data = db.session.query(
                func.date(Invoice.created_at).label('day'),
                func.coalesce(func.sum(Invoice.total_amount), 0).label('total')
            ).filter(
                Invoice.organization_id == organization_id,
                Invoice.is_deleted == False,
                func.date(Invoice.created_at) >= start_date
            ).group_by(func.date(Invoice.created_at)).order_by(func.date(Invoice.created_at)).all()
            
            labels = []
            values = []
            data_dict = {item[0]: float(item[1]) for item in data}
            
            for i in range(7):
                current_date = today - timedelta(days=6-i)
                labels.append(current_date.strftime('%a'))
                values.append(data_dict.get(current_date, 0))
            
            return {'labels': labels, 'data': values}
        
        else:
            # Default: last 30 days (by week)
            start_date = today - timedelta(days=30)
            
            data = db.session.query(
                func.date(Invoice.created_at).label('day'),
                func.coalesce(func.sum(Invoice.total_amount), 0).label('total')
            ).filter(
                Invoice.organization_id == organization_id,
                Invoice.is_deleted == False,
                func.date(Invoice.created_at) >= start_date
            ).group_by(func.date(Invoice.created_at)).order_by(func.date(Invoice.created_at)).all()
            
            labels = []
            values = []
            data_dict = {item[0]: float(item[1]) for item in data}
            
            for i in range(30):
                current_date = today - timedelta(days=29-i)
                labels.append(current_date.strftime('%d %b'))
                values.append(data_dict.get(current_date, 0))
            
            return {'labels': labels, 'data': values}
    
    @staticmethod
    def get_recent_transactions(organization_id, limit=10):
        """Get real recent transactions from database."""
        invoices = DashboardService.get_recent_invoices(organization_id, limit)
        
        transactions = []
        for invoice in invoices:
            transactions.append({
                'invoice_id': invoice.invoice_number,
                'client_name': invoice.customer_name,
                'tax_info': f"{invoice.customer_gstin or 'No GST'} ({invoice.customer_state_code})",
                'amount': format_inr_currency(float(invoice.total_amount)),
                'status': invoice.status
            })
        
        # Empty state
        if not transactions:
            transactions.append({
                'invoice_id': 'N/A',
                'client_name': 'No transactions yet',
                'tax_info': 'Create your first invoice',
                'amount': '₹ 0.00',
                'status': 'Pending'
            })
        
        return transactions


def get_dashboard_data(organization_id, range_name='30days'):
    """
    Main function to fetch all dashboard data.
    Consolidates widgets, charts, alerts, and transactions.
    
    CRITICAL: organization_id is passed and used in all queries for tenant isolation.
    """
    widgets = generate_kpi_widgets(organization_id)
    chart_data = get_sales_revenue_trend(organization_id, range_name)
    alerts = get_critical_alerts(organization_id)
    transactions = get_recent_transactions(organization_id)
    
    return {
        'widgets': widgets,
        'chart_labels': chart_data['labels'],
        'chart_values': chart_data['data'],
        'alerts': alerts,
        'transactions': transactions
    }

