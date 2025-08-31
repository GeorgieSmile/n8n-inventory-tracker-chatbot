from fastapi import FastAPI
from database import Base, engine
from routers import categories, products, stocks, sales, inventories, report
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(stocks.router)
app.include_router(sales.router)
app.include_router(inventories.router)
app.include_router(report.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Inventory and Sales API"}


    