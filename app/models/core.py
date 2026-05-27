import uuid
import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.core.extensions import db

# Portable UUID type for Postgres/SQLite
class UUIDType(db.TypeDecorator):
    impl = db.String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(db.String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)

class Base(db.Model):
    __abstract__ = True
    
    id = db.Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, index=True)

    def soft_delete(self):
        self.is_deleted = True
        db.session.commit()

# Branch model
class Branch(Base):
    __tablename__ = 'branches'
    
    organization_id = db.Column(UUIDType, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50), nullable=False, index=True)
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationships
    organization = db.relationship('Organization', backref=db.backref('branches', lazy=True, cascade='all, delete-orphan'))
    
    # Unique branch code per organization
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'code', name='uq_org_branch_code'),
    )
    
    def __repr__(self):
        return f"<Branch {self.name} ({self.code})>"

class TenantBase(Base):
    __abstract__ = True
    
    # Organization-based data isolation
    organization_id = db.Column(UUIDType, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    tenant_id = db.Column(UUIDType, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Branch-based data isolation
    branch_id = db.Column(UUIDType, db.ForeignKey('branches.id', ondelete='SET NULL'), nullable=True, index=True)

# Organization model (Tenant)
class Organization(Base):
    __tablename__ = 'organizations'
    
    name = db.Column(db.String(150), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, index=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    plan_name = db.Column(db.String(50), default='Free')
    
    # Relationships
    users = db.relationship('User', back_populates='organization', lazy=True)
    
    def __repr__(self):
        return f"<Organization {self.name} ({self.subdomain})>"

# Association table for User <-> Role (Many-to-Many)
user_roles = db.Table('user_roles',
    db.Column('user_id', UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role_id', UUIDType, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

# Association table for Role <-> Permission (Many-to-Many)
role_permissions = db.Table('role_permissions',
    db.Column('role_id', UUIDType, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', UUIDType, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)

# Role model
class Role(Base):
    __tablename__ = 'roles'
    
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)
    description = db.Column(db.String(255))
    scope = db.Column(db.String(50), default='branch', nullable=False)  # 'global', 'branch'
    
    # Relationships
    users = db.relationship('User', secondary=user_roles, back_populates='roles')
    permissions = db.relationship('Permission', secondary=role_permissions, back_populates='roles')
    
    def __repr__(self):
        return f"<Role {self.name}>"

# Permission model
class Permission(Base):
    __tablename__ = 'permissions'
    
    name = db.Column(db.String(100), unique=True, index=True, nullable=False)
    description = db.Column(db.String(255))
    module_name = db.Column(db.String(100), nullable=True, index=True)  # e.g., 'hrm', 'pos', 'billing'
    
    # Relationships
    roles = db.relationship('Role', secondary=role_permissions, back_populates='permissions')
    
    def __repr__(self):
        return f"<Permission {self.name}>"

# User model
class User(UserMixin, Base):
    __tablename__ = 'users'
    
    username = db.Column(db.String(80), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Multitenancy organization link
    organization_id = db.Column(UUIDType, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Branch link
    branch_id = db.Column(UUIDType, db.ForeignKey('branches.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Relationships
    organization = db.relationship('Organization', back_populates='users')
    branch = db.relationship('Branch', backref=db.backref('users', lazy=True))
    roles = db.relationship('Role', secondary=user_roles, back_populates='users', lazy='joined')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def has_permission(self, perm_name):
        for role in self.roles:
            if any(perm.name == perm_name for perm in role.permissions):
                return True
        return False
        
    def __repr__(self):
        return f"<User {self.username}>"

# Platform Users (SaaS Administrators)
class PlatformUser(UserMixin, Base):
    __tablename__ = 'platform_users'
    
    username = db.Column(db.String(80), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    role = db.Column(db.String(50), default='platform_admin')  # platform_owner, platform_staff
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_id(self):
        return f"platform_{self.id}"
        
    def has_permission(self, perm_name):
        return False
        
    def __repr__(self):
        return f"<PlatformUser {self.username}>"

# SaaS Activity and Operations Audit Trails
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    platform_user_id = db.Column(UUIDType, db.ForeignKey('platform_users.id', ondelete='SET NULL'), nullable=True, index=True)
    organization_id = db.Column(UUIDType, db.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    old_values = db.Column(db.Text, nullable=True)
    new_values = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))
    platform_user = db.relationship('PlatformUser', backref=db.backref('audit_logs', lazy='dynamic'))
    organization = db.relationship('Organization', backref=db.backref('audit_logs', lazy='dynamic'))
    
    def __repr__(self):
        return f"<AuditLog {self.action} on {self.created_at}>"

