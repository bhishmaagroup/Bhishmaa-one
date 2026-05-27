from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Email, ValidationError
from app.blueprints.crm.validators import validate_phone_number, validate_gst_number

class CustomerForm(FlaskForm):
    name = StringField('Customer Name', validators=[DataRequired(), Length(max=150)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=15)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    gstin = StringField('GSTIN', validators=[Optional(), Length(max=15)])
    state_code = StringField('State Code (GST)', default='07', validators=[DataRequired(), Length(min=2, max=2)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    outstanding_balance = DecimalField('Outstanding Dues (₹)', default=0.0, validators=[Optional()])
    
    submit = SubmitField('Save Customer')

    def validate_phone(self, field):
        if field.data and not validate_phone_number(field.data):
            raise ValidationError('Invalid 10-digit phone number format.')

    def validate_gstin(self, field):
        if field.data and not validate_gst_number(field.data):
            raise ValidationError('Invalid Indian GSTIN format.')

class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired(), Length(max=150)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=15)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    gstin = StringField('GSTIN', validators=[Optional(), Length(max=15)])
    state_code = StringField('State Code (GST)', default='07', validators=[DataRequired(), Length(min=2, max=2)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    outstanding_balance = DecimalField('Outstanding Balance Owed (₹)', default=0.0, validators=[Optional()])
    
    submit = SubmitField('Save Supplier')

    def validate_phone(self, field):
        if field.data and not validate_phone_number(field.data):
            raise ValidationError('Invalid 10-digit phone number format.')

    def validate_gstin(self, field):
        if field.data and not validate_gst_number(field.data):
            raise ValidationError('Invalid Indian GSTIN format.')
