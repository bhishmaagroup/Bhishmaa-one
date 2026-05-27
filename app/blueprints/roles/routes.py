from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.blueprints.roles.forms import RoleForm
from app.blueprints.roles.services import (
    get_all_roles, get_role_by_id, create_role, update_role, delete_role, get_all_permissions
)
from app.blueprints.roles.permissions import role_management_required
from app.blueprints.roles.constants import ROLES

roles_bp = Blueprint(
    'roles',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@roles_bp.route('/')
@login_required
@role_management_required
def list_roles():
    """
    Renders list of all system roles and their associated permissions count.
    """
    roles = get_all_roles()
    return render_template('roles/list.html', roles=roles, system_roles=ROLES)

@roles_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_management_required
def create():
    """
    Renders custom role creation form.
    """
    form = RoleForm()
    permissions = get_all_permissions()
    form.permissions.choices = [(str(p.id), f"{p.name} - {p.description}") for p in permissions]
    
    if form.validate_on_submit():
        try:
            create_role(
                name=form.name.data,
                description=form.description.data,
                permission_ids=form.permissions.data
            )
            flash(f"Custom role '{form.name.data}' successfully created!", "success")
            return redirect(url_for('roles.list_roles'))
        except ValueError as e:
            flash(str(e), "danger")
            
    return render_template('roles/create.html', form=form, permissions=permissions)

@roles_bp.route('/edit/<role_id>', methods=['GET', 'POST'])
@login_required
@role_management_required
def edit(role_id):
    """
    Renders editing form for a specific role.
    """
    role = get_role_by_id(role_id)
    if not role:
        flash("Role not found.", "danger")
        return redirect(url_for('roles.list_roles'))
        
    form_data = {
        'name': role.name,
        'description': role.description,
        'permissions': [str(p.id) for p in role.permissions]
    }
    
    form = RoleForm(data=form_data)
    permissions = get_all_permissions()
    form.permissions.choices = [(str(p.id), f"{p.name} - {p.description}") for p in permissions]
    
    # Disable modifying system role names
    is_system = role.name in ROLES
    
    if form.validate_on_submit():
        try:
            update_role(
                role_id=role.id,
                name=role.name if is_system else form.name.data,
                description=form.description.data,
                permission_ids=form.permissions.data
            )
            flash("Role updated successfully!", "success")
            return redirect(url_for('roles.list_roles'))
        except ValueError as e:
            flash(str(e), "danger")
            
    return render_template('roles/edit.html', form=form, role=role, is_system=is_system, permissions=permissions)

@roles_bp.route('/delete/<role_id>', methods=['POST'])
@login_required
@role_management_required
def delete(role_id):
    """
    Triggers deletion of a custom role.
    """
    try:
        delete_role(role_id)
        flash("Role deleted successfully!", "success")
    except ValueError as e:
        flash(str(e), "danger")
        
    return redirect(url_for('roles.list_roles'))
