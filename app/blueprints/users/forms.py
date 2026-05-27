from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, BooleanField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from app.blueprints.users.validators import validate_phone_format
from app.blueprints.users.constants import DESIGNATIONS, DEPARTMENTS

class StaffCreateForm(FlaskForm):
    username = StringField('Username (Auto-generated if empty)', validators=[Optional(), Length(min=3, max=80)])
    email = StringField('Email Address (Auto-generated if empty)', validators=[Optional(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=15)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    
    designation = SelectField('Designation', choices=[(d, d) for d in DESIGNATIONS], default='Staff')
    department = SelectField('Department', choices=[(dept, dept) for dept in DEPARTMENTS], default='Operations')
    basic_salary = DecimalField('Basic Salary (₹)', default=0.0, validators=[Optional()])
    
    roles = SelectMultipleField('Assign System Roles', coerce=str, validators=[DataRequired()])
    submit = SubmitField('Create Staff Member')

    def validate_phone(self, field):
        if field.data and not validate_phone_format(field.data):
            raise ValidationError('Invalid Indian phone number format (must be 10 digits).')

    def validate_username(self, field):
        if not field.data:
            return
        from app.models.core import User
        user = User.query.filter_by(username=field.data.lower()).first()
        if user:
            raise ValidationError('Username is already registered.')

    def validate_email(self, field):
        if not field.data:
            return
        from app.models.core import User
        user = User.query.filter_by(email=field.data.lower()).first()
        if user:
            raise ValidationError('Email address is already registered.')

class StaffEditForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=15)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    
    designation = SelectField('Designation', choices=[(d, d) for d in DESIGNATIONS])
    department = SelectField('Department', choices=[(dept, dept) for dept in DEPARTMENTS])
    basic_salary = DecimalField('Basic Salary (₹)', validators=[Optional()])
    
    roles = SelectMultipleField('System Roles', coerce=str, validators=[DataRequired()])
    is_active = BooleanField('Active Account Status', default=True)
    submit = SubmitField('Save Changes')

    def validate_phone(self, field):
        if field.data and not validate_phone_format(field.data):
            raise ValidationError('Invalid Indian phone number format.')
