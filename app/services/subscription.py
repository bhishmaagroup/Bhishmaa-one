import json
from app.models.organizations import OrganizationSubscription
from app.models.core import User


def get_active_subscription(organization_id):
    """
    Retrieves the currently active subscription record for a tenant organization.
    """
    if not organization_id:
        return None
    return OrganizationSubscription.query.filter_by(
        organization_id=organization_id,
        status='Active',
        is_deleted=False
    ).order_by(OrganizationSubscription.starts_at.desc()).first()


def is_subscription_active(organization_id):
    """
    Checks if a tenant has a valid, active subscription plan.
    """
    sub = get_active_subscription(organization_id)
    if not sub:
        return False
    return sub.is_valid()


def is_feature_enabled(organization_id, feature_name):
    """
    Checks if a specific module feature slug is unlocked under the tenant's current plan.
    """
    sub = get_active_subscription(organization_id)
    if not sub:
        # Default fallback for Free trial/no plan (only allow core dashboard/billing)
        return feature_name in ['dashboard', 'billing']
    return sub.has_feature(feature_name)


def check_user_limit(organization_id):
    """
    Validates whether a tenant is within their subscription plan user quota.
    Returns True if user count is strictly less than max allowed limit, False otherwise.
    """
    sub = get_active_subscription(organization_id)
    if not sub:
        # Fallback Free plan limit
        limit = 5
    else:
        limit = sub.max_users

    current_users_count = User.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).count()

    return current_users_count < limit
