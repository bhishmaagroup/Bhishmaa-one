from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from app.models.core import PlatformUser

def platform_required(f):
    """
    Decorator to ensure route is only accessible by authenticated SaaS Platform Administrators.
    Redirects unauthenticated or tenant-level users to the platform login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, PlatformUser):
            flash("Authentication required. Platform administrators only.", "danger")
            return redirect(url_for('platform.login'))
        return f(*args, **kwargs)
    return decorated_function
