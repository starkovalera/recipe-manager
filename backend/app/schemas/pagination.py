from app.schemas.base import CamelModel


class PaginatedOutMixin(CamelModel):
    total: int
    limit: int
    offset: int
