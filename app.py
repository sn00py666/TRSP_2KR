import re
import time
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
SESSION_COOKIE_MAX_AGE = 300
SESSION_REFRESH_AFTER = 180
signer = Signer(SECRET_KEY)
ACCEPT_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z]{2})?(?:,\s*[A-Za-z]{2,3}(?:-[A-Za-z]{2})?(?:;q=(?:0(?:\.\d{1,3})?|1(?:\.0{1,3})?))?)*$")


def build_session_token(user_id: str, last_activity_ts: int) -> str:
    payload = f"{user_id}.{last_activity_ts}"
    return signer.sign(payload.encode("utf-8")).decode("utf-8")


def parse_session_token(session_token: str) -> tuple[str, int] | None:
    try:
        payload = signer.unsign(session_token.encode("utf-8")).decode("utf-8")
    except BadSignature:
        return None

    parts = payload.split(".")
    if len(parts) != 2:
        return None

    user_id, ts_str = parts

    try:
        UUID(user_id)
        last_activity_ts = int(ts_str)
    except ValueError:
        return None

    return user_id, last_activity_ts


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
    now_ts = int(time.time())
    session_token = build_session_token(user_id, now_ts)
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
async def get_profile(response: Response, session_token: str | None = Cookie(default=None)):
    "Защищенная ручка профиля с проверкой подписи cookie session_token."
    if session_token is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Session expired"},
        )

    parsed_token = parse_session_token(session_token)
    if parsed_token is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid session"},
        )

    user_id, last_activity_ts = parsed_token
    now_ts = int(time.time())

    if last_activity_ts > now_ts:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid session"},
        )

    if user_id not in SESSION_STORE:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Session expired"},
        )

    elapsed = now_ts - last_activity_ts
    if elapsed >= SESSION_COOKIE_MAX_AGE:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Session expired"},
        )

    if SESSION_REFRESH_AFTER <= elapsed < SESSION_COOKIE_MAX_AGE:
        refreshed_token = build_session_token(user_id, now_ts)
        response.set_cookie(
            key="session_token",
            value=refreshed_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=SESSION_COOKIE_MAX_AGE,
        )

    username = SESSION_STORE[user_id]
    return {
        "user_id": user_id,
        "username": username,
        "full_name": "Demo User",
        "auth_method": "signed_cookie",
    }


@app.get("/user")
async def get_user(response: Response, session_token: str | None = Cookie(default=None)):
    "Совместимый alias для /profile."
    return await get_profile(response, session_token)


@app.get("/headers")
async def get_headers(request: Request):
    "Возвращает значения User-Agent и Accept-Language из запроса."
    user_agent = request.headers.get("User-Agent")
    accept_language = request.headers.get("Accept-Language")

    if not user_agent or not accept_language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Required headers are missing",
        )

    if ACCEPT_LANGUAGE_RE.fullmatch(accept_language) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Accept-Language format",
        )

    return {
        "User-Agent": user_agent,
        "Accept-Language": accept_language,
    }
