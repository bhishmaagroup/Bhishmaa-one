from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    organization_name = StringField('Business Name', validators=[DataRequired(), Length(min=3, max=150)])
    subdomain = StringField('Subdomain Prefix', validators=[DataRequired(), Length(min=2, max=50)])
    
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register Business')

    def validate_subdomain(self, field):
        from app.models.core import Organization
        org = Organization.query.filter_by(subdomain=field.data.lower()).first()
        if org:
            raise ValidationError('This subdomain is already taken.')

    def validate_email(self, field):
        from app.models.core import User
        user = User.query.filter_by(email=field.data.lower()).first()
        if user:
            raise ValidationError('Email address is already in use.')

    def validate_username(self, field):
        from app.models.core import User
        user = User.query.filter_by(username=field.data.lower()).first()
        if user:
            raise ValidationError('Username is already taken.')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Send Password Reset Link')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Update Password')

class OtpLoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Send One-Time Passcode')

class OtpVerifyForm(FlaskForm):
    otp_code = StringField('One-Time Passcode (6 Digits)', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify & Sign In')

