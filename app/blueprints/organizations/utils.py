from app.blueprints.organizations.constants import PLAN_LIMITS, PLAN_FREE

def get_organization_limits(organization_plan):
    """
    Resolves the staff, invoice, and product limits for a plan name.
    """
    return PLAN_LIMITS.get(organization_plan, PLAN_LIMITS[PLAN_FREE])

def check_organization_limit(organization, metric, current_count):
    """
    Checks if a specific usage metric has reached or exceeded its plan limits.
    Returns True if limit is exceeded, else False.
    """
    limits = get_organization_limits(organization.plan_name)
    max_limit = limits.get(metric)
    
    if max_limit is None:
        return False  # Unlimited
        
    return current_count >= max_limit
