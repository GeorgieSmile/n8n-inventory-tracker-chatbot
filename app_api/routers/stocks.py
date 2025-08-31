from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime
from database import db_dependency
from models import sqlalchemy_models, request_models, response_models
from sqlalchemy import or_, and_

router = APIRouter(
    prefix="/stock-in",
    tags=["Stock In"]
)

@router.post("/", response_model=response_models.StockIn, status_code=status.HTTP_201_CREATED)
def create_stock_in(stock_in: request_models.StockInCreate, db: db_dependency):
    """
    Create a new stock in entry with multiple items.
    """
    # Validate all products exist
    for item in stock_in.items:
        product = db.query(sqlalchemy_models.ProductDB).filter(
            sqlalchemy_models.ProductDB.product_id == item.product_id
        ).first()
        if not product:
            raise HTTPException(
                status_code=404, 
                detail=f"ไม่พบสินค้า ID: {item.product_id}"
            )
    
    # Create stock_in record using request model
    stock_in_data = stock_in.model_dump(exclude={"items"})
    stock_in_data["total_cost"] = 0  # Will be calculated by database trigger
    
    new_stock_in = sqlalchemy_models.StockInDB(**stock_in_data)
    db.add(new_stock_in)
    db.flush()  # Get the stock_in_id without committing
    
    # Create stock_in items
    for item in stock_in.items:
        stock_in_item = sqlalchemy_models.StockInItemDB(
            stock_in_id=new_stock_in.stock_in_id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_cost=item.unit_cost
        )
        db.add(stock_in_item)
    
    db.commit()
    db.refresh(new_stock_in)
    return new_stock_in

