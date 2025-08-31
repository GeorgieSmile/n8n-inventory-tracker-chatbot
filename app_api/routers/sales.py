from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime
from sqlalchemy import or_, and_
from database import db_dependency
from models import sqlalchemy_models, request_models, response_models

router = APIRouter(
    prefix="/sales",
    tags=["Sales"]
)

@router.post("/", response_model=response_models.Sale, status_code=status.HTTP_201_CREATED)
def create_sale(sale: request_models.SaleCreate, db: db_dependency):
    """
    Create a new sale with multiple items.
    The total_amount is calculated by a database trigger.
    """

    sale.payment_method = sale.payment_method.capitalize()
    if sale.payment_method == 'Qr':
        sale.payment_method = 'QR'
    if sale.payment_method not in ['Cash', 'Card', 'QR']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="วิธีการชำระเงินไม่ถูกต้อง")
    # Create the sale record first, excluding items for now
    sale_data = sale.model_dump(exclude={"items"})
    
    # Total_amount will be handled by existing trigger
    sale_data["total_amount"] = 0  
    
    new_sale = sqlalchemy_models.SaleDB(**sale_data)
    db.add(new_sale)
    db.flush()  # Flush to get the new_sale.sale_id

    # Process each item
    for item in sale.items:
        # 1. Fetch the product to validate it AND get its price
        product = db.query(sqlalchemy_models.ProductDB).filter(
            sqlalchemy_models.ProductDB.product_id == item.product_id
        ).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {item.product_id} not found."
            )
        
        # 2. Determine the unit price
        item_unit_price = item.unit_price if item.unit_price is not None else product.price

        # 3. Create the sale item with the correct price
        sale_item = sqlalchemy_models.SaleItemDB(
            sale_id=new_sale.sale_id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item_unit_price,
            discount=item.discount
        )
        db.add(sale_item)
        
    db.commit()
    db.refresh(new_sale)
    return new_sale

@router.get("/", response_model=response_models.PaginatedResponse[response_models.Sale])
def get_all_sales(
    db: db_dependency,
    search_params: request_models.SaleSearchParams = Depends()
):
    """
    Retrieve all sales with pagination and search functionality.
    
    - **search**: Search in notes
    - **payment_method**: Filter by payment method (Cash, Card, QR)
    - **start_date/end_date**: Date range filtering (YYYY-MM-DD)
    - **page**: Page number (starts from 1)
    - **limit**: Items per page (max 100)
    """
    # Build base query
    query = db.query(sqlalchemy_models.SaleDB)
    
    # Apply search filters
    if search_params.search:
        search_term = f"%{search_params.search}%"
        query = query.filter(sqlalchemy_models.SaleDB.notes.ilike(search_term))
    
    if search_params.payment_method:
        query = query.filter(sqlalchemy_models.SaleDB.payment_method == search_params.payment_method)
    
    if search_params.start_date:
        try:
            start_date = datetime.strptime(search_params.start_date, "%Y-%m-%d").date()
            query = query.filter(sqlalchemy_models.SaleDB.sale_datetime >= start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")
    
    if search_params.end_date:
        try:
            end_date = datetime.strptime(search_params.end_date, "%Y-%m-%d").date()
            # Add one day to include the entire end date
            end_date = datetime.combine(end_date, datetime.max.time())
            query = query.filter(sqlalchemy_models.SaleDB.sale_datetime <= end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")
    
    # Get total count before pagination
    total = query.count()
    
    # Apply ordering and pagination
    sales = query.order_by(sqlalchemy_models.SaleDB.sale_datetime.desc())\
                 .offset((search_params.page - 1) * search_params.limit)\
                 .limit(search_params.limit)\
                 .all()
    
    if not sales and search_params.page == 1:
        raise HTTPException(status_code=404, detail="ไม่พบรายการขาย")
    
    # Calculate pagination metadata
    total_pages = (total + search_params.limit - 1) // search_params.limit
    
    return response_models.PaginatedResponse(
        items=sales,
        total=total,
        page=search_params.page,
        limit=search_params.limit,
        total_pages=total_pages,
        has_next=search_params.page < total_pages,
        has_prev=search_params.page > 1
    )

@router.get("/{sale_id}", response_model=response_models.Sale)
def get_sale_by_id(sale_id: int, db: db_dependency):
    """
    Retrieve a single sale by its ID, including all its items.
    """
    sale = db.query(sqlalchemy_models.SaleDB).filter(
        sqlalchemy_models.SaleDB.sale_id == sale_id
    ).first()
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการขายที่ต้องการ")
    return sale

@router.patch("/{sale_id}", response_model=response_models.Sale)
def update_sale(sale_id: int, sale_update: request_models.SaleUpdate, db: db_dependency):
    """
    Update a sale's main information (e.g., payment method, notes).
    This does not update the sale items.
    """
    sale = db.query(sqlalchemy_models.SaleDB).filter(
        sqlalchemy_models.SaleDB.sale_id == sale_id
    ).first()
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการขายที่ต้องการ Update")

    update_data = sale_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sale, key, value)
        
    db.commit()
    db.refresh(sale)
    return sale

@router.delete("/{sale_id}", status_code=status.HTTP_200_OK)
def delete_sale(sale_id: int, db: db_dependency):
    """
    Delete a sale and all its associated items.
    """
    sale = db.query(sqlalchemy_models.SaleDB).filter(
        sqlalchemy_models.SaleDB.sale_id == sale_id
    ).first()
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการขายที่ต้องการลบ")

    # The database's ON DELETE CASCADE will handle deleting the sale items
    db.delete(sale)
    db.commit()

    return {"detail": f"รายการขาย ID {sale_id} และรายการสินค้าขายที่เกี่ยวข้องทั้งหมดได้ถูกลบแล้ว."}

# Endpoints for Sale Items

@router.get("/items/{sale_item_id}", response_model=response_models.SaleItem)
def get_sale_items(sale_item_id: int, db: db_dependency):
    """
    Retrieve all items for a specific sale.
    """
    items = db.query(sqlalchemy_models.SaleItemDB).filter(
        sqlalchemy_models.SaleItemDB.sale_item_id == sale_item_id
    ).first()
    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการสินค้าสำหรับการขายนี้")
    return items

@router.post("/{sale_id}/items", response_model=response_models.SaleItem, status_code=status.HTTP_201_CREATED)
def add_sale_item(sale_id: int, item: request_models.SaleItemCreate, db: db_dependency):
    """
    Add a new item to an existing sale.
    """
    # Ensure the sale exists
    sale = db.query(sqlalchemy_models.SaleDB).filter(
        sqlalchemy_models.SaleDB.sale_id == sale_id
    ).first()
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการขายนี้")
    
    # Ensure the product exists
    product = db.query(sqlalchemy_models.ProductDB).filter(
        sqlalchemy_models.ProductDB.product_id == item.product_id
    ).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ไม่พบสินค้า ID {item.product_id}")

    # Prevent adding a duplicate product to the same sale
    existing_item = db.query(sqlalchemy_models.SaleItemDB).filter(
        sqlalchemy_models.SaleItemDB.sale_id == sale_id,
        sqlalchemy_models.SaleItemDB.product_id == item.product_id
    ).first()
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"สินค้า ID {item.product_id} มีอยู่แล้วในรายการขายนี้"
        )
    
    if item.unit_price is None:
        item.unit_price = product.price

    new_item = sqlalchemy_models.SaleItemDB(
        sale_id=sale_id,
        **item.model_dump()
    )
    db.add(new_item)
    # The database trigger will automatically update the sale's total_amount
    db.commit()
    db.refresh(new_item)
    return new_item

