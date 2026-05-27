import datetime
from decimal import Decimal
from sqlalchemy import func
from app.models.billing import Invoice, InvoiceItem
from app.models.expenses import Expense
from app.models.hrm import SalarySlip
from app.blueprints.expenses.constants import EXPENSE_PAID
from app.blueprints.hrm.constants import PAYROLL_PAID

def get_sales_audit_data(organization_id, start_date, end_date):
    """
    Aggregates invoice details over a specified date range.
    """
    invoices = Invoice.query.filter(
        Invoice.organization_id == organization_id,
        func.date(Invoice.created_at) >= start_date,
        func.date(Invoice.created_at) <= end_date,
        Invoice.is_deleted == False
    ).all()
    
    subtotal = Decimal('0.00')
    cgst = Decimal('0.00')
    sgst = Decimal('0.00')
    igst = Decimal('0.00')
    discount = Decimal('0.00')
    total = Decimal('0.00')
    
    for inv in invoices:
        subtotal += inv.sub_total
        cgst += inv.cgst
        sgst += inv.sgst
        igst += inv.igst
        discount += Decimal(str(inv.discount))
        total += inv.total_amount
        
    return {
        'invoice_count': len(invoices),
        'subtotal': float(subtotal),
        'cgst': float(cgst),
        'sgst': float(sgst),
        'igst': float(igst),
        'total_tax': float(cgst + sgst + igst),
        'discount': float(discount),
        'total_sales': float(total)
    }

def get_gst_filing_data(organization_id, start_date, end_date):
    """
    Compiles GSTR-1 style compliance summaries for B2B and B2C sales.
    """
    invoices = Invoice.query.filter(
        Invoice.organization_id == organization_id,
        func.date(Invoice.created_at) >= start_date,
        func.date(Invoice.created_at) <= end_date,
        Invoice.is_deleted == False
    ).all()
    
    b2b_map = {} # Key: (gstin, state_code, rate) -> {taxable, cgst, sgst, igst}
    b2c_map = {} # Key: (state_code, rate) -> {taxable, cgst, sgst, igst}
    
    for inv in invoices:
        is_b2b = bool(inv.customer_gstin and inv.customer_gstin.strip())
        
        for item in inv.items:
            rate = float(item.gst_rate)
            qty = Decimal(str(item.quantity))
            price = Decimal(str(item.unit_price))
            taxable_val = qty * price
            
            cgst = item.cgst_amount
            sgst = item.sgst_amount
            igst = item.igst_amount
            
            if is_b2b:
                key = (inv.customer_gstin.strip().upper(), inv.customer_state_code, rate)
                if key not in b2b_map:
                    b2b_map[key] = {'taxable': Decimal('0.00'), 'cgst': Decimal('0.00'), 'sgst': Decimal('0.00'), 'igst': Decimal('0.00')}
                b2b_map[key]['taxable'] += taxable_val
                b2b_map[key]['cgst'] += cgst
                b2b_map[key]['sgst'] += sgst
                b2b_map[key]['igst'] += igst
            else:
                key = (inv.customer_state_code, rate)
                if key not in b2c_map:
                    b2c_map[key] = {'taxable': Decimal('0.00'), 'cgst': Decimal('0.00'), 'sgst': Decimal('0.00'), 'igst': Decimal('0.00')}
                b2c_map[key]['taxable'] += taxable_val
                b2c_map[key]['cgst'] += cgst
                b2c_map[key]['sgst'] += sgst
                b2c_map[key]['igst'] += igst
                
    # Format B2B results
    b2b_list = []
    for (gstin, state, rate), vals in b2b_map.items():
        b2b_list.append({
            'gstin': gstin,
            'state_code': state,
            'gst_rate': rate,
            'taxable_value': float(vals['taxable']),
            'cgst': float(vals['cgst']),
            'sgst': float(vals['sgst']),
            'igst': float(vals['igst']),
            'total_tax': float(vals['cgst'] + vals['sgst'] + vals['igst'])
        })
        
    # Format B2C results
    b2c_list = []
    for (state, rate), vals in b2c_map.items():
        b2c_list.append({
            'state_code': state,
            'gst_rate': rate,
            'taxable_value': float(vals['taxable']),
            'cgst': float(vals['cgst']),
            'sgst': float(vals['sgst']),
            'igst': float(vals['igst']),
            'total_tax': float(vals['cgst'] + vals['sgst'] + vals['igst'])
        })
        
    return {
        'b2b_schedules': b2b_list,
        'b2c_schedules': b2c_list
    }

def get_profit_loss_sheet(organization_id, start_date, end_date):
    """
    Compiles income and expenditure balance data sheet, factoring in discounts and unpaid losses.
    """
    # 1. Total Revenues (sales invoices total)
    invoices = Invoice.query.filter(
        Invoice.organization_id == organization_id,
        func.date(Invoice.created_at) >= start_date,
        func.date(Invoice.created_at) <= end_date,
        Invoice.is_deleted == False
    ).order_by(Invoice.created_at.desc()).all()
    
    gross_revenue = Decimal('0.00')
    total_discounts = Decimal('0.00')
    unpaid_receivables = Decimal('0.00')
    realized_revenue = Decimal('0.00')
    
    for inv in invoices:
        # Gross revenue before discount
        inv_gross = inv.sub_total + inv.cgst + inv.sgst + inv.igst
        gross_revenue += inv_gross
        total_discounts += inv.discount_amount
        
        pending = inv.total_amount - inv.amount_paid
        if pending > 0:
            unpaid_receivables += pending
            
        realized_revenue += inv.amount_paid

    # 2. Expenses Paid (outflows paid)
    expenses = Expense.query.filter(
        Expense.organization_id == organization_id,
        Expense.date >= start_date,
        Expense.date <= end_date,
        Expense.status == EXPENSE_PAID,
        Expense.is_deleted == False
    ).order_by(Expense.date.desc()).all()
    expenses_total = sum(exp.amount for exp in expenses)
    
    # 3. Payroll Paid (salary slips paid)
    slips = SalarySlip.query.filter(
        SalarySlip.organization_id == organization_id,
        SalarySlip.payment_date >= start_date,
        SalarySlip.payment_date <= end_date,
        SalarySlip.status == PAYROLL_PAID,
        SalarySlip.is_deleted == False
    ).order_by(SalarySlip.payment_date.desc()).all()
    payroll_total = sum(slip.net_salary for slip in slips)
    
    total_outflows_and_losses = expenses_total + payroll_total + total_discounts + unpaid_receivables
    net_profit = gross_revenue - total_outflows_and_losses
    
    return {
        'gross_revenue': float(gross_revenue),
        'discounts': float(total_discounts),
        'unpaid_loss': float(unpaid_receivables),
        'realized_revenue': float(realized_revenue),
        'expenses': float(expenses_total),
        'payroll': float(payroll_total),
        'total_outflows': float(expenses_total + payroll_total),
        'total_outflows_and_losses': float(total_outflows_and_losses),
        'net_profit': float(net_profit),
        'invoices_list': invoices,
        'expenses_list': expenses,
        'payroll_list': slips
    }