@router.get("/", response_model=response_models.PaginatedResponse[response_models.StockIn])
def get_all_stock_in(
    db: db_dependency,
    search_params: request_models.StockInSearchParams = Depends()
):
    """
    Retrieve all stock in records with pagination and search functionality.
    
    - **search**: Search in ref no. or notes
    - **start_date/end_date**: Date range filtering (YYYY-MM-DD)
    - **page**: Page number (starts from 1)
    - **limit**: Items per page (max 100)
    """
    # Build base query
    query = db.query(sqlalchemy_models.StockInDB)
    
    # Apply search filters
    if search_params.search:
        search_term = f"%{search_params.search}%"
        query = query.filter(
            or_(
                sqlalchemy_models.StockInDB.ref_no.ilike(search_term),
                sqlalchemy_models.StockInDB.notes.ilike(search_term)
            )
        )
    
    if search_params.start_date:
        try:
            start_date = datetime.strptime(search_params.start_date, "%Y-%m-%d").date()
            query = query.filter(sqlalchemy_models.StockInDB.stock_in_date >= start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")
    
    if search_params.end_date:
        try:
            end_date = datetime.strptime(search_params.end_date, "%Y-%m-%d").date()
            # Include the entire end date
            end_date = datetime.combine(end_date, datetime.max.time())
            query = query.filter(sqlalchemy_models.StockInDB.stock_in_date <= end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")
    
    # Get total count before pagination
    total = query.count()
    
    # Apply ordering and pagination
    stock_ins = query.order_by(sqlalchemy_models.StockInDB.stock_in_date.desc())\
                    .offset((search_params.page - 1) * search_params.limit)\
                    .limit(search_params.limit)\
                    .all()
    
    if not stock_ins and search_params.page == 1:
        raise HTTPException(status_code=404, detail="ไม่พบรายการสินค้าเข้า")
    
    # Calculate pagination metadata
    total_pages = (total + search_params.limit - 1) // search_params.limit
    
    return response_models.PaginatedResponse(
        items=stock_ins,
        total=total,
        page=search_params.page,
        limit=search_params.limit,
        total_pages=total_pages,
        has_next=search_params.page < total_pages,
        has_prev=search_params.page > 1
    )

@router.get("/{stock_in_id}", response_model=response_models.StockIn)
def get_stock_in_by_id(stock_in_id: int, db: db_dependency):
    """
    Retrieve a single stock in record by its ID with all items.
    """
    stock_in = db.query(sqlalchemy_models.StockInDB).filter(
        sqlalchemy_models.StockInDB.stock_in_id == stock_in_id
    ).first()
    if stock_in is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการสินค้าเข้าที่ต้องการ")
    return stock_in

@router.patch("/{stock_in_id}", response_model=response_models.StockIn)
def update_stock_in(stock_in_id: int, stock_in_update: request_models.StockInUpdate, db: db_dependency):
    """
    Update a stock in record's basic information (not items).
    """
    stock_in = db.query(sqlalchemy_models.StockInDB).filter(
        sqlalchemy_models.StockInDB.stock_in_id == stock_in_id
    ).first()
    if stock_in is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการสินค้าเข้าที่ต้องการ Update")
    
    # Update only the fields that are provided
    update_data = stock_in_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(stock_in, key, value)
    
    db.commit()
    db.refresh(stock_in)
    return stock_in

@router.delete("/{stock_in_id}", status_code=status.HTTP_200_OK)
def delete_stock_in(stock_in_id: int, db: db_dependency):
    """
    Delete a stock in record and all its items.
    """
    stock_in = db.query(sqlalchemy_models.StockInDB).filter(
        sqlalchemy_models.StockInDB.stock_in_id == stock_in_id
    ).first()
    if stock_in is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการสินค้าเข้าที่ต้องการลบ")
        
    # Due to CASCADE DELETE, stock_in_items will be automatically deleted
    db.delete(stock_in)
    db.commit()
    
    return {"detail": f"รายการสินค้าเข้า ID: {stock_in_id} และรายการสินค้าเข้าที่เกี่ยวข้องถูกลบเรียบร้อยแล้ว"}

# Stock In Items endpoints
@router.get("/items/{stock_in_item_id}", response_model=response_models.StockInItem)
def get_stock_in_items(stock_in_item_id: int, db: db_dependency):
    """
    Retrieve specific item in stock in record.
    """
    # Check if stock_in_item exists
    stock_in_item = db.query(sqlalchemy_models.StockInItemDB).filter(
        sqlalchemy_models.StockInItemDB.stock_in_item_id == stock_in_item_id
    ).first()
    if stock_in_item is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการสินค้าเข้า")
    
    items = db.query(sqlalchemy_models.StockInItemDB).filter(
        sqlalchemy_models.StockInItemDB.stock_in_item_id == stock_in_item_id
    ).first()
    return items

@router.post("/{stock_in_id}/items", response_model=response_models.StockInItem, status_code=status.HTTP_201_CREATED)
def add_stock_in_item(stock_in_id: int, item: request_models.StockInItemCreate, db: db_dependency):
    """
    Add a new item to an existing stock in record.
    """
    # Check if stock_in exists
    stock_in = db.query(sqlalchemy_models.StockInDB).filter(
        sqlalchemy_models.StockInDB.stock_in_id == stock_in_id
    ).first()
    if stock_in is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการสินค้าเข้า")
    
    # Check if product exists
    product = db.query(sqlalchemy_models.ProductDB).filter(
        sqlalchemy_models.ProductDB.product_id == item.product_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า ID: {item.product_id}")
    
    # Check if item already exists for this product in this stock_in
    existing_item = db.query(sqlalchemy_models.StockInItemDB).filter(
        sqlalchemy_models.StockInItemDB.stock_in_id == stock_in_id,
        sqlalchemy_models.StockInItemDB.product_id == item.product_id
    ).first()
    if existing_item:
        raise HTTPException(
            status_code=400, 
            detail=f"สินค้า ID {item.product_id} มีอยู่แล้วในรายการสินค้าเข้านี้"
        )
    
    # Create new stock_in item
    new_item = sqlalchemy_models.StockInItemDB(
        stock_in_id=stock_in_id,
        **item.model_dump()
    )
    db.add(new_item)
    
    # Database trigger will recalculate total_cost automatically
    db.commit()
    db.refresh(new_item)
    return new_item

@router.patch("/{stock_in_id}/items/{item_id}", response_model=response_models.StockInItem)
def update_stock_in_item(stock_in_id: int, item_id: int, item_update: request_models.StockInItemUpdate, db: db_dependency):
    """
    Update a specific stock in item.
    """
    # Check if stock_in item exists and belongs to the stock_in
    stock_in_item = db.query(sqlalchemy_models.StockInItemDB).filter(
        sqlalchemy_models.StockInItemDB.stock_in_item_id == item_id,
        sqlalchemy_models.StockInItemDB.stock_in_id == stock_in_id
    ).first()
    if stock_in_item is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการสินค้าในการนำเข้า")
    
    # If product_id is being updated, validate it exists and not duplicate
    if item_update.product_id is not None and item_update.product_id != stock_in_item.product_id:
        product = db.query(sqlalchemy_models.ProductDB).filter(
            sqlalchemy_models.ProductDB.product_id == item_update.product_id
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า ID: {item_update.product_id}")
        
        # Check for duplicate product in same stock_in (excluding current item)
        existing_item = db.query(sqlalchemy_models.StockInItemDB).filter(
            sqlalchemy_models.StockInItemDB.stock_in_id == stock_in_id,
            sqlalchemy_models.StockInItemDB.product_id == item_update.product_id,
            sqlalchemy_models.StockInItemDB.stock_in_item_id != item_id
        ).first()
        if existing_item:
            raise HTTPException(
                status_code=400, 
                detail=f"สินค้า ID {item_update.product_id} มีอยู่แล้วในรายการสินค้าเข้านี้"
            )
    
    # Update item
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(stock_in_item, key, value)
    
    # Database trigger will recalculate total_cost automatically
    db.commit()
    db.refresh(stock_in_item)
    return stock_in_item

@router.delete("/{stock_in_id}/items/{item_id}", status_code=status.HTTP_200_OK)
def delete_stock_in_item(stock_in_id: int, item_id: int, db: db_dependency):
    """
    Delete a specific stock in item.
    """
    # Check if stock_in item exists and belongs to the stock_in
    stock_in_item = db.query(sqlalchemy_models.StockInItemDB).filter(
        sqlalchemy_models.StockInItemDB.stock_in_item_id == item_id,
        sqlalchemy_models.StockInItemDB.stock_in_id == stock_in_id
    ).first()
    if stock_in_item is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการสินค้าในการนำเข้า")
    
    # Delete the item
    db.delete(stock_in_item)
    
    # Database trigger will recalculate total_cost automatically
    db.commit()
    
    return {"detail": f"รายการสินค้า ID {item_id} ถูกลบออกจากการนำเข้า ID {stock_in_id}เรียบร้อยแล้ว"}
