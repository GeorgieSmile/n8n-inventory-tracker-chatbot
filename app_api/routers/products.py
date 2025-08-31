from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import or_, and_
from typing import List
from database import db_dependency
from models import sqlalchemy_models, request_models, response_models

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

@router.post("/", response_model=response_models.Product, status_code=status.HTTP_201_CREATED)
def create_product(product: request_models.ProductCreate, db: db_dependency):
    """
    Create a new product.
    """
    # If category_id is provided, check if it exists
    if product.category_id is not None:
        category = db.query(sqlalchemy_models.CategoryDB).filter(sqlalchemy_models.CategoryDB.category_id == product.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail=f"ไม่พบหมวดหมู่ ID: {product.category_id}")
        
    # Check if SKU already exists
    if product.sku:
        existing_product = db.query(sqlalchemy_models.ProductDB).filter(sqlalchemy_models.ProductDB.sku == product.sku).first()
        if existing_product:
            raise HTTPException(status_code=400, detail=f"มีสินค้าที่มี SKU '{product.sku}' นี้อยู่แล้ว")

    new_product = sqlalchemy_models.ProductDB(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@router.get("/", response_model=response_models.PaginatedResponse[response_models.Product])
def get_all_products(
    db: db_dependency,
    search_params: request_models.ProductSearchParams = Depends()
):
    """
    Retrieve all products with pagination and search functionality.
    
    - **search**: Search in product name or SKU
    - **category_id**: Filter by specific category
    - **min_price/max_price**: Price range filtering
    - **page**: Page number (starts from 1)
    - **limit**: Items per page (max 100)
    """
    # Build base query
    query = db.query(sqlalchemy_models.ProductDB)
    
    # Apply search filters
    if search_params.search:
        search_term = f"%{search_params.search}%"
        query = query.filter(
            or_(
                sqlalchemy_models.ProductDB.name.ilike(search_term),
                sqlalchemy_models.ProductDB.sku.ilike(search_term)
            )
        )
    
    if search_params.category_id:
        query = query.filter(sqlalchemy_models.ProductDB.category_id == search_params.category_id)
    
    if search_params.min_price is not None:
        query = query.filter(sqlalchemy_models.ProductDB.price >= search_params.min_price)
    
    if search_params.max_price is not None:
        query = query.filter(sqlalchemy_models.ProductDB.price <= search_params.max_price)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply ordering and pagination
    products = query.order_by(sqlalchemy_models.ProductDB.product_id)\
                   .offset((search_params.page - 1) * search_params.limit)\
                   .limit(search_params.limit)\
                   .all()
    
    if not products and search_params.page == 1:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    
    # Calculate pagination metadata
    total_pages = (total + search_params.limit - 1) // search_params.limit
    
    return response_models.PaginatedResponse(
        items=products,
        total=total,
        page=search_params.page,
        limit=search_params.limit,
        total_pages=total_pages,
        has_next=search_params.page < total_pages,
        has_prev=search_params.page > 1
    )

@router.get("/{product_id}", response_model=response_models.Product)
def get_product_by_id(product_id: int, db: db_dependency):
    """
    Retrieve a single product by its ID.
    """
    db_product = db.query(sqlalchemy_models.ProductDB).filter(sqlalchemy_models.ProductDB.product_id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้าที่ต้องการ")
    return db_product

@router.patch("/{product_id}", response_model=response_models.Product)
def update_product(product_id: int, product_update: request_models.ProductUpdate, db: db_dependency):
    """
    Update a product's details partially.
    """
    db_product = db.query(sqlalchemy_models.ProductDB).filter(sqlalchemy_models.ProductDB.product_id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้าที่ต้องการ Update")

    # If category_id is provided, check if it exists
    if product_update.category_id is not None:
        category = db.query(sqlalchemy_models.CategoryDB).filter(sqlalchemy_models.CategoryDB.category_id == product_update.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail=f"ไม่พบหมวดหมู่ ID: {product_update.category_id}")

    # If SKU is provided, check for conflict
    if product_update.sku:
        existing_sku = db.query(sqlalchemy_models.ProductDB).filter(
            sqlalchemy_models.ProductDB.sku == product_update.sku,
            sqlalchemy_models.ProductDB.product_id != product_id
        ).first()
        if existing_sku:
            raise HTTPException(status_code=400, detail=f"มีสินค้าอื่นใช้ SKU '{product_update.sku}' นี้แล้ว")

    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(product_id: int, db: db_dependency):
    """
    Delete a product by its ID.
    """
    db_product = db.query(sqlalchemy_models.ProductDB).filter(sqlalchemy_models.ProductDB.product_id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้าที่ต้องการลบ")

    db.delete(db_product)
    db.commit()

    return {"detail": f"{db_product.name} ถูกลบเรียบร้อยแล้ว"}

