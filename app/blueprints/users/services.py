from app.core.extensions import db
from app.models.core import User, Role
from app.models.users import UserDetail
from app.blueprints.users.utils import generate_random_password

def create_staff_member(organization_id, data):
    """
    Creates a new User profile and links UserDetail metadata.
    Auto-generates temporary passwords.
    """
    from app.services.subscription import check_user_limit
    if not check_user_limit(organization_id):
        raise ValueError("User quota limit reached. Upgrade subscription plan.")

    temp_pass = generate_random_password()
    
    # Auto-generate username if empty
    username = data.get('username')
    if not username:
        base = f"{data['first_name'].lower().strip()}_{data['last_name'].lower().strip()}".replace(' ', '')
        import re
        base = re.sub(r'[^a-zA-Z0-9_]', '', base)
        if not base:
            base = "staff"
        username = base
        counter = 1
        while User.query.filter_by(username=username.lower()).first():
            username = f"{base}_{counter}"
            counter += 1
    username = username.lower()

    # Auto-generate email if empty
    email = data.get('email')
    if not email:
        from app.models.organizations import Organization
        org = Organization.query.get(organization_id)
        org_slug = org.name.lower().strip().replace(' ', '') if org else "bhishmaa"
        import re
        org_slug = re.sub(r'[^a-zA-Z0-9]', '', org_slug)
        if not org_slug:
            org_slug = "bhishmaa"
        email = f"{username}@{org_slug}.com"
        counter = 1
        while User.query.filter_by(email=email.lower()).first():
            email = f"{username}_{counter}@{org_slug}.com"
            counter += 1
    email = email.lower()

    # 1. Create User
    user = User(
        username=username,
        email=email,
        first_name=data['first_name'],
        last_name=data['last_name'],
        organization_id=organization_id,
        is_active=True
    )
    user.set_password(temp_pass)
    user.temp_password = temp_pass
    db.session.add(user)
    db.session.flush()  # Resolve user.id
    
    # 2. Add Roles
    if 'roles' in data:
        assigned_roles = Role.query.filter(Role.id.in_(data['roles'])).all()
        user.roles.extend(assigned_roles)
        
    # 3. Create UserDetail
    detail = UserDetail(
        user_id=user.id,
        phone=data.get('phone'),
        address=data.get('address'),
        designation=data.get('designation', 'Staff'),
        department=data.get('department', 'Operations'),
        basic_salary=data.get('basic_salary', 0.0)
    )
    db.session.add(detail)
    db.session.commit()
    
    # Log temporary password for console validation
    print(f"\n[STAFF CREATION] User: {user.username} | Temporary Password: {temp_pass}\n")
    return user

def update_staff_member(user_id, data):
    """
    Modifies User and linked UserDetail parameters.
    """
    user = User.query.get(user_id)
    if not user:
        return None
        
    # Update User properties
    user.first_name = data['first_name']
    user.last_name = data['last_name']
    user.email = data['email'].lower()
    user.is_active = data.get('is_active', True)
    
    # Sync roles
    if 'roles' in data:
        user.roles = Role.query.filter(Role.id.in_(data['roles'])).all()
        
    # Update detail
    detail = user.detail
    if not detail:
        detail = UserDetail(user_id=user.id)
        db.session.add(detail)
        
    detail.phone = data.get('phone')
    detail.address = data.get('address')
    detail.designation = data.get('designation')
    detail.department = data.get('department')
    detail.basic_salary = data.get('basic_salary', 0.0)
    
    db.session.commit()
    return user

def get_organization_staff(organization_id):
    """
    Fetches all users registered under a specific organization tenant.
    """
    return User.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).all()
