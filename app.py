from fastapi import FastAPI, HTTPException, Query

from models import UserCreate
from products import sample_products

app = FastAPI()


@app.post("/create_user")
def create_user(user: UserCreate):
    "Ручка для создания пользователя"
    return user


@app.get("/product/{product_id}")
async def get_product(product_id: int):
    "Ручка для получения информации о продукте по ID"
    for product in sample_products:
        if product["product_id"] == product_id:
            return product

    raise HTTPException(status_code=404, detail="Product not found")


@app.get("/products/search")
async def search_products(
    keyword: str = Query(..., min_length=1),
    category: str | None = None,
    limit: int = Query(default=10, ge=1),
):
    "Ручка для поиска продуктов по ключевому слову, категории и лимиту"
    keyword_lower = keyword.lower()

    filtered_products = []
    for product in sample_products:
        is_keyword_match = keyword_lower in product["name"].lower()
        is_category_match = category is None or product["category"].lower() == category.lower()

        if is_keyword_match and is_category_match:
            filtered_products.append(product)

    return filtered_products[:limit]