from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.blueprints.expenses import expenses_bp
from app.core.decorators import subscription_required

@expenses_bp.before_request
@subscription_required('expenses')
def gate_expenses_module():
    pass
from app.blueprints.expenses.forms import ExpenseForm
from app.blueprints.expenses.constants import PAYMENT_MODES, EXPENSE_CATEGORIES
from app.blueprints.expenses.services import (
    get_organization_expenses, get_expense_by_id,
    create_expense, pay_draft_expense, delete_expense
)
from app.blueprints.crm.services import get_organization_suppliers
from app.blueprints.expenses.permissions import expenses_management_required

@expenses_bp.route('/')
@login_required
@expenses_management_required
def list_expenses():
    """
    Renders corporate outflow ledger.
    """
    category_filter = request.args.get('category', '').strip()
    category = category_filter if category_filter in EXPENSE_CATEGORIES else None
    
    expenses = get_organization_expenses(current_user.organization_id, category=category)
    total_outflow = sum(float(e.amount) for e in expenses)
    
    return render_template(
        'expenses/expenses_list.html',
        expenses=expenses,
        total_outflow=total_outflow,
        categories=EXPENSE_CATEGORIES,
        selected_category=category
    )

@expenses_bp.route('/create', methods=['GET', 'POST'])
@login_required
@expenses_management_required
def create_expense_route():
    """
    Creates and records a new outgoing transaction.
    """
    form = ExpenseForm()
    
    # Populate suppliers list dynamically
    suppliers = get_organization_suppliers(current_user.organization_id)
    form.supplier_id.choices = [('', '-- Select Supplier (Optional) --')] + [
        (str(s.id), f"{s.name} (Outstanding: ₹{s.outstanding_balance:.2f})") for s in suppliers
    ]
    
    if form.validate_on_submit():
        data = {
            'category': form.category.data,
            'amount': float(form.amount.data),
            'date': form.date.data,
            'description': form.description.data,
            'payment_mode': form.payment_mode.data,
            'supplier_id': form.supplier_id.data if form.supplier_id.data else None,
            'status': form.status.data
        }
        try:
            create_expense(current_user.organization_id, current_user.id, data)
            flash("Expense record saved successfully.", "success")
            return redirect(url_for('expenses.list_expenses'))
        except ValueError as e:
            flash(str(e), "danger")
            
    return render_template('expenses/expense_form.html', form=form)

@expenses_bp.route('/pay/<expense_id>', methods=['POST'])
@login_required
@expenses_management_required
def pay_draft_expense_route(expense_id):
    """
    Records payout for draft expenses.
    """
    try:
        pay_draft_expense(expense_id, current_user.organization_id)
        flash("Expense transaction recorded as Paid.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for('expenses.list_expenses'))

@expenses_bp.route('/delete/<expense_id>', methods=['POST'])
@login_required
@expenses_management_required
def delete_expense_route(expense_id):
    """
    Deletes an expense. Reverts supplier outstanding balance if paid.
    """
    try:
        delete_expense(expense_id, current_user.organization_id)
        flash("Expense entry successfully deleted.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for('expenses.list_expenses'))
