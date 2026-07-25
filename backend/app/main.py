from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import test_connection, engine, get_session
from .models import Base, User
from . import schemas

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Create tables automatically in local dev for convenience
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/db-check")
async def db_check():
    try:
        await test_connection()
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.post("/users", response_model=schemas.UserRead)
async def create_user(user: schemas.UserCreate, session: AsyncSession = Depends(get_session)):
    new_user = User(email=user.email, hashed_password=user.password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

@app.get("/users", response_model=list[schemas.UserRead])
async def list_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users
