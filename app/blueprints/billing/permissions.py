from functools import wraps
from flask import abort
from flask_login import current_user

def billing_management_required(f):
    """
    Decorator to check if user has permission to manage billing and generate sales invoices.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('can_manage_billing'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
