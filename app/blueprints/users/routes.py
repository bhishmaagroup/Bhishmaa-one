from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.core import User, Role
from app.blueprints.users.forms import StaffCreateForm, StaffEditForm
from app.blueprints.users.services import get_organization_staff, create_staff_member, update_staff_member
from app.blueprints.users.permissions import staff_management_required

users_bp = Blueprint(
    'users',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@users_bp.route('/')
@login_required
@staff_management_required
def list_users():
    staff = get_organization_staff(current_user.organization_id)
    search_query = request.args.get('q', '').strip().lower()
    
    if search_query:
        staff = [
            m for m in staff 
            if search_query in m.first_name.lower() 
            or search_query in m.last_name.lower()
            or search_query in m.username.lower()
            or (m.detail and search_query in m.detail.designation.lower())
        ]
        
    from flask import session
    new_credentials = session.pop('new_staff_credentials', None)
    return render_template('users/list.html', staff=staff, q=search_query, new_credentials=new_credentials)

@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@staff_management_required
def create():
    form = StaffCreateForm()
    # Populate role selection choices dynamically
    form.roles.choices = [(str(role.id), role.name) for role in Role.query.all()]
    
    if form.validate_on_submit():
        data = {
            'username': form.username.data,
            'email': form.email.data,
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'phone': form.phone.data,
            'address': form.address.data,
            'designation': form.designation.data,
            'department': form.department.data,
            'basic_salary': float(form.basic_salary.data or 0.0),
            'roles': form.roles.data
        }
        user = create_staff_member(current_user.organization_id, data)
        
        from flask import session
        session['new_staff_credentials'] = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'email': user.email,
            'password': user.temp_password
        }
        
        flash(f"Staff member '{form.first_name.data}' successfully onboarded!", "success")
        return redirect(url_for('users.list_users'))
        
    return render_template('users/create.html', form=form)

@users_bp.route('/edit/<user_id>', methods=['GET', 'POST'])
@login_required
@staff_management_required
def edit(user_id):
    user = User.query.filter_by(id=user_id, organization_id=current_user.organization_id).first_or_404()
    
    # Pre-populate details
    form_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'is_active': user.is_active,
        'roles': [str(role.id) for role in user.roles]
    }
    if user.detail:
        form_data.update({
            'phone': user.detail.phone,
            'address': user.detail.address,
            'designation': user.detail.designation,
            'department': user.detail.department,
            'basic_salary': user.detail.basic_salary
        })
        
    form = StaffEditForm(data=form_data)
    form.roles.choices = [(str(role.id), role.name) for role in Role.query.all()]
    
    if form.validate_on_submit():
        data = {
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone': form.phone.data,
            'address': form.address.data,
            'designation': form.designation.data,
            'department': form.department.data,
            'basic_salary': float(form.basic_salary.data or 0.0),
            'roles': form.roles.data,
            'is_active': form.is_active.data
        }
        update_staff_member(user.id, data)
        flash("Staff member profile updated successfully!", "success")
        return redirect(url_for('users.list_users'))
        
    return render_template('users/edit.html', form=form, user=user)

@users_bp.route('/details/<user_id>')
@login_required
@staff_management_required
def details(user_id):
    user = User.query.filter_by(id=user_id, organization_id=current_user.organization_id).first_or_404()
    return render_template('users/details.html', user=user)
