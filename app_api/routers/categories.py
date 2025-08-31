from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import db_dependency 
from models import sqlalchemy_models, request_models, response_models

# Create an APIRouter instance
router = APIRouter(
    prefix="/categories", 
    tags=["Categories"]   
)

@router.post("/", response_model=response_models.Category, status_code=status.HTTP_201_CREATED)
def create_category(category: request_models.CategoryCreate, db: db_dependency):
    """
    Create a new category.
    """
    db_category = db.query(sqlalchemy_models.CategoryDB).filter(sqlalchemy_models.CategoryDB.name == category.name).first()
    if db_category:
        raise HTTPException(status_code=400, detail="มีหมวดหมู่นี้อยู่แล้ว")
    
    new_category = sqlalchemy_models.CategoryDB(name=category.name)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@router.get("/", response_model=response_models.PaginatedResponse[response_models.Category])
def get_all_categories(
    db: db_dependency,
    search_params: request_models.CategorySearchParams = Depends()
):
    """
    Retrieve all categories with pagination and search functionality.

    - **search**: Search in category name
    - **page**: Page number (starts from 1)
    - **limit**: Items per page (max 100)
    """
    query = db.query(sqlalchemy_models.CategoryDB)

    # Apply search filter
    if search_params.search:
        search_term = f"%{search_params.search}%"
        query = query.filter(sqlalchemy_models.CategoryDB.name.ilike(search_term))

    total = query.count()

    categories = query.order_by(sqlalchemy_models.CategoryDB.category_id)\
        .offset((search_params.page - 1) * search_params.limit)\
        .limit(search_params.limit)\
        .all()

    if not categories and search_params.page == 1:
        raise HTTPException(status_code=404, detail="ไม่พบหมวดหมู่")

    total_pages = (total + search_params.limit - 1) // search_params.limit

    return response_models.PaginatedResponse(
        items=categories,
        total=total,
        page=search_params.page,
        limit=search_params.limit,
        total_pages=total_pages,
        has_next=search_params.page < total_pages,
        has_prev=search_params.page > 1
    )

@router.get("/{category_id}", response_model=response_models.Category)
def get_category_by_id(category_id: int, db: db_dependency):
    """
    Retrieve a single category by its ID.
    """
    db_category = db.query(sqlalchemy_models.CategoryDB).filter(sqlalchemy_models.CategoryDB.category_id == category_id).first()
    
    if db_category is None:
        raise HTTPException(status_code=404, detail="ไม่พบหมวดหมู่ที่ต้องการ")

    return db_category

@router.put("/{category_id}", response_model=response_models.Category)
def update_category(category_id: int, category_update: request_models.CategoryCreate, db: db_dependency):
    """
    Update a category's name.
    """
    db_category = db.query(sqlalchemy_models.CategoryDB).filter(sqlalchemy_models.CategoryDB.category_id == category_id).first()

    if db_category is None:
        raise HTTPException(status_code=404, detail="ไม่พบหมวดหมู่ที่ต้องการแก้ไข")

    # Check if the new name is already taken by another category
    existing_category_with_name = db.query(sqlalchemy_models.CategoryDB).filter(sqlalchemy_models.CategoryDB.name == category_update.name).first()
    if existing_category_with_name and existing_category_with_name.category_id != category_id:
        raise HTTPException(status_code=400, detail="มีหมวดหมู่นี้อยู่แล้ว")

    db_category.name = category_update.name
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
def delete_category(category_id: int, db: db_dependency):
    """
    Delete a category by its ID.
    """
    db_category = db.query(sqlalchemy_models.CategoryDB).filter(sqlalchemy_models.CategoryDB.category_id == category_id).first()

    if db_category is None:
        raise HTTPException(status_code=404, detail="ไม่พบหมวดหมู่ที่ต้องการลบ")

    db.delete(db_category)
    db.commit()

    return {"detail": f"หมวดหมู่ {db_category.name} ถูกลบเรียบร้อยแล้ว"}