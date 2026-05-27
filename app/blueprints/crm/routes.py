from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.blueprints.crm.forms import CustomerForm, SupplierForm
from app.blueprints.crm.services import (
    get_organization_customers, get_customer_by_id, create_customer, update_customer, delete_customer,
    get_organization_suppliers, get_supplier_by_id, create_supplier, update_supplier, delete_supplier
)
from app.blueprints.crm.permissions import crm_management_required

crm_bp = Blueprint(
    'crm',
    __name__,
    template_folder='templates',
    static_folder='static'
)

# CUSTOMER ROUTES
@crm_bp.route('/customers')
@login_required
@crm_management_required
def list_customers():
    """
    Renders customer directory listing.
    """
    customers = get_organization_customers(current_user.organization_id)
    search_q = request.args.get('search', '').strip().lower()
    
    if search_q:
        customers = [
            c for c in customers
            if search_q in c.name.lower()
            or (c.phone and search_q in c.phone)
            or (c.email and search_q in c.email.lower())
        ]
        
    return render_template('crm/customers_list.html', customers=customers)

@crm_bp.route('/customers/create', methods=['GET', 'POST'])
@login_required
@crm_management_required
def create_customer_route():
    form = CustomerForm()
    
    # States choice bindings helper
    indian_states = [
        ('01', 'Jammu & Kashmir'), ('02', 'Himachal Pradesh'), ('03', 'Punjab'), 
        ('07', 'Delhi'), ('08', 'Rajasthan'), ('09', 'Uttar Pradesh'), ('27', 'Maharashtra'), 
        ('29', 'Karnataka'), ('32', 'Kerala'), ('33', 'Tamil Nadu'), ('36', 'Telangana'), ('37', 'Andhra Pradesh')
    ]
    
    if form.validate_on_submit():
        data = {
            'name': form.name.data,
            'phone': form.phone.data,
            'email': form.email.data,
            'gstin': form.gstin.data,
            'state_code': form.state_code.data,
            'address': form.address.data,
            'outstanding_balance': float(form.outstanding_balance.data or 0.0)
        }
        try:
            create_customer(current_user.organization_id, data)
            flash(f"Customer '{form.name.data}' successfully added to CRM directory.", "success")
            return redirect(url_for('crm.list_customers'))
        except ValueError as e:
            flash(str(e), "danger")
            
    return render_template('crm/customer_form.html', form=form, indian_states=indian_states, action="Create")

@crm_bp.route('/customers/edit/<customer_id>', methods=['GET', 'POST'])
@login_required
@crm_management_required
def edit_customer_route(customer_id):
    customer = get_customer_by_id(customer_id, current_user.organization_id)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('crm.list_customers'))
        
    form_data = {
        'name': customer.name,
        'phone': customer.phone,
        'email': customer.email,
        'gstin': customer.gstin,
        'state_code': customer.state_code,
        'address': customer.address,
        'outstanding_balance': customer.outstanding_balance
    }
    
    form = CustomerForm(data=form_data)
    indian_states = [
        ('01', 'Jammu & Kashmir'), ('02', 'Himachal Pradesh'), ('03', 'Punjab'), 
        ('07', 'Delhi'), ('08', 'Rajasthan'), ('09', 'Uttar Pradesh'), ('27', 'Maharashtra'), 
        ('29', 'Karnataka'), ('32', 'Kerala'), ('33', 'Tamil Nadu'), ('36', 'Telangana'), ('37', 'Andhra Pradesh')
    ]
    
    if form.validate_on_submit():
        data = {
            'name': form.name.data,
            'phone': form.phone.data,
            'email': form.email.data,
            'gstin': form.gstin.data,
            'state_code': form.state_code.data,
            'address': form.address.data,
            'outstanding_balance': float(form.outstanding_balance.data or 0.0)
        }
        try:
            update_customer(customer_id, current_user.organization_id, data)
            flash("Customer profile updated successfully.", "success")
            return redirect(url_for('crm.list_customers'))
        except ValueError as e:
            flash(str(e), "danger")
            
    return render_template('crm/customer_form.html', form=form, product=customer, indian_states=indian_states, action="Edit")

