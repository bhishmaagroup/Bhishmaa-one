"""
Billing Module Models for Bhishmaa One ERP.

Models:
- Invoice: Sales invoice/bill
- InvoiceItem: Line items in invoice
- Payment: Payment records for invoices
"""

import datetime
from app.core.extensions import db
from app.models.core import Base, TenantBase, UUIDType


class Invoice(TenantBase):
    """
    Sales Invoice/Bill for POS and standard billing.
    
    CRITICAL: All queries must filter by organization_id
    """
    __tablename__ = 'invoices'
    
    # Invoice Information
    invoice_number = db.Column(db.String(50), nullable=False, index=True)
    financial_year = db.Column(db.String(10), nullable=False, default='2526', index=True)
    invoice_date = db.Column(db.Date, default=datetime.date.today, index=True)
    due_date = db.Column(db.Date)
    register_session_id = db.Column(
        UUIDType,
        db.ForeignKey('cash_register_sessions.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # Customer Information (Can be stored directly or via customer_id)
    customer_id = db.Column(
        UUIDType,
        db.ForeignKey('customers.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    customer_name = db.Column(db.String(150), nullable=False)
    customer_phone = db.Column(db.String(15))
    customer_gstin = db.Column(db.String(15))
    customer_state_code = db.Column(db.String(2), default='07')  # For GST calculation
    customer_address = db.Column(db.Text)
    
    # Financial Breakdown
    sub_total = db.Column(db.Numeric(10, 2), default=0.0)
    cgst = db.Column(db.Numeric(10, 2), default=0.0)
    sgst = db.Column(db.Numeric(10, 2), default=0.0)
    igst = db.Column(db.Numeric(10, 2), default=0.0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.0)
    discount_percentage = db.Column(db.Numeric(5, 2), default=0.0)
    shipping_amount = db.Column(db.Numeric(10, 2), default=0.0)
    total_amount = db.Column(db.Numeric(10, 2), default=0.0)

    @property
    def discount(self):
        return float(self.discount_amount or 0.0)

    @discount.setter
    def discount(self, value):
        self.discount_amount = value
    
    # Payment Information
    payment_mode = db.Column(db.String(50), default='Cash')  # Cash, Card, Check, Bank Transfer, etc.
    payment_status = db.Column(db.String(30), default='Pending')  # Pending, Partial, Paid
    amount_paid = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Invoice Status
    status = db.Column(db.String(30), default='Draft')  # Draft, Submitted, Accepted, Rejected, Paid
    
    # Notes
    notes = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)
    
    # Unique constraint per tenant and financial year
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'financial_year', 'invoice_number', name='uq_tenant_fy_invoice_number'),
    )
    
    # Audit Trail
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
    
    # Relationships
    items = db.relationship(
        'InvoiceItem',
        back_populates='invoice',
        cascade='all, delete-orphan',
        lazy='joined'
    )
    payments = db.relationship(
        'Payment',
        back_populates='invoice',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    customer = db.relationship('Customer', backref='invoices')
    register_session = db.relationship('CashRegisterSession', backref='invoices')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='invoices_created')
    updated_by = db.relationship('User', foreign_keys=[updated_by_id], backref='invoices_updated')
    
    def get_pending_amount(self):
        """Get amount still pending for payment."""
        return float(self.total_amount) - float(self.amount_paid)
    
    def is_fully_paid(self):
        """Check if invoice is fully paid."""
        return float(self.amount_paid) >= float(self.total_amount)
    
    def __repr__(self):
        return f"<Invoice {self.invoice_number} - Total: ₹{self.total_amount} - Status: {self.status}>"


class InvoiceItem(Base):
    """
    Individual line items in an invoice.
    """
    __tablename__ = 'invoice_items'
    
    # Reference to Invoice
    invoice_id = db.Column(
        UUIDType,
        db.ForeignKey('invoices.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Item Information
    product_id = db.Column(
        UUIDType,
        db.ForeignKey('products.id', ondelete='SET NULL'),
        nullable=True
    )
    product_name = db.Column(db.String(255), nullable=False)
    product_sku = db.Column(db.String(50))
    description = db.Column(db.Text)
    
    # Quantity and Pricing
    quantity = db.Column(db.Numeric(10, 2), default=1.0, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    
    # Tax Information
    gst_rate = db.Column(db.Numeric(5, 2), default=18.0)
    cgst_amount = db.Column(db.Numeric(10, 2), default=0.0)
    sgst_amount = db.Column(db.Numeric(10, 2), default=0.0)
    igst_amount = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Line Total
    subtotal = db.Column(db.Numeric(10, 2), default=0.0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.0)
    total_amount = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Relationships
    invoice = db.relationship('Invoice', back_populates='items')
    product = db.relationship('Product', backref='invoice_items')
    
    def __repr__(self):
        return f"<InvoiceItem {self.product_name} - Qty: {self.quantity} - Total: ₹{self.total_amount}>"


class Payment(TenantBase):
    """
    Payment records for invoices.
    Tracks partial and full payments.
    """
    __tablename__ = 'payments'
    
    # Reference to Invoice
    invoice_id = db.Column(
        UUIDType,
        db.ForeignKey('invoices.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Payment Information
    payment_number = db.Column(db.String(50), nullable=False, index=True)
    payment_date = db.Column(db.Date, default=datetime.date.today, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50))  # Cash, Card, Check, Bank Transfer, etc.
    
    # Payment Details
    reference_number = db.Column(db.String(100))  # Check number, Transaction ID, etc.
    notes = db.Column(db.Text)
    
    # Audit Trail
    received_by_id = db.Column(
        UUIDType,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Unique constraint per tenant for payments
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'payment_number', name='uq_tenant_payment_number'),
    )

    # Relationships
    invoice = db.relationship('Invoice', back_populates='payments')
    received_by = db.relationship('User', backref='payments_received')
    
    def __repr__(self):
        return f"<Payment {self.payment_number} - Amount: ₹{self.amount}>"

