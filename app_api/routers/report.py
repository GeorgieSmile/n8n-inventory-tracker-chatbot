from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from database import db_dependency
from models import sqlalchemy_models, response_models, request_models
from datetime import timedelta, datetime
from sqlalchemy import or_, func

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)

@router.get("/product-stock", response_model=response_models.PaginatedResponse[response_models.ProductStock])
def get_product_stock_report(
    db: db_dependency,
    search_params: request_models.ProductStockSearchParams = Depends()
):
    """
    Retrieve the current product stock data from the v_product_stock view with search and pagination.
    """
    # Base query from the view
    query = db.query(sqlalchemy_models.ProductStockView)

    # Apply filters
    if search_params.productFilter == "r":
        query = query.filter(sqlalchemy_models.ProductStockView.needs_restock == 1)
    elif search_params.productFilter == "nr":
        query = query.filter(sqlalchemy_models.ProductStockView.needs_restock == 0)
    
    if search_params.search:
        # Search in product name (case-insensitive)
        search_filter = f"%{search_params.search}%"
        query = query.filter(
            sqlalchemy_models.ProductStockView.name.ilike(search_filter)
        )

    # Get total count before pagination
    total = query.count()
    
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบข้อมูลสต็อกสินค้า"
        )

    # Calculate pagination
    total_pages = (total + search_params.limit - 1) // search_params.limit
    
    # Apply pagination and ordering
    stock_data = query.order_by(sqlalchemy_models.ProductStockView.name)\
                     .offset((search_params.page - 1) * search_params.limit)\
                     .limit(search_params.limit)\
                     .all()

    return response_models.PaginatedResponse(
        items=stock_data,
        total=total,
        page=search_params.page,
        limit=search_params.limit,
        total_pages=total_pages,
        has_next=search_params.page < total_pages,
        has_prev=search_params.page > 1
    )


