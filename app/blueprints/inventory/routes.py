"""
Inventory Module Routes for Bhishmaa One ERP.

Handles:
- Product CRUD operations
- Category management
- Brand management  
- Unit management
- Stock adjustments and history
- Low stock alerts
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.core.extensions import db
from app.blueprints.inventory.forms import ProductForm, StockAdjustmentForm
from app.blueprints.inventory.services import (
    # Products
    get_organization_products, get_product_by_id, create_product, 
    update_product, delete_product, adjust_product_stock, search_products,
    get_low_stock_products,
    # Categories
    get_categories, create_category, update_category, 
    delete_category as service_delete_category,
    # Brands
    get_brands, create_brand, update_brand, delete_brand as service_delete_brand,
    # Units
    get_units, create_unit, update_unit, delete_unit as service_delete_unit,
    # Stock
    get_product_stock_history
)
from app.blueprints.inventory.permissions import inventory_management_required
from app.models.inventory import StockTransaction

from app.core.decorators import subscription_required

inventory_bp = Blueprint(
    'inventory',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@inventory_bp.before_request
@subscription_required('inventory')
def gate_inventory_module():
    pass

# =============================================================================
# PRODUCT ROUTES
# =============================================================================

@inventory_bp.route('/', endpoint='list_products')
@login_required
@inventory_management_required
def list_products():
    """Product listing with search and filters."""
    org_id = current_user.organization_id
    
    # Get all products
    products = get_organization_products(org_id)
    
    # Search
    search_q = request.args.get('search', '').strip()
    if search_q:
        products = search_products(org_id, search_q)
    
    # Filter by category
    category_filter = request.args.get('category')
    if category_filter:
        products = [p for p in products if p.category_id and str(p.category_id) == category_filter]
    
    # Filter by status
    status_filter = request.args.get('status')
    if status_filter == 'low_stock':
        products = [p for p in products if p.is_low_stock()]
    elif status_filter == 'inactive':
        products = [p for p in products if not p.is_active]
    elif status_filter == 'overstock':
        products = [p for p in products if p.is_overstocked()]
    
    # Get summary data
    categories = get_categories(org_id)
    total_products = len(products)
    low_stock_count = len([p for p in products if p.is_low_stock()])
    total_value = sum(float(p.current_stock) * float(p.selling_price) for p in products)
    
    return render_template(
        'inventory/list.html',
        products=products,
        categories=categories,
        search_q=search_q,
        category_filter=category_filter,
        status_filter=status_filter,
        total_products=total_products,
        low_stock_count=low_stock_count,
        total_value=total_value
    )

@inventory_bp.route('/create', methods=['GET', 'POST'])
@login_required
@inventory_management_required
def create():
    """Create new product."""
    org_id = current_user.organization_id
    form = ProductForm()
    
    # Populate dropdowns
    form.category_id.choices = [('', '-- Select Category --')] + [(str(c.id), c.name) for c in get_categories(org_id)]
    form.brand_id.choices = [('', '-- Select Brand --')] + [(str(b.id), b.name) for b in get_brands(org_id)]
    form.unit_id.choices = [('', '-- Select Unit --')] + [(str(u.id), f"{u.name} ({u.symbol})") for u in get_units(org_id)]
    
    if form.validate_on_submit():
        try:
            data = {
                'name': form.name.data,
                'sku': form.sku.data,
                'barcode': form.barcode.data,
                'description': form.description.data,
                'purchase_price': float(form.purchase_price.data or 0.0),
                'selling_price': float(form.selling_price.data or 0.0),
                'gst_rate': float(form.gst_rate.data),
                'current_stock': float(form.current_stock.data or 0.0),
                'min_stock_alert': float(form.min_stock_alert.data or 5.0),
                'max_stock_level': float(form.max_stock_level.data or 100.0),
                'reorder_quantity': float(form.reorder_quantity.data or 20.0),
                'category_id': form.category_id.data or None,
                'brand_id': form.brand_id.data or None,
                'unit_id': form.unit_id.data or None,
                'is_active': True
            }
            
            product = create_product(org_id, data)
            flash(f"✓ Product '{product.name}' created successfully!", "success")
            return redirect(url_for('inventory.details', product_id=product.id))
        except ValueError as e:
            flash(f"✗ Error: {str(e)}", "danger")
    
    return render_template('inventory/create.html', form=form)

@inventory_bp.route('/<product_id>')
@login_required
@inventory_management_required
def details(product_id):
    """View product details."""
    org_id = current_user.organization_id
    product = get_product_by_id(product_id, org_id)
    
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('inventory.list_products'))
    
    # Get stock history
    stock_history = get_product_stock_history(product_id, org_id)[:20]  # Last 20 transactions
    
    return render_template(
        'inventory/details.html',
        product=product,
        stock_history=stock_history
    )

@inventory_bp.route('/<product_id>/edit', methods=['GET', 'POST'])
@login_required
@inventory_management_required
def edit(product_id):
    """Edit product details."""
    org_id = current_user.organization_id
    product = get_product_by_id(product_id, org_id)
    
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('inventory.list_products'))
    
    form = ProductForm()
    
    # Populate dropdowns
    form.category_id.choices = [('', '-- Select Category --')] + [(str(c.id), c.name) for c in get_categories(org_id)]
    form.brand_id.choices = [('', '-- Select Brand --')] + [(str(b.id), b.name) for b in get_brands(org_id)]
    form.unit_id.choices = [('', '-- Select Unit --')] + [(str(u.id), f"{u.name} ({u.symbol})") for u in get_units(org_id)]
    
    if form.validate_on_submit():
        try:
            data = {
                'name': form.name.data,
                'sku': form.sku.data,
                'barcode': form.barcode.data,
                'description': form.description.data,
                'purchase_price': float(form.purchase_price.data or 0.0),
                'selling_price': float(form.selling_price.data or 0.0),
                'gst_rate': float(form.gst_rate.data),
                'min_stock_alert': float(form.min_stock_alert.data or 5.0),
                'max_stock_level': float(form.max_stock_level.data or 100.0),
                'reorder_quantity': float(form.reorder_quantity.data or 20.0),
                'category_id': form.category_id.data or None,
                'brand_id': form.brand_id.data or None,
                'unit_id': form.unit_id.data or None,
                'is_active': form.is_active.data
            }
            
            product = update_product(product_id, org_id, data)
            flash(f"✓ Product '{product.name}' updated successfully!", "success")
            return redirect(url_for('inventory.details', product_id=product.id))
        except ValueError as e:
            flash(f"✗ Error: {str(e)}", "danger")
    else:
        # Pre-populate form
        form.name.data = product.name
        form.sku.data = product.sku
        form.barcode.data = product.barcode
        form.description.data = product.description
        form.purchase_price.data = product.purchase_price
        form.selling_price.data = product.selling_price
        form.gst_rate.data = product.gst_rate
        form.min_stock_alert.data = product.min_stock_alert
        form.max_stock_level.data = product.max_stock_level
        form.reorder_quantity.data = product.reorder_quantity
        form.category_id.data = str(product.category_id) if product.category_id else ''
        form.brand_id.data = str(product.brand_id) if product.brand_id else ''
        form.unit_id.data = str(product.unit_id) if product.unit_id else ''
        form.is_active.data = product.is_active
    
    return render_template('inventory/edit.html', form=form, product=product)

@inventory_bp.route('/<product_id>/delete', methods=['POST'])
@login_required
@inventory_management_required
def delete(product_id):
    """Delete product."""
    org_id = current_user.organization_id
    
    try:
        product = get_product_by_id(product_id, org_id)
        if not product:
            raise ValueError("Product not found")
        
        product_name = product.name
        delete_product(product_id, org_id)
        flash(f"✓ Product '{product_name}' deleted successfully!", "success")
    except ValueError as e:
        flash(f"✗ Error: {str(e)}", "danger")
    
    return redirect(url_for('inventory.list_products'))

# =============================================================================
# STOCK ADJUSTMENT ROUTES
# =============================================================================

@inventory_bp.route('/<product_id>/adjust-stock', methods=['GET', 'POST'], endpoint='adjust')
@login_required
@inventory_management_required
def adjust(product_id):
    """Adjust product stock."""
    org_id = current_user.organization_id
    product = get_product_by_id(product_id, org_id)
    
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('inventory.list_products'))
    
    form = StockAdjustmentForm()
    
    if form.validate_on_submit():
        try:
            quantity = float(form.quantity_change.data)
            
            adjust_product_stock(product_id, org_id, quantity)
            
            flash(f"✓ Stock adjusted by {quantity}", "success")
            return redirect(url_for('inventory.details', product_id=product.id))
        except ValueError as e:
            flash(f"✗ Error: {str(e)}", "danger")
    
    return render_template('inventory/adjust.html', form=form, product=product)

@inventory_bp.route('/<product_id>/stock-history')
@login_required
@inventory_management_required
def stock_history(product_id):
    """View product stock transaction history."""
    org_id = current_user.organization_id
    product = get_product_by_id(product_id, org_id)
    
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('inventory.list_products'))
    
    # Get all transactions
    transactions = StockTransaction.query.filter_by(
        product_id=product_id,
        organization_id=org_id,
        is_deleted=False
    ).order_by(StockTransaction.created_at.desc()).all()
    
    return render_template(
        'inventory/stock_history.html',
        product=product,
        transactions=transactions
    )

# =============================================================================
# CATEGORY ROUTES
# =============================================================================

@inventory_bp.route('/categories')
@login_required
@inventory_management_required
def list_categories():
    """List all categories."""
    org_id = current_user.organization_id
    categories = get_categories(org_id)
    
    return render_template('inventory/categories.html', categories=categories)

@inventory_bp.route('/categories/create', methods=['POST'])
@login_required
@inventory_management_required
def create_category_route():
    """Create new category (AJAX)."""
    org_id = current_user.organization_id
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '#007bff')
        
        if not name:
            return jsonify({'success': False, 'message': 'Category name required'}), 400
        
        category = create_category(org_id, name, description, color)
        
        return jsonify({
            'success': True,
            'message': f'Category "{name}" created',
            'id': str(category.id),
            'name': category.name
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/categories/<category_id>/edit', methods=['POST'])
@login_required
@inventory_management_required
def edit_category(category_id):
    """Edit category."""
    org_id = current_user.organization_id
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '#007bff')
        
        if not name:
            return jsonify({'success': False, 'message': 'Category name required'}), 400
        
        category = update_category(category_id, org_id, {
            'name': name,
            'description': description,
            'color': color
        })
        
        return jsonify({'success': True, 'message': 'Category updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/categories/<category_id>/delete', methods=['POST'])
@login_required
@inventory_management_required
def delete_category_route(category_id):
    """Delete category."""
    org_id = current_user.organization_id
    
    try:
        service_delete_category(category_id, org_id)
        return jsonify({'success': True, 'message': 'Category deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# =============================================================================
# BRAND ROUTES
# =============================================================================

@inventory_bp.route('/brands')
@login_required
@inventory_management_required
def list_brands():
    """List all brands."""
    org_id = current_user.organization_id
    brands = get_brands(org_id)
    
    return render_template('inventory/brands.html', brands=brands)

@inventory_bp.route('/brands/create', methods=['POST'])
@login_required
@inventory_management_required
def create_brand_route():
    """Create new brand (AJAX)."""
    org_id = current_user.organization_id
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        logo_url = request.form.get('logo_url', '')
        
        if not name:
            return jsonify({'success': False, 'message': 'Brand name required'}), 400
        
        brand = create_brand(org_id, name, description, logo_url)
        
        return jsonify({
            'success': True,
            'message': f'Brand "{name}" created',
            'id': str(brand.id),
            'name': brand.name
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/brands/<brand_id>/delete', methods=['POST'])
@login_required
@inventory_management_required
def delete_brand_route(brand_id):
    """Delete brand."""
    org_id = current_user.organization_id
    
    try:
        service_delete_brand(brand_id, org_id)
        return jsonify({'success': True, 'message': 'Brand deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# =============================================================================
# UNIT ROUTES
# =============================================================================

@inventory_bp.route('/units')
@login_required
@inventory_management_required
def list_units():
    """List all units."""
    org_id = current_user.organization_id
    units = get_units(org_id)
    
    return render_template('inventory/units.html', units=units)

@inventory_bp.route('/units/create', methods=['POST'])
@login_required
@inventory_management_required
def create_unit_route():
    """Create new unit (AJAX)."""
    org_id = current_user.organization_id
    
    try:
        name = request.form.get('name', '').strip()
        symbol = request.form.get('symbol', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name or not symbol:
            return jsonify({'success': False, 'message': 'Name and symbol required'}), 400
        
        unit = create_unit(org_id, name, symbol, description)
        
        return jsonify({
            'success': True,
            'message': f'Unit "{name}" created',
            'id': str(unit.id),
            'name': unit.name,
            'symbol': unit.symbol
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/units/<unit_id>/delete', methods=['POST'])
@login_required
@inventory_management_required
def delete_unit_route(unit_id):
    """Delete unit."""
    org_id = current_user.organization_id
    
    try:
        service_delete_unit(unit_id, org_id)
        return jsonify({'success': True, 'message': 'Unit deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# =============================================================================
# API ENDPOINTS FOR AUTOCOMPLETE/DROPDOWNS
# =============================================================================

@inventory_bp.route('/api/products/search')
@login_required
def api_search_products():
    """API endpoint for product search (for autocomplete)."""
    org_id = current_user.organization_id
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    products = search_products(org_id, query)
    
    results = [{
        'id': str(p.id),
        'name': p.name,
        'sku': p.sku,
        'price': float(p.selling_price),
        'stock': float(p.current_stock)
    } for p in products[:10]]
    
    return jsonify(results)

@inventory_bp.route('/api/products/<product_id>/available-quantity')
@login_required
def api_product_quantity(product_id):
    """Get available quantity of product."""
    org_id = current_user.organization_id
    product = get_product_by_id(product_id, org_id)
    
    if not product:
        return jsonify({'available': 0}), 404
    
    return jsonify({
        'available': float(product.current_stock),
        'unit': product.get_unit_symbol(),
        'low_stock': product.is_low_stock(),
        'selling_price': float(product.selling_price)
    })

