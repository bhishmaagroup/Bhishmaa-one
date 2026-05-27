import datetime
import random
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.core.extensions import db
from app.models.core import User
from app.models.users import UserDetail
from app.models.hrm import Attendance, SalarySlip
from app.blueprints.hrm.constants import (
    ATTENDANCE_STATUSES, ATTENDANCE_PRESENT, ATTENDANCE_ABSENT,
    ATTENDANCE_HALF_DAY, ATTENDANCE_LATE, ATTENDANCE_ON_LEAVE,
    PAYROLL_DRAFT, PAYROLL_PAID
)

# ATTENDANCE SERVICES
def get_organization_attendance(organization_id, target_date):
    """
    Returns attendance dictionary mapped by user_id for a given date.
    """
    records = Attendance.query.filter_by(
        organization_id=organization_id,
        date=target_date,
        is_deleted=False
    ).all()
    return {r.user_id: r for r in records}

def log_attendance(organization_id, user_id, date, status, check_in=None, check_out=None, notes=None):
    """
    Logs or updates staff attendance log for a specific date.
    """
    if status not in ATTENDANCE_STATUSES:
        raise ValueError(f"Invalid attendance status: {status}")
        
    record = Attendance.query.filter_by(
        organization_id=organization_id,
        user_id=user_id,
        date=date,
        is_deleted=False
    ).first()
    
    if not record:
        record = Attendance(
            organization_id=organization_id,
            tenant_id=organization_id,
            user_id=user_id,
            date=date,
            status=status,
            check_in=check_in,
            check_out=check_out,
            notes=notes
        )
        db.session.add(record)
    else:
        record.status = status
        if check_in:
            record.check_in = check_in
        if check_out:
            record.check_out = check_out
        if notes is not None:
            record.notes = notes
            
    db.session.commit()
    return record

def get_monthly_attendance_summary(organization_id, user_id, month, year):
    """
    Calculates summary of attendance metrics for payroll processing.
    """
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
    records = Attendance.query.filter(
        Attendance.organization_id == organization_id,
        Attendance.user_id == user_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date,
        Attendance.is_deleted == False
    ).all()
    
    present = 0.0
    absent = 0.0
    leaves = 0.0
    lates = 0
    
    for r in records:
        if r.status == ATTENDANCE_PRESENT:
            present += 1.0
        elif r.status == ATTENDANCE_LATE:
            present += 1.0
            lates += 1
        elif r.status == ATTENDANCE_HALF_DAY:
            present += 0.5
            absent += 0.5
        elif r.status == ATTENDANCE_ABSENT:
            absent += 1.0
        elif r.status == ATTENDANCE_ON_LEAVE:
            leaves += 1.0
            
    return {
        'present_days': present,
        'absent_days': absent,
        'leave_days': leaves,
        'late_days': lates
    }

# PAYROLL SERVICES
def get_organization_salary_slips(organization_id, month=None, year=None):
    """
    Retrieves list of generated payslips.
    """
    query = SalarySlip.query.filter_by(organization_id=organization_id, is_deleted=False)
    if month:
        query = query.filter_by(month=month)
    if year:
        query = query.filter_by(year=year)
    return query.order_by(SalarySlip.year.desc(), SalarySlip.month.desc()).all()

def get_salary_slip_by_id(slip_id, organization_id):
    return SalarySlip.query.filter_by(
        id=slip_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()

def calculate_suggested_payroll(organization_id, user_id, month, year):
    """
    Pulls employee salary settings, aggregates attendance, and calculates default deductions.
    """
    detail = UserDetail.query.filter_by(user_id=user_id).first()
    basic_salary = Decimal(str(detail.basic_salary if detail else 0.0))
    
    summary = get_monthly_attendance_summary(organization_id, user_id, month, year)
    
    # Calculate unpaid leave deductions: Basic Salary / 30 per absent day
    absent_days = Decimal(str(summary['absent_days']))
    daily_rate = basic_salary / Decimal('30.0')
    suggested_deductions = daily_rate * absent_days
    
    # Clean calculations
    suggested_deductions = suggested_deductions.quantize(Decimal('0.01'))
    net_salary = (basic_salary - suggested_deductions).quantize(Decimal('0.01'))
    
    return {
        'basic_salary': float(basic_salary),
        'present_days': summary['present_days'],
        'absent_days': summary['absent_days'],
        'leave_days': summary['leave_days'],
        'late_days': summary['late_days'],
        'suggested_allowances': 0.0,
        'suggested_deductions': float(suggested_deductions),
        'suggested_net_salary': float(net_salary)
    }

def generate_salary_slip(organization_id, user_id, month, year, allowances, deductions):
    """
    Creates a new draft salary slip for an employee.
    """
    # Check if a payslip already exists for this staff/month/year combination
    existing = SalarySlip.query.filter_by(
        organization_id=organization_id,
        user_id=user_id,
        month=month,
        year=year,
        is_deleted=False
    ).first()
    
    if existing:
        raise ValueError(f"A payroll record for this staff member already exists for {month}/{year}.")
        
    calc = calculate_suggested_payroll(organization_id, user_id, month, year)
    
    # Format a unique payslip receipt number
    rand_seq = "".join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    slip_number = f"SLIP-{year}-{month:02d}-{rand_seq}"
    
    basic_salary = Decimal(str(calc['basic_salary']))
    allow_decimal = Decimal(str(allowances))
    deduct_decimal = Decimal(str(deductions))
    net_salary = basic_salary + allow_decimal - deduct_decimal
    
    slip = SalarySlip(
        organization_id=organization_id,
        tenant_id=organization_id,
        slip_number=slip_number,
        user_id=user_id,
        month=month,
        year=year,
        present_days=calc['present_days'],
        absent_days=calc['absent_days'],
        leave_days=calc['leave_days'],
        basic_salary=basic_salary,
        allowances=allow_decimal,
        deductions=deduct_decimal,
        net_salary=net_salary,
        status=PAYROLL_DRAFT
    )
    
    db.session.add(slip)
    db.session.commit()
    return slip

def pay_salary_slip(slip_id, organization_id, payment_mode):
    """
    Marks a salary slip as Paid.
    """
    slip = get_salary_slip_by_id(slip_id, organization_id)
    if not slip:
        raise ValueError("Salary slip not found.")
        
    slip.status = PAYROLL_PAID
    slip.payment_mode = payment_mode
    slip.payment_date = datetime.date.today()
    
    db.session.commit()
    return slip
