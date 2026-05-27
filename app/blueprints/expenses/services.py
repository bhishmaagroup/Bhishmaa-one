import datetime
import random
from decimal import Decimal
from app.core.extensions import db
from app.models.expenses import Expense
from app.blueprints.expenses.constants import EXPENSE_PAID, EXPENSE_SUPPLIER_PAYMENT

def get_organization_expenses(organization_id, category=None):
    """
    Retrieves all non-deleted expenses for an organization.
    """
    query = Expense.query.filter_by(organization_id=organization_id, is_deleted=False)
    if category:
        query = query.filter_by(category=category)
    return query.order_by(Expense.date.desc(), Expense.created_at.desc()).all()

def get_expense_by_id(expense_id, organization_id):
    return Expense.query.filter_by(
        id=expense_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()

def create_expense(organization_id, user_id, data):
    """
    Generates and logs a business expense.
    """
    category = data.get('category')
    amount = float(data.get('amount') or 0.0)
    
    # Process date
    date_val = data.get('date')
    if isinstance(date_val, str):
        try:
            date = datetime.datetime.strptime(date_val, '%Y-%m-%d').date()
        except ValueError:
            date = datetime.date.today()
    elif isinstance(date_val, datetime.date):
        date = date_val
    else:
        date = datetime.date.today()
        
    description = data.get('description', '').strip()
    payment_mode = data.get('payment_mode', 'Cash')
    supplier_id = data.get('supplier_id')
    status = data.get('status', 'Paid')
    
    if amount <= 0:
        raise ValueError("Expense amount must be greater than zero.")
        
    # Generate unique sequence identifier
    rand_seq = "".join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    expense_number = f"EXP-{date.year}-{date.month:02d}-{rand_seq}"
    
    amt_decimal = Decimal(str(amount))
    
    # If the user selected a supplier but the category wasn't supplier payment,
    # or vice-versa, make sure they align
    if category != EXPENSE_SUPPLIER_PAYMENT:
        supplier_id = None
        
    expense = Expense(
        organization_id=organization_id,
        tenant_id=organization_id,
        expense_number=expense_number,
        category=category,
        amount=amt_decimal,
        date=date,
        description=description,
        payment_mode=payment_mode,
        supplier_id=supplier_id,
        status=status,
        created_by=user_id
    )
    
    db.session.add(expense)
    
    # CRM Integration: Decrement supplier outstanding balance on paid supplier payments
    if status == EXPENSE_PAID and category == EXPENSE_SUPPLIER_PAYMENT and supplier_id:
        from app.models.crm import Supplier
        sup = Supplier.query.filter_by(id=supplier_id, organization_id=organization_id).first()
        if sup:
            sup.outstanding_balance -= amt_decimal
            
    db.session.commit()
    return expense

def pay_draft_expense(expense_id, organization_id):
    """
    Approves and pays a draft/approved expense.
    """
    expense = get_expense_by_id(expense_id, organization_id)
    if not expense:
        raise ValueError("Expense not found.")
        
    if expense.status == EXPENSE_PAID:
        return expense
        
    expense.status = EXPENSE_PAID
    
    # Decrement supplier outstanding balance on status transition
    if expense.category == EXPENSE_SUPPLIER_PAYMENT and expense.supplier_id:
        from app.models.crm import Supplier
        sup = Supplier.query.filter_by(id=expense.supplier_id, organization_id=organization_id).first()
        if sup:
            sup.outstanding_balance -= expense.amount
            
    db.session.commit()
    return expense

def delete_expense(expense_id, organization_id):
    """
    Soft deletes an expense. If the expense was a paid supplier payment,
    reverts the supplier's balance (adds it back).
    """
    expense = get_expense_by_id(expense_id, organization_id)
    if not expense:
        raise ValueError("Expense not found.")
        
    # Revert supplier balance if deleting paid supplier payment
    if expense.status == EXPENSE_PAID and expense.category == EXPENSE_SUPPLIER_PAYMENT and expense.supplier_id:
        from app.models.crm import Supplier
        sup = Supplier.query.filter_by(id=expense.supplier_id, organization_id=organization_id).first()
        if sup:
            sup.outstanding_balance += expense.amount
            
    expense.soft_delete()
    return True
