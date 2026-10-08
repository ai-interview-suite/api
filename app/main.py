from fastapi import FastAPI
from app.config import settings
from app.routers import interview, auth

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(auth.router)
app.include_router(interview.router)

@app.get("/")
def health_check():
    return {
        "message": "AI Interview Service is running!"
    }