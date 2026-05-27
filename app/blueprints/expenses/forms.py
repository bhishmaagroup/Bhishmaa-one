import datetime
from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from app.blueprints.expenses.constants import EXPENSE_CATEGORIES, EXPENSE_STATUSES, PAYMENT_MODES

class ExpenseForm(FlaskForm):
    category = SelectField('Expense Category', choices=[(c, c) for c in EXPENSE_CATEGORIES], validators=[DataRequired()])
    amount = DecimalField('Amount (₹)', validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than zero.")])
    date = DateField('Expense Date', default=datetime.date.today, format='%Y-%m-%d', validators=[DataRequired()])
    payment_mode = SelectField('Payment Mode', choices=[(m, m) for m in PAYMENT_MODES], default='Cash', validators=[DataRequired()])
    supplier_id = SelectField('Associated Supplier (For Supplier Payments)', validators=[Optional()])
    status = SelectField('Payment Status', choices=[(s, s) for s in EXPENSE_STATUSES], default='Paid', validators=[DataRequired()])
    description = TextAreaField('Description / Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record Expense')