@crm_bp.route('/customers/delete/<customer_id>', methods=['POST'])
@login_required
@crm_management_required
def delete_customer_route(customer_id):
    try:
        delete_customer(customer_id, current_user.organization_id)
        flash("Customer deleted successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
        
    return redirect(url_for('crm.list_customers'))


# SUPPLIER ROUTES
@crm_bp.route('/suppliers')
@login_required
@crm_management_required
def list_suppliers():
    """
    Renders supplier directory listing.
    """
    suppliers = get_organization_suppliers(current_user.organization_id)
    search_q = request.args.get('search', '').strip().lower()
    
    if search_q:
        suppliers = [
            s for s in suppliers 
            if search_q in s.name.lower()
            or (s.phone and search_q in s.phone)
            or (s.email and search_q in s.email.lower())
        ]
        
    return render_template('crm/suppliers_list.html', suppliers=suppliers)

@crm_bp.route('/suppliers/create', methods=['GET', 'POST'])
@login_required
@crm_management_required
def create_supplier_route():
    form = SupplierForm()
    indian_states = [
        ('01', 'Jammu & Kashmir'), ('02', 'Himachal Pradesh'), ('03', 'Punjab'), 
        ('07', 'Delhi'), ('08', 'Rajasthan'), ('09', 'Uttar Pradesh'), ('27', 'Maharashtra'), 
        ('29', 'Karnataka'), ('32', 'Kerala'), ('33', 'Tamil Nadu'), ('36', 'Telangana'), ('37', 'Andhra Pradesh')
    ]
    
    if form.validate_on_submit():
        data = {
            'name': form.name.data,
            'phone': form.phone.data,
            'email': form.email.data,
            'gstin': form.gstin.data,
            'state_code': form.state_code.data,
            'address': form.address.data,
            'outstanding_balance': float(form.outstanding_balance.data or 0.0)
        }
        try:
            create_supplier(current_user.organization_id, data)
            flash(f"Supplier '{form.name.data}' successfully registered in directory.", "success")
            return redirect(url_for('crm.list_suppliers'))
        except ValueError as e:
            flash(str(e), "danger")
            
    return render_template('crm/supplier_form.html', form=form, indian_states=indian_states, action="Create")

@crm_bp.route('/suppliers/edit/<supplier_id>', methods=['GET', 'POST'])
@login_required
@crm_management_required
def edit_supplier_route(supplier_id):
    supplier = get_supplier_by_id(supplier_id, current_user.organization_id)
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('crm.list_suppliers'))
        
    form_data = {
        'name': supplier.name,
        'phone': supplier.phone,
        'email': supplier.email,
        'gstin': supplier.gstin,
        'state_code': supplier.state_code,
        'address': supplier.address,
        'outstanding_balance': supplier.outstanding_balance
    }
    
    form = SupplierForm(data=form_data)
    indian_states = [
        ('01', 'Jammu & Kashmir'), ('02', 'Himachal Pradesh'), ('03', 'Punjab'), 
        ('07', 'Delhi'), ('08', 'Rajasthan'), ('09', 'Uttar Pradesh'), ('27', 'Maharashtra'), 
        ('29', 'Karnataka'), ('32', 'Kerala'), ('33', 'Tamil Nadu'), ('36', 'Telangana'), ('37', 'Andhra Pradesh')
    ]
    
    if form.validate_on_submit():
        data = {
            'name': form.name.data,
            'phone': form.phone.data,
            'email': form.email.data,
            'gstin': form.gstin.data,
            'state_code': form.state_code.data,
            'address': form.address.data,
            'outstanding_balance': float(form.outstanding_balance.data or 0.0)
        }
        try:
            update_supplier(supplier_id, current_user.organization_id, data)
            flash("Supplier profile updated successfully.", "success")
            return redirect(url_for('crm.list_suppliers'))
        except ValueError as e:
            flash(str(e), "danger")
            
    return render_template('crm/supplier_form.html', form=form, supplier=supplier, indian_states=indian_states, action="Edit")

@crm_bp.route('/suppliers/delete/<supplier_id>', methods=['POST'])
@login_required
@crm_management_required
def delete_supplier_route(supplier_id):
    try:
        delete_supplier(supplier_id, current_user.organization_id)
        flash("Supplier profile deleted successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
        
    return redirect(url_for('crm.list_suppliers'))
