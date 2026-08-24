import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/forest_guard")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
NODE_OFFLINE_MINUTES = int(os.getenv("NODE_OFFLINE_MINUTES", "5"))
FUSION_WINDOW_SECONDS = int(os.getenv("FUSION_WINDOW_SECONDS", "30"))
