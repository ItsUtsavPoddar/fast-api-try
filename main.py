from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from database import connect_to_mongo, close_mongo_connection
from routers import surveys_router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title="Survey Generator API",
    description="Backend API for Dynamic Survey Generator - replaces localStorage with MongoDB",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(surveys_router)

@app.get("/")
async def root():
    return {
        "message": "Survey Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "description": "MongoDB-backed survey storage API"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
