import datetime
from app.models.billing import Invoice, Payment

from app.models.core import Organization

PAYMENT_PREFIX = 'PAY'

def generate_invoice_number(organization_id):
    """
    Generates a sequential invoice number for the organization tenant.
    Format: INV-[SUBDOMAIN]-YYYYMMDD-XXXX where XXXX is a 4-digit zero-padded index.
    """
    org = Organization.query.get(organization_id)
    org_prefix = org.subdomain.upper() if org else "SYS"
    today_str = datetime.date.today().strftime('%Y%m%d')
    prefix = f"INV-{org_prefix}-{today_str}-"
    
    # Query count of invoices today for this tenant
    count = Invoice.query.filter(
        Invoice.organization_id == organization_id,
        Invoice.invoice_number.like(f"{prefix}%")
    ).count()
    
    seq = count + 1
    return f"{prefix}{seq:04d}"


def generate_payment_number(organization_id):
    """
    Generates a sequential payment number for the organization tenant.
    Format: PAY-[SUBDOMAIN]-YYYYMMDD-XXXX where XXXX is a 4-digit zero-padded index.
    """
    org = Organization.query.get(organization_id)
    org_prefix = org.subdomain.upper() if org else "SYS"
    today_str = datetime.date.today().strftime('%Y%m%d')
    prefix = f"{PAYMENT_PREFIX}-{org_prefix}-{today_str}-"
    
    count = Payment.query.filter(
        Payment.organization_id == organization_id,
        Payment.payment_number.like(f"{prefix}%")
    ).count()
    seq = count + 1
    return f"{prefix}{seq:04d}"


def calculate_item_gst(org_state_code, customer_state_code, price, qty, gst_rate):
    """
    Performs GST split calculations based on state matches.
    If org state matches customer state: CGST + SGST (half rate each).
    Else: IGST (full rate).
    """
    price = float(price or 0.0)
    qty = float(qty or 0.0)
    gst_rate = float(gst_rate or 0.0)
    
    subtotal = price * qty
    gst_amount = subtotal * (gst_rate / 100.0)
    
    cgst = 0.0
    sgst = 0.0
    igst = 0.0
    
    # Clean string state codes
    org_state = str(org_state_code or '').strip()
    cust_state = str(customer_state_code or '').strip()
    
    if org_state == cust_state:
        # Same state: CGST & SGST split
        cgst = gst_amount / 2.0
        sgst = gst_amount / 2.0
    else:
        # Different state: IGST full
        igst = gst_amount
        
    line_total = subtotal + gst_amount
    
    return {
        'subtotal': round(subtotal, 2),
        'cgst': round(cgst, 2),
        'sgst': round(sgst, 2),
        'igst': round(igst, 2),
        'line_total': round(line_total, 2)
    }
