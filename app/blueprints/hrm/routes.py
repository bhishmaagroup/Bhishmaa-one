import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.core.extensions import db
from app.models.core import User
from app.blueprints.hrm import hrm_bp
from app.core.decorators import subscription_required

@hrm_bp.before_request
@subscription_required('hrm')
def gate_hrm_module():
    pass
from app.blueprints.hrm.forms import AttendanceForm, SalarySlipForm
from app.blueprints.hrm.constants import PAYMENT_MODES
from app.blueprints.hrm.services import (
    get_organization_attendance, log_attendance,
    get_organization_salary_slips, get_salary_slip_by_id,
    generate_salary_slip, pay_salary_slip
)
from app.blueprints.hrm.permissions import hrm_management_required

# ATTENDANCE VIEW ROUTES
@hrm_bp.route('/attendance')
@login_required
@hrm_management_required
def list_attendance():
    """
    Renders daily attendance matrix log sheet.
    """
    date_str = request.args.get('date', '').strip()
    try:
        if date_str:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = datetime.date.today()
    except ValueError:
        flash("Invalid date parameter, loading today instead.", "warning")
        target_date = datetime.date.today()
        
    # Get active organization staff
    staff_list = User.query.filter(
        User.organization_id == current_user.organization_id,
        User.is_active == True,
        User.is_deleted == False
    ).order_by(User.first_name).all()
    
    # Query today's existing records
    records_map = get_organization_attendance(current_user.organization_id, target_date)
    
    return render_template(
        'hrm/attendance.html',
        staff_list=staff_list,
        records_map=records_map,
        target_date=target_date,
        target_date_str=target_date.strftime('%Y-%m-%d')
    )

# PAYROLL VIEW ROUTES
@hrm_bp.route('/payroll')
@login_required
@hrm_management_required
def list_payroll():
    """
    Renders past salary slips ledger.
    """
    month_filter = request.args.get('month', '').strip()
    year_filter = request.args.get('year', '').strip()
    
    month = int(month_filter) if month_filter.isdigit() else None
    year = int(year_filter) if year_filter.isdigit() else None
    
    slips = get_organization_salary_slips(current_user.organization_id, month=month, year=year)
    payment_modes = PAYMENT_MODES
    
    return render_template(
        'hrm/payroll_list.html',
        slips=slips,
        month=month,
        year=year,
        payment_modes=payment_modes
    )

@hrm_bp.route('/payroll/generate', methods=['GET', 'POST'])
@login_required
@hrm_management_required
def generate_payroll_route():
    """
    Form view to calculate and compile a new salary payslip.
    """
    form = SalarySlipForm()
    
    # Populate staff choices dynamically
    active_users = User.query.filter(
        User.organization_id == current_user.organization_id,
        User.is_active == True,
        User.is_deleted == False
    ).order_by(User.first_name).all()
    form.user_id.choices = [(str(u.id), f"{u.first_name or ''} {u.last_name or ''} ({u.username})") for u in active_users]
    
    if form.validate_on_submit():
        try:
            generate_salary_slip(
                organization_id=current_user.organization_id,
                user_id=form.user_id.data,
                month=form.month.data,
                year=form.year.data,
                allowances=float(form.allowances.data or 0.0),
                deductions=float(form.deductions.data or 0.0)
            )
            flash("Salary payslip generated successfully as a Draft.", "success")
            return redirect(url_for('hrm.list_payroll'))
        except ValueError as e:
            flash(str(e), "danger")
            
    # Set default values if not POSTing
    if not form.is_submitted():
        form.month.data = datetime.date.today().month
        form.year.data = datetime.date.today().year
        
    return render_template('hrm/payroll_form.html', form=form)

@hrm_bp.route('/payroll/pay/<slip_id>', methods=['POST'])
@login_required
@hrm_management_required
def pay_payroll_slip_route(slip_id):
    """
    Records payroll payout details.
    """
    payment_mode = request.form.get('payment_mode')
    if payment_mode not in PAYMENT_MODES:
        flash("Invalid payment mode selected.", "danger")
        return redirect(url_for('hrm.list_payroll'))
        
    try:
        pay_salary_slip(slip_id, current_user.organization_id, payment_mode)
        flash("Payslip paid and archived successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
        
    return redirect(url_for('hrm.list_payroll'))

@hrm_bp.route('/payroll/slip/<slip_id>')
@login_required
@hrm_management_required
def view_payroll_slip(slip_id):
    """
    Detailed printable page for a single salary slip receipt.
    """
    slip = get_salary_slip_by_id(slip_id, current_user.organization_id)
    if not slip:
        flash("Salary slip not found.", "danger")
        return redirect(url_for('hrm.list_payroll'))
        
    # Get organization details for header branding
    from app.models.organizations import OrganizationDetail
    org_detail = OrganizationDetail.query.filter_by(organization_id=current_user.organization_id).first()
    
    return render_template('hrm/payslip_detail.html', slip=slip, org_detail=org_detail)
