import datetime
from app.core.extensions import db
from app.models.core import TenantBase, UUIDType
ATTENDANCE_PRESENT = 'Present'
PAYROLL_DRAFT = 'Draft'

class Attendance(TenantBase):
    __tablename__ = 'attendance'
    
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, default=datetime.date.today, index=True, nullable=False)
    status = db.Column(db.String(30), default=ATTENDANCE_PRESENT, nullable=False)
    
    # Roster times
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('attendance_records', lazy=True, cascade='all, delete-orphan'))
    
    # Enforce one record per employee per day within a single tenant
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'user_id', 'date', name='uq_org_user_date_attendance'),
    )

    def __repr__(self):
        return f"<Attendance {self.user_id} on {self.date}: {self.status}>"

class SalarySlip(TenantBase):
    __tablename__ = 'salary_slips'
    
    slip_number = db.Column(db.String(50), unique=True, index=True, nullable=False)
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Payroll period
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    # Attendance details (at time of slip calculation)
    present_days = db.Column(db.Numeric(4, 1), default=0.0)
    absent_days = db.Column(db.Numeric(4, 1), default=0.0)
    leave_days = db.Column(db.Numeric(4, 1), default=0.0)
    
    # Salary components
    basic_salary = db.Column(db.Numeric(10, 2), default=0.0)
    allowances = db.Column(db.Numeric(10, 2), default=0.0)
    deductions = db.Column(db.Numeric(10, 2), default=0.0)
    net_salary = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Status and mode
    status = db.Column(db.String(30), default=PAYROLL_DRAFT, nullable=False)
    payment_mode = db.Column(db.String(50), nullable=True)
    payment_date = db.Column(db.Date, nullable=True)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('salary_slips', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<SalarySlip {self.slip_number} - Month: {self.month}/{self.year} - Net: ₹{self.net_salary}>"
