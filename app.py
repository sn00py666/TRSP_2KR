from uuid import UUID, uuid4

from fastapi import (
    Cookie,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, Signer

from models import UserCreate
from products import sample_products

app = FastAPI()


VALID_USERS = {
    "user123": "password123",
}
SESSION_STORE: dict[str, str] = {}
SECRET_KEY = "dev-super-secret-key"
SESSION_COOKIE_MAX_AGE = 3600
signer = Signer(SECRET_KEY)


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


@app.post("/login")
async def login(
    request: Request,
    response: Response,
):
    "Ручка логина. Поддерживает JSON и form-data/x-www-form-urlencoded."
    username: str | None = None
    password: str | None = None

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        raw_username = payload.get("username") if isinstance(payload, dict) else None
        raw_password = payload.get("password") if isinstance(payload, dict) else None
        username = raw_username if isinstance(raw_username, str) else None
        password = raw_password if isinstance(raw_password, str) else None
    else:
        form_data = await request.form()
        raw_username = form_data.get("username")
        raw_password = form_data.get("password")
        username = raw_username if isinstance(raw_username, str) else None
        password = raw_password if isinstance(raw_password, str) else None

    if not username or not password or VALID_USERS.get(username) != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user_id = str(uuid4())
    session_token = signer.sign(user_id.encode("utf-8")).decode("utf-8")
    SESSION_STORE[user_id] = username
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_COOKIE_MAX_AGE,
    )

    return {"message": "Login successful"}


@app.get("/profile")
async def get_profile(session_token: str | None = Cookie(default=None)):
    "Защищенная ручка профиля с проверкой подписи cookie session_token."
    if session_token is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Unauthorized"},
        )

    try:
        user_id = signer.unsign(session_token.encode("utf-8")).decode("utf-8")
    except BadSignature:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Unauthorized"},
        )

    try:
        UUID(user_id)
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Unauthorized"},
        )

    if user_id not in SESSION_STORE:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Unauthorized"},
        )

    username = SESSION_STORE[user_id]
    return {
        "user_id": user_id,
        "username": username,
        "full_name": "Demo User",
        "auth_method": "signed_cookie",
    }
