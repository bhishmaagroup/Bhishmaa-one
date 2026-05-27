from app.core.extensions import db
from app.models.crm import Customer, Supplier
from app.blueprints.crm.utils import clean_contact_name

# CUSTOMER SERVICES
def get_organization_customers(organization_id):
    return Customer.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).order_by(Customer.name).all()

def get_customer_by_id(customer_id, organization_id):
    return Customer.query.filter_by(
        id=customer_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()

def get_customer_by_phone_or_name(phone, name, organization_id):
    """
    Looks up a customer by phone first, then falls back to case-insensitive name match.
    """
    cust = None
    if phone:
        cust = Customer.query.filter_by(
            organization_id=organization_id,
            is_deleted=False,
            phone=phone
        ).first()
        
    if not cust and name:
        cust = Customer.query.filter(
            Customer.organization_id == organization_id,
            Customer.is_deleted == False,
            Customer.name.ilike(name.strip())
        ).first()
        
    return cust

def create_customer(organization_id, data):
    name = clean_contact_name(data.get('name'))
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    gstin = data.get('gstin', '').strip()
    state_code = data.get('state_code', '07').strip()
    address = data.get('address', '').strip()
    outstanding_balance = float(data.get('outstanding_balance') or 0.0)
    
    if not name:
        raise ValueError("Customer name is required.")
        
    customer = Customer(
        organization_id=organization_id,
        tenant_id=organization_id,
        name=name,
        phone=phone,
        email=email,
        gstin=gstin,
        state_code=state_code,
        address=address,
        outstanding_balance=outstanding_balance
    )
    
    db.session.add(customer)
    db.session.commit()
    return customer

def update_customer(customer_id, organization_id, data):
    customer = get_customer_by_id(customer_id, organization_id)
    if not customer:
        raise ValueError("Customer not found.")
        
    name = clean_contact_name(data.get('name'))
    if not name:
        raise ValueError("Customer name is required.")
        
    customer.name = name
    customer.phone = data.get('phone', '').strip()
    customer.email = data.get('email', '').strip()
    customer.gstin = data.get('gstin', '').strip()
    customer.state_code = data.get('state_code', '07').strip()
    customer.address = data.get('address', '').strip()
    
    if 'outstanding_balance' in data:
        customer.outstanding_balance = float(data.get('outstanding_balance') or 0.0)
        
    db.session.commit()
    return customer

def delete_customer(customer_id, organization_id):
    customer = get_customer_by_id(customer_id, organization_id)
    if not customer:
        raise ValueError("Customer not found.")
    customer.soft_delete()
    return True


# SUPPLIER SERVICES
def get_organization_suppliers(organization_id):
    return Supplier.query.filter_by(
        organization_id=organization_id,
        is_deleted=False
    ).order_by(Supplier.name).all()

def get_supplier_by_id(supplier_id, organization_id):
    return Supplier.query.filter_by(
        id=supplier_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()

def create_supplier(organization_id, data):
    name = clean_contact_name(data.get('name'))
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    gstin = data.get('gstin', '').strip()
    state_code = data.get('state_code', '07').strip()
    address = data.get('address', '').strip()
    outstanding_balance = float(data.get('outstanding_balance') or 0.0)
    
    if not name:
        raise ValueError("Supplier name is required.")
        
    supplier = Supplier(
        organization_id=organization_id,
        tenant_id=organization_id,
        name=name,
        phone=phone,
        email=email,
        gstin=gstin,
        state_code=state_code,
        address=address,
        outstanding_balance=outstanding_balance
    )
    
    db.session.add(supplier)
    db.session.commit()
    return supplier

def update_supplier(supplier_id, organization_id, data):
    supplier = get_supplier_by_id(supplier_id, organization_id)
    if not supplier:
        raise ValueError("Supplier not found.")
        
    name = clean_contact_name(data.get('name'))
    if not name:
        raise ValueError("Supplier name is required.")
        
    supplier.name = name
    supplier.phone = data.get('phone', '').strip()
    supplier.email = data.get('email', '').strip()
    supplier.gstin = data.get('gstin', '').strip()
    supplier.state_code = data.get('state_code', '07').strip()
    supplier.address = data.get('address', '').strip()
    
    if 'outstanding_balance' in data:
        supplier.outstanding_balance = float(data.get('outstanding_balance') or 0.0)
        
    db.session.commit()
    return supplier

def delete_supplier(supplier_id, organization_id):
    supplier = get_supplier_by_id(supplier_id, organization_id)
    if not supplier:
        raise ValueError("Supplier not found.")
    supplier.soft_delete()
    return True


# CROSS-MODULE INTEGRATION
def update_customer_balance_on_billing(organization_id, customer_name, customer_phone, unpaid_amount):
    """
    Links Billing checkout with CRM. Finds or creates the customer,
    then updates their outstanding balance with the unpaid invoice sum.
    """
    if not customer_name:
        return
        
    customer = get_customer_by_phone_or_name(customer_phone, customer_name, organization_id)
    
    from decimal import Decimal
    unpaid_decimal = Decimal(str(unpaid_amount))
    
    if not customer:
        # Auto-create Walk-in customer profile
        customer = Customer(
            organization_id=organization_id,
            tenant_id=organization_id,
            name=customer_name,
            phone=customer_phone,
            outstanding_balance=unpaid_decimal
        )
        db.session.add(customer)
    else:
        # Increment outstanding balance
        customer.outstanding_balance += unpaid_decimal
        
    db.session.commit()
