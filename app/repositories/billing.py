from app.repositories.base import BaseRepository
from app.models.billing import Invoice


class BillingRepository(BaseRepository):
    """
    Data repository for Invoice and billing-related database operations.
    """
    def __init__(self):
        super().__init__(Invoice)

    def get_by_invoice_number(self, invoice_number):
        """Finds an invoice by its invoice number within the tenant context."""
        return self._get_base_query().filter_by(invoice_number=invoice_number).first()

    def get_unpaid_invoices(self):
        """Retrieves all unpaid or partially paid invoices for the active tenant."""
        return self._get_base_query().filter(
            Invoice.payment_status != 'Paid'
        ).all()
