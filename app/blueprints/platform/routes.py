from flask import render_template, redirect, url_for, flash, request, session, abort
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.platform import platform_bp
from app.blueprints.platform.forms import PlatformLoginForm, TenantOnboardForm, SubscriptionLimitsForm
from app.blueprints.platform.permissions import platform_required
from app.blueprints.platform.services import (
    authenticate_platform_user, get_platform_metrics,
    create_organization_from_platform, suspend_organization_from_platform,
    log_audit_event
)
from app.models.core import Organization, PlatformUser, db

@platform_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Renders SaaS Platform Admin login interface.
    """
    # If already logged in as a Platform User, redirect to platform dashboard
    if current_user.is_authenticated and isinstance(current_user, PlatformUser):
        return redirect(url_for('platform.dashboard'))
        
    form = PlatformLoginForm()
    if form.validate_on_submit():
        user = authenticate_platform_user(form.username.data, form.password.data)
        if user:
            login_user(user, remember=form.remember.data)
            
            # Log audit event
            log_audit_event(
                action='PLATFORM_LOGIN',
                platform_user_id=user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            flash('Platform administrator signed in successfully.', 'success')
            return redirect(url_for('platform.dashboard'))
        else:
            flash('Invalid platform administrator credentials.', 'danger')
            
    return render_template('platform/login.html', form=form)

@platform_bp.route('/dashboard', methods=['GET'])
@platform_required
def dashboard():
    """
    Renders platform stats, metrics, and global SaaS audit logs.
    """
    metrics = get_platform_metrics()
    return render_template(
        'platform/dashboard.html',
        metrics=metrics
    )

@platform_bp.route('/organizations', methods=['GET', 'POST'])
@platform_required
def organizations():
    """
    Renders details of all SaaS tenants. Handles new client onboarding.
    """
    form = TenantOnboardForm()
    
    if form.validate_on_submit():
        data = {
            'name': form.name.data,
            'subdomain': form.subdomain.data,
            'plan_name': form.plan_name.data,
            'owner_username': form.owner_username.data,
            'owner_email': form.owner_email.data,
            'owner_first_name': form.owner_first_name.data,
            'owner_last_name': form.owner_last_name.data,
            'owner_password': form.owner_password.data
        }
        try:
            create_organization_from_platform(
                data=data,
                creator_platform_user_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            flash(f"Business tenant '{form.name.data}' onboarded successfully!", "success")
            return redirect(url_for('platform.organizations'))
        except ValueError as e:
            flash(str(e), "danger")
            
    orgs = Organization.query.filter_by(is_deleted=False).order_by(Organization.created_at.desc()).all()
    return render_template('platform/organizations.html', orgs=orgs, form=form)

@platform_bp.route('/organizations/suspend/<org_id>', methods=['POST'])
@platform_required
def suspend_tenant(org_id):
    """
    Toggles suspension status for a tenant organization.
    """
    try:
        org = suspend_organization_from_platform(
            org_id=org_id,
            modifier_platform_user_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        status = "suspended" if not org.is_active else "reactivated"
        flash(f"Organization '{org.name}' successfully {status}.", "success")
    except ValueError as e:
        flash(str(e), "danger")
        
    return redirect(url_for('platform.organizations'))

@platform_bp.route('/logout', methods=['GET'])
@platform_required
def logout():
    """
    Signs out platform administrator.
    """
    # Log audit event before logging out
    log_audit_event(
        action='PLATFORM_LOGOUT',
        platform_user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')
    )
    logout_user()
    flash('Platform administrator signed out.', 'info')
    return redirect(url_for('platform.login'))


@platform_bp.route('/organizations/limits/<org_id>', methods=['GET', 'POST'])
@platform_required
def edit_limits(org_id):
    """
    Renders and processes tenant subscription configuration and module feature flags.
    """
    org = Organization.query.get(org_id)
    if not org:
        flash("Organization not found.", "danger")
        return redirect(url_for('platform.organizations'))

    from app.models.organizations import OrganizationSubscription
    sub = OrganizationSubscription.query.filter_by(
        organization_id=org.id,
        status='Active',
        is_deleted=False
    ).first()

    if not sub:
        # Create active subscription if missing
        sub = OrganizationSubscription(
            organization_id=org.id,
            plan_name=org.plan_name or 'Free',
            status='Active'
        )
        db.session.add(sub)
        db.session.commit()

    form = SubscriptionLimitsForm()
    
    import json
    if form.validate_on_submit():
        features = []
        if form.feature_pos.data:
            features.append('pos')
        if form.feature_inventory.data:
            features.append('inventory')
        if form.feature_hrm.data:
            features.append('hrm')
        if form.feature_expenses.data:
            features.append('expenses')

        sub.max_users = form.max_users.data
        sub.max_storage_gb = form.max_storage_gb.data
        sub.allowed_features = json.dumps(features)
        db.session.commit()

        # Update organization plan name for syncing
        org.plan_name = org.plan_name # trigger change if any
        db.session.commit()

        log_audit_event(
            action='TENANT_LIMITS_UPDATED',
            new_values={
                'max_users': sub.max_users,
                'max_storage_gb': float(sub.max_storage_gb),
                'allowed_features': features
            },
            platform_user_id=current_user.id,
            organization_id=org.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        flash(f"Subscription limits for '{org.name}' updated successfully.", "success")
        return redirect(url_for('platform.organizations'))

    # Pre-populate form
    if request.method == 'GET':
        form.max_users.data = sub.max_users
        form.max_storage_gb.data = sub.max_storage_gb
        
        try:
            allowed = json.loads(sub.allowed_features or '[]')
        except Exception:
            allowed = []
            
        form.feature_pos.data = 'pos' in allowed
        form.feature_inventory.data = 'inventory' in allowed
        form.feature_hrm.data = 'hrm' in allowed
        form.feature_expenses.data = 'expenses' in allowed

    return render_template('platform/limits.html', form=form, org=org, sub=sub)


@platform_bp.route('/impersonate/<org_id>', methods=['POST'])
@platform_required
def impersonate(org_id):
    """
    Super Admin "Login-as-Tenant" impersonation utility.
    Stores the active platform admin ID in Flask session before switching identity.
    """
    org = Organization.query.get(org_id)
    if not org:
        flash("Organization not found.", "danger")
        return redirect(url_for('platform.organizations'))

    from app.models.core import User, Role
    # Find Owner user
    owner_user = User.query.filter(User.organization_id == org.id).join(User.roles).filter(Role.name == 'Owner').first()
    if not owner_user:
        # Fallback to first user in org
        owner_user = User.query.filter_by(organization_id=org.id, is_deleted=False).first()

    if not owner_user:
        flash("No active users found for this tenant. Impersonation aborted.", "warning")
        return redirect(url_for('platform.organizations'))

    # Store platform impersonator ID in session
    session['impersonator_platform_user_id'] = current_user.id
    
    # Audit log
    log_audit_event(
        action='IMPERSONATION_STARTED',
        new_values={'target_tenant': org.name, 'target_user': owner_user.username},
        platform_user_id=current_user.id,
        organization_id=org.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')
    )

    # Log in as tenant user
    login_user(owner_user)
    flash(f"Impersonating session: logged in as '{owner_user.username}' for '{org.name}'", "info")
    return redirect(url_for('dashboard.index'))


@platform_bp.route('/stop-impersonate', methods=['GET', 'POST'])
@login_required
def stop_impersonate():
    """
    Reverts impersonation session back to the original Platform Administrator.
    Does not use platform_required since user identity is currently mapped to tenant.
    """
    admin_id = session.get('impersonator_platform_user_id')
    if not admin_id:
        flash("No active impersonation session found.", "warning")
        return redirect(url_for('dashboard.index'))

    from app.models.core import PlatformUser
    platform_admin = PlatformUser.query.get(admin_id)
    if not platform_admin:
        flash("Original administrator account not found.", "danger")
        return redirect(url_for('dashboard.index'))

    # Pop impersonator context
    session.pop('impersonator_platform_user_id', None)

    # Log audit event
    log_audit_event(
        action='IMPERSONATION_STOPPED',
        platform_user_id=platform_admin.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')
    )

    # Log back in as admin user
    login_user(platform_admin)
    flash("Impersonation ended. Identity restored to Platform Administrator.", "success")
    return redirect(url_for('platform.dashboard'))
