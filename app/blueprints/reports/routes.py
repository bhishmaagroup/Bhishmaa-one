import datetime
from flask import render_template, request, flash
from flask_login import login_required, current_user
from app.blueprints.reports import reports_bp
from app.blueprints.reports.permissions import reports_management_required
from app.blueprints.reports.services import (
    get_sales_audit_data, get_gst_filing_data, get_profit_loss_sheet
)
from app.models.billing import Invoice

def parse_date_filters():
    """
    Parses start_date and end_date from request parameters, defaulting to the current month.
    """
    today = datetime.date.today()
    start_str = request.args.get('start_date', '').strip()
    end_str = request.args.get('end_date', '').strip()
    
    try:
        start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else datetime.date(today.year, today.month, 1)
        end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
    except ValueError:
        flash("Invalid date format, using current month instead.", "warning")
        start_date = datetime.date(today.year, today.month, 1)
        end_date = today
        
    return start_date, end_date

@reports_bp.route('/')
@login_required
@reports_management_required
def dashboard():
    """
    Renders reports module central dashboard page.
    """
    today = datetime.date.today()
    start_date = datetime.date(today.year, today.month, 1)
    end_date = today
    
    # Pre-calculate simple summary totals for widgets
    sales = get_sales_audit_data(current_user.organization_id, start_date, end_date)
    pl = get_profit_loss_sheet(current_user.organization_id, start_date, end_date)
    
    return render_template(
        'reports/dashboard.html',
        sales=sales,
        pl=pl,
        month_name=today.strftime('%B %Y')
    )

@reports_bp.route('/sales')
@login_required
@reports_management_required
def sales_report():
    """
    Renders detailed sales ledger audit report.
    """
    start_date, end_date = parse_date_filters()
    
    # Query aggregated stats
    audit = get_sales_audit_data(current_user.organization_id, start_date, end_date)
    
    # Query invoice details list in range
    from sqlalchemy import func
    invoices = Invoice.query.filter(
        Invoice.organization_id == current_user.organization_id,
        func.date(Invoice.created_at) >= start_date,
        func.date(Invoice.created_at) <= end_date,
        Invoice.is_deleted == False
    ).order_by(Invoice.created_at.desc()).all()
    
    return render_template(
        'reports/sales_report.html',
        audit=audit,
        invoices=invoices,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

@reports_bp.route('/gst')
@login_required
@reports_management_required
def gst_report():
    """
    Renders GSTR-1 compliance schedules reports.
    """
    start_date, end_date = parse_date_filters()
    
    # Query schedules
    gst_schedules = get_gst_filing_data(current_user.organization_id, start_date, end_date)
    
    return render_template(
        'reports/gst_report.html',
        b2b=gst_schedules['b2b_schedules'],
        b2c=gst_schedules['b2c_schedules'],
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

@reports_bp.route('/profit-loss')
@login_required
@reports_management_required
def profit_loss_report():
    """
    Renders balance sheet profit vs loss statement sheet.
    """
    start_date, end_date = parse_date_filters()
    
    # Query profit loss sheet
    pl = get_profit_loss_sheet(current_user.organization_id, start_date, end_date)
    
    return render_template(
        'reports/profit_loss_report.html',
        pl=pl,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
