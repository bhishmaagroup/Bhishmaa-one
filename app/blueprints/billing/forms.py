from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from app.blueprints.billing.constants import PAYMENT_MODES, INVOICE_STATUSES
from app.blueprints.billing.validators import validate_gstin_format, validate_state_code

class InvoiceHeaderForm(FlaskForm):
    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(max=150)])
    customer_phone = StringField('Phone Number', validators=[Optional(), Length(max=15)])
    customer_gstin = StringField('GSTIN', validators=[Optional(), Length(max=15)])
    customer_state_code = StringField('State Code (GST)', default='07', validators=[DataRequired(), Length(min=2, max=2)])
    
    payment_mode = SelectField('Payment Mode', choices=[(m, m) for m in PAYMENT_MODES], default='Cash')
    status = SelectField('Payment Status', choices=[(s, s) for s in INVOICE_STATUSES], default='Paid')
    amount_paid = DecimalField('Amount Paid (₹)', default=0.0, validators=[Optional()])
    discount = DecimalField('Discount (₹)', default=0.0, validators=[Optional()])
    
    submit = SubmitField('Generate Bill')

    def validate_customer_gstin(self, field):
        if field.data and not validate_gstin_format(field.data):
            raise ValidationError('Invalid Indian GSTIN format.')

    def validate_customer_state_code(self, field):
        if field.data and not validate_state_code(field.data):
            raise ValidationError('State code must be a 2-digit numeric code (e.g. 07).')
            
class InvoiceFilterForm(FlaskForm):
    search = StringField('Search client...', validators=[Optional()])
    status = SelectField('Payment Status', choices=[('', 'All Statuses')] + [(s, s) for s in INVOICE_STATUSES], default='')
    submit = SubmitField('Filter')

class InvoiceEditForm(FlaskForm):
    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(max=150)])
    customer_phone = StringField('Phone Number', validators=[Optional(), Length(max=15)])
    customer_gstin = StringField('GSTIN', validators=[Optional(), Length(max=15)])
    customer_state_code = StringField('State Code (GST)', validators=[DataRequired(), Length(min=2, max=2)])
    
    payment_mode = SelectField('Payment Mode', choices=[(m, m) for m in PAYMENT_MODES], default='Cash')
    status = SelectField('Payment Status', choices=[(s, s) for s in INVOICE_STATUSES], default='Paid')
    amount_paid = DecimalField('Amount Paid (₹)', validators=[DataRequired()])
    
    submit = SubmitField('Update Invoice')

    def validate_customer_gstin(self, field):
        if field.data and not validate_gstin_format(field.data):
            raise ValidationError('Invalid Indian GSTIN format.')

    def validate_customer_state_code(self, field):
        if field.data and not validate_state_code(field.data):
            raise ValidationError('State code must be a 2-digit numeric code (e.g. 07).')

