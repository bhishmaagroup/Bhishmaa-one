import json
from sqlalchemy import func
from app.core.extensions import db
from app.models.core import User, Organization, Role, PlatformUser, AuditLog
from app.models.billing import Invoice
from app.blueprints.roles.constants import ROLE_OWNER

def authenticate_platform_user(username, password):
    """
    Validates platform user credentials.
    """
    user = PlatformUser.query.filter_by(username=username, is_active=True).first()
    if user and user.check_password(password):
        return user
    return None

def log_audit_event(action, old_values=None, new_values=None, user_id=None, platform_user_id=None, organization_id=None, ip_address=None, user_agent=None):
    """
    Persists a new audit trail entry inside the database.
    """
    # Convert dict/lists to string if needed
    old_str = json.dumps(old_values) if isinstance(old_values, (dict, list)) else str(old_values) if old_values is not None else None
    new_str = json.dumps(new_values) if isinstance(new_values, (dict, list)) else str(new_values) if new_values is not None else None
    
    log = AuditLog(
        user_id=user_id,
        platform_user_id=platform_user_id,
        organization_id=organization_id,
        action=action,
        old_values=old_str,
        new_values=new_str,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.session.add(log)
    db.session.commit()
    return log

def get_platform_metrics():
    """
    Aggregates overall SaaS platform KPIs.
    """
    total_orgs = Organization.query.filter_by(is_deleted=False).count()
    active_orgs = Organization.query.filter_by(is_active=True, is_deleted=False).count()
    
    # Plans aggregates
    premium_orgs = Organization.query.filter_by(plan_name='Premium', is_deleted=False).count()
    basic_orgs = Organization.query.filter_by(plan_name='Basic', is_deleted=False).count()
    free_orgs = Organization.query.filter_by(plan_name='Free', is_deleted=False).count()
    
    # Global sales sums across all tenants
    total_sales = db.session.query(func.coalesce(func.sum(Invoice.total_amount), 0)).filter(Invoice.is_deleted == False).scalar()
    total_invoices = Invoice.query.filter_by(is_deleted=False).count()
    
    # Global staff users
    total_users = User.query.filter_by(is_deleted=False).count()
    
    # Recent organizations (limit 5)
    recent_orgs = Organization.query.filter_by(is_deleted=False).order_by(Organization.created_at.desc()).limit(5).all()
    
    # Recent audit events (limit 15)
    recent_audits = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(15).all()
    
    return {
        'total_organizations': total_orgs,
        'active_organizations': active_orgs,
        'premium_plans': premium_orgs,
        'basic_plans': basic_orgs,
        'free_plans': free_orgs,
        'gross_sales': float(total_sales),
        'total_invoices': total_invoices,
        'total_users': total_users,
        'recent_organizations': recent_orgs,
        'recent_audits': recent_audits
    }

def create_organization_from_platform(data, creator_platform_user_id=None, ip_address=None, user_agent=None):
    """
    Onboards a new client organization/tenant and seeds the administrator account.
    """
    org_name = data.get('name').strip()
    subdomain = data.get('subdomain').strip().lower()
    plan_name = data.get('plan_name', 'Free')
    
    # Validate subdomain conflict
    conflict = Organization.query.filter_by(subdomain=subdomain, is_deleted=False).first()
    if conflict:
        raise ValueError(f"Subdomain slug '{subdomain}' is already taken.")
        
    # 1. Create Tenant
    org = Organization(
        name=org_name,
        subdomain=subdomain,
        plan_name=plan_name
    )
    db.session.add(org)
    db.session.commit()
    
    # 2. Create Owner User
    user = User(
        username=data.get('owner_username').strip(),
        email=data.get('owner_email').strip().lower(),
        first_name=data.get('owner_first_name').strip(),
        last_name=data.get('owner_last_name').strip(),
        organization_id=org.id
    )
    user.set_password(data.get('owner_password'))
    
    # Assign Owner role
    owner_role = Role.query.filter_by(name=ROLE_OWNER).first()
    if owner_role:
        user.roles.append(owner_role)
        
    db.session.add(user)
    db.session.commit()
    
    # 3. Create Audit Event
    log_audit_event(
        action='TENANT_REGISTERED',
        new_values={'organization': org.name, 'subdomain': org.subdomain, 'plan': org.plan_name, 'owner': user.username},
        platform_user_id=creator_platform_user_id,
        organization_id=org.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return org

def suspend_organization_from_platform(org_id, modifier_platform_user_id=None, ip_address=None, user_agent=None):
    """
    Suspends or reactivates a tenant organization.
    """
    org = Organization.query.get(org_id)
    if not org:
        raise ValueError("Organization not found.")
        
    old_state = org.is_active
    org.is_active = not org.is_active
    db.session.commit()
    
    action = 'TENANT_SUSPENDED' if not org.is_active else 'TENANT_ACTIVATED'
    
    # Log Audit Event
    log_audit_event(
        action=action,
        old_values={'is_active': old_state},
        new_values={'is_active': org.is_active},
        platform_user_id=modifier_platform_user_id,
        organization_id=org.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return org
