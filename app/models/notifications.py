from app.core.extensions import db
from app.models.core import TenantBase, UUIDType

class Notification(TenantBase):
    __tablename__ = 'notifications'
    
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='System')  # 'Stock Alert', 'Sales', 'Payroll', 'System'
    is_read = db.Column(db.Boolean, default=False, index=True)
    link = db.Column(db.String(255), nullable=True)
    
    # Recipient user link (if NULL, broadcast to all organization users)
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    
    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<Notification {self.title} - Read: {self.is_read}>"
