from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from app.blueprints.organizations.utils import get_organization_limits

def feature_required(feature_name):
    """
    Decorator enforcing that the current user's organization has access
    to a specific SaaS feature flag under their subscription plan.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.organization:
                abort(401)
                
            limits = get_organization_limits(current_user.organization.plan_name)
            allowed_features = limits.get('features', [])
            
            if feature_name not in allowed_features:
                flash(f"Your active plan doesn't include the '{feature_name}' module. Please upgrade.", "warning")
                return redirect(url_for('organizations.subscription'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
