"""
Inventory Module Models for Bhishmaa One ERP.

Models:
- Category: Product categories
- Brand: Product brands
- Unit: Units of measurement
- Product: Main product model
- StockTransaction: Stock movement history
"""

from datetime import datetime
from app.core.extensions import db
from app.models.core import Base, TenantBase, UUIDType


class Category(TenantBase):
    """Product categories for organization."""
    __tablename__ = 'product_categories'
    
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')  # Bootstrap primary color
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f"<Category {self.name}>"


class Brand(TenantBase):
    """Product brands for organization."""
    __tablename__ = 'product_brands'
    
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(500))
    
    # Relationships
    products = db.relationship('Product', backref='brand', lazy='dynamic')
    
    def __repr__(self):
        return f"<Brand {self.name}>"


class Unit(TenantBase):
    """Units of measurement for products."""
    __tablename__ = 'product_units'
    
    name = db.Column(db.String(50), nullable=False, index=True)
    symbol = db.Column(db.String(10), nullable=False)
    description = db.Column(db.Text)
    
    # Relationships
    products = db.relationship('Product', backref='unit_obj', lazy='dynamic')
    
    def __repr__(self):
        return f"<Unit {self.name} ({self.symbol})>"


class Product(TenantBase):
    """
    Main product model for inventory management.
    
    CRITICAL: All queries must filter by organization_id
    """
    __tablename__ = 'products'
    
    # Basic Information
    name = db.Column(db.String(255), nullable=False, index=True)
    sku = db.Column(db.String(50), nullable=True, unique=True, index=True)
    barcode = db.Column(db.String(100), nullable=True, index=True)
    description = db.Column(db.Text)
    
    # Category & Brand
    category_id = db.Column(
        UUIDType,
        db.ForeignKey('product_categories.id', ondelete='SET NULL'),
        nullable=True
    )
    brand_id = db.Column(
        UUIDType,
        db.ForeignKey('product_brands.id', ondelete='SET NULL'),
        nullable=True
    )
    unit_id = db.Column(
        UUIDType,
        db.ForeignKey('product_units.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Financials
    purchase_price = db.Column(db.Numeric(10, 2), default=0.0)
    selling_price = db.Column(db.Numeric(10, 2), default=0.0)
    gst_rate = db.Column(db.Numeric(5, 2), default=18.0)  # GST rate: 0, 5, 12, 18, 28%
    
    # Stock Management
    current_stock = db.Column(db.Numeric(10, 2), default=0.0, index=True)
    min_stock_alert = db.Column(db.Numeric(10, 2), default=5.0)
    max_stock_level = db.Column(db.Numeric(10, 2), default=100.0)
    reorder_quantity = db.Column(db.Numeric(10, 2), default=20.0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationships
    transactions = db.relationship(
        'StockTransaction',
        backref='product',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def is_low_stock(self):
        """Check if product is below minimum stock threshold."""
        return self.current_stock < self.min_stock_alert
    
    def is_overstocked(self):
        """Check if product exceeds maximum stock level."""
        return self.current_stock > self.max_stock_level
    
    def needs_reordering(self):
        """Check if product should be reordered."""
        return self.current_stock <= self.reorder_quantity
    
    def get_category_name(self):
        """Get category name or 'Uncategorized'."""
        return self.category.name if self.category else 'Uncategorized'
    
    def get_brand_name(self):
        """Get brand name or 'Generic'."""
        return self.brand.name if self.brand else 'Generic'
    
    def get_unit_symbol(self):
        """Get unit symbol or default 'PCS'."""
        return self.unit_obj.symbol if self.unit_obj else 'PCS'
    
    def __repr__(self):
        return f"<Product {self.name} (SKU: {self.sku}) - Stock: {self.current_stock}>"


class StockTransaction(TenantBase):
    """
    Stock movement history for audit trail and inventory tracking.
    
    Types:
    - IN: Stock increase (purchase, return, adjustment)
    - OUT: Stock decrease (sale, damage, adjustment)
    """
    __tablename__ = 'stock_transactions'
    
    TRANSACTION_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUSTMENT', 'Stock Adjustment'),
        ('DAMAGE', 'Damaged'),
        ('RETURN', 'Customer Return'),
        ('WASTAGE', 'Wastage')
    ]
    
    # Core Information
    product_id = db.Column(
        UUIDType,
        db.ForeignKey('products.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    transaction_type = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Reference Information
    reference_type = db.Column(db.String(50))  # 'invoice', 'purchase_order', 'manual', etc.
    reference_id = db.Column(db.String(100))   # Link to invoice or PO
    
    # Details
    reason = db.Column(db.Text)
    created_by_id = db.Column(
        UUIDType,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Relationships
    created_by = db.relationship('User', backref='stock_transactions')
    
    def __repr__(self):
        return f"<StockTransaction {self.transaction_type} - {self.product.name} - Qty: {self.quantity}>"


class BranchStock(TenantBase):
    """
    Branch-specific stock tracking for multi-branch operations.
    Overrides branch_id to be NOT nullable since stock must belong to a branch.
    """
    __tablename__ = 'branch_stocks'

    branch_id = db.Column(
        UUIDType,
        db.ForeignKey('branches.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    product_id = db.Column(
        UUIDType,
        db.ForeignKey('products.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    current_stock = db.Column(db.Numeric(10, 2), default=0.0, index=True)
    min_stock_alert = db.Column(db.Numeric(10, 2), default=5.0)
    max_stock_level = db.Column(db.Numeric(10, 2), default=100.0)

    # Unique stock record per branch and product
    __table_args__ = (
        db.UniqueConstraint('branch_id', 'product_id', name='uq_branch_product_stock'),
    )

    # Relationships
    product = db.relationship(
        'Product',
        backref=db.backref('branch_stocks', lazy='dynamic', cascade='all, delete-orphan')
    )
    branch = db.relationship(
        'Branch',
        backref=db.backref('branch_stocks', lazy='dynamic', cascade='all, delete-orphan')
    )

    def is_low_stock(self):
        """Check if branch stock is below minimum threshold."""
        return self.current_stock < self.min_stock_alert

    def __repr__(self):
        return f"<BranchStock Branch: {self.branch_id} - Product: {self.product_id} - Stock: {self.current_stock}>"


class StockTransfer(TenantBase):
    """
    Tracks stock transfer requests between branches.
    """
    __tablename__ = 'stock_transfers'

    from_branch_id = db.Column(
        UUIDType,
        db.ForeignKey('branches.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    to_branch_id = db.Column(
        UUIDType,
        db.ForeignKey('branches.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    status = db.Column(db.String(30), default='Pending', index=True, nullable=False)  # 'Pending', 'Approved', 'Cancelled'
    
    created_by_id = db.Column(
        UUIDType,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    approved_by_id = db.Column(
        UUIDType,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    from_branch = db.relationship('Branch', foreign_keys=[from_branch_id], backref='transfers_out')
    to_branch = db.relationship('Branch', foreign_keys=[to_branch_id], backref='transfers_in')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='transfers_created')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], backref='transfers_approved')
    
    items = db.relationship(
        'StockTransferItem',
        back_populates='transfer',
        cascade='all, delete-orphan',
        lazy='joined'
    )

    def __repr__(self):
        return f"<StockTransfer {self.id} from {self.from_branch_id} to {self.to_branch_id} - Status: {self.status}>"


class StockTransferItem(Base):
    """
    Individual items included in a stock transfer.
    """
    __tablename__ = 'stock_transfer_items'

    transfer_id = db.Column(
        UUIDType,
        db.ForeignKey('stock_transfers.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    product_id = db.Column(
        UUIDType,
        db.ForeignKey('products.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    quantity = db.Column(db.Numeric(10, 2), default=1.0, nullable=False)

    # Relationships
    transfer = db.relationship('StockTransfer', back_populates='items')
    product = db.relationship('Product', backref='transfer_items')

    def __repr__(self):
        return f"<StockTransferItem Product: {self.product_id} - Qty: {self.quantity}>"


