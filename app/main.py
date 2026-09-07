from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import client, create_indexes

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.otp import router as otp_router
from app.middleware import security_headers
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.rate_limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):

    # -----------------------------
    # Application startup
    # -----------------------------

    await client.admin.command("ping")

    print("Database connected")

    await create_indexes()

    print("Indexes created")

    yield

    # -----------------------------
    # Application shutdown
    # -----------------------------

    await client.close()

    print("Database connection closed")


app = FastAPI(
    title="FastAPI Security",
    lifespan=lifespan
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

# -----------------------------
# Routers
# -----------------------------

app.include_router(users_router)

app.include_router(auth_router)

app.include_router(otp_router)


# -----------------------------
# CORS
# -----------------------------

app.middleware("http")(security_headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Root
# -----------------------------

@app.get("/")
async def root():

    return {
        "message": "FastAPI is running"
    }


# -----------------------------
# Health
# -----------------------------

@app.get("/health")
async def health():

    await client.admin.command("ping")

    return {
        "message": "DB is connected"
    }