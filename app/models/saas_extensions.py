import datetime
from app.core.extensions import db
from app.models.core import TenantBase, Base, UUIDType

class FinancialYear(TenantBase):
    """
    Represents tenant-scoped financial years (accounting periods).
    """
    __tablename__ = 'financial_years'

    name = db.Column(db.String(50), nullable=False)  # e.g., "FY 2025-26"
    code = db.Column(db.String(10), nullable=False)  # e.g., "2526"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Unique constraint per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'code', name='uq_tenant_fy_code'),
    )

    def __repr__(self):
        return f"<FinancialYear {self.name} ({self.code}) - Tenant: {self.tenant_id}>"


class InvoiceSequence(TenantBase):
    """
    Tracks sequential numbers for invoice and payment generation.
    Supports tenant-wise and optionally branch-wise sequences.
    """
    __tablename__ = 'invoice_sequences'

    financial_year = db.Column(db.String(10), nullable=False, index=True)  # e.g., "2526"
    prefix = db.Column(db.String(20), nullable=False, default='INV')  # e.g., "INV", "PAY", "MED"
    current_value = db.Column(db.Integer, default=0, nullable=False)

    # Unique constraint: only one counter per tenant, branch, financial year, and prefix
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'branch_id', 'financial_year', 'prefix', name='uq_tenant_branch_fy_prefix'),
    )

    def __repr__(self):
        return f"<InvoiceSequence {self.prefix} FY:{self.financial_year} Val:{self.current_value}>"


class PosTerminal(TenantBase):
    """
    Represents multiple physical/virtual POS terminals/devices in a branch.
    """
    __tablename__ = 'pos_terminals'

    name = db.Column(db.String(100), nullable=False)
    terminal_code = db.Column(db.String(50), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'terminal_code', name='uq_tenant_terminal_code'),
    )

    def __repr__(self):
        return f"<PosTerminal {self.name} ({self.terminal_code})>"


class TaxConfig(TenantBase):
    """
    Core tax configuration rules per tenant.
    """
    __tablename__ = 'tax_configurations'

    name = db.Column(db.String(100), nullable=False)  # e.g. GST 18%, Exempt
    cgst_rate = db.Column(db.Numeric(5, 2), default=0.0, nullable=False)
    sgst_rate = db.Column(db.Numeric(5, 2), default=0.0, nullable=False)
    igst_rate = db.Column(db.Numeric(5, 2), default=0.0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    def __repr__(self):
        return f"<TaxConfig {self.name} - CGST: {self.cgst_rate}% SGST: {self.sgst_rate}%>"


class Setting(TenantBase):
    """
    General tenant-scoped settings store.
    """
    __tablename__ = 'tenant_settings'

    key = db.Column(db.String(100), nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'key', name='uq_tenant_setting_key'),
    )

    def __repr__(self):
        return f"<Setting {self.key} = {self.value}>"


class OfflineSyncQueue(TenantBase):
    """
    Stores local/offline operations to sync to PostgreSQL cloud.
    """
    __tablename__ = 'offline_sync_queue'

    model_name = db.Column(db.String(50), nullable=False, index=True)  # e.g. 'Invoice'
    record_id = db.Column(db.String(36), nullable=False, index=True)  # UUID of record
    action = db.Column(db.String(10), nullable=False)  # INSERT, UPDATE, DELETE
    payload = db.Column(db.Text, nullable=False)  # JSON-encoded data
    attempts = db.Column(db.Integer, default=0, nullable=False)
    last_error = db.Column(db.Text, nullable=True)
    synced = db.Column(db.Boolean, default=False, nullable=False, index=True)

    def __repr__(self):
        return f"<OfflineSyncQueue {self.model_name}:{self.record_id} Action:{self.action} Synced:{self.synced}>"
