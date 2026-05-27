from flask import request, abort
from flask_login import current_user
from app.models.core import PlatformUser

def enforce_tenant_isolation():
    """
    Flask before_request hook to enforce tenant and branch boundary checks.
    Ensures that any request containing org_id/organization_id/tenant_id/branch_id
    matches the active user's session context across URL path, query params, form data, and JSON body.
    """
    if not current_user or not current_user.is_authenticated:
        return
        
    # Platform users bypass tenant-level isolation filters
    if isinstance(current_user, PlatformUser):
        return
        
    user_org_id = str(current_user.organization_id) if current_user.organization_id else None
    user_branch_id = str(current_user.branch_id) if hasattr(current_user, 'branch_id') and current_user.branch_id else None
    
    # Owners and Managers can operate across branches
    is_admin_or_owner = False
    if hasattr(current_user, 'roles'):
        is_admin_or_owner = any(r.name in ['Owner', 'Manager'] for r in current_user.roles)

    # Collect all parameters to audit
    params = {}
    if request.view_args:
        params.update({k: str(v) for k, v in request.view_args.items() if v is not None})
    if request.args:
        params.update({k: str(v) for k, v in request.args.items() if v is not None})
    if request.form:
        params.update({k: str(v) for k, v in request.form.items() if v is not None})
        
    json_data = request.get_json(silent=True)
    if isinstance(json_data, dict):
        params.update({k: str(v) for k, v in json_data.items() if v is not None})

    # 1. Validate Organization / Tenant ID
    org_keys = ['organization_id', 'org_id', 'tenant_id']
    for key in org_keys:
        if key in params:
            if params[key] != user_org_id:
                abort(403, "Security Access Violation: Organization context mismatch")
                
    # 2. Validate Branch ID for Branch-restricted users
    if 'branch_id' in params:
        if not is_admin_or_owner and params['branch_id'] != user_branch_id:
            abort(403, "Security Access Violation: Branch context mismatch")

def verify_tenant_boundary(*records):
    """
    Validates that database records belong to the active user's organization and branch.
    Raises 403 Forbidden on violation.
    
    Args:
        *records: SQLAlchemy models/records to inspect
    """
    if not current_user or not current_user.is_authenticated or isinstance(current_user, PlatformUser):
        return True
        
    for record in records:
        if record is None:
            continue
            
        # 1. Organization boundary validation
        if hasattr(record, 'organization_id') and record.organization_id:
            rec_org = str(record.organization_id)
            user_org = str(current_user.organization_id) if current_user.organization_id else None
            if rec_org != user_org:
                abort(403, "Security Access Violation: Cross-tenant data leak prevented")
                
        # 2. Branch boundary validation (for non-admin branch-restricted users)
        if hasattr(record, 'branch_id') and record.branch_id and current_user.branch_id:
            rec_branch = str(record.branch_id)
            user_branch = str(current_user.branch_id)
            
            is_admin_or_owner = any(r.name in ['Owner', 'Manager'] for r in current_user.roles)
            if not is_admin_or_owner and rec_branch != user_branch:
                abort(403, "Security Access Violation: Cross-branch data leak prevented")
                
    return True
