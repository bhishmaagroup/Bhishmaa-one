from flask import request, jsonify, abort
from flask_login import login_required, current_user
from app.blueprints.billing.routes import billing_bp
from app.blueprints.billing.services import get_organization_invoices, get_invoice_by_id, create_invoice, delete_invoice
from app.blueprints.billing.permissions import billing_management_required

@billing_bp.route('/api/invoices', methods=['GET'])
@login_required
@billing_management_required
def api_list_invoices():
    """
    Returns list of all invoices.
    """
    invoices = get_organization_invoices(current_user.organization_id)
    return jsonify({
        'invoices': [{
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'customer_name': inv.customer_name,
            'customer_phone': inv.customer_phone,
            'total_amount': float(inv.total_amount),
            'amount_paid': float(inv.amount_paid),
            'pending_amount': float(inv.get_pending_amount()),
            'status': inv.status,
            'created_at': inv.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for inv in invoices]
    }), 200

@billing_bp.route('/api/invoices/<invoice_id>', methods=['GET'])
@login_required
@billing_management_required
def api_get_invoice(invoice_id):
    """
    Returns a single invoice details with line items.
    """
    invoice = get_invoice_by_id(invoice_id, current_user.organization_id)
    if not invoice:
        return jsonify({'error': 'Invoice not found.'}), 404
        
    return jsonify({
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'customer_name': invoice.customer_name,
        'customer_phone': invoice.customer_phone,
        'customer_gstin': invoice.customer_gstin,
        'customer_state_code': invoice.customer_state_code,
        'sub_total': float(invoice.sub_total),
        'cgst': float(invoice.cgst),
        'sgst': float(invoice.sgst),
        'igst': float(invoice.igst),
        'discount': float(invoice.discount),
        'total_amount': float(invoice.total_amount),
        'payment_mode': invoice.payment_mode,
        'status': invoice.status,
        'created_at': invoice.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'amount_paid': float(invoice.amount_paid),
        'pending_amount': float(invoice.get_pending_amount()),
        'items': [{
            'id': item.id,
            'product_name': item.product_name,
            'quantity': float(item.quantity),
            'unit_price': float(item.unit_price),
            'gst_rate': float(item.gst_rate),
            'cgst_amount': float(item.cgst_amount),
            'sgst_amount': float(item.sgst_amount),
            'igst_amount': float(item.igst_amount),
            'total_amount': float(item.total_amount)
        } for item in invoice.items]
    }), 200

@billing_bp.route('/api/invoices', methods=['POST'])
@login_required
@billing_management_required
def api_create_invoice():
    """
    Accepts JSON payload to generate an invoice.
    """
    data = request.get_json() or {}
    
    # Check if there is an active cash register session for the current user in their current branch
    from app.blueprints.pos.services import get_active_register_session
    branch_id = current_user.branch_id
    active_session = None
    if branch_id:
        active_session = get_active_register_session(current_user.id, branch_id)
        
    if active_session:
        data['branch_id'] = str(active_session.branch_id)
        data['register_session_id'] = str(active_session.id)
        
    try:
        invoice = create_invoice(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            invoice_data=data
        )
        
        # Create Sales notification alert
        try:
            from app.blueprints.notifications.services import create_notification
            from flask import url_for
            invoice_link = url_for('billing.details', invoice_id=invoice.id)
            create_notification(
                organization_id=current_user.organization_id,
                title="New Invoice Checkout",
                message=f"Invoice #{invoice.invoice_number} has been checked out successfully. Total: ₹{invoice.total_amount:.2f}",
                type="Sales",
                link=invoice_link
            )
        except Exception as e:
            print(f"[Notification Error] Failed to create checkout notification: {e}")
            
        # Deduct inventory stock levels (branch-scoped if active session exists)
        try:
            from app.blueprints.inventory.services import deduct_stock_from_invoice
            deduct_stock_from_invoice(
                current_user.organization_id,
                data.get('items', []),
                branch_id=active_session.branch_id if active_session else None
            )
        except Exception as e:
            # Log stock deduction failure, but do not fail the invoice transaction itself
            print(f"[Stock Error] Failed to deduct inventory stock: {e}")
            
        # Update active register session totals
        if active_session:
            try:
                from decimal import Decimal
                amt = Decimal(str(invoice.amount_paid))
                if invoice.payment_mode == 'Cash':
                    active_session.total_cash_sales = Decimal(str(active_session.total_cash_sales)) + amt
                elif invoice.payment_mode == 'Card':
                    active_session.total_card_sales = Decimal(str(active_session.total_card_sales)) + amt
                elif invoice.payment_mode == 'UPI':
                    active_session.total_upi_sales = Decimal(str(active_session.total_upi_sales)) + amt
                db.session.commit()
            except Exception as e:
                print(f"[POS Session Error] Failed to update session totals: {e}")
            
        # Update CRM customer outstanding balance
        try:
            status = data.get('status', 'Paid')
            unpaid_amount = 0.0
            if status == 'Unpaid' or status == 'Partial':
                unpaid_amount = float(invoice.total_amount)
                
            if unpaid_amount > 0:
                from app.blueprints.crm.services import update_customer_balance_on_billing
                update_customer_balance_on_billing(
                    organization_id=current_user.organization_id,
                    customer_name=invoice.customer_name,
                    customer_phone=invoice.customer_phone,
                    unpaid_amount=unpaid_amount
                )
        except Exception as e:
            print(f"[CRM Error] Failed to update customer balance: {e}")
            
        return jsonify({
            'message': 'Invoice successfully generated.',
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'total_amount': float(invoice.total_amount)
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An internal database error occurred: ' + str(e)}), 500
