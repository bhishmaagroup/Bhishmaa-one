import datetime
import json
from app.core.extensions import db
from app.models.core import Base, UUIDType

class OrganizationSubscription(Base):
    __tablename__ = 'organization_subscriptions'
    
    organization_id = db.Column(UUIDType, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    plan_name = db.Column(db.String(50), default='Free', nullable=False)
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, annually
    amount_paid = db.Column(db.Numeric(10, 2), default=0.0)
    starts_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Active', index=True)  # Active, Expired, Suspended, Cancelled
    payment_reference = db.Column(db.String(100))
    
    # Quota Limits & Features (SaaS Constraints)
    max_users = db.Column(db.Integer, default=5, nullable=False)
    max_storage_gb = db.Column(db.Numeric(10, 2), default=5.0, nullable=False)
    allowed_features = db.Column(db.Text, default='[]', nullable=False)  # JSON serialized list of features

    # Relationships
    organization = db.relationship('Organization', backref=db.backref('subscriptions', lazy=True, cascade='all, delete-orphan'))

    def is_valid(self):
        if self.status != 'Active':
            return False
        if self.expires_at and self.expires_at < datetime.datetime.utcnow():
            return False
        return True

    def has_feature(self, feature_name):
        """Checks if a feature is enabled and active in the subscription."""
        if not self.is_valid():
            return False
        try:
            features = json.loads(self.allowed_features or '[]')
            return feature_name in features
        except Exception:
            return False

    def __repr__(self):
        return f"<OrgSubscription {self.organization_id} - {self.plan_name} Status: {self.status}>"

class OrganizationDetail(Base):
    __tablename__ = 'organization_details'
    
    organization_id = db.Column(UUIDType, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    gstin = db.Column(db.String(15))
    billing_email = db.Column(db.String(120))
    billing_phone = db.Column(db.String(15))
    billing_address = db.Column(db.Text)
    state_code = db.Column(db.String(2), default='07')  # Indian State Code (default Delhi)
    pan_number = db.Column(db.String(10))
    currency = db.Column(db.String(3), default='INR')

    # Relationships
    organization = db.relationship('Organization', backref=db.backref('details', uselist=False, lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<OrganizationDetail {self.organization_id} - GSTIN: {self.gstin}>"
