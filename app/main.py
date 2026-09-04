from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import client, init_db
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup: initialize database indexes
    await init_db()
    yield
    # Application shutdown: close database client connection
    await client.close()


app = FastAPI(
    title="FastAPI Security",
    lifespan=lifespan
)

app.include_router(users_router)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "FastAPI is running"
    }


@app.get("/health")
async def health():
    await client.admin.command("ping")
    return {
        "message": "DB is connected"
    }