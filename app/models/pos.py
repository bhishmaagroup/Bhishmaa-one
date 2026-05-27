"""
POS Cash Register Models for Bhishmaa One ERP.

Models:
- CashRegisterSession: Tracks counter shifts, cash drawer status, and opening/closing reconciliations.
"""

from datetime import datetime
from app.core.extensions import db
from app.models.core import TenantBase, UUIDType


class CashRegisterSession(TenantBase):
    """
    Tracks a cashier register session (shift) for a specific counter and branch.
    Inherits organization_id, tenant_id, and branch_id from TenantBase.
    """
    __tablename__ = 'cash_register_sessions'

    user_id = db.Column(
        UUIDType,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    counter_number = db.Column(db.String(50), nullable=False)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    closed_at = db.Column(db.DateTime, nullable=True, index=True)
    
    opening_balance = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    closing_balance = db.Column(db.Numeric(10, 2), nullable=True)
    
    total_cash_sales = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    total_card_sales = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    total_upi_sales = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    
    cash_in = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    cash_out = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    
    real_cash_collected = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), default='Open', nullable=False, index=True)  # 'Open', 'Closed'
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    user = db.relationship('User', backref=db.backref('cash_register_sessions', lazy='dynamic'))
    branch = db.relationship('Branch', backref=db.backref('cash_register_sessions', lazy='dynamic'))

    @property
    def expected_cash(self):
        """Calculates expected cash remaining in the register."""
        return float(self.opening_balance) + float(self.total_cash_sales) + float(self.cash_in) - float(self.cash_out)

    @property
    def mismatch_amount(self):
        """Calculates the mismatch if the register is closed."""
        if self.real_cash_collected is None:
            return 0.0
        return float(self.real_cash_collected) - self.expected_cash

    def __repr__(self):
        return f"<CashRegisterSession {self.id} - User: {self.user_id} - Status: {self.status}>"
