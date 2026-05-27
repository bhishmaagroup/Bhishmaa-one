import datetime
from sqlalchemy.exc import IntegrityError
from app.core.extensions import db
from app.models.saas_extensions import InvoiceSequence
from app.models.core import Branch

def get_financial_year(date_val=None):
    """
    Calculates the financial year code in format 'YY-YY' e.g. '2526'.
    """
    if not date_val:
        date_val = datetime.date.today()
    
    year = date_val.year
    month = date_val.month
    
    if month >= 4:
        fy_start = year
        fy_end = year + 1
    else:
        fy_start = year - 1
        fy_end = year
        
    start_str = str(fy_start)[-2:]
    end_str = str(fy_end)[-2:]
    return f"{start_str}{end_str}"


def generate_next_invoice_number(tenant_id, branch_id=None, prefix='INV', date_val=None):
    """
    Transaction-safe concurrent-safe generation of the next invoice number.
    Format: prefix-fy-branch_code-sequence (e.g. INV-2526-LKO-000001)
    """
    if not date_val:
        date_val = datetime.date.today()
        
    fy = get_financial_year(date_val)
    
    # 1. Resolve branch prefix/code if branch_id is present
    branch_code = ""
    if branch_id:
        branch = Branch.query.get(branch_id)
        if branch:
            # Clean up the code to be short and alphanumeric
            branch_code = "".join(c for c in branch.code if c.isalnum()).upper()
            
    # 2. Query sequence row or create atomically
    seq = InvoiceSequence.query.filter_by(
        tenant_id=tenant_id,
        branch_id=branch_id,
        financial_year=fy,
        prefix=prefix
    ).first()
    
    if not seq:
        seq = InvoiceSequence(
            organization_id=tenant_id,
            tenant_id=tenant_id,
            branch_id=branch_id,
            financial_year=fy,
            prefix=prefix,
            current_value=0
        )
        db.session.add(seq)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            # Retry load in case it was created concurrently
            seq = InvoiceSequence.query.filter_by(
                tenant_id=tenant_id,
                branch_id=branch_id,
                financial_year=fy,
                prefix=prefix
            ).first()
            if not seq:
                raise RuntimeError("Failed to initialize invoice sequence counter.")
                
    # 3. Perform atomic increment via database update statement
    db.session.query(InvoiceSequence).filter(InvoiceSequence.id == seq.id).update(
        {InvoiceSequence.current_value: InvoiceSequence.current_value + 1}
    )
    db.session.flush()
    db.session.refresh(seq)
    
    val = seq.current_value
    
    # 4. Construct formatted output
    if branch_code:
        return f"{prefix}-{fy}-{branch_code}-{val:06d}"
    return f"{prefix}-{fy}-{val:06d}"


def generate_next_payment_number(tenant_id, prefix='PAY', date_val=None):
    """
    Concurrent-safe generation of the next payment receipt number.
    Format: prefix-fy-sequence (e.g. PAY-2526-000001)
    """
    if not date_val:
        date_val = datetime.date.today()
        
    fy = get_financial_year(date_val)
    
    # 1. Query sequence row or create atomically
    seq = InvoiceSequence.query.filter_by(
        tenant_id=tenant_id,
        branch_id=None,
        financial_year=fy,
        prefix=prefix
    ).first()
    
    if not seq:
        seq = InvoiceSequence(
            organization_id=tenant_id,
            tenant_id=tenant_id,
            branch_id=None,
            financial_year=fy,
            prefix=prefix,
            current_value=0
        )
        db.session.add(seq)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            seq = InvoiceSequence.query.filter_by(
                tenant_id=tenant_id,
                branch_id=None,
                financial_year=fy,
                prefix=prefix
            ).first()
            if not seq:
                raise RuntimeError("Failed to initialize payment sequence counter.")
                
    # 2. Atomic increment
    db.session.query(InvoiceSequence).filter(InvoiceSequence.id == seq.id).update(
        {InvoiceSequence.current_value: InvoiceSequence.current_value + 1}
    )
    db.session.flush()
    db.session.refresh(seq)
    
    val = seq.current_value
    return f"{prefix}-{fy}-{val:06d}"
