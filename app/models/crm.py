"""
CRM Module Models for Bhishmaa One ERP.

Models:
- Customer: Customer master data
- Supplier: Supplier master data
- CustomerTransaction: Transaction history for customer ledger
- SupplierTransaction: Transaction history for supplier ledger
"""

from app.core.extensions import db
from app.models.core import TenantBase, UUIDType


class Customer(TenantBase):
    """
    Customer master record with ledger tracking.
    
    CRITICAL: All queries must filter by organization_id
    """
    __tablename__ = 'customers'
    
    # Basic Information
    name = db.Column(db.String(150), nullable=False, index=True)
    phone = db.Column(db.String(15), index=True)
    email = db.Column(db.String(120), index=True)
    
    # GST Information
    gstin = db.Column(db.String(15), index=True)
    state_code = db.Column(db.String(2), default='07')  # For GST calculations (Delhi)
    
    # Address Information
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    
    # Financial Tracking
    outstanding_balance = db.Column(db.Numeric(10, 2), default=0.0, index=True)
    credit_limit = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationships
    transactions = db.relationship(
        'CustomerTransaction',
        backref='customer',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def get_credit_available(self):
        """Get available credit for customer."""
        return float(self.credit_limit) - float(self.outstanding_balance)
    
    def is_credit_available(self, amount):
        """Check if customer has credit available."""
        return float(amount) <= self.get_credit_available()
    
    def __repr__(self):
        return f"<Customer {self.name} - Outstanding: ₹{self.outstanding_balance}>"


class Supplier(TenantBase):
    """
    Supplier master record with payment tracking.
    
    CRITICAL: All queries must filter by organization_id
    """
    __tablename__ = 'suppliers'
    
    # Basic Information
    name = db.Column(db.String(150), nullable=False, index=True)
    phone = db.Column(db.String(15), index=True)
    email = db.Column(db.String(120), index=True)
    
    # GST Information
    gstin = db.Column(db.String(15), index=True)
    state_code = db.Column(db.String(2), default='07')
    
    # Address Information
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    
    # Payment Terms
    payment_terms = db.Column(db.String(100))  # e.g., "Net 30", "2/10 Net 30"
    
    # Financial Tracking
    outstanding_balance = db.Column(db.Numeric(10, 2), default=0.0, index=True)
    total_purchases = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationships
    transactions = db.relationship(
        'SupplierTransaction',
        backref='supplier',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f"<Supplier {self.name} - Balance: ₹{self.outstanding_balance}>"


class CustomerTransaction(TenantBase):
    """
    Customer ledger transaction history.
    
    Types:
    - INVOICE: Sale transaction
    - PAYMENT: Payment received
    - CREDIT_MEMO: Adjustment/return
    """
    __tablename__ = 'customer_transactions'
    
    TRANSACTION_TYPES = [
        ('INVOICE', 'Invoice'),
        ('PAYMENT', 'Payment'),
        ('CREDIT_MEMO', 'Credit Memo'),
        ('DEBIT_MEMO', 'Debit Memo')
    ]
    
    # Core Information
    customer_id = db.Column(
        UUIDType,
        db.ForeignKey('customers.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    transaction_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Reference Information
    reference_type = db.Column(db.String(50))  # 'invoice', 'payment', etc.
    reference_id = db.Column(db.String(100))   # Invoice number, payment ID
    
    # Details
    description = db.Column(db.Text)
    balance_after = db.Column(db.Numeric(10, 2))  # Balance after this transaction
    
    def __repr__(self):
        return f"<CustomerTransaction {self.transaction_type} - ₹{self.amount}>"


class SupplierTransaction(TenantBase):
    """
    Supplier ledger transaction history.
    
    Types:
    - PURCHASE_ORDER: Purchase transaction
    - PAYMENT: Payment made
    - DEBIT_MEMO: Adjustment/return
    """
    __tablename__ = 'supplier_transactions'
    
    TRANSACTION_TYPES = [
        ('PURCHASE_ORDER', 'Purchase Order'),
        ('PAYMENT', 'Payment'),
        ('DEBIT_MEMO', 'Debit Memo'),
        ('CREDIT_MEMO', 'Credit Memo')
    ]
    
    # Core Information
    supplier_id = db.Column(
        UUIDType,
        db.ForeignKey('suppliers.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    transaction_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Reference Information
    reference_type = db.Column(db.String(50))  # 'purchase_order', 'payment', etc.
    reference_id = db.Column(db.String(100))   # PO number, payment ID
    
    # Details
    description = db.Column(db.Text)
    balance_after = db.Column(db.Numeric(10, 2))  # Balance after this transaction
    
    def __repr__(self):
        return f"<SupplierTransaction {self.transaction_type} - ₹{self.amount}>"

