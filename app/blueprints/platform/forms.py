from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError

class PlatformLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class TenantOnboardForm(FlaskForm):
    name = StringField('Business Name', validators=[DataRequired(), Length(min=3, max=150)])
    subdomain = StringField('Subdomain Slug', validators=[DataRequired(), Length(min=2, max=50)])
    plan_name = SelectField('Subscription Plan', choices=[('Free', 'Free Plan'), ('Basic', 'Basic Plan'), ('Premium', 'Premium Plan')], default='Free')
    
    # Owner Account Setup
    owner_username = StringField('Owner Username', validators=[DataRequired(), Length(min=3, max=80)])
    owner_email = StringField('Owner Email', validators=[DataRequired(), Email(), Length(max=120)])
    owner_first_name = StringField('Owner First Name', validators=[DataRequired(), Length(max=50)])
    owner_last_name = StringField('Owner Last Name', validators=[DataRequired(), Length(max=50)])
    owner_password = PasswordField('Owner Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Onboard Tenant')

    def validate_subdomain(self, field):
        from app.models.core import Organization
        org = Organization.query.filter_by(subdomain=field.data.lower(), is_deleted=False).first()
        if org:
            raise ValidationError('This subdomain is already taken.')


from wtforms import IntegerField, DecimalField

class SubscriptionLimitsForm(FlaskForm):
    max_users = IntegerField('Maximum User Count', validators=[DataRequired()])
    max_storage_gb = DecimalField('Maximum Storage (GB)', validators=[DataRequired()])
    feature_pos = BooleanField('Point of Sale (POS) Module')
    feature_inventory = BooleanField('Inventory & Warehouses Module')
    feature_hrm = BooleanField('Human Resource Management (HRM) Module')
    feature_expenses = BooleanField('Expense Tracking Module')
    submit = SubmitField('Update Subscription Limits')
