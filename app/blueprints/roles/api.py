from flask import request, jsonify, abort
from flask_login import login_required
from app.blueprints.roles.routes import roles_bp
from app.blueprints.roles.services import get_all_roles, get_role_by_id, create_role, update_role, delete_role
from app.blueprints.roles.permissions import role_management_required

@roles_bp.route('/api', methods=['GET'])
@login_required
@role_management_required
def api_get_roles():
    """
    Returns list of all roles.
    """
    roles = get_all_roles()
    return jsonify({
        'roles': [{
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions': [p.name for p in role.permissions]
        } for role in roles]
    }), 200

@roles_bp.route('/api/<role_id>', methods=['GET'])
@login_required
@role_management_required
def api_get_role(role_id):
    """
    Returns a single role.
    """
    role = get_role_by_id(role_id)
    if not role:
        return jsonify({'error': 'Role not found.'}), 404
    return jsonify({
        'id': role.id,
        'name': role.name,
        'description': role.description,
        'permissions': [p.name for p in role.permissions]
    }), 200

@roles_bp.route('/api', methods=['POST'])
@login_required
@role_management_required
def api_create_role():
    """
    Creates a new role via JSON request.
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    permission_ids = data.get('permissions', [])
    
    if not name:
        return jsonify({'error': 'Role name is required.'}), 400
        
    try:
        role = create_role(name, description, permission_ids)
        return jsonify({
            'message': 'Role created successfully.',
            'id': role.id,
            'name': role.name
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@roles_bp.route('/api/<role_id>', methods=['PUT'])
@login_required
@role_management_required
def api_update_role(role_id):
    """
    Updates an existing role via JSON request.
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    permission_ids = data.get('permissions')
    
    try:
        role = update_role(role_id, name, description, permission_ids)
        return jsonify({
            'message': 'Role updated successfully.',
            'id': role.id,
            'name': role.name
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@roles_bp.route('/api/<role_id>', methods=['DELETE'])
@login_required
@role_management_required
def api_delete_role(role_id):
    """
    Deletes a role.
    """
    try:
        delete_role(role_id)
        return jsonify({'message': 'Role deleted successfully.'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
