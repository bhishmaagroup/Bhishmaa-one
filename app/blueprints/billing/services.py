from decimal import Decimal
from app.core.extensions import db
from app.models.billing import Invoice, InvoiceItem, Payment
from app.models.organizations import OrganizationDetail
from app.blueprints.billing.utils import calculate_item_gst
from app.services.sequence import generate_next_invoice_number, generate_next_payment_number, get_financial_year

def get_organization_invoices(organization_id):
    """
    Returns all invoices registered under the tenant organization, ordered by created date desc.
    """
    return Invoice.query.filter_by(
        organization_id=organization_id, 
        is_deleted=False
    ).order_by(Invoice.created_at.desc()).all()

def get_invoice_by_id(invoice_id, organization_id):
    """
    Retrieves a single invoice by its ID, ensuring it belongs to the tenant.
    """
    return Invoice.query.filter_by(
        id=invoice_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()

def create_invoice(organization_id, user_id, invoice_data):
    """
    Creates a new sales invoice with calculated taxes and dynamic line items.
    """
    # 1. Resolve organization state code for tax splits
    org_detail = OrganizationDetail.query.filter_by(organization_id=organization_id).first()
    org_state_code = org_detail.state_code if (org_detail and org_detail.state_code) else '07'
    
    # 2. Extract Customer details
    customer_name = invoice_data.get('customer_name', '').strip()
    customer_phone = invoice_data.get('customer_phone', '').strip()
    customer_gstin = invoice_data.get('customer_gstin', '').strip()
    customer_state_code = invoice_data.get('customer_state_code', org_state_code).strip()
    
    payment_mode = invoice_data.get('payment_mode', 'Cash')
    status = invoice_data.get('status', 'Paid')
    discount_val = float(invoice_data.get('discount') or 0.0)
    amount_paid_val = float(invoice_data.get('amount_paid') or 0.0)
    
    # Generate sequential invoice number via the concurrent-safe sequence generator
    branch_id = invoice_data.get('branch_id')
    inv_num = generate_next_invoice_number(organization_id, branch_id=branch_id)
    
    # Initialize header financial variables
    invoice_subtotal = 0.0
    invoice_cgst = 0.0
    invoice_sgst = 0.0
    invoice_igst = 0.0
    
    invoice_items = []
    
    # Process items
    items_list = invoice_data.get('items', [])
    if not items_list:
        raise ValueError("Cannot create an invoice with no line items.")
        
    for item in items_list:
        product_name = item.get('product_name', '').strip()
        if not product_name:
            raise ValueError("Product name is required for all line items.")
            
        qty = float(item.get('quantity', 1.0))
        price = float(item.get('unit_price', 0.0))
        gst_rate = float(item.get('gst_rate', 18.0))
        
        # Calculate tax breakdowns for this item
        calc = calculate_item_gst(org_state_code, customer_state_code, price, qty, gst_rate)
        
        invoice_subtotal += calc['subtotal']
        invoice_cgst += calc['cgst']
        invoice_sgst += calc['sgst']
        invoice_igst += calc['igst']
        
        item_obj = InvoiceItem(
            product_name=product_name,
            quantity=qty,
            unit_price=price,
            gst_rate=gst_rate,
            cgst_amount=calc['cgst'],
            sgst_amount=calc['sgst'],
            igst_amount=calc['igst'],
            subtotal=calc['subtotal'],
            total_amount=calc['line_total']
        )
        invoice_items.append(item_obj)
        
    # Calculate final total
    total_tax = invoice_cgst + invoice_sgst + invoice_igst
    total_before_discount = invoice_subtotal + total_tax
    final_total = max(0.0, total_before_discount - discount_val)
    
    if status == 'Paid':
        amount_paid_val = final_total
    if status == 'Unpaid':
        amount_paid_val = 0.0
    if amount_paid_val < 0:
        raise ValueError('Amount paid cannot be negative.')
    if amount_paid_val > final_total:
        raise ValueError('Amount paid cannot exceed invoice total.')
    if status == 'Partial' and amount_paid_val == 0.0:
        raise ValueError('Partial payment requires a paid amount greater than zero.')
    
    # Save the Invoice Header
    invoice = Invoice(
        organization_id=organization_id,
        tenant_id=organization_id,
        branch_id=branch_id,
        register_session_id=invoice_data.get('register_session_id'),
        invoice_number=inv_num,
        financial_year=get_financial_year(),
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_gstin=customer_gstin,
        customer_state_code=customer_state_code,
        sub_total=round(invoice_subtotal, 2),
        cgst=round(invoice_cgst, 2),
        sgst=round(invoice_sgst, 2),
        igst=round(invoice_igst, 2),
        discount_amount=round(discount_val, 2),
        total_amount=round(final_total, 2),
        payment_mode=payment_mode,
        payment_status=status,
        status=status,
        amount_paid=round(amount_paid_val, 2),
        created_by_id=user_id
    )
    
    # Associate items
    invoice.items = invoice_items
    db.session.add(invoice)
    db.session.flush()

    if amount_paid_val > 0:
        payment = Payment(
            organization_id=organization_id,
            tenant_id=organization_id,
            invoice_id=invoice.id,
            payment_number=generate_next_payment_number(organization_id),
            amount=round(amount_paid_val, 2),
            payment_method=payment_mode,
            received_by_id=user_id
        )
        db.session.add(payment)

    db.session.commit()
    return invoice

def delete_invoice(invoice_id, organization_id):
    """
    Soft-deletes an invoice.
    """
    invoice = get_invoice_by_id(invoice_id, organization_id)
    if not invoice:
        raise ValueError("Invoice not found.")
    invoice.soft_delete()
    return True

def update_invoice(invoice_id, organization_id, update_data, user_id):
    """
    Updates invoice header details (customer details, payment status, amount paid).
    """
    invoice = get_invoice_by_id(invoice_id, organization_id)
    if not invoice:
        raise ValueError("Invoice not found.")
        
    # Update customer info if provided
    if 'customer_name' in update_data:
        invoice.customer_name = update_data['customer_name'].strip()
    if 'customer_phone' in update_data:
        invoice.customer_phone = update_data['customer_phone'].strip()
    if 'customer_gstin' in update_data:
        invoice.customer_gstin = update_data['customer_gstin'].strip()
    if 'customer_state_code' in update_data:
        invoice.customer_state_code = update_data['customer_state_code'].strip()
        
    # Update payment details
    old_amount_paid = float(invoice.amount_paid or 0.0)
    new_amount_paid = float(update_data.get('amount_paid') or 0.0)
    new_status = update_data.get('status', invoice.status)
    payment_mode = update_data.get('payment_mode', invoice.payment_mode)
    
    final_total = float(invoice.total_amount)
    
    if new_status == 'Paid':
        new_amount_paid = final_total
    elif new_status == 'Unpaid':
        new_amount_paid = 0.0
    elif new_status == 'Partial' and new_amount_paid == 0.0:
        new_status = 'Unpaid'
        new_amount_paid = 0.0
    elif new_amount_paid >= final_total:
        new_status = 'Paid'
        new_amount_paid = final_total
    elif 0.0 < new_amount_paid < final_total:
        new_status = 'Partial'
        
    invoice.status = new_status
    invoice.payment_status = new_status
    invoice.amount_paid = round(new_amount_paid, 2)
    invoice.payment_mode = payment_mode
    invoice.updated_by_id = user_id
    
    # If the payment amount increased, log a Payment record for the diff!
    diff = new_amount_paid - old_amount_paid
    if diff > 0:
        payment = Payment(
            organization_id=organization_id,
            tenant_id=organization_id,
            invoice_id=invoice.id,
            payment_number=generate_next_payment_number(organization_id),
            amount=round(diff, 2),
            payment_method=payment_mode,
            received_by_id=user_id,
            notes="Adjusted during invoice edit"
        )
        db.session.add(payment)
        
    db.session.commit()
    return invoice

