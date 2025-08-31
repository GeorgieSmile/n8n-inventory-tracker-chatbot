from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class CategoryDB(Base):
    __tablename__ = "category"
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    
    # Relationship
    products = relationship("ProductDB", back_populates="category")

class ProductDB(Base):
    __tablename__ = "product"
    
    product_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    category_id = Column(Integer, ForeignKey("category.category_id"), nullable=True)
    sku = Column(String(64), nullable=True, unique=True)
    price = Column(DECIMAL(10, 2), nullable=False)
    reorder_level = Column(Integer, nullable=False, default=10)
    
    # Relationships
    category = relationship("CategoryDB", back_populates="products")
    sale_items = relationship("SaleItemDB", back_populates="product")
    stock_in_items = relationship("StockInItemDB", back_populates="product")
    inventory_movements = relationship("InventoryMovementDB", back_populates="product")

class SaleDB(Base):
    __tablename__ = "sale"
    
    sale_id = Column(Integer, primary_key=True, autoincrement=True)
    sale_datetime = Column(DateTime, nullable=False, default=func.current_timestamp())
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(Enum('Cash', 'Card', 'QR'), nullable=False)
    notes = Column(String(255), nullable=True)
    
    # Relationship
    items = relationship(
        "SaleItemDB", 
        back_populates="sale",
        cascade="all, delete-orphan",  
        passive_deletes=True
        )

class SaleItemDB(Base):
    __tablename__ = "sale_item"
    
    sale_item_id = Column(Integer, primary_key=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sale.sale_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    discount = Column(DECIMAL(10, 2), nullable=False, default=0)
    
    # Relationships
    sale = relationship("SaleDB", back_populates="items")
    product = relationship("ProductDB", back_populates="sale_items")

class StockInDB(Base):
    __tablename__ = "stock_in"
    
    stock_in_id = Column(Integer, primary_key=True, autoincrement=True)
    ref_no = Column(String(80), nullable=True)
    stock_in_date = Column(DateTime, nullable=False, default=func.current_timestamp())
    total_cost = Column(DECIMAL(12, 2), nullable=False, default=0)
    notes = Column(String(255), nullable=True)
    
    # Relationship
    items = relationship(
        "StockInItemDB", 
        back_populates="stock_in",
        cascade="all, delete-orphan",  
        passive_deletes=True 
    )

class StockInItemDB(Base):
    __tablename__ = "stock_in_item"
    
    stock_in_item_id = Column(Integer, primary_key=True, autoincrement=True)
    stock_in_id = Column(Integer, ForeignKey("stock_in.stock_in_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(DECIMAL(10, 2), nullable=False)
    
    # Relationships
    stock_in = relationship("StockInDB", back_populates="items")
    product = relationship("ProductDB", back_populates="stock_in_items")

class InventoryMovementDB(Base):
    __tablename__ = "inventory_movement"
    
    movement_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.product_id"), nullable=False)
    movement_type = Column(Enum('OPENING', 'STOCK_IN', 'SALE'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(DECIMAL(10, 2), nullable=True)
    sale_price = Column(DECIMAL(10, 2), nullable=True)
    sale_item_id = Column(Integer, ForeignKey("sale_item.sale_item_id"), nullable=True)
    stock_in_item_id = Column(Integer, ForeignKey("stock_in_item.stock_in_item_id"), nullable=True)
    movement_date = Column(DateTime, nullable=False, default=func.current_timestamp())
    
    # Relationships
    product = relationship("ProductDB", back_populates="inventory_movements")


class ProductStockView(Base):
    __tablename__ = "v_product_stock"
    
    product_id = Column(Integer, primary_key=True)
    name = Column(String(150))
    price = Column(DECIMAL(10, 2))
    reorder_level = Column(Integer)
    stock_on_hand = Column(Integer)
    needs_restock = Column(Integer)  # 0 or 1

class ProfitabilityReportView(Base):
    __tablename__ = "v_profitability_report"
    
    sale_item_id = Column(Integer, primary_key=True)
    sale_id = Column(Integer)
    sale_datetime = Column(DateTime)
    product_id = Column(Integer)
    product_name = Column(String(150))
    quantity = Column(Integer)
    unit_price = Column(DECIMAL(10, 2))
    discount = Column(DECIMAL(10, 2))
    total_revenue = Column(DECIMAL(22, 4))
    average_cost_at_sale = Column(DECIMAL(22, 4))
    total_cogs = Column(DECIMAL(22, 4))
    gross_profit = Column(DECIMAL(22, 4))