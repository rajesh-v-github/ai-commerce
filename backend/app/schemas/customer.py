from pydantic import BaseModel


class CustomerSearchRequest(BaseModel):
    search: str
