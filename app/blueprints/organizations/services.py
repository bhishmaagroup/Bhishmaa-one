import datetime
from app.core.extensions import db
from app.models.core import Organization
from app.models.organizations import OrganizationDetail, OrganizationSubscription

def update_organization_profile(organization_id, name, subdomain):
    """
    Updates basic profile attributes of an Organization.
    """
    org = Organization.query.get(organization_id)
    if org:
        org.name = name
        org.subdomain = subdomain.lower()
        db.session.commit()
        return org
    return None

def get_or_create_org_details(organization_id):
    """
    Resolves the billing settings details sheet for an organization.
    Creates a blank one with defaults if none exists.
    """
    detail = OrganizationDetail.query.filter_by(organization_id=organization_id).first()
    if not detail:
        org = Organization.query.get(organization_id)
        email = org.users[0].email if org and org.users else ''
        detail = OrganizationDetail(
            organization_id=organization_id,
            billing_email=email
        )
        db.session.add(detail)
        db.session.commit()
    return detail

def update_billing_settings(organization_id, details_data):
    """
    Updates the GSTIN, State code, and billing parameters of an organization.
    """
    detail = get_or_create_org_details(organization_id)
    for key, val in details_data.items():
        if hasattr(detail, key):
            setattr(detail, key, val)
    db.session.commit()
    return detail

def upgrade_subscription_plan(organization_id, new_plan_name, billing_cycle='monthly', amount=0.0):
    """
    Updates the active SaaS plan of an organization and logs details.
    """
    org = Organization.query.get(organization_id)
    if not org:
        return False, "Organization profile not resolved."
        
    # Invalidate older subscriptions
    old_subs = OrganizationSubscription.query.filter_by(
        organization_id=organization_id,
        status='Active'
    ).all()
    for osb in old_subs:
        osb.status = 'Superseded'
        osb.expires_at = datetime.datetime.utcnow()
        
    # Save Organization plan flag
    org.plan_name = new_plan_name
    
    # Save active plan period details
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=365 if billing_cycle == 'annually' else 30)
    
    from app.blueprints.organizations.utils import get_organization_limits
    import json
    limits = get_organization_limits(new_plan_name)
    max_users = limits.get('max_staff', 5)
    allowed_features = json.dumps(limits.get('features', []))

    sub = OrganizationSubscription(
        organization_id=organization_id,
        plan_name=new_plan_name,
        billing_cycle=billing_cycle,
        amount_paid=amount,
        starts_at=datetime.datetime.utcnow(),
        expires_at=expires_at,
        status='Active',
        max_users=max_users,
        allowed_features=allowed_features
    )
    db.session.add(sub)
    db.session.commit()
    return True, "Subscription successfully updated!"