@router.get("/profitability", response_model=response_models.PaginatedResponse[response_models.ProfitabilityReport])
def get_profitability_report(
    db: db_dependency,
    search_params: request_models.ProfitabilityReportSearchParams = Depends()
):
    """
    Retrieve the profit and loss report for each sold product with search and pagination.
    """
    query = db.query(sqlalchemy_models.ProfitabilityReportView)

    # Apply date filters
    if search_params.start_date:
        try:
            start_date = datetime.strptime(search_params.start_date, "%Y-%m-%d").date()
            query = query.filter(sqlalchemy_models.ProfitabilityReportView.sale_datetime >= start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")

    if search_params.end_date:
        try:        
            end_date = datetime.strptime(search_params.end_date, "%Y-%m-%d").date()
            # Add one day to include the entire end date
            end_date = datetime.combine(end_date, datetime.max.time())
            query = query.filter(sqlalchemy_models.ProfitabilityReportView.sale_datetime <= end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")
    
    # Apply search filter
    if search_params.search:
        # Search in product name (case-insensitive)
        search_filter = f"%{search_params.search}%"
        query = query.filter(
            sqlalchemy_models.ProfitabilityReportView.product_name.ilike(search_filter)
        )
    
    # Apply product filter
    if search_params.product_id:
        query = query.filter(sqlalchemy_models.ProfitabilityReportView.product_id == search_params.product_id)

    # Get total count before pagination
    total = query.count()
    
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบข้อมูลกำไรขาดทุนตามเงื่อนไขที่ระบุ"
        )

    # Calculate pagination    
    total_pages = (total + search_params.limit - 1) // search_params.limit
    
    # Apply pagination and ordering (latest sales first)
    report_data = query.order_by(sqlalchemy_models.ProfitabilityReportView.sale_datetime.desc())\
                       .offset((search_params.page - 1) * search_params.limit)\
                       .limit(search_params.limit)\
                       .all()

    return response_models.PaginatedResponse(
        items=report_data,
        total=total,
        page=search_params.page,
        limit=search_params.limit,
        total_pages=total_pages,
        has_next=search_params.page < total_pages,
        has_prev=search_params.page > 1
    )

@router.get("/product-stock/summary", response_model=response_models.ProductStockSummary)
def get_product_stock_summary(
    db: db_dependency,
    needs_restock_only: bool = Query(False, description="Filter only products that need restocking")
):
    """
    Get summary statistics for product stock report.
    Scope follows `needs_restock_only`. Percent is computed within the same scope.
    """
    base_q = db.query(sqlalchemy_models.ProductStockView)

    # Scope: all products or only those needing restock
    if needs_restock_only:
        base_q = base_q.filter(sqlalchemy_models.ProductStockView.needs_restock == 1)

    # Totals within scope
    total_products = base_q.count()

    total_stock_value = (
        base_q.with_entities(
            func.sum(
                sqlalchemy_models.ProductStockView.stock_on_hand
                * sqlalchemy_models.ProductStockView.price
            )
        ).scalar() or 0
    )

    # Count needing restock within the same scope
    products_needing_restock = base_q.filter(
        sqlalchemy_models.ProductStockView.needs_restock == 1
    ).count()

    restock_percentage = round(
        (products_needing_restock / max(total_products, 1)) * 100, 2
    )

    return response_models.ProductStockSummary(
        total_products=total_products,
        total_stock_value=float(total_stock_value),
        products_needing_restock=products_needing_restock,
        restock_percentage=restock_percentage,
    )


@router.get("/profitability/summary", response_model=response_models.ProfitabilitySummary)
def get_profitability_summary(
    db: db_dependency,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get summary statistics for profitability report.
    """
    q = db.query(sqlalchemy_models.ProfitabilityReportView)

    # Apply date filters
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            q = q.filter(sqlalchemy_models.ProfitabilityReportView.sale_datetime >= start_date_obj)
        except ValueError:
            raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            end_date_obj = datetime.combine(end_date_obj, datetime.max.time())
            q = q.filter(sqlalchemy_models.ProfitabilityReportView.sale_datetime <= end_date_obj)
        except ValueError:
            raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")

    total_sales = q.count()

    if total_sales == 0:
        return response_models.ProfitabilitySummary(
            total_sales=0,
            total_revenue=0.0,
            total_cogs=0.0,
            total_gross_profit=0.0,
            average_profit_margin=0.0,
            most_profitable_product=None
        )

    totals = q.with_entities(
        func.sum(sqlalchemy_models.ProfitabilityReportView.total_revenue).label('total_revenue'),
        func.sum(sqlalchemy_models.ProfitabilityReportView.total_cogs).label('total_cogs'),
        func.sum(sqlalchemy_models.ProfitabilityReportView.gross_profit).label('total_gross_profit')
    ).first()

    total_revenue = float(totals.total_revenue or 0)
    total_cogs = float(totals.total_cogs or 0)
    total_gross_profit = float(totals.total_gross_profit or 0)

    average_profit_margin = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    top_products_query = q.with_entities(
        sqlalchemy_models.ProfitabilityReportView.product_name,
        func.sum(sqlalchemy_models.ProfitabilityReportView.gross_profit).label('total_profit')
    ).group_by(
        sqlalchemy_models.ProfitabilityReportView.product_id,
        sqlalchemy_models.ProfitabilityReportView.product_name
    ).order_by(
        func.sum(sqlalchemy_models.ProfitabilityReportView.gross_profit).desc()
    ).limit(3).all()

    # Create a list of Pydantic models from the query result
    top_profitable_products_list = []
    for product in top_products_query:
        top_profitable_products_list.append(
            response_models.MostProfitableProduct(
                name=product.product_name,
                total_profit=float(product.total_profit)
            )
        )

    return response_models.ProfitabilitySummary(
        total_sales=total_sales,
        total_revenue=total_revenue,
        total_cogs=total_cogs,
        total_gross_profit=total_gross_profit,
        average_profit_margin=round(average_profit_margin, 2),
        top_profitable_products=top_profitable_products_list
    )
