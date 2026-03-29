from fastapi import FastAPI

from models import UserCreate

app = FastAPI()


@app.post("/create_user")
def create_user(user: UserCreate):
    "Ручка для создания пользователя"
    return user


