from pydantic import BaseModel
from typing import Optional


class CatalogQuery(BaseModel):
    oem: Optional[str] = None
    segment: Optional[str] = None
    model: Optional[str] = None
    variant_type: Optional[str] = None
    year: Optional[int] = None
    fuel_type: Optional[str] = None
    product: Optional[str] = None
    part_number: Optional[str] = None