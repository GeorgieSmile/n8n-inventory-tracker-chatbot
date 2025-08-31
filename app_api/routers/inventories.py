from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime
from database import db_dependency
from models import sqlalchemy_models, request_models, response_models

router = APIRouter(
    prefix="/inventory-movements",
    tags=["Inventory Movements"]
)

@router.get("/", response_model=response_models.PaginatedResponse[response_models.InventoryMovement])
def get_all_inventory_movements(
    db: db_dependency,
    search_params: request_models.InventoryMovementSearchParams = Depends()
):
    """
    Retrieve all inventory movements with pagination and filtering.
    """
    # Start with base query
    query = db.query(sqlalchemy_models.InventoryMovementDB)
    
    # Apply filters
    if search_params.product_id:
        query = query.filter(sqlalchemy_models.InventoryMovementDB.product_id == search_params.product_id)
        
    if search_params.movement_type:
        # Validate movement_type
        allowed_types = {'OPENING', 'STOCK_IN', 'SALE'}
        if search_params.movement_type.upper() not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ประเภท movement_type ไม่ถูกต้อง ค่าที่อนุญาตคือ: {', '.join(allowed_types)}"
            )
        query = query.filter(sqlalchemy_models.InventoryMovementDB.movement_type == search_params.movement_type.upper())
    
    # Date filtering
    if search_params.start_date:
        try:
            start_datetime = datetime.strptime(search_params.start_date, "%Y-%m-%d")
            query = query.filter(sqlalchemy_models.InventoryMovementDB.movement_date >= start_datetime)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="รูปแบบวันที่เริ่มต้นไม่ถูกต้อง ใช้รูปแบบ YYYY-MM-DD"
            )
    
    if search_params.end_date:
        try:
            end_datetime = datetime.strptime(search_params.end_date, "%Y-%m-%d")
            # Add 23:59:59 to include the entire end date
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
            query = query.filter(sqlalchemy_models.InventoryMovementDB.movement_date <= end_datetime)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="รูปแบบวันที่สิ้นสุดไม่ถูกต้อง ใช้รูปแบบ YYYY-MM-DD"
            )
    
    # Get total count before pagination
    total = query.count()
    
    # Apply ordering and pagination
    movements = query.order_by(
        sqlalchemy_models.InventoryMovementDB.movement_date.desc()
    ).offset(
        (search_params.page - 1) * search_params.limit
    ).limit(search_params.limit).all()
    
    if not movements and search_params.page == 1:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการเคลื่อนไหวสินค้าที่ระบุ")

    # Calculate pagination info
    total_pages = (total + search_params.limit - 1) // search_params.limit
    
    
    return response_models.PaginatedResponse(
        items=movements,
        total=total,
        page=search_params.page,
        limit=search_params.limit,
        total_pages=total_pages,
        has_next=search_params.page < total_pages,
        has_prev=search_params.page > 1
    )



@router.get("/{movement_id}", response_model=response_models.InventoryMovement)
def get_inventory_movement_by_id(movement_id: int, db: db_dependency):
    """
    Retrieve a single inventory movement by its ID.
    """
    movement = db.query(sqlalchemy_models.InventoryMovementDB).filter(
        sqlalchemy_models.InventoryMovementDB.movement_id == movement_id
    ).first()
    
    if movement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบข้อมูลการเคลื่อนไหวสินค้าที่ระบุ"
        )
        
    return movement


@router.patch("/{movement_id}", response_model=response_models.InventoryMovement)
def update_inventory_movement_type(movement_id: int, movement_update: request_models.InventoryMovementUpdate, db: db_dependency):
    """
    Update only the movement_type of an existing inventory movement.
    """
    # 1. Find the movement
    movement_db = db.query(sqlalchemy_models.InventoryMovementDB).filter(
        sqlalchemy_models.InventoryMovementDB.movement_id == movement_id
    ).first()
    
    if not movement_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบข้อมูลการเคลื่อนไหวสินค้าที่มี ID {movement_id}"
        )
    
    # 2. Update only movement_type
    if movement_update.movement_type:
        allowed_types = {'OPENING', 'STOCK_IN', 'SALE'}
        if movement_update.movement_type.upper() not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ประเภท movement_type ไม่ถูกต้อง ค่าที่อนุญาตคือ: {', '.join(allowed_types)}"
            )
        movement_db.movement_type = movement_update.movement_type.upper()

    db.commit()
    db.refresh(movement_db)
    
    return movement_db
