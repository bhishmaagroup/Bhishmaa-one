"""
Decorators for access control and authorization in Bhishmaa One ERP.

Provides:
- Role-based access control (RBAC)
- Permission-based decorators
- Organization isolation enforcement
"""

from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user


def permission_required(permission_name):
    """
    Decorator to enforce permission-based access.
    
    Usage:
        @app.route('/inventory')
        @login_required
        @permission_required('can_view_inventory')
        def inventory_list():
            return render_template('inventory/index.html')
    
    Args:
        permission_name: Name of permission to check
        
    Raises:
        403 Forbidden if user lacks permission
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.has_permission(permission_name):
                flash('You do not have permission to access this resource.', 'danger')
                abort(403)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def role_required(role_name):
    """
    Decorator to enforce role-based access.
    
    Usage:
        @app.route('/admin/users')
        @login_required
        @role_required('Admin')
        def admin_users():
            return render_template('admin/users.html')
    
    Args:
        role_name: Name of role to check
        
    Raises:
        403 Forbidden if user lacks role
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not any(role.name == role_name for role in current_user.roles):
                flash('You do not have the required role to access this resource.', 'danger')
                abort(403)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def permission_or_role_required(permission_name=None, role_name=None):
    """
    Decorator allowing access if user has permission OR role.
    
    Usage:
        @app.route('/reports')
        @login_required
        @permission_or_role_required(permission_name='can_view_reports', role_name='Manager')
        def reports():
            return render_template('reports/index.html')
    
    Args:
        permission_name: Permission to check (optional)
        role_name: Role to check (optional)
        
    Raises:
        403 Forbidden if user lacks both
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            has_permission = True
            has_role = True
            
            if permission_name:
                has_permission = current_user.has_permission(permission_name)
            
            if role_name:
                has_role = any(role.name == role_name for role in current_user.roles)
            
            if not (has_permission or has_role):
                flash('You do not have permission to access this resource.', 'danger')
                abort(403)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def organization_access_required():
    """
    Decorator to ensure user has active organization.
    
    Usage:
        @app.route('/inventory')
        @login_required
        @organization_access_required()
        def inventory():
            return render_template('inventory/index.html')
    
    Raises:
        403 Forbidden if user has no organization
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.organization_id:
                flash('You must belong to an organization to access this feature.', 'warning')
                abort(403)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def branch_access_required():
    """
    Decorator to ensure user has access to a specific branch.
    If the route has a 'branch_id' parameter, checks that:
    - User has access to that branch (matches current_user.branch_id, or user has admin/owner roles).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
                
            from app.models.core import PlatformUser
            if isinstance(current_user, PlatformUser):
                return func(*args, **kwargs)
                
            branch_id_param = kwargs.get('branch_id')
            if branch_id_param:
                branch_id_param = str(branch_id_param)
                user_branch_id = str(current_user.branch_id) if current_user.branch_id else None
                
                is_admin_or_owner = any(role.name in ['Owner', 'Manager'] for role in current_user.roles)
                if not is_admin_or_owner and branch_id_param != user_branch_id:
                    flash('You do not have access to this branch resource.', 'danger')
                    abort(403)
                    
            return func(*args, **kwargs)
        return wrapper
    return decorator


def subscription_required(feature_name):
    """
    Decorator to gate route access behind SaaS subscription features.
    Aborts with 402 Payment Required if the feature is not active.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
                
            from app.models.core import PlatformUser
            if isinstance(current_user, PlatformUser):
                return func(*args, **kwargs)
                
            from app.services.subscription import is_feature_enabled
            org_id = current_user.organization_id
            
            if not is_feature_enabled(org_id, feature_name):
                # Raise 402 Payment Required for SaaS paywall
                abort(402, f"Feature Locked: '{feature_name}' requires subscription upgrade.")
                
            return func(*args, **kwargs)
        return wrapper
    return decorator
