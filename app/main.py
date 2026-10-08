from fastapi import FastAPI
from app.config import settings
from app.routers.interview import router as interview_router

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(interview_router)

@app.get("/")
def health_check():
    return {
        "message": "AI Interview Service is running!"
    }