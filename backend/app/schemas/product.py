from pydantic import BaseModel


class ProductResponse(BaseModel):

    id: int

    name: str

    description: str

    category: str

    stock: int

    price: float