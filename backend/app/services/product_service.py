from app.repositories.product_repository import ProductRepository


class ProductService:

    @staticmethod
    def get_products(db):

        return ProductRepository.get_all(db)

    @staticmethod
    def get_product(
            db,
            product_id: int
    ):

        return ProductRepository.get_by_id(
            db,
            product_id
        )
