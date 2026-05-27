from app.repositories.base import BaseRepository
from app.models.inventory import Product, BranchStock


class InventoryRepository(BaseRepository):
    """
    Data repository for Product and Inventory-related database operations.
    """
    def __init__(self):
        super().__init__(Product)

    def get_by_sku(self, sku):
        """Finds a product by SKU within the tenant context."""
        return self._get_base_query().filter_by(sku=sku).first()

    def get_by_barcode(self, barcode):
        """Finds a product by barcode value within the tenant context."""
        return self._get_base_query().filter_by(barcode=barcode).first()

    def get_branch_stock(self, branch_id, product_id):
        """Finds BranchStock record for product and branch."""
        # Note: Since BranchStock is also organization-scoped, we query it directly
        return BranchStock.query.filter_by(
            branch_id=branch_id,
            product_id=product_id
        ).first()
