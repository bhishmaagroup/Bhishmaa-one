from datetime import datetime
from decimal import Decimal
from app.core.extensions import db
from app.models.core import User, Branch
from app.models.pos import CashRegisterSession
from app.models.inventory import Product, BranchStock, StockTransfer, StockTransferItem, StockTransaction


def get_active_register_session(user_id, branch_id):
    """
    Retrieves the currently open cash register session for a user and branch.
    """
    return CashRegisterSession.query.filter_by(
        user_id=user_id,
        branch_id=branch_id,
        status='Open',
        is_deleted=False
    ).first()


def open_register_session(user_id, branch_id, counter_number, opening_balance):
    """
    Opens a new cash register session.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")

    # Check if a session is already open
    active_session = get_active_register_session(user_id, branch_id)
    if active_session:
        return active_session

    session = CashRegisterSession(
        organization_id=user.organization_id,
        tenant_id=user.organization_id,
        branch_id=branch_id,
        user_id=user_id,
        counter_number=counter_number,
        opening_balance=Decimal(opening_balance),
        status='Open'
    )
    db.session.add(session)
    db.session.commit()
    return session


def close_register_session(session_id, real_cash_collected, notes=None):
    """
    Closes an active register session, calculating expected cash and mismatch.
    """
    session = CashRegisterSession.query.get(session_id)
    if not session:
        raise ValueError("Register session not found")
    if session.status == 'Closed':
        return session

    # Re-calculate totals from associated invoices
    cash_sales = Decimal('0.00')
    card_sales = Decimal('0.00')
    upi_sales = Decimal('0.00')

    for invoice in session.invoices:
        if invoice.is_deleted:
            continue
        amt = Decimal(str(invoice.amount_paid or 0.0))
        if invoice.payment_mode == 'Cash':
            cash_sales += amt
        elif invoice.payment_mode == 'Card':
            card_sales += amt
        elif invoice.payment_mode == 'UPI':
            upi_sales += amt

    session.total_cash_sales = cash_sales
    session.total_card_sales = card_sales
    session.total_upi_sales = upi_sales
    session.real_cash_collected = Decimal(real_cash_collected)
    session.notes = notes
    session.closed_at = datetime.utcnow()
    session.status = 'Closed'

    db.session.commit()
    return session


def get_or_create_branch_stock(branch_id, product_id, organization_id):
    """
    Gets or creates a BranchStock record for a product and branch.
    """
    branch_stock = BranchStock.query.filter_by(
        branch_id=branch_id,
        product_id=product_id
    ).first()

    if not branch_stock:
        product = Product.query.get(product_id)
        if not product:
            raise ValueError("Product not found")
        
        # If no other branch stock records exist, use the product's current stock as default
        other_stocks_exist = BranchStock.query.filter_by(product_id=product_id).first() is not None
        initial_stock = product.current_stock if not other_stocks_exist else Decimal('0.00')
        
        branch_stock = BranchStock(
            organization_id=organization_id,
            tenant_id=organization_id,
            branch_id=branch_id,
            product_id=product_id,
            current_stock=Decimal(str(initial_stock)),
            min_stock_alert=product.min_stock_alert,
            max_stock_level=product.max_stock_level
        )
        db.session.add(branch_stock)
        db.session.commit()

    return branch_stock


def create_stock_transfer(from_branch_id, to_branch_id, items_list, user_id, notes=None):
    """
    Creates a pending stock transfer between two branches.
    items_list format: [{'product_id': '...', 'quantity': 10}]
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")
    if from_branch_id == to_branch_id:
        raise ValueError("Source and destination branches cannot be the same")

    transfer = StockTransfer(
        organization_id=user.organization_id,
        tenant_id=user.organization_id,
        from_branch_id=from_branch_id,
        to_branch_id=to_branch_id,
        created_by_id=user_id,
        status='Pending',
        notes=notes
    )
    db.session.add(transfer)
    db.session.commit()

    for item in items_list:
        product_id = item['product_id']
        qty = Decimal(str(item['quantity']))
        if qty <= 0:
            raise ValueError("Quantity must be greater than zero")

        product = Product.query.get(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        transfer_item = StockTransferItem(
            transfer_id=transfer.id,
            product_id=product_id,
            quantity=qty
        )
        db.session.add(transfer_item)

    db.session.commit()
    return transfer


def approve_stock_transfer(transfer_id, user_id):
    """
    Approves a stock transfer, moving inventory from source to destination branch.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")

    transfer = StockTransfer.query.get(transfer_id)
    if not transfer:
        raise ValueError("Stock transfer not found")
    if transfer.status != 'Pending':
        raise ValueError(f"Cannot approve transfer with status '{transfer.status}'")

    # Verify and deduct/add stock
    for item in transfer.items:
        # Check source branch stock
        from_stock = get_or_create_branch_stock(transfer.from_branch_id, item.product_id, transfer.organization_id)
        if Decimal(str(from_stock.current_stock)) < Decimal(str(item.quantity)):
            raise ValueError(f"Insufficient stock for product '{item.product.name}' at source branch. Available: {from_stock.current_stock}, Required: {item.quantity}")

        # Deduct from source branch stock
        from_stock.current_stock = Decimal(str(from_stock.current_stock)) - Decimal(str(item.quantity))

        # Add to destination branch stock
        to_stock = get_or_create_branch_stock(transfer.to_branch_id, item.product_id, transfer.organization_id)
        to_stock.current_stock = Decimal(str(to_stock.current_stock)) + Decimal(str(item.quantity))

        # Log source branch Stock Transaction (OUT)
        tx_out = StockTransaction(
            organization_id=transfer.organization_id,
            tenant_id=transfer.organization_id,
            branch_id=transfer.from_branch_id,
            product_id=item.product_id,
            transaction_type='OUT',
            quantity=item.quantity,
            reference_type='transfer',
            reference_id=str(transfer.id),
            reason=f"Transfer to Branch: {transfer.to_branch.name}",
            created_by_id=user_id
        )
        db.session.add(tx_out)

        # Log destination branch Stock Transaction (IN)
        tx_in = StockTransaction(
            organization_id=transfer.organization_id,
            tenant_id=transfer.organization_id,
            branch_id=transfer.to_branch_id,
            product_id=item.product_id,
            transaction_type='IN',
            quantity=item.quantity,
            reference_type='transfer',
            reference_id=str(transfer.id),
            reason=f"Transfer from Branch: {transfer.from_branch.name}",
            created_by_id=user_id
        )
        db.session.add(tx_in)

    transfer.status = 'Approved'
    transfer.approved_by_id = user_id
    db.session.commit()
    return transfer


def cancel_stock_transfer(transfer_id, user_id):
    """
    Cancels a pending stock transfer.
    """
    transfer = StockTransfer.query.get(transfer_id)
    if not transfer:
        raise ValueError("Stock transfer not found")
    if transfer.status != 'Pending':
        raise ValueError(f"Cannot cancel transfer with status '{transfer.status}'")

    transfer.status = 'Cancelled'
    db.session.commit()
    return transfer
