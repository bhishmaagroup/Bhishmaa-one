from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app.core.extensions import db
from app.models.core import Branch
from app.models.inventory import Product, Category, BranchStock, StockTransfer
from app.blueprints.pos.forms import OpenSessionForm, CloseSessionForm, StockTransferForm
from app.blueprints.pos.services import (
    get_active_register_session, open_register_session, close_register_session,
    create_stock_transfer, approve_stock_transfer, cancel_stock_transfer, get_or_create_branch_stock
)
from app.blueprints.pos.utils import generate_barcode_base64, generate_qrcode_base64
from decimal import Decimal

from app.core.decorators import subscription_required

pos_bp = Blueprint(
    'pos',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@pos_bp.before_request
@subscription_required('pos')
def gate_pos_module():
    pass


@pos_bp.route('/counter', methods=['GET', 'POST'])
@login_required
def open_session():
    """
    Shows counter shift opening form. Redirects to billing if session already open.
    """
    branch_id = current_user.branch_id
    if not branch_id:
        # Assign first active branch if user is not linked to any
        branch = Branch.query.filter_by(organization_id=current_user.organization_id, is_active=True).first()
        if not branch:
            flash("No active branches found for your business. Please configure branches first.", "warning")
            return redirect(url_for('dashboard.index'))
        
        # Link user to this branch
        current_user.branch_id = branch.id
        db.session.commit()
        branch_id = branch.id

    active_session = get_active_register_session(current_user.id, branch_id)
    if active_session:
        return redirect(url_for('pos.billing'))

    form = OpenSessionForm()
    if form.validate_on_submit():
        try:
            open_register_session(
                user_id=current_user.id,
                branch_id=branch_id,
                counter_number=form.counter_number.data,
                opening_balance=form.opening_balance.data
            )
            flash("Register shift opened successfully. Welcome!", "success")
            return redirect(url_for('pos.billing'))
        except Exception as e:
            flash(f"Error opening register session: {e}", "danger")

    branch = Branch.query.get(branch_id)
    return render_template('pos/open_session.html', form=form, branch=branch)


@pos_bp.route('/billing', methods=['GET'])
@login_required
def billing():
    """
    Renders the unified POS billing screen.
    """
    branch_id = current_user.branch_id
    if not branch_id:
        return redirect(url_for('pos.open_session'))

    active_session = get_active_register_session(current_user.id, branch_id)
    if not active_session:
        flash("You must open a register session before using the billing counter.", "info")
        return redirect(url_for('pos.open_session'))

    # Load products and enrich with branch stock levels
    products = Product.query.filter_by(
        organization_id=current_user.organization_id,
        is_deleted=False,
        is_active=True
    ).order_by(Product.name).all()

    for p in products:
        b_stock = get_or_create_branch_stock(branch_id, p.id, current_user.organization_id)
        p.branch_stock_level = float(b_stock.current_stock) if b_stock else 0.0

    categories = Category.query.filter_by(
        organization_id=current_user.organization_id,
        is_deleted=False
    ).order_by(Category.name).all()

    branch = Branch.query.get(branch_id)
    return render_template(
        'pos/billing.html',
        products=products,
        categories=categories,
        active_session=active_session,
        branch=branch
    )


@pos_bp.route('/settlement', methods=['GET', 'POST'])
@login_required
def settlement():
    """
    Close shift screen with settlement/reconciliation details.
    """
    branch_id = current_user.branch_id
    if not branch_id:
        return redirect(url_for('pos.open_session'))

    active_session = get_active_register_session(current_user.id, branch_id)
    if not active_session:
        flash("No active register session found to close.", "warning")
        return redirect(url_for('pos.open_session'))

    # Pre-calculate totals for user display before actual closure
    cash_sales = Decimal('0.00')
    card_sales = Decimal('0.00')
    upi_sales = Decimal('0.00')
    for invoice in active_session.invoices:
        if invoice.is_deleted:
            continue
        amt = Decimal(str(invoice.amount_paid or 0.0))
        if invoice.payment_mode == 'Cash':
            cash_sales += amt
        elif invoice.payment_mode == 'Card':
            card_sales += amt
        elif invoice.payment_mode == 'UPI':
            upi_sales += amt

    expected_cash = Decimal(str(active_session.opening_balance)) + cash_sales + Decimal(str(active_session.cash_in)) - Decimal(str(active_session.cash_out))

    form = CloseSessionForm()
    if form.validate_on_submit():
        try:
            real_cash = form.real_cash_collected.data
            mismatch = float(real_cash) - float(expected_cash)
            
            close_register_session(
                session_id=active_session.id,
                real_cash_collected=real_cash,
                notes=form.notes.data
            )
            
            if mismatch != 0.0:
                sign = "+" if mismatch > 0 else ""
                flash(f"Shift settled successfully. Note: Cash discrepancy of {sign}₹{mismatch:.2f} detected.", "warning")
            else:
                flash("Shift settled successfully with no cash discrepancies.", "success")
                
            return redirect(url_for('dashboard.index'))
        except Exception as e:
            flash(f"Error settling session: {e}", "danger")

    return render_template(
        'pos/settlement.html',
        form=form,
        register_session=active_session,
        cash_sales=cash_sales,
        card_sales=card_sales,
        upi_sales=upi_sales,
        expected_cash=expected_cash
    )


@pos_bp.route('/transfers', methods=['GET', 'POST'])
@login_required
def list_transfers():
    """
    Renders inter-branch stock transfers and lets users create new ones.
    """
    branch_id = current_user.branch_id
    if not branch_id:
        flash("You must be linked to a branch to manage transfers.", "warning")
        return redirect(url_for('dashboard.index'))

    # Populate WTForm
    form = StockTransferForm()
    branches = Branch.query.filter(
        Branch.organization_id == current_user.organization_id,
        Branch.id != branch_id,
        Branch.is_active == True
    ).all()
    form.to_branch_id.choices = [(str(b.id), f"{b.name} ({b.code})") for b in branches]

    # Fetch products for transfer modal selection
    products = Product.query.filter_by(
        organization_id=current_user.organization_id,
        is_deleted=False,
        is_active=True
    ).order_by(Product.name).all()
    for p in products:
        b_stock = BranchStock.query.filter_by(branch_id=branch_id, product_id=p.id).first()
        p.branch_stock_level = float(b_stock.current_stock) if b_stock else 0.0

    # Query transfers involving current branch
    transfers = StockTransfer.query.filter(
        db.or_(
            StockTransfer.from_branch_id == branch_id,
            StockTransfer.to_branch_id == branch_id
        )
    ).order_by(StockTransfer.created_at.desc()).all()

    return render_template(
        'pos/transfers.html',
        form=form,
        transfers=transfers,
        products=products,
        current_branch_id=branch_id
    )


@pos_bp.route('/transfers/create', methods=['POST'])
@login_required
def api_create_transfer():
    """
    AJAX endpoint to create inter-branch stock transfer.
    """
    data = request.get_json() or {}
    to_branch_id = data.get('to_branch_id')
    items = data.get('items', [])
    notes = data.get('notes', '')

    if not to_branch_id:
        return jsonify({'error': 'Destination branch is required.'}), 400
    if not items:
        return jsonify({'error': 'Transfer must contain at least one product.'}), 400

    try:
        transfer = create_stock_transfer(
            from_branch_id=current_user.branch_id,
            to_branch_id=to_branch_id,
            items_list=items,
            user_id=current_user.id,
            notes=notes
        )
        return jsonify({
            'message': 'Stock transfer created successfully as Pending.',
            'transfer_id': transfer.id
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to create transfer: {e}'}), 500


@pos_bp.route('/transfers/<transfer_id>/approve', methods=['POST'])
@login_required
def approve_transfer_route(transfer_id):
    """
    Approves a stock transfer, executing stock movements.
    """
    try:
        approve_stock_transfer(transfer_id, current_user.id)
        flash("Stock transfer approved and stock updated successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Error approving transfer: {e}", "danger")
    return redirect(url_for('pos.list_transfers'))


@pos_bp.route('/transfers/<transfer_id>/cancel', methods=['POST'])
@login_required
def cancel_transfer_route(transfer_id):
    """
    Cancels a pending stock transfer.
    """
    try:
        cancel_stock_transfer(transfer_id, current_user.id)
        flash("Stock transfer cancelled successfully.", "info")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Error cancelling transfer: {e}", "danger")
    return redirect(url_for('pos.list_transfers'))


@pos_bp.route('/barcodes', methods=['GET'])
@login_required
def barcodes():
    """
    Barcode and QR Code label generation sheet.
    """
    products = Product.query.filter_by(
        organization_id=current_user.organization_id,
        is_deleted=False
    ).order_by(Product.name).all()

    selected_product_id = request.args.get('product_id', '')
    quantity = int(request.args.get('quantity', '12'))
    label_type = request.args.get('type', 'barcode')  # barcode, qrcode, both

    barcode_base64 = ""
    qrcode_base64 = ""
    selected_product = None

    if selected_product_id:
        selected_product = Product.query.filter_by(
            id=selected_product_id,
            organization_id=current_user.organization_id,
            is_deleted=False
        ).first()

        if selected_product:
            val_to_encode = selected_product.barcode or selected_product.sku or str(selected_product.id)[:8]
            barcode_base64 = generate_barcode_base64(val_to_encode)
            
            # For QR code, we encode product info e.g. SKU and selling price
            qr_data = f"Name: {selected_product.name}\nSKU: {selected_product.sku}\nPrice: INR {selected_product.selling_price:.2f}"
            qrcode_base64 = generate_qrcode_base64(qr_data)

    return render_template(
        'pos/barcodes.html',
        products=products,
        selected_product=selected_product,
        quantity=quantity,
        label_type=label_type,
        barcode_base64=barcode_base64,
        qrcode_base64=qrcode_base64
    )
