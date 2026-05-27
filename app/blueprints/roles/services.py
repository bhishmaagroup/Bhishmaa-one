from app.core.extensions import db
from app.models.core import Role, Permission
from app.blueprints.roles.constants import ROLES, PERMISSIONS, DEFAULT_ROLE_PERMISSIONS

def seed_roles_and_permissions():
    """
    Seeds initial system roles and permissions, and maps standard permissions to roles.
    This is called during application startup or migration.
    """
    # 1. Seed Permissions
    permission_objects = {}
    for perm_name, perm_desc in PERMISSIONS.items():
        perm = Permission.query.filter_by(name=perm_name).first()
        if not perm:
            perm = Permission(name=perm_name, description=perm_desc)
            db.session.add(perm)
        else:
            perm.description = perm_desc  # Update description if it changed
        permission_objects[perm_name] = perm
    
    db.session.commit()
    
    # 2. Seed Roles and map permissions
    for role_name in ROLES:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(
                name=role_name,
                description=f"Standard {role_name} role with predefined access permissions."
            )
            db.session.add(role)
            db.session.commit() # Commit to generate ID
            
        # Synced mapped permissions
        target_perm_names = DEFAULT_ROLE_PERMISSIONS.get(role_name, [])
        role.permissions = [permission_objects[p_name] for p_name in target_perm_names if p_name in permission_objects]
    
    db.session.commit()

    # 3. Seed default Platform Owner Administrator
    from app.models.core import PlatformUser
    admin_user = PlatformUser.query.filter_by(username='platform_admin').first()
    if not admin_user:
        admin_user = PlatformUser(
            username='platform_admin',
            email='platform_admin@bhishmaa.one',
            first_name='Bhishmaa',
            last_name='Owner',
            role='platform_owner',
            is_active=True
        )
        admin_user.set_password('platform123')
        db.session.add(admin_user)
        db.session.commit()

    # 4. Seed default Main Branch for organizations and backfill records
    from app.models.core import Organization, Branch, User
    from app.models.billing import Invoice, Payment
    from app.models.inventory import Product, StockTransaction, Category, Brand, Unit
    from app.models.expenses import Expense
    from app.models.hrm import Attendance, SalarySlip
    from app.models.notifications import Notification

    orgs = Organization.query.all()
    for org in orgs:
        # Check if default main branch exists
        branch = Branch.query.filter_by(organization_id=org.id, code='main').first()
        if not branch:
            branch = Branch(
                organization_id=org.id,
                name='Main Branch',
                code='main',
                address='Headquarters Address',
                phone='0000000000',
                is_active=True
            )
            db.session.add(branch)
            db.session.commit()
            
        # Backfill users
        users_to_update = User.query.filter_by(organization_id=org.id, branch_id=None).all()
        for u in users_to_update:
            u.branch_id = branch.id
            
        # Backfill other tenant records
        models_to_backfill = [
            Product, Category, Brand, Unit, StockTransaction,
            Invoice, Payment, Expense, Attendance, SalarySlip, Notification
        ]
        for model in models_to_backfill:
            try:
                records = model.query.filter_by(organization_id=org.id, branch_id=None).all()
                for r in records:
                    r.branch_id = branch.id
            except Exception as e:
                # Catch any database or missing column exceptions gracefully
                pass
                
        db.session.commit()

def get_all_roles():
    """
    Retrieves all roles in the system.
    """
    return Role.query.all()

def get_role_by_id(role_id):
    """
    Retrieves a role by its UUID.
    """
    return Role.query.get(role_id)

def get_all_permissions():
    """
    Retrieves all permissions in the system.
    """
    return Permission.query.order_by(Permission.name).all()

def create_role(name, description, permission_ids):
    """
    Creates a new custom role with associated permissions.
    """
    # Check if role name already exists
    existing = Role.query.filter_by(name=name).first()
    if existing:
        raise ValueError(f"Role with name '{name}' already exists.")
        
    role = Role(name=name, description=description)
    
    # Associate permissions
    if permission_ids:
        perms = Permission.query.filter(Permission.id.in_(permission_ids)).all()
        role.permissions = perms
        
    db.session.add(role)
    db.session.commit()
    return role

def update_role(role_id, name, description, permission_ids):
    """
    Updates role description and permission mapping.
    Prevents updating name of system-defined roles to avoid breaking RBAC logic.
    """
    role = Role.query.get(role_id)
    if not role:
        raise ValueError("Role not found.")
        
    # If it is a system role, we don't allow renaming it
    if role.name in ROLES:
        # Prevent rename but allow description and permission updates
        pass
    else:
        # Verify custom role name does not conflict
        existing = Role.query.filter_by(name=name).first()
        if existing and existing.id != role_id:
            raise ValueError(f"Role with name '{name}' already exists.")
        role.name = name
        
    role.description = description
    
    # Re-sync permissions
    if permission_ids is not None:
        perms = Permission.query.filter(Permission.id.in_(permission_ids)).all()
        role.permissions = perms
        
    db.session.commit()
    return role

def delete_role(role_id):
    """
    Deletes a custom role. Prevents deleting system-defined roles.
    """
    role = Role.query.get(role_id)
    if not role:
        raise ValueError("Role not found.")
        
    if role.name in ROLES:
        raise ValueError("System-defined roles cannot be deleted.")
        
    # Verify no users are currently assigned to this role
    if len(role.users) > 0:
        raise ValueError("Cannot delete role because it is currently assigned to one or more staff members.")
        
    db.session.delete(role)
    db.session.commit()
    return True
