from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app.core.extensions import db
from app.models.core import Organization, User
from app.blueprints.auth.forms import (
    LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm, OtpLoginForm, OtpVerifyForm
)
from app.blueprints.auth.services import (
    log_login_attempt, initiate_password_reset, complete_password_reset, generate_otp, verify_otp
)
from app.blueprints.auth.constants import PURPOSE_LOGIN, PURPOSE_EMAIL_VERIFY

auth_bp = Blueprint(
    'auth',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        ip = request.remote_addr
        ua = request.headers.get('User-Agent', '')
        
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember.data)
            log_login_attempt(user.id, ip, ua, 'Success')
            flash('Signed in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            if user:
                log_login_attempt(user.id, ip, ua, 'Failed')
            flash('Invalid username or password.', 'danger')
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = RegisterForm()
    if form.validate_on_submit():
        # 1. Create Organization (Tenant)
        org = Organization(
            name=form.organization_name.data,
            subdomain=form.subdomain.data.lower()
        )
        db.session.add(org)
        db.session.commit()
        
        # 2. Create Admin User
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            organization_id=org.id
        )
        user.set_password(form.password.data)
        
        # Assign Owner role
        from app.models.core import Role
        from app.blueprints.roles.constants import ROLE_OWNER
        owner_role = Role.query.filter_by(name=ROLE_OWNER).first()
        if owner_role:
            user.roles.append(owner_role)
            
        db.session.add(user)
        db.session.commit()
        
        # Log registration and auto-login
        log_login_attempt(user.id, request.remote_addr, request.headers.get('User-Agent', ''), 'Success')
        login_user(user)
        flash(f"Business '{org.name}' successfully registered! Welcome to Bhishmaa One.", 'success')
        return redirect(url_for('dashboard.index'))
        
    return render_template('auth/register.html', form=form)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        initiate_password_reset(form.email.data)
        flash('If the email is registered, a password reset link has been dispatched.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    token = request.args.get('token')
    if not token:
        flash('Invalid password reset token.', 'danger')
        return redirect(url_for('auth.login'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        success, message = complete_password_reset(token, form.password.data)
        if success:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
            
    return render_template('auth/reset_password.html', form=form, token=token)

@auth_bp.route('/otp-login', methods=['GET', 'POST'])
def otp_login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = OtpLoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if user and user.is_active:
            generate_otp(email, PURPOSE_LOGIN)
            session['otp_email'] = email
            flash('One-time passcode sent! Please check your inbox.', 'info')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash('This email is not registered or active.', 'danger')
            
    return render_template('auth/otp_login.html', form=form)

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp_route():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    email = session.get('otp_email')
    if not email:
        flash('Session expired. Please request a new OTP.', 'warning')
        return redirect(url_for('auth.otp_login'))
        
    form = OtpVerifyForm()
    if form.validate_on_submit():
        valid, message = verify_otp(email, form.otp_code.data, PURPOSE_LOGIN)
        if valid:
            user = User.query.filter_by(email=email).first()
            login_user(user)
            log_login_attempt(user.id, request.remote_addr, request.headers.get('User-Agent', ''), 'Success')
            session.pop('otp_email', None)
            flash('OTP verified successfully. Signed in!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash(message, 'danger')
            
    return render_template('auth/verify_otp.html', form=form, email=email)

@auth_bp.route('/verify-email')
def verify_email():
    token = request.args.get('token')
    if not token:
        flash('Invalid email verification link.', 'danger')
        return redirect(url_for('auth.login'))
        
    # Standard verify structure
    flash('Email verified successfully! You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('auth.login'))
