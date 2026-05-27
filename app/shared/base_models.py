"""
Shared Base Model Classes for Bhishmaa One Enterprise ERP

All data models inherit from these base classes to ensure:
- Consistent UUID primary keys
- Automatic timestamps
- Soft deletes
- Multi-tenant organization isolation
- Audit trails
"""

import uuid
import datetime
from app.core.extensions import db


class UUIDType(db.TypeDecorator):
    """
    Portable UUID type that works with both PostgreSQL and SQLite.
    Uses native PostgreSQL UUID type, falls back to String for SQLite.
    """
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


class BaseModel(db.Model):
    """
    Abstract base model for all non-tenant-specific entities.
    
    Provides:
    - UUID primary key
    - Created/Updated timestamps
    - Soft delete support
    - Query filtering
    """
    __abstract__ = True
    
    id = db.Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(
        db.DateTime, 
        default=datetime.datetime.utcnow, 
        index=True
    )
    updated_at = db.Column(
        db.DateTime, 
        default=datetime.datetime.utcnow, 
        onupdate=datetime.datetime.utcnow
    )
    is_deleted = db.Column(db.Boolean, default=False, index=True)

    def soft_delete(self):
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        db.session.commit()

    def restore(self):
        """Restore soft-deleted record."""
        self.is_deleted = False
        db.session.commit()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"


class TenantBaseModel(BaseModel):
    """
    Abstract base model for all tenant-scoped (multi-tenant) entities.
    
    CRITICAL: Every query using this model MUST filter by organization_id
    to prevent cross-organization data leakage.
    
    Provides (in addition to BaseModel):
    - Organization-based data isolation
    - Automatic organization_id indexing
    - Tenant safety assertions
    """
    __abstract__ = True
    
    organization_id = db.Column(
        UUIDType,
        db.ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    def __init__(self, *args, **kwargs):
        """Ensure organization_id is set on creation."""
        super().__init__(*args, **kwargs)
        if not self.organization_id:
            from flask_login import current_user
            if current_user.is_authenticated:
                self.organization_id = current_user.organization_id

    @classmethod
    def query_for_org(cls, organization_id):
        """
        Get query filtered to specific organization.
        
        Usage:
            products = Product.query_for_org(org_id).filter(...).all()
        
        Args:
            organization_id: UUID of organization
            
        Returns:
            SQLAlchemy query filtered to organization
        """
        return cls.query.filter_by(
            organization_id=organization_id,
            is_deleted=False
        )

    @classmethod
    def get_for_org(cls, record_id, organization_id):
        """
        Get single record for specific organization (safe get).
        
        Usage:
            product = Product.get_for_org(product_id, org_id)
        
        Args:
            record_id: UUID of record
            organization_id: UUID of organization
            
        Returns:
            Record or None if not found or not in organization
        """
        return cls.query.filter_by(
            id=record_id,
            organization_id=organization_id,
            is_deleted=False
        ).first()


class AuditModel(TenantBaseModel):
    """
    Extended base model with full audit trail.
    
    Provides (in addition to TenantBaseModel):
    - Created by user tracking
    - Updated by user tracking
    - Change reason tracking
    """
    __abstract__ = True
    
    created_by_id = db.Column(
        UUIDType,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    updated_by_id = db.Column(
        UUIDType,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    change_reason = db.Column(db.String(255))

    def __init__(self, *args, **kwargs):
        """Auto-set created_by on creation."""
        super().__init__(*args, **kwargs)
        if not self.created_by_id:
            from flask_login import current_user
            if current_user.is_authenticated:
                self.created_by_id = current_user.id