@router.patch("/{sale_id}/items/{item_id}", response_model=response_models.SaleItem)
def update_sale_item(sale_id: int, item_id: int, item_update: request_models.SaleItemUpdate, db: db_dependency):
    """
    Update a specific item in a sale.
    """
    sale_item = db.query(sqlalchemy_models.SaleItemDB).filter(
        sqlalchemy_models.SaleItemDB.sale_item_id == item_id,
        sqlalchemy_models.SaleItemDB.sale_id == sale_id
    ).first()
    if sale_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการสินค้าขายนี้")

    # If product_id is being updated, validate it
    if item_update.product_id is not None and item_update.product_id != sale_item.product_id:
        product = db.query(sqlalchemy_models.ProductDB).filter(
            sqlalchemy_models.ProductDB.product_id == item_update.product_id
        ).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"ไม่พบสินค้า ID {item_update.product_id} ที่ต้องการ Update."
            )
        # Check for duplicates
        existing_item = db.query(sqlalchemy_models.SaleItemDB).filter(
            sqlalchemy_models.SaleItemDB.sale_id == sale_id,
            sqlalchemy_models.SaleItemDB.product_id == item_update.product_id,
            sqlalchemy_models.SaleItemDB.sale_item_id != item_id
        ).first()
        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"สินค้า ID {item_update.product_id} มีอยู่แล้วในรายการขายนี้"
            )
            
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sale_item, key, value)
        
    # The database trigger will automatically update the sale's total_amount
    db.commit()
    db.refresh(sale_item)
    return sale_item

@router.delete("/{sale_id}/items/{item_id}", status_code=status.HTTP_200_OK)
def delete_sale_item(sale_id: int, item_id: int, db: db_dependency):
    """
    Delete a specific item from a sale.
    """
    sale_item = db.query(sqlalchemy_models.SaleItemDB).filter(
        sqlalchemy_models.SaleItemDB.sale_item_id == item_id,
        sqlalchemy_models.SaleItemDB.sale_id == sale_id
    ).first()
    if sale_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการสินค้าขายที่ต้องการลบ.")
        
    db.delete(sale_item)
    # The database trigger will automatically update the sale's total_amount
    db.commit()

    return {"detail": f"สินค้า ID {item_id} ได้ถูกลบออกจากรายการขาย ID {sale_id}."}