from flask import request, jsonify
from flask_login import current_user, login_required
from app.blueprints.organizations.routes import organizations_bp
from app.blueprints.organizations.utils import get_organization_limits

@organizations_bp.route('/api/profile', methods=['GET'])
@login_required
def api_org_profile():
    """
    Retrieves the tenant's profile metadata and active limits configurations.
    """
    org = current_user.organization
    if not org:
        return jsonify({'message': 'No organization linked to profile.'}), 400
        
    limits = get_organization_limits(org.plan_name)
    details = org.details
    
    return jsonify({
        'organization': {
            'id': org.id,
            'name': org.name,
            'subdomain': org.subdomain,
            'plan_name': org.plan_name,
            'is_active': org.is_active
        },
        'billing_settings': {
            'gstin': details.gstin if details else None,
            'billing_email': details.billing_email if details else None,
            'state_code': details.state_code if details else '07',
            'currency': details.currency if details else 'INR'
        },
        'subscription_limits': limits
    }), 200
