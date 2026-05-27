from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from app.blueprints.organizations.validators import validate_gstin_format
from app.blueprints.organizations.constants import PLAN_FREE, PLAN_STARTER, PLAN_BUSINESS, PLAN_PREMIUM

class OrganizationProfileForm(FlaskForm):
    name = StringField('Business Name', validators=[DataRequired(), Length(min=3, max=150)])
    subdomain = StringField('Subdomain Prefix (Slug)', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Update Profile')

class BillingSettingsForm(FlaskForm):
    gstin = StringField('GSTIN', validators=[Length(max=15)])
    billing_email = StringField('Billing Email', validators=[DataRequired(), Email(), Length(max=120)])
    billing_phone = StringField('Billing Phone', validators=[Length(max=15)])
    billing_address = TextAreaField('Billing Address', validators=[Length(max=500)])
    state_code = SelectField('State Code (GST)', choices=[
        ('01', '01 - Jammu & Kashmir'),
        ('02', '02 - Himachal Pradesh'),
        ('03', '03 - Punjab'),
        ('05', '05 - Uttarakhand'),
        ('06', '06 - Haryana'),
        ('07', '07 - Delhi'),
        ('08', '08 - Rajasthan'),
        ('09', '09 - Uttar Pradesh'),
        ('10', '10 - Bihar'),
        ('19', '19 - West Bengal'),
        ('24', '24 - Gujarat'),
        ('27', '27 - Maharashtra'),
        ('29', '29 - Karnataka'),
        ('33', '33 - Tamil Nadu'),
        ('36', '36 - Telangana')
    ], default='07')
    pan_number = StringField('PAN Number', validators=[Length(max=10)])
    currency = SelectField('Currency', choices=[('INR', 'INR (₹)'), ('USD', 'USD ($)')], default='INR')
    submit = SubmitField('Save Billing Settings')

    def validate_gstin(self, field):
        if field.data and not validate_gstin_format(field.data):
            raise ValidationError('Invalid Indian GSTIN format.')
            
    def validate_pan_number(self, field):
        if field.data and not field.data.isalnum():
            raise ValidationError('PAN must be alphanumeric.')

class ChangePlanForm(FlaskForm):
    plan_name = SelectField('Select Subscription Plan', choices=[
        (PLAN_FREE, 'Free Trial Plan'),
        (PLAN_STARTER, 'Starter Plan (₹ 499 / mo)'),
        (PLAN_BUSINESS, 'Business Premium (₹ 1,499 / mo)'),
        (PLAN_PREMIUM, 'Enterprise Scale (Custom Plan)')
    ], validators=[DataRequired()])
    submit = SubmitField('Change Plan')
