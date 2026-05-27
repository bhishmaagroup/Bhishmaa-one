from app.repositories.base import BaseRepository
from app.models.core import User


class UserRepository(BaseRepository):
    """
    Data repository for User-related database operations.
    """
    def __init__(self):
        super().__init__(User)

    def get_by_username(self, username):
        """Finds a user by their username within the tenant context."""
        return self._get_base_query().filter_by(username=username).first()

    def get_by_email(self, email):
        """Finds a user by their email (case-insensitive) within the tenant context."""
        if not email:
            return None
        return self._get_base_query().filter(
            User.email == email.strip().lower()
        ).first()
