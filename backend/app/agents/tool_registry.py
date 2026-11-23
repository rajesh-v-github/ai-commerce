class ToolRegistry:

    def __init__(
        self,
        product_service,
        order_service
    ):
        self.product_service = (
            product_service
        )

        self.order_service = (
            order_service
        )

    def search_products(
            self,
            query
    ):
        pass

    def get_order_status(
            self,
            order_id
    ):
        pass