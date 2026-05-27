from flask import request, jsonify
from flask_login import login_required, current_user
from app.blueprints.crm.routes import crm_bp
from app.blueprints.crm.services import (
    get_organization_customers, get_customer_by_id, create_customer,
    get_organization_suppliers, get_supplier_by_id, create_supplier
)
from app.blueprints.crm.permissions import crm_management_required

@crm_bp.route('/api/customers', methods=['GET'])
@login_required
@crm_management_required
def api_list_customers():
    """
    Returns list of customers. Supports ?q= to search by name/phone/GSTIN.
    Allows billing POS terminal to search and auto-complete customer data.
    """
    search_q = request.args.get('q', '').strip().lower()
    customers = get_organization_customers(current_user.organization_id)
    
    if search_q:
        customers = [
            c for c in customers
            if search_q in c.name.lower()
            or (c.phone and search_q in c.phone)
            or (c.gstin and search_q in c.gstin.lower())
        ]
        
    return jsonify({
        'customers': [{
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'email': c.email,
            'gstin': c.gstin,
            'state_code': c.state_code,
            'address': c.address,
            'outstanding_balance': float(c.outstanding_balance)
        } for c in customers]
    }), 200

@crm_bp.route('/api/suppliers', methods=['GET'])
@login_required
@crm_management_required
def api_list_suppliers():
    """
    Returns list of suppliers.
    """
    suppliers = get_organization_suppliers(current_user.organization_id)
    return jsonify({
        'suppliers': [{
            'id': s.id,
            'name': s.name,
            'phone': s.phone,
            'email': s.email,
            'gstin': s.gstin,
            'state_code': s.state_code,
            'address': s.address,
            'outstanding_balance': float(s.outstanding_balance)
        } for s in suppliers]
    }), 200
