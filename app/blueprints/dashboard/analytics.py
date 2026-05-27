from datetime import datetime, timedelta
from app.core.extensions import db
from app.models.billing import Invoice
from app.blueprints.dashboard.utils import format_inr_currency

def get_sales_revenue_trend(organization_id, range_name='30days'):
    """
    Returns real database chart labels and data values for sales revenue trends.
    """
    today = datetime.utcnow().date()
    
    if range_name == 'today':
        invoices = Invoice.query.filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False,
            Invoice.invoice_date == today
        ).all()
        
        hours = ['09:00', '11:00', '13:00', '15:00', '17:00', '19:00', '21:00']
        hourly_data = {h: 0.0 for h in hours}
        
        for inv in invoices:
            h = inv.created_at.hour
            if h < 10: bucket = '09:00'
            elif h < 12: bucket = '11:00'
            elif h < 14: bucket = '13:00'
            elif h < 16: bucket = '15:00'
            elif h < 18: bucket = '17:00'
            elif h < 20: bucket = '19:00'
            else: bucket = '21:00'
            hourly_data[bucket] += float(inv.total_amount or 0.0)
            
        return {
            'labels': hours,
            'data': [hourly_data[h] for h in hours]
        }
        
    elif range_name == '7days':
        start_date = today - timedelta(days=6)
        invoices = Invoice.query.filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False,
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= today
        ).all()
        
        day_map = {start_date + timedelta(days=i): 0.0 for i in range(7)}
        for inv in invoices:
            d = inv.invoice_date
            if d in day_map:
                day_map[d] += float(inv.total_amount or 0.0)
                
        labels = [d.strftime('%a') for d in sorted(day_map.keys())]
        data = [day_map[d] for d in sorted(day_map.keys())]
        return {'labels': labels, 'data': data}
        
    elif range_name == '30days':
        start_date = today - timedelta(days=29)
        invoices = Invoice.query.filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False,
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= today
        ).all()
        
        day_map = {start_date + timedelta(days=i): 0.0 for i in range(30)}
        for inv in invoices:
            d = inv.invoice_date
            if d in day_map:
                day_map[d] += float(inv.total_amount or 0.0)
                
        sorted_dates = sorted(day_map.keys())
        labels = [d.strftime('%b %d') if i % 5 == 0 or d == today else '' for i, d in enumerate(sorted_dates)]
        data = [day_map[d] for d in sorted_dates]
        return {'labels': labels, 'data': data}
        
    else: # Last 6 months
        start_date = today - timedelta(days=180)
        invoices = Invoice.query.filter(
            Invoice.organization_id == organization_id,
            Invoice.is_deleted == False,
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= today
        ).all()
        
        labels = []
        month_keys = []
        for i in range(5, -1, -1):
            d = today - timedelta(days=i*30)
            month_keys.append(d.strftime('%Y-%m'))
            labels.append(d.strftime('%b'))
            
        month_map = {m: 0.0 for m in month_keys}
        for inv in invoices:
            m_key = inv.invoice_date.strftime('%Y-%m')
            if m_key in month_map:
                month_map[m_key] += float(inv.total_amount or 0.0)
                
        return {
            'labels': labels,
            'data': [month_map[m] for m in month_keys]
        }

def get_recent_transactions(organization_id):
    """
    Returns list of real billing operations/transactions from the database.
    """
    invoices = Invoice.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).order_by(Invoice.created_at.desc()).limit(5).all()
    
    transactions = []
    for inv in invoices:
        tax_info = f"{inv.customer_gstin} ({inv.payment_mode})" if inv.customer_gstin else f"Walk-in ({inv.payment_mode})"
        transactions.append({
            'id': str(inv.id),
            'invoice_id': inv.invoice_number,
            'client_name': inv.customer_name,
            'tax_info': tax_info,
            'amount': format_inr_currency(float(inv.total_amount or 0.0)),
            'status': inv.status
        })
    return transactions

