from flask import request, jsonify
from flask_login import login_required, current_user
from app.blueprints.inventory.routes import inventory_bp
from app.blueprints.inventory.services import (
    get_organization_products, get_product_by_id, create_product, 
    update_product, delete_product, adjust_product_stock
)
from app.blueprints.inventory.permissions import inventory_management_required

@inventory_bp.route('/api/products', methods=['GET'])
@login_required
@inventory_management_required
def api_list_products():
    """
    Returns list of products. Exposes query parameter ?q= to search by name/SKU/barcode.
    Perfect for POS integration!
    """
    search_q = request.args.get('q', '').strip().lower()
    products = get_organization_products(current_user.organization_id)
    
    if search_q:
        products = [
            p for p in products
            if search_q in p.name.lower()
            or (p.sku and search_q in p.sku.lower())
            or (p.barcode and search_q in p.barcode.lower())
        ]
        
    return jsonify({
        'products': [{
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'barcode': p.barcode,
            'selling_price': float(p.selling_price),
            'purchase_price': float(p.purchase_price),
            'gst_rate': float(p.gst_rate),
            'current_stock': float(p.current_stock),
            'unit': p.get_unit_symbol()
        } for p in products]
    }), 200

@inventory_bp.route('/api/products/<product_id>', methods=['GET'])
@login_required
@inventory_management_required
def api_get_product(product_id):
    """
    Returns detail of a single product.
    """
    product = get_product_by_id(product_id, current_user.organization_id)
    if not product:
        return jsonify({'error': 'Product not found.'}), 404
        
    return jsonify({
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'barcode': product.barcode,
        'description': product.description,
        'unit': product.get_unit_symbol(),
        'purchase_price': float(product.purchase_price),
        'selling_price': float(product.selling_price),
        'gst_rate': float(product.gst_rate),
        'current_stock': float(product.current_stock),
        'min_stock_alert': float(product.min_stock_alert)
    }), 200

@inventory_bp.route('/api/products', methods=['POST'])
@login_required
@inventory_management_required
def api_create_product():
    """
    Creates a new product via JSON.
    """
    data = request.get_json() or {}
    try:
        product = create_product(current_user.organization_id, data)
        return jsonify({
            'message': 'Product successfully registered.',
            'id': product.id,
            'sku': product.sku
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@inventory_bp.route('/api/products/<product_id>/adjust', methods=['POST'])
@login_required
@inventory_management_required
def api_adjust_stock(product_id):
    """
    Adjusts stock level via JSON.
    """
    data = request.get_json() or {}
    qty_change = data.get('quantity_change')
    
    if qty_change is None:
        return jsonify({'error': 'quantity_change parameter is required.'}), 400
        
    try:
        product = adjust_product_stock(product_id, current_user.organization_id, qty_change)
        return jsonify({
            'message': 'Stock successfully adjusted.',
            'product_id': product.id,
            'new_stock': float(product.current_stock)
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
