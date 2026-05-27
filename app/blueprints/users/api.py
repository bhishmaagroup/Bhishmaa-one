from flask import request, jsonify
from flask_login import current_user, login_required
from app.blueprints.users.routes import users_bp
from app.blueprints.users.services import get_organization_staff

@users_bp.route('/api/staff', methods=['GET'])
@login_required
def api_list_staff():
    """
    Returns list of all active staff under organization tenant.
    """
    staff = get_organization_staff(current_user.organization_id)
    return jsonify({
        'staff': [{
            'id': member.id,
            'username': member.username,
            'email': member.email,
            'first_name': member.first_name,
            'last_name': member.last_name,
            'designation': member.detail.designation if member.detail else 'Staff',
            'department': member.detail.department if member.detail else 'Operations',
            'is_active': member.is_active
        } for member in staff]
    }), 200
