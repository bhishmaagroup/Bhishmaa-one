from decimal import Decimal
from sqlalchemy import and_, or_
from app.core.extensions import db
from app.models.inventory import Product, Category, Brand, Unit, StockTransaction
from app.blueprints.inventory.utils import generate_auto_sku
from flask_login import current_user

# =============================================================================
# PRODUCT SERVICES
# =============================================================================

def get_organization_products(organization_id):
    """
    Returns list of all products belonging to the tenant, ordered by name.
    """
    return Product.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).order_by(Product.name).all()

def get_product_by_id(product_id, organization_id):
    """
    Returns a product by ID, verifying tenant ownership.
    """
    return Product.query.filter_by(
        id=product_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()

def get_product_by_sku_or_name(sku_or_name, organization_id):
    """
    Queries product by SKU or exact case-insensitive name match.
    """
    p = Product.query.filter(
        Product.organization_id == organization_id,
        Product.is_deleted == False,
        Product.sku == sku_or_name
    ).first()
    
    if not p:
        p = Product.query.filter(
            Product.organization_id == organization_id,
            Product.is_deleted == False,
            Product.name.ilike(sku_or_name)
        ).first()
        
    return p

def search_products(organization_id, search_query):
    """Search products by name, SKU, or barcode."""
    search_term = f"%{search_query}%"
    
    return Product.query.filter(
        Product.organization_id == organization_id,
        Product.is_deleted == False,
        or_(
            Product.name.ilike(search_term),
            Product.sku.ilike(search_term),
            Product.barcode.ilike(search_term)
        )
    ).all()

def get_low_stock_products(organization_id):
    """Get all products below minimum stock threshold."""
    return Product.query.filter(
        Product.organization_id == organization_id,
        Product.is_deleted == False,
        Product.current_stock < Product.min_stock_alert
    ).order_by(Product.current_stock.asc()).all()

def create_product(organization_id, data):
    """
    Creates a new inventory product. Auto-generates SKU if not provided.
    """
    name = data.get('name', '').strip()
    sku = data.get('sku', '').strip()
    barcode = data.get('barcode', '').strip()
    description = data.get('description', '').strip()
    
    purchase_price = float(data.get('purchase_price') or 0.0)
    selling_price = float(data.get('selling_price') or 0.0)
    gst_rate = float(data.get('gst_rate') or 18.0)
    current_stock = float(data.get('current_stock') or 0.0)
    min_stock_alert = float(data.get('min_stock_alert') or 5.0)
    max_stock_level = float(data.get('max_stock_level') or 100.0)
    reorder_quantity = float(data.get('reorder_quantity') or 20.0)
    
    if not name:
        raise ValueError("Product name is required.")
        
    if not sku:
        sku = generate_auto_sku(name)
        
    # Check for SKU conflict in this tenant
    conflict = Product.query.filter_by(organization_id=organization_id, sku=sku, is_deleted=False).first()
    if conflict:
        raise ValueError(f"SKU code '{sku}' is already assigned to product '{conflict.name}'.")
        
    product = Product(
        organization_id=organization_id,
        tenant_id=organization_id,
        name=name,
        sku=sku,
        barcode=barcode,
        description=description,
        purchase_price=purchase_price,
        selling_price=selling_price,
        gst_rate=gst_rate,
        current_stock=current_stock,
        min_stock_alert=min_stock_alert,
        max_stock_level=max_stock_level,
        reorder_quantity=reorder_quantity,
        category_id=data.get('category_id'),
        brand_id=data.get('brand_id'),
        unit_id=data.get('unit_id'),
        is_active=data.get('is_active', True)
    )
    
    db.session.add(product)
    db.session.commit()
    
    # Sync initial stock to active branch if current user is linked to a branch
    if current_stock > 0:
        try:
            if current_user and current_user.is_authenticated and current_user.branch_id:
                from app.blueprints.pos.services import get_or_create_branch_stock
                b_stock = get_or_create_branch_stock(current_user.branch_id, product.id, organization_id)
                b_stock.current_stock = Decimal(str(current_stock))
                db.session.commit()
        except Exception as e:
            pass
            
    return product

def update_product(product_id, organization_id, data):
    """
    Updates an existing product's attributes.
    """
    product = get_product_by_id(product_id, organization_id)
    if not product:
        raise ValueError("Product not found.")
        
    name = data.get('name', '').strip()
    sku = data.get('sku', '').strip()
    
    if not name:
        raise ValueError("Product name is required.")
        
    if sku and sku != product.sku:
        # Check SKU conflict
        conflict = Product.query.filter_by(organization_id=organization_id, sku=sku, is_deleted=False).first()
        if conflict:
            raise ValueError(f"SKU code '{sku}' is already assigned to another product.")
        product.sku = sku
        
    product.name = name
    product.barcode = data.get('barcode', '').strip()
    product.description = data.get('description', '').strip()
    product.purchase_price = float(data.get('purchase_price') or 0.0)
    product.selling_price = float(data.get('selling_price') or 0.0)
    product.gst_rate = float(data.get('gst_rate') or 18.0)
    product.min_stock_alert = float(data.get('min_stock_alert') or 5.0)
    product.max_stock_level = float(data.get('max_stock_level') or 100.0)
    product.reorder_quantity = float(data.get('reorder_quantity') or 20.0)
    product.category_id = data.get('category_id', product.category_id)
    product.brand_id = data.get('brand_id', product.brand_id)
    product.unit_id = data.get('unit_id', product.unit_id)
    product.is_active = data.get('is_active', product.is_active)
    
    db.session.commit()
    return product

def delete_product(product_id, organization_id):
    """
    Soft-deletes a product.
    """
    product = get_product_by_id(product_id, organization_id)
    if not product:
        raise ValueError("Product not found.")
    product.soft_delete()
    return True

def adjust_product_stock(product_id, organization_id, quantity_change, transaction_type='ADJUSTMENT', reason=None):
    """
    Adjust product stock and create transaction record.
    """
    product = get_product_by_id(product_id, organization_id)
    if not product:
        raise ValueError("Product not found.")
    
    # Validate stock for deductions
    if quantity_change < 0 and product.current_stock < abs(quantity_change):
        raise ValueError(f"Insufficient stock. Available: {product.current_stock}")
    
    # Update stock
    product.current_stock += Decimal(str(quantity_change))
    
    # Also update the branch stock for the current user's branch if available
    try:
        if current_user and current_user.is_authenticated and current_user.branch_id:
            from app.blueprints.pos.services import get_or_create_branch_stock
            b_stock = get_or_create_branch_stock(current_user.branch_id, product_id, organization_id)
            b_stock.current_stock = Decimal(str(b_stock.current_stock)) + Decimal(str(quantity_change))
    except Exception as e:
        pass
    
    # Safely extract current user ID if available in request context
    current_user_id = None
    try:
        if current_user and current_user.is_authenticated:
            current_user_id = current_user.id
    except Exception:
        pass

    # Create transaction record
    transaction = StockTransaction(
        organization_id=organization_id,
        tenant_id=organization_id,
        product_id=product_id,
        transaction_type=transaction_type,
        quantity=abs(quantity_change),
        reason=reason,
        created_by_id=current_user_id
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    # Trigger notification if low stock
    if product.is_low_stock():
        try:
            from flask import url_for
            link = url_for('inventory.list_products')
        except RuntimeError:
            link = '/inventory/'
            
        try:
            from app.blueprints.notifications.services import create_notification
            create_notification(
                organization_id=organization_id,
                title="Stock Alert",
                message=f"Product '{product.name}' is low in stock ({product.current_stock} remaining, limit {product.min_stock_alert}).",
                type="Stock Alert",
                link=link
            )
        except Exception as e:
            print(f"[Notification Error] Failed to create stock alert notification: {e}")
    
    return product

def deduct_stock_from_invoice(organization_id, items, branch_id=None):
    """
    Deducts inventory stock when products are sold in an invoice checkout.
    Attempts matching line items by name or SKU. If branch_id is passed, deducts from BranchStock.
    """
    for item in items:
        prod_name = item.get('product_name')
        qty = Decimal(str(item.get('quantity', 0.0)))
        
        product = get_product_by_sku_or_name(prod_name, organization_id)
        if product:
            if qty <= 0:
                continue
                
            if branch_id:
                from app.blueprints.pos.services import get_or_create_branch_stock
                branch_stock = get_or_create_branch_stock(branch_id, product.id, organization_id)
                if Decimal(str(branch_stock.current_stock)) < qty:
                    raise ValueError(f"Insufficient stock for '{product.name}' in the current branch. Available: {branch_stock.current_stock}, requested: {qty}")
                branch_stock.current_stock = Decimal(str(branch_stock.current_stock)) - qty
                
                # Also decrement global product stock for compatibility
                product.current_stock = float(Decimal(str(product.current_stock)) - qty)
            else:
                if Decimal(str(product.current_stock)) < qty:
                    raise ValueError(f"Insufficient stock for '{product.name}'. Available: {product.current_stock}, requested: {qty}")
                product.current_stock = float(Decimal(str(product.current_stock)) - qty)
            
            # Safely extract current user ID if available in request context
            current_user_id = None
            try:
                if current_user and current_user.is_authenticated:
                    current_user_id = current_user.id
            except Exception:
                pass

            # Create stock transaction
            transaction = StockTransaction(
                organization_id=organization_id,
                tenant_id=organization_id,
                branch_id=branch_id,
                product_id=product.id,
                transaction_type='OUT',
                quantity=qty,
                reason='Invoice sales deduction',
                created_by_id=current_user_id
            )
            db.session.add(transaction)
            
            # Trigger low stock notification check (branch-specific or global)
            is_low = False
            curr_stock_val = 0.0
            limit_val = 0.0
            if branch_id:
                # We check branch-specific low stock
                is_low = branch_stock.is_low_stock()
                curr_stock_val = float(branch_stock.current_stock)
                limit_val = float(branch_stock.min_stock_alert)
            else:
                is_low = product.is_low_stock()
                curr_stock_val = float(product.current_stock)
                limit_val = float(product.min_stock_alert)

            if is_low:
                try:
                    from flask import url_for
                    link = url_for('inventory.list_products')
                except RuntimeError:
                    link = '/inventory/'
                try:
                    from app.blueprints.notifications.services import create_notification
                    create_notification(
                        organization_id=organization_id,
                        title="Stock Alert",
                        message=f"Product '{product.name}' is low in stock ({curr_stock_val} remaining, limit {limit_val}).",
                        type="Stock Alert",
                        link=link
                    )
                except Exception as e:
                    print(f"[Notification Error] Failed to create stock alert notification: {e}")
            
    db.session.commit()

# =============================================================================
# CATEGORY SERVICES
# =============================================================================

def get_categories(organization_id):
    """Get all categories for organization."""
    return Category.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).order_by(Category.name).all()

def create_category(organization_id, name, description=None, color=None):
    """Create product category."""
    category = Category(
        organization_id=organization_id,
        tenant_id=organization_id,
        name=name,
        description=description or '',
        color=color or '#007bff'
    )
    
    db.session.add(category)
    db.session.commit()
    
    return category

def update_category(category_id, organization_id, data):
    """Update category."""
    category = Category.query.filter_by(
        id=category_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()
    
    if not category:
        raise ValueError("Category not found")
    
    category.name = data.get('name', category.name)
    category.description = data.get('description', category.description)
    category.color = data.get('color', category.color)
    
    db.session.commit()
    
    return category

def delete_category(category_id, organization_id):
    """Delete category."""
    category = Category.query.filter_by(
        id=category_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()
    
    if not category:
        raise ValueError("Category not found")
    
    category.soft_delete()
    return category

# =============================================================================
# BRAND SERVICES
# =============================================================================

def get_brands(organization_id):
    """Get all brands for organization."""
    return Brand.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).order_by(Brand.name).all()

def create_brand(organization_id, name, description=None, logo_url=None):
    """Create brand."""
    brand = Brand(
        organization_id=organization_id,
        tenant_id=organization_id,
        name=name,
        description=description or '',
        logo_url=logo_url
    )
    
    db.session.add(brand)
    db.session.commit()
    
    return brand

def update_brand(brand_id, organization_id, data):
    """Update brand."""
    brand = Brand.query.filter_by(
        id=brand_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()
    
    if not brand:
        raise ValueError("Brand not found")
    
    brand.name = data.get('name', brand.name)
    brand.description = data.get('description', brand.description)
    brand.logo_url = data.get('logo_url', brand.logo_url)
    
    db.session.commit()
    
    return brand

def delete_brand(brand_id, organization_id):
    """Delete brand."""
    brand = Brand.query.filter_by(
        id=brand_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()
    
    if not brand:
        raise ValueError("Brand not found")
    
    brand.soft_delete()
    return brand

# =============================================================================
# UNIT SERVICES
# =============================================================================

def get_units(organization_id):
    """Get all units for organization."""
    return Unit.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).order_by(Unit.name).all()

def create_unit(organization_id, name, symbol, description=None):
    """Create unit."""
    unit = Unit(
        organization_id=organization_id,
        tenant_id=organization_id,
        name=name,
        symbol=symbol,
        description=description or ''
    )
    
    db.session.add(unit)
    db.session.commit()
    
    return unit

def update_unit(unit_id, organization_id, data):
    """Update unit."""
    unit = Unit.query.filter_by(
        id=unit_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()
    
    if not unit:
        raise ValueError("Unit not found")
    
    unit.name = data.get('name', unit.name)
    unit.symbol = data.get('symbol', unit.symbol)
    unit.description = data.get('description', unit.description)
    
    db.session.commit()
    
    return unit

def delete_unit(unit_id, organization_id):
    """Delete unit."""
    unit = Unit.query.filter_by(
        id=unit_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()
    
    if not unit:
        raise ValueError("Unit not found")
    
    unit.soft_delete()
    return unit

# =============================================================================
# STOCK TRANSACTION SERVICES
# =============================================================================

def get_product_stock_history(product_id, organization_id):
    """Get stock transaction history for product."""
    return StockTransaction.query.filter_by(
        product_id=product_id,
        organization_id=organization_id,
        is_deleted=False
    ).order_by(StockTransaction.created_at.desc()).all()
