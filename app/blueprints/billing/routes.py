from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.blueprints.billing.forms import InvoiceHeaderForm, InvoiceFilterForm, InvoiceEditForm
from app.blueprints.billing.services import get_organization_invoices, get_invoice_by_id, delete_invoice, update_invoice
from app.blueprints.billing.permissions import billing_management_required
from app.models.organizations import OrganizationDetail

billing_bp = Blueprint(
    'billing',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@billing_bp.route('/')
@login_required
@billing_management_required
def list_invoices():
    """
    Renders table of all sales bills under tenant organization.
    """
    form = InvoiceFilterForm(request.args)
    invoices = get_organization_invoices(current_user.organization_id)
    
    search_q = request.args.get('search', '').strip().lower()
    status_q = request.args.get('status', '').strip()
    
    if search_q:
        invoices = [
            inv for inv in invoices 
            if search_q in inv.customer_name.lower() 
            or search_q in inv.invoice_number.lower()
            or (inv.customer_phone and search_q in inv.customer_phone)
        ]
        
    if status_q:
        invoices = [inv for inv in invoices if inv.status == status_q]
        
    return render_template('billing/list.html', invoices=invoices, form=form)

@billing_bp.route('/create', methods=['GET'])
@login_required
@billing_management_required
def create():
    """
    Renders high-fidelity POS billing screen.
    """
    form = InvoiceHeaderForm()
    
    # Pre-populate organization tax state code
    org_detail = OrganizationDetail.query.filter_by(organization_id=current_user.organization_id).first()
    if org_detail and org_detail.state_code:
        form.customer_state_code.data = org_detail.state_code
        
    # Standard Indian states listing for state-based tax selection
    indian_states = [
        ('01', 'Jammu & Kashmir'), ('02', 'Himachal Pradesh'), ('03', 'Punjab'), 
        ('04', 'Chandigarh'), ('05', 'Uttarakhand'), ('06', 'Haryana'), 
        ('07', 'Delhi'), ('08', 'Rajasthan'), ('09', 'Uttar Pradesh'), 
        ('10', 'Bihar'), ('11', 'Sikkim'), ('12', 'Arunachal Pradesh'), 
        ('13', 'Nagaland'), ('14', 'Manipur'), ('15', 'Mizoram'), 
        ('16', 'Tripura'), ('17', 'Meghalaya'), ('18', 'Assam'), 
        ('19', 'West Bengal'), ('20', 'Jharkhand'), ('21', 'Odisha'), 
        ('22', 'Chhattisgarh'), ('23', 'Madhya Pradesh'), ('24', 'Gujarat'), 
        ('26', 'Dadra & Nagar Haveli & Daman & Diu'), ('27', 'Maharashtra'), 
        ('28', 'Andhra Pradesh (Before Split)'), ('29', 'Karnataka'), ('30', 'Goa'), 
        ('31', 'Lakshadweep'), ('32', 'Kerala'), ('33', 'Tamil Nadu'), 
        ('34', 'Puducherry'), ('35', 'Andaman & Nicobar Islands'), ('36', 'Telangana'), 
        ('37', 'Andhra Pradesh')
    ]
    
    return render_template(
        'billing/create.html', 
        form=form, 
        indian_states=indian_states,
        org_detail=org_detail
    )

@billing_bp.route('/details/<invoice_id>')
@login_required
@billing_management_required
def details(invoice_id):
    """
    Renders invoice detail viewer.
    """
    invoice = get_invoice_by_id(invoice_id, current_user.organization_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('billing.list_invoices'))
        
    org_detail = OrganizationDetail.query.filter_by(organization_id=current_user.organization_id).first()
    return render_template('billing/details.html', invoice=invoice, org_detail=org_detail)

@billing_bp.route('/print/<invoice_id>')
@login_required
@billing_management_required
def print_invoice(invoice_id):
    """
    Renders A4 invoice print layout without standard sidebar/navbar.
    """
    invoice = get_invoice_by_id(invoice_id, current_user.organization_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('billing.list_invoices'))
        
    org_detail = OrganizationDetail.query.filter_by(organization_id=current_user.organization_id).first()
    return render_template('billing/print.html', invoice=invoice, org_detail=org_detail)

@billing_bp.route('/edit/<invoice_id>', methods=['GET', 'POST'])
@login_required
@billing_management_required
def edit_invoice_route(invoice_id):
    """
    Renders invoice editor to update customer information or record payment status later.
    """
    invoice = get_invoice_by_id(invoice_id, current_user.organization_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('billing.list_invoices'))
        
    form = InvoiceEditForm()
    
    if form.validate_on_submit():
        try:
            update_data = {
                'customer_name': form.customer_name.data,
                'customer_phone': form.customer_phone.data,
                'customer_gstin': form.customer_gstin.data,
                'customer_state_code': form.customer_state_code.data,
                'payment_mode': form.payment_mode.data,
                'status': form.status.data,
                'amount_paid': float(form.amount_paid.data or 0.0)
            }
            update_invoice(invoice.id, current_user.organization_id, update_data, current_user.id)
            flash(f"Invoice {invoice.invoice_number} updated successfully.", "success")
            return redirect(url_for('billing.details', invoice_id=invoice.id))
        except ValueError as e:
            flash(str(e), "danger")
            
    # Pre-populate form with current invoice values on GET request
    if request.method == 'GET':
        form.customer_name.data = invoice.customer_name
        form.customer_phone.data = invoice.customer_phone
        form.customer_gstin.data = invoice.customer_gstin
        form.customer_state_code.data = invoice.customer_state_code
        form.payment_mode.data = invoice.payment_mode
        form.status.data = invoice.status
        form.amount_paid.data = invoice.amount_paid
        
    org_detail = OrganizationDetail.query.filter_by(organization_id=current_user.organization_id).first()
    return render_template(
        'billing/edit.html',
        form=form,
        invoice=invoice,
        org_detail=org_detail
    )

