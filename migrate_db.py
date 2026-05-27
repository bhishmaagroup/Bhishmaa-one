import os
import sys
import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run import app, db
from app.services.sequence import get_financial_year

def run_migration():
    print("Starting database migration...")
    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        # Step 1: Read data from invoices_old / invoices if they exist
        invoices_data = []
        print("Reading invoices...")
        try:
            cursor.execute("SELECT id, invoice_number, invoice_date, due_date, register_session_id, customer_id, customer_name, customer_phone, customer_gstin, customer_state_code, customer_address, sub_total, cgst, sgst, igst, discount_amount, discount_percentage, shipping_amount, total_amount, payment_mode, payment_status, amount_paid, status, notes, terms_conditions, created_by_id, updated_by_id, organization_id, tenant_id, branch_id, created_at, updated_at, is_deleted FROM invoices_old")
            invoices_data = cursor.fetchall()
            print(f"Loaded {len(invoices_data)} invoices from invoices_old.")
        except Exception:
            try:
                cursor.execute("SELECT id, invoice_number, invoice_date, due_date, register_session_id, customer_id, customer_name, customer_phone, customer_gstin, customer_state_code, customer_address, sub_total, cgst, sgst, igst, discount_amount, discount_percentage, shipping_amount, total_amount, payment_mode, payment_status, amount_paid, status, notes, terms_conditions, created_by_id, updated_by_id, organization_id, tenant_id, branch_id, created_at, updated_at, is_deleted FROM invoices")
                invoices_data = cursor.fetchall()
                print(f"Loaded {len(invoices_data)} invoices from invoices.")
            except Exception as e:
                print(f"Could not load invoices: {e}")

        # Step 2: Read data from payments_old / payments if they exist
        payments_data = []
        print("Reading payments...")
        try:
            cursor.execute("SELECT id, payment_number, payment_date, amount, payment_method, reference_number, notes, received_by_id, organization_id, tenant_id, branch_id, created_at, updated_at, is_deleted, invoice_id FROM payments_old")
            payments_data = cursor.fetchall()
            print(f"Loaded {len(payments_data)} payments from payments_old.")
        except Exception:
            try:
                cursor.execute("SELECT id, payment_number, payment_date, amount, payment_method, reference_number, notes, received_by_id, organization_id, tenant_id, branch_id, created_at, updated_at, is_deleted, invoice_id FROM payments")
                payments_data = cursor.fetchall()
                print(f"Loaded {len(payments_data)} payments from payments.")
            except Exception as e:
                print(f"Could not load payments: {e}")

        # Step 3: Drop all old and temporary tables to clean up indexes
        print("Dropping tables to clear indexes...")
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("DROP TABLE IF EXISTS payments")
        cursor.execute("DROP TABLE IF EXISTS invoices")
        cursor.execute("DROP TABLE IF EXISTS payments_old")
        cursor.execute("DROP TABLE IF EXISTS invoices_old")
        conn.commit()

        # Step 4: Recreate all tables via db.create_all()
        print("Creating new database schema and tables...")
        db.create_all()

        # Step 5: Restore data from memory
        print("Restoring invoices and payments...")
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        for inv in invoices_data:
            inv_date = None
            if inv[2]:
                if isinstance(inv[2], str):
                    try:
                        inv_date = datetime.datetime.strptime(inv[2].split()[0], '%Y-%m-%d').date()
                    except ValueError:
                        inv_date = datetime.date.today()
                else:
                    inv_date = inv[2]
            
            fy = get_financial_year(inv_date)

            cursor.execute("""
                INSERT INTO invoices (
                    id, invoice_number, financial_year, invoice_date, due_date, 
                    register_session_id, customer_id, customer_name, customer_phone, 
                    customer_gstin, customer_state_code, customer_address, sub_total, 
                    cgst, sgst, igst, discount_amount, discount_percentage, 
                    shipping_amount, total_amount, payment_mode, payment_status, 
                    amount_paid, status, notes, terms_conditions, created_by_id, 
                    updated_by_id, organization_id, tenant_id, branch_id, 
                    created_at, updated_at, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv[0], inv[1], fy, inv[2], inv[3],
                inv[4], inv[5], inv[6], inv[7],
                inv[8], inv[9], inv[10], inv[11],
                inv[12], inv[13], inv[14], inv[15], inv[16],
                inv[17], inv[18], inv[19], inv[20],
                inv[21], inv[22], inv[23], inv[24], inv[25],
                inv[26], inv[27], inv[28], inv[29],
                inv[30], inv[31], inv[32]
            ))

        for pay in payments_data:
            cursor.execute("""
                INSERT INTO payments (
                    id, payment_number, payment_date, amount, payment_method, 
                    reference_number, notes, received_by_id, organization_id, 
                    tenant_id, branch_id, created_at, updated_at, is_deleted, invoice_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pay[0], pay[1], pay[2], pay[3], pay[4],
                pay[5], pay[6], pay[7], pay[8],
                pay[9], pay[10], pay[11], pay[12], pay[13], pay[14]
            ))

        conn.commit()

        # Step 6: Enable foreign keys
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()

        print("Migration complete!")

if __name__ == '__main__':
    run_migration()
