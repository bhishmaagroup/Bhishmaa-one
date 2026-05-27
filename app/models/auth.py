import datetime
from app.core.extensions import db
from app.models.core import Base, UUIDType

class LoginHistory(Base):
    __tablename__ = 'login_histories'
    
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Success')  # Success, Failed
    device_type = db.Column(db.String(50))  # Mobile, Tablet, Desktop
    location = db.Column(db.String(100))
    
    # Relationships
    user = db.relationship('User', backref=db.backref('login_history', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<LoginHistory {self.user_id} - {self.status} on {self.created_at}>"

class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_token = db.Column(db.String(255), unique=True, index=True, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, index=True)
    last_activity = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('sessions', lazy=True, cascade='all, delete-orphan'))

    def is_valid(self):
        return self.is_active and self.expires_at > datetime.datetime.utcnow()

    def __repr__(self):
        return f"<UserSession {self.user_id} - Active: {self.is_active}>"

class OTPVerification(Base):
    __tablename__ = 'otp_verifications'
    
    email = db.Column(db.String(120), nullable=False, index=True)
    otp_code_hash = db.Column(db.String(128), nullable=False)
    purpose = db.Column(db.String(50), nullable=False)  # login, verify_email, reset_password
    is_used = db.Column(db.Boolean, default=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0)

    def is_expired(self):
        return datetime.datetime.utcnow() > self.expires_at

    def __repr__(self):
        return f"<OTPVerification {self.email} - Used: {self.is_used}>"
