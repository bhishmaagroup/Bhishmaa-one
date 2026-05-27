import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, Length
from app.blueprints.hrm.constants import ATTENDANCE_STATUSES

class AttendanceForm(FlaskForm):
    status = SelectField('Attendance Status', choices=[(s, s) for s in ATTENDANCE_STATUSES], validators=[DataRequired()])
    check_in_time = StringField('Check-in Time (HH:MM)', validators=[Optional()])
    check_out_time = StringField('Check-out Time (HH:MM)', validators=[Optional()])
    notes = TextAreaField('Internal Notes / Reason', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Attendance')

class SalarySlipForm(FlaskForm):
    user_id = SelectField('Staff Member', validators=[DataRequired()])
    month = SelectField('Payroll Month', coerce=int, validators=[DataRequired()])
    year = SelectField('Payroll Year', coerce=int, validators=[DataRequired()])
    allowances = DecimalField('Allowances / Bonuses (₹)', default=0.0, validators=[Optional()])
    deductions = DecimalField('Deductions / LOP (₹)', default=0.0, validators=[Optional()])
    submit = SubmitField('Generate Payslip')

    def __init__(self, *args, **kwargs):
        super(SalarySlipForm, self).__init__(*args, **kwargs)
        
        self.month.choices = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
        
        current_year = datetime.date.today().year
        self.year.choices = [(y, str(y)) for y in range(current_year - 2, current_year + 2)]
