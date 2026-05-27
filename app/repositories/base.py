from flask_login import current_user
from app.core.extensions import db
from app.models.core import PlatformUser


class BaseRepository:
    """
    Base Repository class providing common CRUD operations.
    Enforces tenant boundaries automatically based on the logged-in user context.
    """
    def __init__(self, model):
        self.model = model

    def _get_base_query(self):
        """
        Creates a base query object. Automatically applies tenant organization filters
        and soft-delete filters if the model supports them.
        """
        query = self.model.query
        
        # Enforce Tenant Isolation at Query Compile Time
        if hasattr(self.model, 'organization_id') and current_user and current_user.is_authenticated:
            if not isinstance(current_user, PlatformUser):
                query = query.filter(self.model.organization_id == current_user.organization_id)
        
        # Enforce Branch Isolation for non-admin/owner branch-restricted users
        if hasattr(self.model, 'branch_id') and current_user and current_user.is_authenticated:
            if not isinstance(current_user, PlatformUser) and current_user.branch_id:
                is_admin_or_owner = any(r.name in ['Owner', 'Manager'] for r in current_user.roles)
                if not is_admin_or_owner:
                    query = query.filter(self.model.branch_id == current_user.branch_id)

        # Apply soft delete filter
        if hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)

        return query

    def get_by_id(self, id):
        """Fetches a single record by ID."""
        return self._get_base_query().filter_by(id=id).first()

    def find_all(self):
        """Retrieves all active records matching the active tenant scope."""
        return self._get_base_query().all()

    def find_by(self, **kwargs):
        """Filters active records by keyword arguments."""
        return self._get_base_query().filter_by(**kwargs).all()

    def find_one_by(self, **kwargs):
        """Retrieves the first active record matching keyword arguments."""
        return self._get_base_query().filter_by(**kwargs).first()

    def create(self, **kwargs):
        """Creates a new record, automatically seeding tenant columns if omitted."""
        if hasattr(self.model, 'organization_id') and 'organization_id' not in kwargs:
            if current_user and current_user.is_authenticated and not isinstance(current_user, PlatformUser):
                kwargs['organization_id'] = current_user.organization_id
                if hasattr(self.model, 'tenant_id') and 'tenant_id' not in kwargs:
                    kwargs['tenant_id'] = current_user.organization_id
                    
        if hasattr(self.model, 'branch_id') and 'branch_id' not in kwargs:
            if current_user and current_user.is_authenticated and not isinstance(current_user, PlatformUser):
                kwargs['branch_id'] = current_user.branch_id

        instance = self.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance

    def update(self, instance, **kwargs):
        """Updates record attributes and commits changes."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    def delete(self, instance):
        """Hard deletes a database record."""
        db.session.delete(instance)
        db.session.commit()
        return True

    def soft_delete(self, instance):
        """Soft deletes a database record if supported, falling back to hard delete."""
        if hasattr(instance, 'soft_delete'):
            instance.soft_delete()
        elif hasattr(instance, 'is_deleted'):
            instance.is_deleted = True
            db.session.commit()
        else:
            self.delete(instance)
        return True

    def count(self):
        """Returns the total number of scoped active records."""
        return self._get_base_query().count()
