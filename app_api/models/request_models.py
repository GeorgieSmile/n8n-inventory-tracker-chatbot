from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CategoryCreate(BaseModel):
    name: str

class ProductCreate(BaseModel):
    name: str
    category_id: Optional[int] = None
    sku: Optional[str] = None
    price: float
    reorder_level: int = 10

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    category_id: Optional[int] = None
    sku: Optional[str] = Field(None, max_length=64)
    price: Optional[float] = Field(None, gt=0)
    reorder_level: Optional[int] = None

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int
    unit_price: Optional[float] = None
    discount: float = 0

class SaleCreate(BaseModel):
    sale_datetime: Optional[datetime] = None
    payment_method: str  # 'Cash', 'Card', or 'QR'
    notes: Optional[str] = None
    items: List[SaleItemCreate]

class SaleUpdate(BaseModel):
    sale_datetime: Optional[datetime] = None
    payment_method: Optional[str] = Field(None, pattern="^(Cash|Card|QR)$")
    notes: Optional[str] = Field(None, max_length=255)

class SaleItemUpdate(BaseModel):
    product_id: Optional[int] = None
    quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, gt=0)
    discount: Optional[float] = Field(None, ge=0)

class StockInItemCreate(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float

class StockInCreate(BaseModel):
    stock_in_date: Optional[datetime] = None
    ref_no: Optional[str] = None
    notes: Optional[str] = None
    items: List[StockInItemCreate]

class StockInUpdate(BaseModel):
    ref_no: Optional[str] = Field(None, max_length=80)
    stock_in_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=255)

class StockInItemUpdate(BaseModel):
    product_id: Optional[int] = None
    quantity: Optional[int] = Field(None, gt=0)
    unit_cost: Optional[float] = Field(None, gt=0)

class InventoryMovementUpdate(BaseModel):
    movement_type: str = None

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    limit: int = Field(default=10, ge=1, le=100, description="Items per page (max 100)")
    
class ProductSearchParams(PaginationParams):
    search: Optional[str] = Field(default=None, description="Search in product name or SKU")
    category_id: Optional[int] = Field(default=None, description="Filter by category ID")
    min_price: Optional[float] = Field(default=None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(default=None, ge=0, description="Maximum price filter")

class SaleSearchParams(PaginationParams):
    search: Optional[str] = Field(default=None, description="Search in notes")
    payment_method: Optional[str] = Field(default=None, description="Filter by payment method")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")

class StockInSearchParams(PaginationParams):
    search: Optional[str] = Field(default=None, description="Search in ref no. or notes")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")

class InventoryMovementSearchParams(PaginationParams):
    product_id: Optional[int] = Field(None, description="Filter by product ID")
    movement_type: Optional[str] = Field(None, description="Filter by movement type (OPENING, STOCK_IN, SALE)")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")

class ProductStockSearchParams(PaginationParams):
    search: Optional[str] = Field(default=None, description="Search in product name")
    productFilter: Optional[str] = Field(default=None, description="Filter products 1. All product (Leave Blank) 2. Needs Restock products ('r') 3. Does not need restock ('nr')")

class ProfitabilityReportSearchParams(PaginationParams):
    search: Optional[str] = Field(default=None, description="Search in product name")
    product_id: Optional[int] = Field(default=None, description="Filter by specific product ID")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")

class CategorySearchParams(PaginationParams):
    search: Optional[str] = Field(default=None, description="Search in category name")