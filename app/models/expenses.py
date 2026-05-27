import datetime
from app.core.extensions import db
from app.models.core import TenantBase, UUIDType
EXPENSE_DRAFT = 'Draft'

class Expense(TenantBase):
    __tablename__ = 'expenses'
    
    expense_number = db.Column(db.String(50), unique=True, index=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    date = db.Column(db.Date, default=datetime.date.today, index=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    payment_mode = db.Column(db.String(50), nullable=False)
    
    # Supplier link for cross-module CRM sync
    supplier_id = db.Column(UUIDType, db.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True, index=True)
    status = db.Column(db.String(30), default=EXPENSE_DRAFT, nullable=False)
    created_by = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    supplier = db.relationship('Supplier', backref=db.backref('expenses', lazy=True))
    creator = db.relationship('User', backref=db.backref('expenses_created', lazy=True))

    def __repr__(self):
        return f"<Expense {self.expense_number} - {self.category} - Amount: ₹{self.amount}>"
